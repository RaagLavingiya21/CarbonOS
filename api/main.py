"""FastAPI application entrypoint for the production backend migration."""

from __future__ import annotations

import logging
import os
import re
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.middleware.auth import SupabaseAuthMiddleware
from api.models.schemas import HealthResponse
from api.routes import (
    advisor,
    analyzer,
    chat,
    copilot,
    factors,
    gap_analyzer,
    org,
    panels,
    public,
    requests,
    rollup,
    scenarios,
    scope1,
    scope2_calc,
    scope2_eac,
    scope2_ingestion,
    scope2_landlord,
    scope2_reports,
    scope2_sites,
    scope2_targets,
    scope3_inventory,
    scope3_obligations,
    scope3_questionnaire,
    scope3_targets,
    shares,
)

logger = logging.getLogger("api.request")
logging.basicConfig(level=logging.INFO)

_DEV_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)

# Localhost dev (any port) plus all Vercel deployments for this project:
# the production alias and per-branch/per-commit preview URLs (e.g.
# carbon-os-git-<branch>-<team>.vercel.app). Auth is via Bearer token, not
# cookies, so a broad vercel.app match is safe here.
_CORS_ORIGIN_REGEX = re.compile(
    r"http://(localhost|127\.0\.0\.1):\d+"
    r"|https://[a-z0-9-]+\.vercel\.app"
)


def _cors_origins() -> list[str]:
    """Allowed browser origins: FRONTEND_URL in production, localhost for dev."""
    origins = list(_DEV_ORIGINS)
    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if frontend_url and frontend_url not in origins:
        origins.append(frontend_url)
    return origins


def _origin_allowed(origin: str) -> bool:
    """Whether a browser Origin is permitted (explicit list or regex)."""
    return origin in _cors_origins() or bool(_CORS_ORIGIN_REGEX.fullmatch(origin))


def _cors_headers(request: Request) -> dict[str, str]:
    """Manual CORS headers for error responses (see unhandled_exception_handler)."""
    headers: dict[str, str] = {}
    origin = request.headers.get("origin")
    if origin and _origin_allowed(origin):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
    return headers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(
    title="Product Carbon Footprint Analyzer API",
    description=(
        "REST API for BOM parsing, emission factor matching, footprint calculation, "
        "advisor chat, gap analysis, and supplier engagement workflows."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(SupabaseAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=_CORS_ORIGIN_REGEX.pattern,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return unhandled errors as JSON with CORS headers so the browser
    sees the real message.

    A catch-all Exception handler runs inside Starlette's
    ServerErrorMiddleware, which sits OUTSIDE CORSMiddleware, so the 500 it
    produces would otherwise lack CORS headers and the browser would mask
    the real error as an "Access-Control-Allow-Origin" failure. We attach
    the CORS headers manually here, mirroring the configured allow rules.
    """
    headers = _cors_headers(request)

    # Transient network failures reaching Supabase (auth verification or a
    # database call, both over httpx) are retryable infrastructure blips, not
    # server bugs. Surface them as 503 so the client can show a "retry" prompt
    # instead of a generic "internal server error".
    if isinstance(exc, httpx.TransportError):
        logger.warning(
            "Upstream connection error on %s %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": "A required service is temporarily unreachable. Please retry in a moment."
            },
            headers=headers,
        )

    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
        headers=headers,
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(analyzer.router)
app.include_router(factors.router)
app.include_router(rollup.router)
app.include_router(shares.router)
app.include_router(public.router)
app.include_router(requests.router)
app.include_router(advisor.router)
app.include_router(gap_analyzer.router)
app.include_router(copilot.router)
app.include_router(chat.router)
app.include_router(panels.router)
app.include_router(org.router)
app.include_router(scenarios.router)
app.include_router(scope1.router)
# Scope 3 lane — ships dark behind NEXT_PUBLIC_SCOPE3_ENABLED (nav hidden until GA).
app.include_router(scope3_inventory.router)
app.include_router(scope3_obligations.router)
app.include_router(scope3_questionnaire.router)
app.include_router(scope3_targets.router)

# Scope 2 ("Grid") module — isolated; shares only auth + app instance.
app.include_router(scope2_sites.router)
app.include_router(scope2_ingestion.router)
app.include_router(scope2_calc.router)
app.include_router(scope2_eac.router)
app.include_router(scope2_landlord.router)
app.include_router(scope2_reports.router)
app.include_router(scope2_targets.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")

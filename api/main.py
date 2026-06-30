"""FastAPI application entrypoint for the production backend migration."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.middleware.auth import SupabaseAuthMiddleware
from api.models.schemas import HealthResponse
from api.routes import advisor, analyzer, chat, copilot, gap_analyzer, org, panels

logger = logging.getLogger("api.request")
logging.basicConfig(level=logging.INFO)

_DEV_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def _cors_origins() -> list[str]:
    """Allowed browser origins: FRONTEND_URL in production, localhost for dev."""
    origins = list(_DEV_ORIGINS)
    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if frontend_url and frontend_url not in origins:
        origins.append(frontend_url)
    return origins


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
    # Allow localhost dev (any port) and all Vercel deployments for this
    # project: the production alias plus per-branch/per-commit preview URLs
    # (e.g. carbon-os-git-<branch>-<team>.vercel.app). Auth is via Bearer
    # token, not cookies, so a broad vercel.app match is safe here.
    allow_origin_regex=(
        r"http://(localhost|127\.0\.0\.1):\d+"
        r"|https://[a-z0-9-]+\.vercel\.app"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return unhandled errors as JSON so the browser sees a real message.

    Without this, a crash bubbles up to Starlette's ServerErrorMiddleware
    (outside CORSMiddleware), so the 500 lacks CORS headers and the browser
    masks it as an "Access-Control-Allow-Origin" failure. Returning a
    JSONResponse here keeps the response inside the CORS layer.
    """
    logger.exception(
        "Unhandled error on %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
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
app.include_router(advisor.router)
app.include_router(gap_analyzer.router)
app.include_router(copilot.router)
app.include_router(chat.router)
app.include_router(panels.router)
app.include_router(org.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")

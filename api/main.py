"""FastAPI application entrypoint for the production backend migration."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.auth import SupabaseAuthMiddleware
from api.models.schemas import HealthResponse
from api.routes import advisor, analyzer, copilot, gap_analyzer

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")

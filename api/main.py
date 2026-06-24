"""FastAPI application entrypoint for the production backend migration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.models.schemas import HealthResponse
from api.routes import advisor, analyzer, copilot, gap_analyzer
from db.copilot_store import init_copilot_db
from db.store import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    init_copilot_db()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyzer.router)
app.include_router(advisor.router)
app.include_router(gap_analyzer.router)
app.include_router(copilot.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")

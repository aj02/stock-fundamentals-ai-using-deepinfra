"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import DISCLAIMER, get_settings
from app.core.db import dispose_engine
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    log = structlog.get_logger(__name__)
    log.info(
        "backend.startup",
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
    )
    try:
        yield
    finally:
        log.info("backend.shutdown")
        await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="fundamentals-ai",
        summary="Multi-agent fundamental analysis for Indian equities (NSE/BSE).",
        description=(
            f"**{DISCLAIMER}**\n\n"
            "See README and ARCHITECTURE.md in the repository root."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    # Permissive CORS for the showcase. The Next.js app and backend live on
    # different host ports during local development; in docker-compose they
    # share a network but the browser still issues from localhost:3000.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()

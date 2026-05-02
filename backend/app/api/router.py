"""Top-level FastAPI router. Sub-routers register here as we build them."""

from __future__ import annotations

from fastapi import APIRouter

from app.api import agents, analyze, health, tickers, ws

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(tickers.router)
api_router.include_router(analyze.router)
api_router.include_router(ws.router)
api_router.include_router(agents.router)

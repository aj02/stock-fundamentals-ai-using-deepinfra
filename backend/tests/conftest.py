"""Pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

# Set a placeholder API key BEFORE app modules are imported. Tests that call
# the Financials Agent override the model with TestModel, so this key is
# never actually used to talk to Anthropic — but `build_model` rejects an
# empty key on principle, and that check fires at agent-construction time.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-pytest")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402

# Force Settings to re-read after we've set ANTHROPIC_API_KEY.
get_settings.cache_clear()

from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

"""Runtime configuration.

Pydantic-Settings reads values from the process environment (and a `.env`
file at the working directory if present). Every key has a default so that
running `pytest` or `uvicorn` outside docker-compose doesn't immediately blow
up; production deployments are expected to override the secrets.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ── Postgres ────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://fundamentals:fundamentals@localhost:5432/fundamentals_ai"
    )

    # ── Redis ───────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── LLM provider toggle ─────────────────────────────────────────────
    # "anthropic" or "deepinfra". DeepInfra uses an OpenAI-compatible API.
    LLM_PROVIDER: Literal["anthropic", "deepinfra"] = "anthropic"

    # ── Anthropic (used when LLM_PROVIDER=anthropic) ────────────────────
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_AGENT_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_FAST_MODEL: str = "claude-haiku-4-5-20251001"
    LLM_FALLBACK_ENABLED: bool = False
    OPENAI_API_KEY: str = ""
    OPENAI_AGENT_MODEL: str = "gpt-4o"

    # ── DeepInfra (used when LLM_PROVIDER=deepinfra) ────────────────────
    DEEPINFRA_API_KEY: str = ""
    DEEPINFRA_BASE_URL: str = "https://api.deepinfra.com/v1/openai"
    DEEPINFRA_AGENT_MODEL: str = "moonshotai/Kimi-K2.6"
    DEEPINFRA_FAST_MODEL: str = "moonshotai/Kimi-K2.6"

    # ── Scraper ethics (used from step 3 onwards) ───────────────────────
    SCRAPER_USER_AGENT: str = (
        "fundamentals-ai/0.1 (+https://github.com/your-org/fundamentals-ai; educational demo)"
    )
    SCRAPER_MIN_INTERVAL_SECONDS: float = 3.0
    SCRAPER_RESPECT_ROBOTS_TXT: bool = True

    # ── Cache TTLs (seconds) ────────────────────────────────────────────
    CACHE_TTL_YFINANCE_SECONDS: int = 21_600
    CACHE_TTL_SCREENER_SECONDS: int = 86_400
    CACHE_TTL_REPORT_SECONDS: int = 43_200

    # ── Server ──────────────────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"  # noqa: S104  Bind-all is intentional inside the container.
    BACKEND_PORT: int = 8000
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Public reminder string that every API response is required to carry. Kept
# in one place so any wording change ripples everywhere.
DISCLAIMER: str = (
    "Educational and engineering demo. NOT investment advice. NOT a "
    "recommendation to buy or sell any security. Output is a structured "
    "summary of publicly available information for analytical study."
)

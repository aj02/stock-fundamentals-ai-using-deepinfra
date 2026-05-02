"""LLM model factory for PydanticAI agents.

Two providers supported:
  - "anthropic": Anthropic Claude. Sonnet for analysis agents, Haiku for
    simple tasks. Optional fallback to OpenAI via FallbackModel.
  - "deepinfra": DeepInfra-hosted open models (e.g. Moonshot Kimi K2). Uses
    PydanticAI's OpenAIModel against DeepInfra's OpenAI-compatible endpoint
    (https://api.deepinfra.com/v1/openai). The chosen model MUST support
    OpenAI-style tool calling — every agent in this repo depends on it.

Toggle via LLM_PROVIDER in .env. The wiring is in one place so all agents
pick up the active provider automatically.
"""

from __future__ import annotations

from enum import Enum

from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.config import Settings


class ModelTier(str, Enum):
    AGENT = "agent"  # Sonnet / Kimi K2 — for analysis-heavy agents
    FAST = "fast"  # Haiku / smaller — for simple deterministic tasks


def build_model(tier: ModelTier, settings: Settings) -> Model:
    if settings.LLM_PROVIDER == "deepinfra":
        return _build_deepinfra(tier, settings)
    return _build_anthropic(tier, settings)


def _build_anthropic(tier: ModelTier, settings: Settings) -> Model:
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError(
            "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. "
            "Add it to .env or switch LLM_PROVIDER to 'deepinfra'."
        )

    model_name = (
        settings.ANTHROPIC_AGENT_MODEL
        if tier is ModelTier.AGENT
        else settings.ANTHROPIC_FAST_MODEL
    )
    anthropic = AnthropicModel(
        model_name,
        provider=AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY),
    )

    if not settings.LLM_FALLBACK_ENABLED or not settings.OPENAI_API_KEY:
        return anthropic

    openai = OpenAIModel(
        settings.OPENAI_AGENT_MODEL,
        provider=OpenAIProvider(api_key=settings.OPENAI_API_KEY),
    )
    return FallbackModel(anthropic, openai)


def _build_deepinfra(tier: ModelTier, settings: Settings) -> Model:
    if not settings.DEEPINFRA_API_KEY:
        raise RuntimeError(
            "LLM_PROVIDER=deepinfra but DEEPINFRA_API_KEY is not set. "
            "Get one at https://deepinfra.com/dash/api_keys and add to .env."
        )

    model_name = (
        settings.DEEPINFRA_AGENT_MODEL
        if tier is ModelTier.AGENT
        else settings.DEEPINFRA_FAST_MODEL
    )
    return OpenAIModel(
        model_name,
        provider=OpenAIProvider(
            api_key=settings.DEEPINFRA_API_KEY,
            base_url=settings.DEEPINFRA_BASE_URL,
        ),
    )

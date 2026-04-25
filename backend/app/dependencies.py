from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.llm_client import (
    AnthropicLLMClient,
    LLMClient,
    OpenAICompatibleLLMClient,
)
from app.services.resy_client import RealResyClient, ResyClient


@lru_cache(maxsize=1)
def _real_llm() -> LLMClient:
    settings = get_settings()
    if settings.llm_provider == "nvidia":
        return OpenAICompatibleLLMClient(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            default_model=settings.nvidia_model,
        )
    return AnthropicLLMClient(api_key=settings.anthropic_api_key, default_model=settings.llm_model)


_llm_override: LLMClient | None = None


def get_llm_client() -> LLMClient:
    if _llm_override is not None:
        return _llm_override
    return _real_llm()


def set_llm_override(client: LLMClient | None) -> None:
    global _llm_override
    _llm_override = client


_resy_override: ResyClient | None = None


@lru_cache(maxsize=1)
def _real_resy() -> ResyClient:
    settings = get_settings()
    return RealResyClient(
        api_key=settings.resy_api_key,
        auth_token=settings.resy_auth_token,
    )


def get_resy_client() -> ResyClient:
    if _resy_override is not None:
        return _resy_override
    return _real_resy()


def set_resy_override(client: ResyClient | None) -> None:
    global _resy_override
    _resy_override = client

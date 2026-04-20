from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.llm_client import AnthropicLLMClient, LLMClient


@lru_cache(maxsize=1)
def _real_llm() -> LLMClient:
    settings = get_settings()
    return AnthropicLLMClient(api_key=settings.anthropic_api_key, default_model=settings.llm_model)


_llm_override: LLMClient | None = None


def get_llm_client() -> LLMClient:
    if _llm_override is not None:
        return _llm_override
    return _real_llm()


def set_llm_override(client: LLMClient | None) -> None:
    global _llm_override
    _llm_override = client

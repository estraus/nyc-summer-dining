from __future__ import annotations

import pytest

from app import dependencies
from app.config import get_settings
from app.services.resy_client import RealResyClient


def test_get_settings_returns_cached_instance() -> None:
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b


def test_get_settings_cache_clear_picks_up_env_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_MODEL", "model-v1")
    first = get_settings()
    assert first.llm_model == "model-v1"

    monkeypatch.setenv("LLM_MODEL", "model-v2")
    assert get_settings().llm_model == "model-v1", "cache should hold first value"

    get_settings.cache_clear()
    assert get_settings().llm_model == "model-v2"


def test_real_resy_client_reads_keys_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import Settings

    monkeypatch.delenv("RESY_API_KEY", raising=False)
    monkeypatch.delenv("RESY_AUTH_TOKEN", raising=False)

    custom = Settings(resy_api_key="from-settings", resy_auth_token="settings-token")
    monkeypatch.setattr(dependencies, "get_settings", lambda: custom)

    dependencies._real_resy.cache_clear()
    try:
        client = dependencies._real_resy()
    finally:
        dependencies._real_resy.cache_clear()

    assert isinstance(client, RealResyClient)
    assert client._api_key == "from-settings"
    assert client._auth_token == "settings-token"

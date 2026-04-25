import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password, sign_session
from app.db import run_migrations
from app.dependencies import set_llm_override
from app.models import SeedRestaurant, SeedSource
from app.services.llm_client import FakeLLMClient
from scrapers.importer import import_seed


@pytest.fixture
def streaming_client(tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("SHARED_PASSWORD_HASH", hash_password("p"))
    monkeypatch.setenv("COOKIE_SIGNING_KEY", "k")
    run_migrations(tmp_db)
    import_seed(
        tmp_db,
        [
            SeedRestaurant(
                name="A",
                neighborhood="Williamsburg",
                borough="Brooklyn",
                price_tier=2,
                booking_platform="resy",
                cuisine_tags=["a"],
                vibe_tags=["casual"],
                sources=[SeedSource(publication="eater_nyc")],
            ),
            SeedRestaurant(
                name="B",
                neighborhood="West Village",
                borough="Manhattan",
                price_tier=2,
                booking_platform="resy",
                cuisine_tags=["b"],
                vibe_tags=["casual"],
                sources=[SeedSource(publication="eater_nyc")],
            ),
        ],
    )
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        c.cookies.set("session", sign_session(1, "Eli", "k"))
        yield c


def _parse_sse(raw: str) -> list[tuple[str, object]]:
    events: list[tuple[str, object]] = []
    for block in raw.split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())
        if data_lines:
            events.append((event_name, json.loads("\n".join(data_lines))))
    return events


def test_stream_routes_through_active_llm_model_when_provider_overridden(
    streaming_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_MODEL", "test/nvidia-only-model")
    get_settings.cache_clear()
    fake = FakeLLMClient(stream_responses=[['<card id="a-williamsburg">x</card>']])
    set_llm_override(fake)
    try:
        with streaming_client.stream(
            "POST", "/api/search/stream", json={"preferences_text": "fun"}
        ) as resp:
            assert resp.status_code == 200
            list(resp.iter_text())
    finally:
        set_llm_override(None)

    assert fake.calls, "expected the streaming endpoint to call the LLM"
    assert fake.calls[0].model == "test/nvidia-only-model"


def test_stream_emits_candidates_then_cards_then_done(streaming_client: TestClient) -> None:
    fake = FakeLLMClient(
        stream_responses=[
            ['<card id="b-west-village">b reason.</card><card id="a-williamsburg">a reason.</card>']
        ]
    )
    set_llm_override(fake)
    try:
        with streaming_client.stream(
            "POST",
            "/api/search/stream",
            json={"preferences_text": "fun"},
        ) as resp:
            assert resp.status_code == 200
            raw = "".join(resp.iter_text())
    finally:
        set_llm_override(None)

    events = _parse_sse(raw)
    names = [e[0] for e in events]
    assert names[0] == "candidates"
    assert names[-1] == "done"
    card_events = [e for e in events if e[0] == "card"]
    card_payloads = [e[1] for e in card_events if isinstance(e[1], dict)]
    assert [p["id"] for p in card_payloads] == ["b-west-village", "a-williamsburg"]
    assert card_payloads[0]["reason"] == "b reason."

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
def logged_in_client(tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("SHARED_PASSWORD_HASH", hash_password("p"))
    monkeypatch.setenv("COOKIE_SIGNING_KEY", "k")

    run_migrations(tmp_db)
    import_seed(
        tmp_db,
        [
            SeedRestaurant(
                name="Lilia",
                neighborhood="Williamsburg",
                borough="Brooklyn",
                price_tier=3,
                booking_platform="resy",
                cuisine_tags=["italian"],
                vibe_tags=["date-night"],
                sources=[SeedSource(publication="eater_nyc")],
            ),
            SeedRestaurant(
                name="Nami Nori",
                neighborhood="West Village",
                borough="Manhattan",
                price_tier=2,
                booking_platform="resy",
                cuisine_tags=["japanese"],
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


def test_search_returns_ranked_results(logged_in_client: TestClient) -> None:
    fake = FakeLLMClient(
        responses=[
            '<card id="nami-nori-west-village">Casual, right vibe.</card>'
            '<card id="lilia-williamsburg">Splurge backup.</card>'
        ]
    )
    set_llm_override(fake)
    try:
        resp = logged_in_client.post(
            "/api/search",
            json={"preferences_text": "casual", "vibes": ["casual"]},
        )
    finally:
        set_llm_override(None)

    assert resp.status_code == 200
    body = resp.json()
    assert [c["id"] for c in body["ranked"]] == ["nami-nori-west-village", "lilia-williamsburg"]
    assert body["ranked"][0]["reason"].startswith("Casual")
    assert {c["id"] for c in body["candidates"]} == {"lilia-williamsburg", "nami-nori-west-village"}


def test_search_with_neighborhood_filter(logged_in_client: TestClient) -> None:
    fake = FakeLLMClient(responses=['<card id="lilia-williamsburg">Only option.</card>'])
    set_llm_override(fake)
    try:
        resp = logged_in_client.post(
            "/api/search",
            json={"neighborhoods": ["Williamsburg"], "preferences_text": ""},
        )
    finally:
        set_llm_override(None)

    body = resp.json()
    assert [c["id"] for c in body["candidates"]] == ["lilia-williamsburg"]


def test_search_requires_auth(tmp_db: Path) -> None:
    from app.main import create_app

    with TestClient(create_app()) as c:
        resp = c.post("/api/search", json={})
    assert resp.status_code == 401


def test_search_empty_shortlist(logged_in_client: TestClient) -> None:
    fake = FakeLLMClient(responses=[])
    set_llm_override(fake)
    try:
        resp = logged_in_client.post("/api/search", json={"neighborhoods": ["Harlem"]})
    finally:
        set_llm_override(None)
    body = resp.json()
    assert body["candidates"] == []
    assert body["ranked"] == []

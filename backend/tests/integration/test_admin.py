"""Integration tests for admin routes."""

from __future__ import annotations

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

# ---------------------------------------------------------------------------
# Fixture: logged-in client with two seeded restaurants
# ---------------------------------------------------------------------------


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
                sources=[
                    SeedSource(publication="eater_nyc", source_url="https://example.com/lilia")
                ],
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
    from app.routes import admin as admin_routes

    app = create_app()
    app.include_router(admin_routes.router)
    with TestClient(app) as c:
        c.cookies.set("session", sign_session(1, "Eli", "k"))
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_restaurants_default(logged_in_client: TestClient) -> None:
    resp = logged_in_client.get("/api/admin/restaurants")
    assert resp.status_code == 200
    data = resp.json()
    names = {r["name"] for r in data}
    assert "Lilia" in names
    assert "Nami Nori" in names


def test_list_restaurants_filter_open(logged_in_client: TestClient) -> None:
    # All seeded restaurants have status=open by default
    resp = logged_in_client.get("/api/admin/restaurants?status=open")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    resp_closed = logged_in_client.get("/api/admin/restaurants?status=closed")
    assert resp_closed.status_code == 200
    assert resp_closed.json() == []


def test_get_restaurant_detail(logged_in_client: TestClient) -> None:
    resp = logged_in_client.get("/api/admin/restaurants/lilia-williamsburg")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Lilia"
    assert data["neighborhood"] == "Williamsburg"
    assert "italian" in data["cuisine_tags"]
    assert "date-night" in data["vibe_tags"]
    # Should have sources list
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) >= 1
    assert data["sources"][0]["publication"] == "eater_nyc"


def test_get_restaurant_not_found(logged_in_client: TestClient) -> None:
    resp = logged_in_client.get("/api/admin/restaurants/does-not-exist")
    assert resp.status_code == 404


def test_close_restaurant(logged_in_client: TestClient) -> None:
    resp = logged_in_client.post("/api/admin/restaurants/lilia-williamsburg/close")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    # Confirm status is now closed
    detail = logged_in_client.get("/api/admin/restaurants/lilia-williamsburg")
    assert detail.json()["status"] == "closed"


def test_resolve_restaurant(logged_in_client: TestClient) -> None:
    # Close first
    logged_in_client.post("/api/admin/restaurants/lilia-williamsburg/close")
    detail = logged_in_client.get("/api/admin/restaurants/lilia-williamsburg")
    assert detail.json()["status"] == "closed"

    # Then resolve
    resp = logged_in_client.post("/api/admin/restaurants/lilia-williamsburg/resolve")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    detail2 = logged_in_client.get("/api/admin/restaurants/lilia-williamsburg")
    assert detail2.json()["status"] == "open"


def test_delete_restaurant(logged_in_client: TestClient) -> None:
    resp = logged_in_client.delete("/api/admin/restaurants/lilia-williamsburg")
    assert resp.status_code == 204

    # Should be gone
    resp2 = logged_in_client.get("/api/admin/restaurants/lilia-williamsburg")
    assert resp2.status_code == 404


def test_add_by_url(logged_in_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock httpx.get to avoid real network call
    class FakeResponse:
        text = "<html><body>Lilia restaurant Williamsburg Brooklyn Italian pasta</body></html>"

        def raise_for_status(self) -> None:
            pass

    monkeypatch.setattr("httpx.get", lambda *a, **kw: FakeResponse())

    seed_json = json.dumps(
        {
            "name": "Lilia",
            "neighborhood": "Williamsburg",
            "borough": "Brooklyn",
            "description": "Great Italian pasta spot",
            "cuisine_tags": ["italian"],
            "vibe_tags": ["date-night"],
            "sources": [],
        }
    )
    fake = FakeLLMClient(responses=[seed_json])
    set_llm_override(fake)
    try:
        resp = logged_in_client.post(
            "/api/admin/add-by-url",
            json={"url": "https://example.com/lilia"},
        )
    finally:
        set_llm_override(None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Lilia"
    assert "description" in data


def test_add_by_name(logged_in_client: TestClient) -> None:
    seed_json = json.dumps(
        {
            "name": "Carbone",
            "neighborhood": "Greenwich Village",
            "borough": "Manhattan",
            "description": "Classic Italian-American chophouse",
            "cuisine_tags": ["italian"],
            "vibe_tags": ["nice"],
            "sources": [],
        }
    )
    fake = FakeLLMClient(responses=[seed_json])
    set_llm_override(fake)
    try:
        resp = logged_in_client.post(
            "/api/admin/add-by-name",
            json={"name": "Carbone", "neighborhood": "Greenwich Village"},
        )
    finally:
        set_llm_override(None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Carbone"


def test_reseed_apply(logged_in_client: TestClient) -> None:
    seeds = [
        {
            "name": "New Restaurant",
            "neighborhood": "SoHo",
            "borough": "Manhattan",
            "price_tier": 2,
            "cuisine_tags": ["american"],
            "vibe_tags": ["casual"],
            "sources": [{"publication": "eater_nyc"}],
        }
    ]
    resp = logged_in_client.post("/api/admin/reseed-apply", json={"seeds": seeds})
    assert resp.status_code == 200
    data = resp.json()
    assert "inserted" in data
    assert "updated" in data
    assert data["inserted"] >= 1


def test_create_restaurant(logged_in_client: TestClient) -> None:
    resp = logged_in_client.post(
        "/api/admin/restaurants",
        json={
            "name": "Don Angie",
            "neighborhood": "West Village",
            "borough": "Manhattan",
            "price_tier": 3,
            "cuisine_tags": ["italian"],
            "vibe_tags": ["date-night"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["id"] == "don-angie-west-village"

    # Verify it appears in the list
    list_resp = logged_in_client.get("/api/admin/restaurants")
    names = {r["name"] for r in list_resp.json()}
    assert "Don Angie" in names


def test_update_sets_and_returns_external_ratings(logged_in_client: TestClient) -> None:
    resp = logged_in_client.put(
        "/api/admin/restaurants/lilia-williamsburg",
        json={"google_rating": 4.6, "google_review_count": 2100, "beli_score": 8.7},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["google_rating"] == 4.6
    assert body["google_review_count"] == 2100
    assert body["beli_score"] == 8.7


@pytest.mark.parametrize(
    "payload", [{"google_rating": 6}, {"beli_score": 11}, {"google_review_count": -3}]
)
def test_update_rejects_out_of_range_ratings(
    logged_in_client: TestClient, payload: dict[str, float]
) -> None:
    resp = logged_in_client.put("/api/admin/restaurants/lilia-williamsburg", json=payload)
    assert resp.status_code == 422


def test_update_can_clear_a_rating(logged_in_client: TestClient) -> None:
    logged_in_client.put("/api/admin/restaurants/lilia-williamsburg", json={"beli_score": 8.7})
    resp = logged_in_client.put(
        "/api/admin/restaurants/lilia-williamsburg", json={"beli_score": None}
    )
    assert resp.status_code == 200
    assert resp.json()["beli_score"] is None

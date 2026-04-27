from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password, sign_session
from app.db import run_migrations
from app.dependencies import set_llm_override
from app.models import SeedRestaurant, SeedSource
from app.services.llm_client import FakeLLMClient
from app.users import create_user
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
    user = create_user(tmp_db, "Eli")

    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        c.cookies.set("session", sign_session(user.id, user.display_name, "k"))
        yield c


def test_upsert_creates_note(logged_in_client: TestClient) -> None:
    resp = logged_in_client.put(
        "/api/notes/lilia-williamsburg",
        json={"status": "want_to_try", "rating": None, "note": "Heard great things"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["restaurant_id"] == "lilia-williamsburg"
    assert body["status"] == "want_to_try"
    assert body["note"] == "Heard great things"
    assert body["rating"] is None
    assert isinstance(body["user_id"], int)
    assert "id" in body


def test_upsert_updates_note(logged_in_client: TestClient) -> None:
    logged_in_client.put(
        "/api/notes/lilia-williamsburg",
        json={"status": "want_to_try"},
    )
    resp = logged_in_client.put(
        "/api/notes/lilia-williamsburg",
        json={"status": "loved", "rating": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "loved"
    assert body["rating"] == 5


def test_list_notes(logged_in_client: TestClient) -> None:
    logged_in_client.put("/api/notes/lilia-williamsburg", json={"status": "want_to_try"})
    logged_in_client.put("/api/notes/nami-nori-west-village", json={"status": "tried", "rating": 4})

    resp = logged_in_client.get("/api/notes")
    assert resp.status_code == 200
    body = resp.json()
    assert "lilia-williamsburg" in body
    assert "nami-nori-west-village" in body
    assert body["lilia-williamsburg"]["status"] == "want_to_try"
    assert body["nami-nori-west-village"]["status"] == "tried"
    assert body["nami-nori-west-village"]["rating"] == 4


def test_delete_note(logged_in_client: TestClient) -> None:
    logged_in_client.put("/api/notes/lilia-williamsburg", json={"status": "tried"})

    del_resp = logged_in_client.delete("/api/notes/lilia-williamsburg")
    assert del_resp.status_code == 204

    list_resp = logged_in_client.get("/api/notes")
    assert list_resp.status_code == 200
    assert "lilia-williamsburg" not in list_resp.json()


def test_delete_nonexistent_is_204(logged_in_client: TestClient) -> None:
    resp = logged_in_client.delete("/api/notes/lilia-williamsburg")
    assert resp.status_code == 204


def test_upsert_unknown_restaurant_returns_404(logged_in_client: TestClient) -> None:
    resp = logged_in_client.put(
        "/api/notes/nonexistent-slug",
        json={"status": "want_to_try"},
    )
    assert resp.status_code == 404


def test_notes_isolated_between_users(tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
        ],
    )
    user1 = create_user(tmp_db, "UserOne")
    user2 = create_user(tmp_db, "UserTwo")

    from app.main import create_app

    app = create_app()
    with TestClient(app) as client1:
        client1.cookies.set("session", sign_session(user1.id, user1.display_name, "k"))
        client1.put("/api/notes/lilia-williamsburg", json={"status": "loved", "rating": 5})

        with TestClient(app) as client2:
            client2.cookies.set("session", sign_session(user2.id, user2.display_name, "k"))
            resp = client2.get("/api/notes")
            assert resp.status_code == 200
            assert "lilia-williamsburg" not in resp.json()


def test_notes_included_in_search_response(logged_in_client: TestClient) -> None:
    logged_in_client.put(
        "/api/notes/lilia-williamsburg",
        json={"status": "loved", "rating": 5, "note": "Amazing pasta"},
    )

    fake = FakeLLMClient(responses=['<card id="lilia-williamsburg">Great pick.</card>'])
    set_llm_override(fake)
    try:
        resp = logged_in_client.post("/api/search", json={"preferences_text": "italian"})
    finally:
        set_llm_override(None)

    assert resp.status_code == 200
    body = resp.json()
    assert "notes" in body
    assert "lilia-williamsburg" in body["notes"]
    note = body["notes"]["lilia-williamsburg"]
    assert note["status"] == "loved"
    assert note["rating"] == 5
    assert note["note"] == "Amazing pasta"

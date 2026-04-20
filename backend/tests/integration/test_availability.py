from collections.abc import Iterator
from datetime import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password, sign_session
from app.db import connect, run_migrations
from app.dependencies import set_resy_override
from app.models import SeedRestaurant
from app.services.resy_client import FakeResyClient, ResyNotFoundError, ResyUpstreamError, Slot
from scrapers.importer import import_seed


@pytest.fixture
def logged_in(tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
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
                resy_venue_id="345",
            ),
            SeedRestaurant(
                name="Joe's Pizza",
                neighborhood="West Village",
                borough="Manhattan",
                price_tier=1,
                booking_platform="walk_in",
            ),
            SeedRestaurant(
                name="Nami Nori",
                neighborhood="West Village",
                borough="Manhattan",
                booking_platform="resy",
            ),
        ],
    )
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        c.cookies.set("session", sign_session(1, "Eli", "k"))
        yield c


def test_availability_happy_path(logged_in: TestClient) -> None:
    fake = FakeResyClient(
        responses=[
            [
                Slot(time=time(19, 30), seat_type="Dining Room", book_url="https://resy.com/x"),
                Slot(time=time(20, 0), seat_type="Bar", book_url="https://resy.com/y"),
            ]
        ]
    )
    set_resy_override(fake)
    try:
        resp = logged_in.get(
            "/api/availability",
            params={
                "restaurant_id": "lilia-williamsburg",
                "party": 2,
                "date": "2026-06-20",
                "time": "19:30",
            },
        )
    finally:
        set_resy_override(None)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["slots"]) == 2
    assert body["slots"][0]["time"] == "19:30"


def test_availability_walk_in(logged_in: TestClient) -> None:
    resp = logged_in.get(
        "/api/availability",
        params={
            "restaurant_id": "joe-s-pizza-west-village",
            "party": 1,
            "date": "2026-06-20",
            "time": "19:00",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "use_booking_url"


def test_availability_no_venue_id(logged_in: TestClient) -> None:
    resp = logged_in.get(
        "/api/availability",
        params={
            "restaurant_id": "nami-nori-west-village",
            "party": 2,
            "date": "2026-06-20",
            "time": "19:00",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "no_venue_id"


def test_availability_venue_not_found_flags_review(logged_in: TestClient, tmp_db: Path) -> None:
    fake = FakeResyClient(errors=[ResyNotFoundError("345")])
    set_resy_override(fake)
    try:
        resp = logged_in.get(
            "/api/availability",
            params={
                "restaurant_id": "lilia-williamsburg",
                "party": 2,
                "date": "2026-06-20",
                "time": "19:00",
            },
        )
    finally:
        set_resy_override(None)
    assert resp.status_code == 404

    conn = connect(tmp_db)
    try:
        row = conn.execute(
            "SELECT status FROM restaurants WHERE id = ?", ("lilia-williamsburg",)
        ).fetchone()
    finally:
        conn.close()
    assert row["status"] == "needs_review"


def test_availability_upstream_error_returns_503(logged_in: TestClient) -> None:
    fake = FakeResyClient(errors=[ResyUpstreamError("boom")])
    set_resy_override(fake)
    try:
        resp = logged_in.get(
            "/api/availability",
            params={
                "restaurant_id": "lilia-williamsburg",
                "party": 2,
                "date": "2026-06-20",
                "time": "19:00",
            },
        )
    finally:
        set_resy_override(None)
    assert resp.status_code == 503
    assert resp.json()["detail"] == "resy_unreachable"


def test_availability_requires_auth(tmp_db: Path) -> None:
    from app.main import create_app

    with TestClient(create_app()) as c:
        resp = c.get(
            "/api/availability",
            params={
                "restaurant_id": "x",
                "party": 2,
                "date": "2026-06-20",
                "time": "19:00",
            },
        )
    assert resp.status_code == 401

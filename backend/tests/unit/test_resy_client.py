import json
from datetime import date, time
from pathlib import Path

import httpx
import pytest

from app.services.resy_client import (
    FakeResyClient,
    RealResyClient,
    ResyFindParams,
    ResyNotFoundError,
    ResyUpstreamError,
    Slot,
    normalize_slots,
)

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "resy"


def _params() -> ResyFindParams:
    return ResyFindParams(
        venue_id="345",
        party_size=2,
        day=date(2026, 6, 20),
        target_time=time(19, 30),
    )


def test_normalize_happy_path() -> None:
    raw = json.loads((FIX / "find_happy.json").read_text())
    slots = normalize_slots(raw, venue_id="345")
    assert [(s.time.isoformat(), s.seat_type) for s in slots] == [
        ("19:30:00", "Dining Room"),
        ("20:00:00", "Bar"),
        ("21:45:00", "Dining Room"),
    ]


def test_normalize_filters_outside_window() -> None:
    raw = json.loads((FIX / "find_happy.json").read_text())
    slots = normalize_slots(raw, venue_id="345", target_time=time(19, 30), window_hours=1)
    # 21:45 is more than 1 hour away
    assert all(s.time.hour < 21 for s in slots)


def test_normalize_empty() -> None:
    raw = json.loads((FIX / "find_empty.json").read_text())
    slots = normalize_slots(raw, venue_id="345")
    assert slots == []


def test_normalize_venue_not_found_raises() -> None:
    raw = json.loads((FIX / "find_venue_not_found.json").read_text())
    with pytest.raises(ResyNotFoundError):
        normalize_slots(raw, venue_id="345")


def test_fake_returns_scripted_slots() -> None:
    fake = FakeResyClient(
        responses=[
            [
                Slot(time=time(19, 30), seat_type="Dining Room", book_url="https://resy.com/..."),
                Slot(time=time(20, 0), seat_type="Bar", book_url="https://resy.com/..."),
            ]
        ]
    )
    out = fake.find_slots(_params())
    assert len(out) == 2


def test_fake_raises_scripted_not_found() -> None:
    fake = FakeResyClient(errors=[ResyNotFoundError("345")])
    with pytest.raises(ResyNotFoundError):
        fake.find_slots(_params())


def test_real_client_uses_httpx() -> None:
    happy = json.loads((FIX / "find_happy.json").read_text())
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=happy))
    client = RealResyClient(api_key="k", auth_token="t", transport=transport)
    slots = client.find_slots(_params())
    assert len(slots) >= 1


def test_real_client_raises_on_5xx() -> None:
    transport = httpx.MockTransport(lambda req: httpx.Response(502))
    client = RealResyClient(api_key="k", auth_token="t", transport=transport)
    with pytest.raises(ResyUpstreamError):
        client.find_slots(_params())


def test_real_client_raises_on_empty_venues() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"results": {"venues": []}})
    )
    client = RealResyClient(api_key="k", auth_token="t", transport=transport)
    with pytest.raises(ResyNotFoundError):
        client.find_slots(_params())

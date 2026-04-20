from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Protocol, cast, runtime_checkable

import httpx


class ResyError(Exception):
    """Base class for Resy errors."""


class ResyNotFoundError(ResyError):
    """Venue not found."""


class ResyUpstreamError(ResyError):
    """Resy returned a non-2xx or unexpected response."""


@dataclass(frozen=True)
class Slot:
    time: time
    seat_type: str
    book_url: str


@dataclass(frozen=True)
class ResyFindParams:
    venue_id: str
    party_size: int
    day: date
    target_time: time | None = None


@runtime_checkable
class ResyClient(Protocol):
    def find_slots(self, params: ResyFindParams) -> list[Slot]: ...


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return cast(list[object], value)
    return []


def _parse_slot(raw: dict[str, object]) -> tuple[time, str, str]:
    date_info = _as_dict(raw.get("date"))
    date_start_val = date_info.get("start")
    date_start = date_start_val if isinstance(date_start_val, str) else ""
    try:
        dt = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ResyUpstreamError(f"unparseable slot date: {date_start!r}") from exc
    cfg = _as_dict(raw.get("config"))
    seat_type_val = cfg.get("type")
    seat_type = seat_type_val if isinstance(seat_type_val, str) else ""
    token_val = cfg.get("token")
    token = token_val if isinstance(token_val, str) else ""
    book_url = f"https://resy.com/cities/ny/book/{token}" if token else ""
    return dt.time(), seat_type, book_url


def normalize_slots(
    raw: dict[str, object],
    *,
    venue_id: str,
    target_time: time | None = None,
    window_hours: float = 2.0,
    limit: int = 5,
) -> list[Slot]:
    results = _as_dict(raw.get("results"))
    venues = _as_list(results.get("venues"))
    if not venues:
        raise ResyNotFoundError(venue_id)
    chosen = _as_dict(venues[0])
    for v in venues:
        v_dict = _as_dict(v)
        vid = _as_dict(_as_dict(v_dict.get("venue")).get("id"))
        if str(vid.get("resy")) == venue_id:
            chosen = v_dict
            break
    slots: list[Slot] = []
    for raw_slot in _as_list(chosen.get("slots")):
        t, seat_type, book_url = _parse_slot(_as_dict(raw_slot))
        slots.append(Slot(time=t, seat_type=seat_type, book_url=book_url))
    if target_time is not None:
        window = timedelta(hours=window_hours)
        target = datetime.combine(date.today(), target_time)
        slots = [s for s in slots if abs(datetime.combine(date.today(), s.time) - target) <= window]
    slots.sort(key=lambda s: s.time)
    return slots[:limit]


@dataclass
class FakeResyClient:
    responses: list[list[Slot]] = field(default_factory=list[list[Slot]])
    errors: list[Exception] = field(default_factory=list[Exception])
    calls: list[ResyFindParams] = field(default_factory=list[ResyFindParams])

    def find_slots(self, params: ResyFindParams) -> list[Slot]:
        self.calls.append(params)
        if self.errors:
            raise self.errors.pop(0)
        if not self.responses:
            return []
        return self.responses.pop(0)


class RealResyClient:
    BASE_URL = "https://api.resy.com/4/find"

    def __init__(
        self,
        *,
        api_key: str,
        auth_token: str,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._auth_token = auth_token
        self._client = httpx.Client(transport=transport, timeout=timeout)

    def find_slots(self, params: ResyFindParams) -> list[Slot]:
        query = {
            "lat": "0",
            "long": "0",
            "day": params.day.isoformat(),
            "party_size": str(params.party_size),
            "venue_id": params.venue_id,
        }
        headers = {
            "Authorization": f'ResyAPI api_key="{self._api_key}"',
            "x-resy-auth-token": self._auth_token,
            "User-Agent": "NYC-Dining/1.0",
        }
        try:
            response = self._client.get(self.BASE_URL, params=query, headers=headers)
        except httpx.HTTPError as exc:
            raise ResyUpstreamError(str(exc)) from exc
        if response.status_code >= 500:
            raise ResyUpstreamError(f"Resy {response.status_code}")
        if response.status_code == 404:
            raise ResyNotFoundError(params.venue_id)
        if response.status_code >= 400:
            raise ResyUpstreamError(f"Resy {response.status_code}")
        try:
            data_raw = response.json()
        except ValueError as exc:
            raise ResyUpstreamError("non-JSON response") from exc
        if not isinstance(data_raw, dict):
            raise ResyUpstreamError("non-object JSON response")
        data = cast(dict[str, object], data_raw)
        return normalize_slots(
            data,
            venue_id=params.venue_id,
            target_time=params.target_time,
        )

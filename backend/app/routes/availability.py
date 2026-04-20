from __future__ import annotations

from datetime import date as date_type
from datetime import time as time_type
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import get_settings
from app.db import connect
from app.dependencies import get_resy_client
from app.services.resy_client import (
    ResyFindParams,
    ResyNotFoundError,
    ResyUpstreamError,
)

router = APIRouter(prefix="/api", tags=["availability"])


class SlotResponse(BaseModel):
    time: str
    seat_type: str
    book_url: str


class AvailabilityResponse(BaseModel):
    slots: list[SlotResponse]


@router.get("/availability", response_model=AvailabilityResponse)
def availability(
    restaurant_id: Annotated[str, Query(min_length=1)],
    party: Annotated[int, Query(ge=1, le=20)],
    date: Annotated[date_type, Query()],
    time: Annotated[time_type, Query()],
) -> AvailabilityResponse:
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        row = conn.execute(
            "SELECT booking_platform, resy_venue_id, booking_url FROM restaurants WHERE id = ?",
            (restaurant_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="restaurant_not_found")
    if row["booking_platform"] != "resy":
        raise HTTPException(status_code=400, detail="use_booking_url")
    venue_id = row["resy_venue_id"]
    if not venue_id:
        raise HTTPException(status_code=400, detail="no_venue_id")

    client = get_resy_client()
    try:
        slots = client.find_slots(
            ResyFindParams(
                venue_id=venue_id,
                party_size=party,
                day=date,
                target_time=time,
            )
        )
    except ResyNotFoundError as exc:
        _flag_for_review(settings.db_path, restaurant_id)
        raise HTTPException(status_code=404, detail="venue_not_found") from exc
    except ResyUpstreamError as exc:
        raise HTTPException(status_code=503, detail="resy_unreachable") from exc

    return AvailabilityResponse(
        slots=[
            SlotResponse(
                time=s.time.strftime("%H:%M"),
                seat_type=s.seat_type,
                book_url=s.book_url,
            )
            for s in slots
        ]
    )


def _flag_for_review(db_path: Path, restaurant_id: str) -> None:
    conn = connect(db_path)
    try:
        conn.execute(
            "UPDATE restaurants SET status='needs_review', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (restaurant_id,),
        )
    finally:
        conn.close()

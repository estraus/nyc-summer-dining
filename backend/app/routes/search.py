from __future__ import annotations

import asyncio
import json
import math
from collections.abc import AsyncIterator
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import connect
from app.dependencies import get_llm_client
from app.rate_limit import SlidingWindowLimiter
from app.services.ranker import RankingRequest, rank_sync, stream_cards
from app.services.shortlist import ShortlistFilters, ShortlistItem, fetch_shortlist

CANDIDATE_LIMIT = 25
SHORTLIST_FETCH_LIMIT = 40

router = APIRouter(prefix="/api", tags=["search"])

_search_limiter: SlidingWindowLimiter | None = None


def _get_search_limiter() -> SlidingWindowLimiter:
    global _search_limiter
    if _search_limiter is None:
        settings = get_settings()
        _search_limiter = SlidingWindowLimiter(
            max_attempts=settings.search_rate_limit,
            window_seconds=settings.search_rate_window_seconds,
        )
    return _search_limiter


def _reset_search_limiter() -> None:  # pyright: ignore[reportUnusedFunction]
    global _search_limiter
    _search_limiter = None


def _client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host or "unknown"


def _enforce_search_rate_limit(request: Request) -> None:
    retry_after = _get_search_limiter().check(_client_ip(request))
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="rate_limited",
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )


class SearchRequest(BaseModel):
    neighborhoods: list[str] = Field(default_factory=list[str])
    boroughs: list[str] = Field(default_factory=list[str])
    price_ceiling: int | None = Field(default=None, ge=1, le=4)
    cuisines: list[str] = Field(default_factory=list[str])
    vibes: list[str] = Field(default_factory=list[str])
    preferences_text: str = ""
    target_n: int = Field(default=8, ge=1, le=20)


class RankedCardResponse(BaseModel):
    id: str
    reason: str


class CandidateResponse(BaseModel):
    id: str
    name: str
    neighborhood: str | None
    borough: str | None
    price_tier: int | None
    booking_platform: str | None
    booking_url: str | None
    resy_venue_id: str | None
    description: str | None
    cuisine_tags: list[str]
    vibe_tags: list[str]
    feature_tags: list[str]
    sources: list[dict[str, str | None]]
    google_rating: float | None = None
    google_review_count: int | None = None
    beli_score: float | None = None


class SearchResponse(BaseModel):
    candidates: list[CandidateResponse]
    ranked: list[RankedCardResponse]
    notes: dict[str, dict[str, object]] = Field(default_factory=dict)


def _candidate_dict(item: ShortlistItem) -> dict[str, object]:
    return {k: v for k, v in asdict(item).items() if k != "source_count"}


def _fetch_notes_for_ids(
    restaurant_ids: list[str], user_id: int | None
) -> dict[str, dict[str, object]]:
    if not restaurant_ids or user_id is None:
        return {}
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        placeholders = ",".join("?" * len(restaurant_ids))
        rows = conn.execute(
            f"""
            SELECT restaurant_id, status, rating, note
            FROM personal_notes
            WHERE user_id = ? AND restaurant_id IN ({placeholders})
            """,
            [user_id, *restaurant_ids],
        ).fetchall()
    finally:
        conn.close()
    return {
        row["restaurant_id"]: {
            "status": row["status"],
            "rating": row["rating"],
            "note": row["note"],
        }
        for row in rows
    }


def _prepare_search(
    body: SearchRequest, user_id: int | None = None
) -> tuple[list[ShortlistItem], RankingRequest, dict[str, dict[str, object]]]:
    settings = get_settings()
    filters = ShortlistFilters(
        neighborhoods=body.neighborhoods,
        boroughs=body.boroughs,
        price_ceiling=body.price_ceiling,
    )
    items = fetch_shortlist(settings.db_path, filters, limit=SHORTLIST_FETCH_LIMIT)
    if len(items) > CANDIDATE_LIMIT:
        items = items[:CANDIDATE_LIMIT]
    restaurant_ids = [item.id for item in items]
    notes = _fetch_notes_for_ids(restaurant_ids, user_id)
    rank_req = RankingRequest(
        shortlist=items,
        cuisines=body.cuisines,
        vibes=body.vibes,
        preferences_text=body.preferences_text,
        target_n=body.target_n,
        notes=notes,
    )
    return items, rank_req, notes


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest, request: Request) -> SearchResponse:
    _enforce_search_rate_limit(request)
    user_id: int | None = getattr(request.state, "user_id", None)
    items, rank_req, notes = _prepare_search(body, user_id)
    candidates = [CandidateResponse.model_validate(_candidate_dict(item)) for item in items]
    ranked_cards = rank_sync(
        llm=get_llm_client(),
        request=rank_req,
        model=get_settings().active_llm_model,
    )
    return SearchResponse(
        candidates=candidates,
        ranked=[RankedCardResponse(id=c.id, reason=c.reason) for c in ranked_cards],
        notes=notes,
    )


def _sse_event(name: str, payload: object) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/search/stream")
async def search_stream(body: SearchRequest, request: Request) -> StreamingResponse:
    _enforce_search_rate_limit(request)
    user_id: int | None = getattr(request.state, "user_id", None)
    items, rank_req, _notes = await asyncio.to_thread(_prepare_search, body, user_id)
    candidates_payload = [_candidate_dict(item) for item in items]
    llm = get_llm_client()
    model = get_settings().active_llm_model

    async def generator() -> AsyncIterator[str]:
        yield _sse_event("candidates", {"candidates": candidates_payload})
        async for card in stream_cards(llm=llm, request=rank_req, model=model):
            yield _sse_event("card", {"id": card.id, "reason": card.reason})
        yield _sse_event("done", {"ok": True})

    return StreamingResponse(generator(), media_type="text/event-stream")

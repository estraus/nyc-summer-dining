from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import asdict

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.dependencies import get_llm_client
from app.services.ranker import RankingRequest, rank_sync, stream_cards
from app.services.shortlist import ShortlistFilters, ShortlistItem, fetch_shortlist

CANDIDATE_LIMIT = 25
SHORTLIST_FETCH_LIMIT = 40

router = APIRouter(prefix="/api", tags=["search"])


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


class SearchResponse(BaseModel):
    candidates: list[CandidateResponse]
    ranked: list[RankedCardResponse]


def _candidate_dict(item: ShortlistItem) -> dict[str, object]:
    return {k: v for k, v in asdict(item).items() if k != "source_count"}


def _prepare_search(body: SearchRequest) -> tuple[list[ShortlistItem], RankingRequest]:
    settings = get_settings()
    filters = ShortlistFilters(
        neighborhoods=body.neighborhoods,
        boroughs=body.boroughs,
        price_ceiling=body.price_ceiling,
    )
    items = fetch_shortlist(settings.db_path, filters, limit=SHORTLIST_FETCH_LIMIT)
    if len(items) > CANDIDATE_LIMIT:
        items = items[:CANDIDATE_LIMIT]
    rank_req = RankingRequest(
        shortlist=items,
        cuisines=body.cuisines,
        vibes=body.vibes,
        preferences_text=body.preferences_text,
        target_n=body.target_n,
    )
    return items, rank_req


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest, _request: Request) -> SearchResponse:
    items, rank_req = _prepare_search(body)
    candidates = [CandidateResponse.model_validate(_candidate_dict(item)) for item in items]
    ranked_cards = rank_sync(
        llm=get_llm_client(),
        request=rank_req,
        model=get_settings().active_llm_model,
    )
    return SearchResponse(
        candidates=candidates,
        ranked=[RankedCardResponse(id=c.id, reason=c.reason) for c in ranked_cards],
    )


def _sse_event(name: str, payload: object) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/search/stream")
async def search_stream(body: SearchRequest) -> StreamingResponse:
    items, rank_req = await asyncio.to_thread(_prepare_search, body)
    candidates_payload = [_candidate_dict(item) for item in items]
    llm = get_llm_client()
    model = get_settings().active_llm_model

    async def generator() -> AsyncIterator[str]:
        yield _sse_event("candidates", {"candidates": candidates_payload})
        async for card in stream_cards(llm=llm, request=rank_req, model=model):
            yield _sse_event("card", {"id": card.id, "reason": card.reason})
        yield _sse_event("done", {"ok": True})

    return StreamingResponse(generator(), media_type="text/event-stream")

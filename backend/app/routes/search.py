from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import asdict

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.dependencies import get_llm_client
from app.services.ranker import RankingRequest, rank_sync, stream_cards
from app.services.shortlist import ShortlistFilters, fetch_shortlist

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


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest, _request: Request) -> SearchResponse:
    settings = get_settings()
    filters = ShortlistFilters(
        neighborhoods=body.neighborhoods,
        boroughs=body.boroughs,
        price_ceiling=body.price_ceiling,
    )
    items = fetch_shortlist(settings.db_path, filters, limit=40)
    if len(items) > 25:
        items = items[:25]
    candidates = [
        CandidateResponse(**{k: v for k, v in asdict(item).items() if k != "source_count"})
        for item in items
    ]

    llm = get_llm_client()
    ranked_cards = rank_sync(
        llm=llm,
        request=RankingRequest(
            shortlist=items,
            cuisines=body.cuisines,
            vibes=body.vibes,
            preferences_text=body.preferences_text,
            target_n=body.target_n,
        ),
        model=settings.active_llm_model,
    )
    return SearchResponse(
        candidates=candidates,
        ranked=[RankedCardResponse(id=c.id, reason=c.reason) for c in ranked_cards],
    )


def _sse_event(name: str, payload: object) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/search/stream")
async def search_stream(body: SearchRequest) -> StreamingResponse:
    settings = get_settings()
    filters = ShortlistFilters(
        neighborhoods=body.neighborhoods,
        boroughs=body.boroughs,
        price_ceiling=body.price_ceiling,
    )
    items = fetch_shortlist(settings.db_path, filters, limit=40)
    if len(items) > 25:
        items = items[:25]
    candidates_payload = [
        {k: v for k, v in asdict(item).items() if k != "source_count"} for item in items
    ]

    llm = get_llm_client()
    rank_req = RankingRequest(
        shortlist=items,
        cuisines=body.cuisines,
        vibes=body.vibes,
        preferences_text=body.preferences_text,
        target_n=body.target_n,
    )

    async def generator() -> AsyncIterator[str]:
        yield _sse_event("candidates", {"candidates": candidates_payload})
        async for card in stream_cards(llm=llm, request=rank_req, model=settings.llm_model):
            yield _sse_event("card", {"id": card.id, "reason": card.reason})
        yield _sse_event("done", {"ok": True})

    return StreamingResponse(generator(), media_type="text/event-stream")

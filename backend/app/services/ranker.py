from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.llm_client import LLMClient
from app.services.shortlist import ShortlistItem

SYSTEM_PROMPT = """You are a helpful NYC dining expert helping a friend pick where to eat.
Given a shortlist of restaurants, soft preferences, and a free-form preferences note,
return a ranked top N with a one-sentence reason for each pick.

Use only the data provided; do not invent details.
Output format: a sequence of `<card id="SLUG">one-sentence reason</card>` tags
in ranked order. No other text before or after the tags.
"""

_CARD_RE = re.compile(r'<card\s+id="([^"]+)"\s*>(.*?)</card>', re.DOTALL)


@dataclass(frozen=True)
class RankedCard:
    id: str
    reason: str


class RankingRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    shortlist: list[ShortlistItem]
    cuisines: list[str] = Field(default_factory=list[str])
    vibes: list[str] = Field(default_factory=list[str])
    preferences_text: str = ""
    target_n: int = 8
    notes: dict[str, dict[str, Any]] = Field(default_factory=dict)


def parse_cards(text: str) -> list[RankedCard]:
    results: list[RankedCard] = []
    for match in _CARD_RE.finditer(text):
        slug = match.group(1).strip()
        reason = " ".join(match.group(2).split())
        results.append(RankedCard(id=slug, reason=reason))
    return results


def _build_user_prompt(req: RankingRequest) -> str:
    shortlist_payload: list[dict[str, Any]] = []
    for item in req.shortlist:
        entry: dict[str, Any] = {
            "id": item.id,
            "name": item.name,
            "neighborhood": item.neighborhood,
            "borough": item.borough,
            "cuisine_tags": item.cuisine_tags,
            "vibe_tags": item.vibe_tags,
            "price_tier": item.price_tier,
            "description": item.description,
            "sources": item.sources,
        }
        my_note = req.notes.get(item.id)
        if my_note is not None:
            entry["my_note"] = my_note
        shortlist_payload.append(entry)
    lines: list[str] = []
    if req.cuisines:
        lines.append("Cuisines preferred: " + ", ".join(req.cuisines))
    if req.vibes:
        lines.append("Vibes preferred: " + ", ".join(req.vibes))
    if req.preferences_text.strip():
        lines.append("Preferences note: " + req.preferences_text.strip())
    lines.append(f"Return top N = min({req.target_n}, shortlist length).")
    lines.append("Shortlist JSON:")
    lines.append(json.dumps(shortlist_payload, ensure_ascii=False))
    return "\n".join(lines)


def _fallback(req: RankingRequest) -> list[RankedCard]:
    items = sorted(
        req.shortlist,
        key=lambda it: (-it.source_count, it.name.lower()),
    )
    limit = min(req.target_n, len(items))
    return [RankedCard(id=i.id, reason="") for i in items[:limit]]


def rank_sync(
    *,
    llm: LLMClient,
    request: RankingRequest,
    model: str,
) -> list[RankedCard]:
    if not request.shortlist:
        return []
    user_prompt = _build_user_prompt(request)
    try:
        raw = llm.complete(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=1500,
            temperature=0.3,
            model=model,
        )
    except Exception:
        return _fallback(request)
    cards = parse_cards(raw)
    if not cards:
        return _fallback(request)
    valid_ids = {item.id for item in request.shortlist}
    return [c for c in cards if c.id in valid_ids]


async def stream_cards(
    *,
    llm: LLMClient,
    request: RankingRequest,
    model: str,
) -> AsyncIterator[RankedCard]:
    if not request.shortlist:
        return
    valid_ids = {item.id for item in request.shortlist}
    buffer = ""
    emitted = False
    try:
        user_prompt = _build_user_prompt(request)
        async for chunk in llm.stream(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=1500,
            temperature=0.3,
            model=model,
        ):
            buffer += chunk
            while True:
                match = _CARD_RE.search(buffer)
                if not match:
                    break
                slug = match.group(1).strip()
                reason = " ".join(match.group(2).split())
                buffer = buffer[match.end() :]
                if slug in valid_ids:
                    emitted = True
                    yield RankedCard(id=slug, reason=reason)
    except Exception:
        pass
    if not emitted:
        for card in _fallback(request):
            yield card

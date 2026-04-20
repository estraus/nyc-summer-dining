from __future__ import annotations

import json
import re
from datetime import date
from typing import cast

from pydantic import ValidationError

from app.models import SeedRestaurant, SeedSource
from app.services.llm_client import LLMClient

SYSTEM_PROMPT = """You extract structured NYC restaurant data from source text.

Return a single JSON object with these keys (omit keys that cannot be inferred):
- name (string, required): canonical restaurant name.
- address (string, optional).
- neighborhood (string): short neighborhood name, e.g. "Williamsburg".
- borough: one of Manhattan, Brooklyn, Queens, Bronx, Staten Island.
- latitude, longitude (floats, optional).
- price_tier (integer 1-4).
- booking_platform: one of resy, opentable, tock, walk_in, other.
- booking_url, resy_venue_id, website_url (strings, optional).
- description (string): one or two sentences paraphrased from the source.
- cuisine_tags (list of strings, lowercase): e.g. ["italian", "pasta"].
- vibe_tags (list of strings, lowercase): from this set only: outdoor, date-night,
  group, counter-only, late-night, tasting-menu, natural-wine, casual, nice, rooftop.
- feature_tags (list of strings, lowercase): optional.

Use only the source text. Do not invent fields. Output ONLY the JSON object.
"""


_CODE_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    m = _CODE_FENCE.match(text.strip())
    return m.group(1) if m else text.strip()


def extract_fields(
    *,
    llm: LLMClient,
    source_url: str,
    source_text: str,
    publication: str,
    list_name: str | None,
    blurb: str | None,
    source_date: date | None = None,
    model: str | None = None,
) -> SeedRestaurant:
    user_prompt = (
        f"Source URL: {source_url}\n"
        f"Publication: {publication}\n"
        f"List: {list_name or '(none)'}\n\n"
        f"Source text:\n{source_text}\n"
    )
    raw = llm.complete(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=800,
        temperature=0.1,
        model=model,
    )
    stripped = _strip_code_fence(raw)
    try:
        parsed_raw = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned non-JSON: {raw!r}") from exc
    if not isinstance(parsed_raw, dict):
        raise ValueError("LLM returned non-object JSON")
    parsed = cast(dict[str, object], parsed_raw)

    parsed["sources"] = [
        SeedSource(
            publication=publication,
            list_name=list_name,
            source_url=source_url,
            blurb=blurb,
            source_date=source_date,
        ).model_dump(mode="json")
    ]

    try:
        return SeedRestaurant.model_validate(parsed)
    except ValidationError as exc:
        raise ValueError(f"LLM output failed schema: {exc}") from exc

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Borough = Literal["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
BookingPlatform = Literal["resy", "opentable", "tock", "walk_in", "other"]
RestaurantStatus = Literal["open", "closed", "needs_review"]
TagKind = Literal["cuisine", "vibe", "feature"]
NoteStatus = Literal["want_to_try", "tried", "loved", "skip"]


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized


class Restaurant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    address: str | None = None
    neighborhood: str | None = None
    borough: Borough | None = None
    latitude: float | None = None
    longitude: float | None = None
    price_tier: int | None = Field(default=None, ge=1, le=4)
    booking_platform: BookingPlatform | None = None
    booking_url: str | None = None
    resy_venue_id: str | None = None
    website_url: str | None = None
    description: str | None = None
    status: RestaurantStatus = "open"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    restaurant_id: str
    publication: str = Field(min_length=1)
    list_name: str | None = None
    source_url: str | None = None
    blurb: str | None = None
    source_date: date | None = None


class Tag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    name: str = Field(min_length=1)
    kind: TagKind


class PersonalNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    user_id: int
    restaurant_id: str
    status: NoteStatus
    rating: int | None = Field(default=None, ge=1, le=5)
    note: str | None = None
    visited_date: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SeedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    publication: str = Field(min_length=1)
    list_name: str | None = None
    source_url: str | None = None
    blurb: str | None = None
    source_date: date | None = None


class SeedRestaurant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    address: str | None = None
    neighborhood: str | None = None
    borough: Borough | None = None
    latitude: float | None = None
    longitude: float | None = None
    price_tier: int | None = Field(default=None, ge=1, le=4)
    booking_platform: BookingPlatform | None = None
    booking_url: str | None = None
    resy_venue_id: str | None = None
    website_url: str | None = None
    description: str | None = None
    cuisine_tags: list[str] = Field(default_factory=list)
    vibe_tags: list[str] = Field(default_factory=list)
    feature_tags: list[str] = Field(default_factory=list)
    sources: list[SeedSource] = Field(default_factory=list)

    @field_validator("cuisine_tags", "vibe_tags", "feature_tags")
    @classmethod
    def lowercase_tags(cls, v: list[str]) -> list[str]:
        return sorted({t.strip().lower() for t in v if t and t.strip()})

    def slug(self) -> str:
        parts = [self.name]
        if self.neighborhood:
            parts.append(self.neighborhood)
        return slugify(" ".join(parts))

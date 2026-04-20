from datetime import date

import pytest
from pydantic import ValidationError

from app.models import PersonalNote, Restaurant, SeedRestaurant, SeedSource, Source, Tag


def test_restaurant_roundtrip() -> None:
    r = Restaurant(
        id="lilia-williamsburg",
        name="Lilia",
        neighborhood="Williamsburg",
        borough="Brooklyn",
        price_tier=3,
        booking_platform="resy",
        resy_venue_id="345",
        status="open",
    )
    assert r.id == "lilia-williamsburg"
    dumped = r.model_dump()
    assert Restaurant.model_validate(dumped) == r


def test_restaurant_rejects_invalid_borough() -> None:
    with pytest.raises(ValidationError):
        Restaurant(id="x", name="X", borough="Jersey City")  # type: ignore[arg-type]


def test_restaurant_rejects_invalid_price_tier() -> None:
    with pytest.raises(ValidationError):
        Restaurant(id="x", name="X", price_tier=7)


def test_restaurant_default_status_is_open() -> None:
    r = Restaurant(id="x", name="X")
    assert r.status == "open"


def test_tag_kind_enum() -> None:
    Tag(name="italian", kind="cuisine")
    with pytest.raises(ValidationError):
        Tag(name="italian", kind="mood")  # type: ignore[arg-type]


def test_personal_note_status_enum() -> None:
    n = PersonalNote(user_id=1, restaurant_id="x", status="tried", rating=4)
    assert n.status == "tried"
    with pytest.raises(ValidationError):
        PersonalNote(user_id=1, restaurant_id="x", status="bookmarked")  # type: ignore[arg-type]


def test_personal_note_rating_range() -> None:
    with pytest.raises(ValidationError):
        PersonalNote(user_id=1, restaurant_id="x", status="tried", rating=9)


def test_seed_restaurant_accepts_minimal() -> None:
    s = SeedRestaurant(
        name="Lilia",
        neighborhood="Williamsburg",
        borough="Brooklyn",
        cuisine_tags=["italian"],
        vibe_tags=["date-night"],
        sources=[
            SeedSource(
                publication="eater_nyc",
                list_name="38 Essential",
                source_url="https://example.com",
                blurb="A pasta temple.",
                source_date=date(2025, 6, 1),
            )
        ],
    )
    assert s.slug() == "lilia-williamsburg"


def test_seed_restaurant_slug_strips_nonascii() -> None:
    s = SeedRestaurant(name="Café Maud'", neighborhood="West Village")
    assert s.slug() == "cafe-maud-west-village"


def test_source_requires_publication() -> None:
    with pytest.raises(ValidationError):
        Source(restaurant_id="x", publication="")

"""Google Maps and Beli ratings: stored, preserved on re-seed, shown, never sent to the ranker."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.db import run_migrations
from app.models import SeedRestaurant, SeedSource
from app.services.llm_client import FakeLLMClient
from app.services.ranker import RankingRequest, rank_sync
from app.services.shortlist import ShortlistFilters, fetch_shortlist
from scrapers.importer import import_seed


def _seed(**ratings: float | int | None) -> SeedRestaurant:
    return SeedRestaurant(
        name="Laser Wolf",
        neighborhood="Williamsburg",
        borough="Brooklyn",
        price_tier=3,
        booking_platform="resy",
        cuisine_tags=["israeli"],
        sources=[SeedSource(publication="infatuation")],
        **ratings,  # type: ignore[arg-type]
    )


@pytest.fixture
def db(tmp_path: Path) -> Path:
    p = tmp_path / "ratings.db"
    run_migrations(p)
    return p


def test_migration_adds_rating_columns(db: Path) -> None:
    conn = sqlite3.connect(db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(restaurants)")}
    conn.close()
    assert {"google_rating", "google_review_count", "beli_score"} <= cols


def test_db_rejects_out_of_range_ratings(db: Path) -> None:
    import_seed(db, [_seed()])
    conn = sqlite3.connect(db)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE restaurants SET google_rating = 5.5")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE restaurants SET beli_score = 11")
    conn.close()


@pytest.mark.parametrize(
    "bad",
    [{"google_rating": 0.5}, {"google_rating": 5.1}, {"beli_score": -1}, {"beli_score": 10.5}],
)
def test_seed_model_validates_ranges(bad: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        _seed(**bad)


def test_shortlist_returns_ratings(db: Path) -> None:
    import_seed(db, [_seed(google_rating=4.6, google_review_count=2100, beli_score=8.7)])
    [item] = fetch_shortlist(db, ShortlistFilters())
    assert item.google_rating == 4.6
    assert item.google_review_count == 2100
    assert item.beli_score == 8.7


def test_reseed_without_ratings_keeps_hand_entered_values(db: Path) -> None:
    import_seed(db, [_seed(google_rating=4.6, google_review_count=2100, beli_score=8.7)])
    import_seed(db, [_seed()])  # a publication re-seed carries no ratings
    [item] = fetch_shortlist(db, ShortlistFilters())
    assert (item.google_rating, item.google_review_count, item.beli_score) == (4.6, 2100, 8.7)


def test_reseed_with_new_rating_overwrites(db: Path) -> None:
    import_seed(db, [_seed(google_rating=4.6)])
    import_seed(db, [_seed(google_rating=4.4)])
    [item] = fetch_shortlist(db, ShortlistFilters())
    assert item.google_rating == 4.4


def test_ratings_are_not_sent_to_the_ranker(db: Path) -> None:
    import_seed(db, [_seed(google_rating=4.6, google_review_count=2100, beli_score=8.7)])
    items = fetch_shortlist(db, ShortlistFilters())
    fake = FakeLLMClient(responses=['<card id="laser-wolf-williamsburg">x</card>'])
    rank_sync(llm=fake, request=RankingRequest(shortlist=items), model="test-model")
    prompt = fake.calls[0].user
    assert "laser-wolf-williamsburg" in prompt
    for leaked in ("google", "beli", "4.6", "2100", "8.7"):
        assert leaked not in prompt.lower()

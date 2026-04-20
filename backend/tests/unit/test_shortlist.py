from pathlib import Path

import pytest

from app.db import run_migrations
from app.models import SeedRestaurant, SeedSource
from app.services.shortlist import ShortlistFilters, fetch_shortlist
from scrapers.importer import import_seed


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    p = tmp_path / "seed.db"
    run_migrations(p)
    seeds = [
        SeedRestaurant(
            name="Lilia",
            neighborhood="Williamsburg",
            borough="Brooklyn",
            price_tier=3,
            booking_platform="resy",
            cuisine_tags=["italian"],
            vibe_tags=["date-night"],
            sources=[SeedSource(publication="eater_nyc", list_name="38 Essential")],
        ),
        SeedRestaurant(
            name="Nami Nori",
            neighborhood="West Village",
            borough="Manhattan",
            price_tier=2,
            booking_platform="resy",
            cuisine_tags=["japanese", "sushi"],
            vibe_tags=["casual", "counter-only"],
            sources=[
                SeedSource(publication="eater_nyc", list_name="38 Essential"),
                SeedSource(publication="infatuation", list_name="Hit List"),
            ],
        ),
        SeedRestaurant(
            name="Joe's Pizza",
            neighborhood="West Village",
            borough="Manhattan",
            price_tier=1,
            booking_platform="walk_in",
            cuisine_tags=["pizza"],
            vibe_tags=["casual", "late-night"],
        ),
    ]
    import_seed(p, seeds)
    return p


def test_no_filters_returns_all_open(seeded_db: Path) -> None:
    results = fetch_shortlist(seeded_db, ShortlistFilters())
    assert {r.name for r in results} == {"Lilia", "Nami Nori", "Joe's Pizza"}


def test_neighborhood_filter(seeded_db: Path) -> None:
    results = fetch_shortlist(seeded_db, ShortlistFilters(neighborhoods=["West Village"]))
    assert {r.name for r in results} == {"Nami Nori", "Joe's Pizza"}


def test_borough_filter(seeded_db: Path) -> None:
    results = fetch_shortlist(seeded_db, ShortlistFilters(boroughs=["Brooklyn"]))
    assert {r.name for r in results} == {"Lilia"}


def test_price_ceiling(seeded_db: Path) -> None:
    results = fetch_shortlist(seeded_db, ShortlistFilters(price_ceiling=2))
    assert {r.name for r in results} == {"Nami Nori", "Joe's Pizza"}


def test_tags_enriched(seeded_db: Path) -> None:
    results = fetch_shortlist(seeded_db, ShortlistFilters(neighborhoods=["Williamsburg"]))
    assert len(results) == 1
    lilia = results[0]
    assert "italian" in lilia.cuisine_tags
    assert "date-night" in lilia.vibe_tags
    assert lilia.source_count >= 1


def test_ordered_by_source_count_desc(seeded_db: Path) -> None:
    results = fetch_shortlist(seeded_db, ShortlistFilters())
    # Nami Nori has 2 sources, others have 1 or 0
    assert results[0].name == "Nami Nori"


def test_closed_excluded(seeded_db: Path) -> None:
    import sqlite3

    conn = sqlite3.connect(seeded_db)
    conn.execute("UPDATE restaurants SET status='closed' WHERE id='lilia-williamsburg'")
    conn.commit()
    conn.close()
    results = fetch_shortlist(seeded_db, ShortlistFilters())
    assert "Lilia" not in {r.name for r in results}


def test_needs_review_excluded_by_default(seeded_db: Path) -> None:
    import sqlite3

    conn = sqlite3.connect(seeded_db)
    conn.execute("UPDATE restaurants SET status='needs_review' WHERE id='lilia-williamsburg'")
    conn.commit()
    conn.close()
    results = fetch_shortlist(seeded_db, ShortlistFilters())
    assert "Lilia" not in {r.name for r in results}


def test_limit_applies(seeded_db: Path) -> None:
    results = fetch_shortlist(seeded_db, ShortlistFilters(), limit=1)
    assert len(results) == 1

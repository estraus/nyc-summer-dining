from datetime import date
from pathlib import Path

import pytest

from app.db import connect, run_migrations
from app.models import SeedRestaurant, SeedSource
from scrapers.importer import import_seed


@pytest.fixture
def db(tmp_path: Path) -> Path:
    p = tmp_path / "import.db"
    run_migrations(p)
    return p


def _sample() -> list[SeedRestaurant]:
    return [
        SeedRestaurant(
            name="Lilia",
            neighborhood="Williamsburg",
            borough="Brooklyn",
            price_tier=3,
            booking_platform="resy",
            resy_venue_id="345",
            cuisine_tags=["italian"],
            vibe_tags=["date-night"],
            sources=[
                SeedSource(
                    publication="eater_nyc",
                    list_name="38 Essential",
                    blurb="A pasta temple.",
                    source_date=date(2025, 6, 1),
                )
            ],
        ),
        SeedRestaurant(
            name="Nami Nori",
            neighborhood="West Village",
            borough="Manhattan",
            price_tier=2,
            booking_platform="resy",
            cuisine_tags=["japanese", "sushi"],
            vibe_tags=["casual", "counter-only"],
        ),
    ]


def test_import_inserts_restaurants_and_tags(db: Path) -> None:
    result = import_seed(db, _sample())
    assert result.inserted == 2
    assert result.updated == 0

    conn = connect(db)
    try:
        rows = conn.execute("SELECT id, name FROM restaurants ORDER BY id").fetchall()
        tag_rows = conn.execute("SELECT t.name, t.kind FROM tags t ORDER BY t.name").fetchall()
        rt_count = conn.execute("SELECT COUNT(*) FROM restaurant_tags").fetchone()[0]
        src_count = conn.execute("SELECT COUNT(*) FROM restaurant_sources").fetchone()[0]
    finally:
        conn.close()

    assert [r["name"] for r in rows] == ["Lilia", "Nami Nori"]
    tag_tuples = {(t["name"], t["kind"]) for t in tag_rows}
    assert ("italian", "cuisine") in tag_tuples
    assert ("date-night", "vibe") in tag_tuples
    assert ("counter-only", "vibe") in tag_tuples
    # 1 (italian) + 1 (date-night) + 2 (japanese, sushi) + 2 (casual, counter-only) = 6
    assert rt_count == 6
    assert src_count == 1


def test_import_is_idempotent(db: Path) -> None:
    import_seed(db, _sample())
    result = import_seed(db, _sample())
    assert result.inserted == 0
    assert result.updated == 2

    conn = connect(db)
    try:
        count = conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0]
        tag_count = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    finally:
        conn.close()
    assert count == 2
    assert tag_count == 6


def test_import_updates_changed_fields(db: Path) -> None:
    import_seed(db, _sample())
    updated = _sample()
    updated[0].price_tier = 4
    result = import_seed(db, updated)
    assert result.updated >= 1

    conn = connect(db)
    try:
        row = conn.execute(
            "SELECT price_tier FROM restaurants WHERE id = ?", ("lilia-williamsburg",)
        ).fetchone()
    finally:
        conn.close()
    assert row["price_tier"] == 4


def test_import_from_json_file(tmp_path: Path, db: Path) -> None:
    path = tmp_path / "seed.json"
    path.write_text(
        '[{"name": "Joe\'s Pizza", "neighborhood": "West Village", "borough": "Manhattan",'
        ' "price_tier": 1, "booking_platform": "walk_in", "cuisine_tags": ["pizza"],'
        ' "vibe_tags": [], "sources": []}]'
    )
    from scrapers.importer import import_seed_file

    result = import_seed_file(db, path)
    assert result.inserted == 1

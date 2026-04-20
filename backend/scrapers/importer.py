from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.db import connect
from app.models import SeedRestaurant, TagKind


@dataclass(frozen=True)
class ImportResult:
    inserted: int
    updated: int


def _upsert_tags(conn: sqlite3.Connection, names: list[str], kind: TagKind) -> list[int]:
    ids: list[int] = []
    for name in names:
        conn.execute(
            "INSERT OR IGNORE INTO tags (name, kind) VALUES (?, ?)",
            (name, kind),
        )
        row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
        if row is not None:
            ids.append(row["id"])
    return ids


def _attach_tags(conn: sqlite3.Connection, restaurant_id: str, tag_ids: list[int]) -> None:
    for tag_id in tag_ids:
        conn.execute(
            "INSERT OR IGNORE INTO restaurant_tags (restaurant_id, tag_id) VALUES (?, ?)",
            (restaurant_id, tag_id),
        )


def _replace_sources(conn: sqlite3.Connection, restaurant_id: str, seed: SeedRestaurant) -> None:
    conn.execute("DELETE FROM restaurant_sources WHERE restaurant_id = ?", (restaurant_id,))
    for s in seed.sources:
        conn.execute(
            """
            INSERT INTO restaurant_sources
              (restaurant_id, publication, list_name, source_url, blurb, source_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                restaurant_id,
                s.publication,
                s.list_name,
                s.source_url,
                s.blurb,
                s.source_date.isoformat() if s.source_date else None,
            ),
        )


def import_seed(db_path: Path, seeds: list[SeedRestaurant]) -> ImportResult:
    inserted = 0
    updated = 0
    conn = connect(db_path)
    try:
        for seed in seeds:
            slug = seed.slug()
            existing = conn.execute("SELECT id FROM restaurants WHERE id = ?", (slug,)).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO restaurants
                      (id, name, address, neighborhood, borough, latitude, longitude,
                       price_tier, booking_platform, booking_url, resy_venue_id, website_url,
                       description, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                    """,
                    (
                        slug,
                        seed.name,
                        seed.address,
                        seed.neighborhood,
                        seed.borough,
                        seed.latitude,
                        seed.longitude,
                        seed.price_tier,
                        seed.booking_platform,
                        seed.booking_url,
                        seed.resy_venue_id,
                        seed.website_url,
                        seed.description,
                    ),
                )
                inserted += 1
            else:
                conn.execute(
                    """
                    UPDATE restaurants SET
                        name=?, address=?, neighborhood=?, borough=?, latitude=?, longitude=?,
                        price_tier=?, booking_platform=?, booking_url=?, resy_venue_id=?,
                        website_url=?, description=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (
                        seed.name,
                        seed.address,
                        seed.neighborhood,
                        seed.borough,
                        seed.latitude,
                        seed.longitude,
                        seed.price_tier,
                        seed.booking_platform,
                        seed.booking_url,
                        seed.resy_venue_id,
                        seed.website_url,
                        seed.description,
                        slug,
                    ),
                )
                updated += 1

            cuisine_ids = _upsert_tags(conn, seed.cuisine_tags, "cuisine")
            vibe_ids = _upsert_tags(conn, seed.vibe_tags, "vibe")
            feature_ids = _upsert_tags(conn, seed.feature_tags, "feature")
            _attach_tags(conn, slug, [*cuisine_ids, *vibe_ids, *feature_ids])
            _replace_sources(conn, slug, seed)
    finally:
        conn.close()
    return ImportResult(inserted=inserted, updated=updated)


def import_seed_file(db_path: Path, json_path: Path) -> ImportResult:
    raw = json.loads(json_path.read_text())
    seeds = [SeedRestaurant.model_validate(item) for item in raw]
    return import_seed(db_path, seeds)

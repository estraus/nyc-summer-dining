from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from app.db import connect


class ShortlistFilters(BaseModel):
    neighborhoods: list[str] = Field(default_factory=list[str])
    boroughs: list[str] = Field(default_factory=list[str])
    price_ceiling: int | None = Field(default=None, ge=1, le=4)
    include_closed: bool = False
    include_needs_review: bool = False


@dataclass(frozen=True)
class ShortlistItem:
    id: str
    name: str
    neighborhood: str | None
    borough: str | None
    price_tier: int | None
    booking_platform: str | None
    booking_url: str | None
    resy_venue_id: str | None
    description: str | None
    cuisine_tags: list[str] = field(default_factory=list[str])
    vibe_tags: list[str] = field(default_factory=list[str])
    feature_tags: list[str] = field(default_factory=list[str])
    sources: list[dict[str, str | None]] = field(default_factory=list[dict[str, str | None]])
    source_count: int = 0


def _build_where(filters: ShortlistFilters) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []

    allowed_statuses = ["open"]
    if filters.include_closed:
        allowed_statuses.append("closed")
    if filters.include_needs_review:
        allowed_statuses.append("needs_review")
    clauses.append("r.status IN (" + ",".join("?" * len(allowed_statuses)) + ")")
    params.extend(allowed_statuses)

    if filters.neighborhoods:
        clauses.append("r.neighborhood IN (" + ",".join("?" * len(filters.neighborhoods)) + ")")
        params.extend(filters.neighborhoods)

    if filters.boroughs:
        clauses.append("r.borough IN (" + ",".join("?" * len(filters.boroughs)) + ")")
        params.extend(filters.boroughs)

    if filters.price_ceiling is not None:
        clauses.append("(r.price_tier IS NULL OR r.price_tier <= ?)")
        params.append(filters.price_ceiling)

    return " AND ".join(clauses), params


def fetch_shortlist(
    db_path: Path, filters: ShortlistFilters, *, limit: int = 40
) -> list[ShortlistItem]:
    where, params = _build_where(filters)
    conn = connect(db_path)
    try:
        rows = conn.execute(
            f"""
            SELECT r.id, r.name, r.neighborhood, r.borough, r.price_tier,
                   r.booking_platform, r.booking_url, r.resy_venue_id, r.description,
                   COALESCE((SELECT COUNT(*) FROM restaurant_sources rs
                             WHERE rs.restaurant_id = r.id), 0) AS source_count
            FROM restaurants r
            WHERE {where}
            ORDER BY source_count DESC, r.updated_at DESC, r.name ASC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        if not rows:
            return []

        ids = [row["id"] for row in rows]
        placeholders = ",".join("?" * len(ids))

        tags_by_restaurant: dict[str, dict[str, list[str]]] = {
            rid: {"cuisine": [], "vibe": [], "feature": []} for rid in ids
        }
        for t in conn.execute(
            f"""
            SELECT rt.restaurant_id, t.name, t.kind FROM tags t
            JOIN restaurant_tags rt ON rt.tag_id = t.id
            WHERE rt.restaurant_id IN ({placeholders})
            """,
            ids,
        ).fetchall():
            bucket = tags_by_restaurant[t["restaurant_id"]]
            kind = t["kind"] if t["kind"] in bucket else "feature"
            bucket[kind].append(t["name"])

        sources_by_restaurant: dict[str, list[dict[str, str | None]]] = {rid: [] for rid in ids}
        for s in conn.execute(
            f"""
            SELECT restaurant_id, publication, list_name, blurb
            FROM restaurant_sources WHERE restaurant_id IN ({placeholders})
            """,
            ids,
        ).fetchall():
            sources_by_restaurant[s["restaurant_id"]].append(
                {
                    "publication": s["publication"],
                    "list_name": s["list_name"],
                    "blurb": s["blurb"],
                }
            )

        items: list[ShortlistItem] = []
        for row in rows:
            tags = tags_by_restaurant[row["id"]]
            items.append(
                ShortlistItem(
                    id=row["id"],
                    name=row["name"],
                    neighborhood=row["neighborhood"],
                    borough=row["borough"],
                    price_tier=row["price_tier"],
                    booking_platform=row["booking_platform"],
                    booking_url=row["booking_url"],
                    resy_venue_id=row["resy_venue_id"],
                    description=row["description"],
                    cuisine_tags=sorted(tags["cuisine"]),
                    vibe_tags=sorted(tags["vibe"]),
                    feature_tags=sorted(tags["feature"]),
                    sources=sources_by_restaurant[row["id"]],
                    source_count=int(row["source_count"]),
                )
            )
        return items
    finally:
        conn.close()

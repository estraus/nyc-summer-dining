from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from selectolax.parser import HTMLParser

from app.config import get_settings
from app.db import connect
from app.dependencies import get_llm_client
from app.models import SeedRestaurant, SeedSource, slugify
from app.services.fields_extractor import extract_fields
from scrapers.common import DEFAULT_HEADERS

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Response / Request models
# ---------------------------------------------------------------------------


class SourceItem(BaseModel):
    id: int
    publication: str
    list_name: str | None
    source_url: str | None
    blurb: str | None
    source_date: str | None


class RestaurantAdminItem(BaseModel):
    id: str
    name: str
    address: str | None
    neighborhood: str | None
    borough: str | None
    latitude: float | None
    longitude: float | None
    price_tier: int | None
    booking_platform: str | None
    booking_url: str | None
    resy_venue_id: str | None
    website_url: str | None
    description: str | None
    status: str
    created_at: str | None
    updated_at: str | None
    cuisine_tags: list[str]
    vibe_tags: list[str]
    feature_tags: list[str]
    source_count: int


class RestaurantDetail(RestaurantAdminItem):
    sources: list[SourceItem]


class RestaurantCreateRequest(BaseModel):
    name: str
    address: str | None = None
    neighborhood: str | None = None
    borough: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    price_tier: int | None = None
    booking_platform: str | None = None
    booking_url: str | None = None
    resy_venue_id: str | None = None
    website_url: str | None = None
    description: str | None = None
    cuisine_tags: list[str] = []
    vibe_tags: list[str] = []
    feature_tags: list[str] = []
    sources: list[dict[str, Any]] = []


class RestaurantUpdateRequest(BaseModel):
    name: str | None = None
    address: str | None = None
    neighborhood: str | None = None
    borough: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    price_tier: int | None = None
    booking_platform: str | None = None
    booking_url: str | None = None
    resy_venue_id: str | None = None
    website_url: str | None = None
    description: str | None = None
    cuisine_tags: list[str] | None = None
    vibe_tags: list[str] | None = None
    feature_tags: list[str] | None = None


class AddByUrlRequest(BaseModel):
    url: str


class AddByNameRequest(BaseModel):
    name: str
    neighborhood: str | None = None


class ReseedApplyRequest(BaseModel):
    seeds: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetch_tags(conn: Any, restaurant_id: str) -> tuple[list[str], list[str], list[str]]:
    """Return (cuisine_tags, vibe_tags, feature_tags) for a restaurant."""
    rows = conn.execute(
        """
        SELECT t.name, t.kind
        FROM tags t
        JOIN restaurant_tags rt ON rt.tag_id = t.id
        WHERE rt.restaurant_id = ?
        ORDER BY t.kind, t.name
        """,
        (restaurant_id,),
    ).fetchall()
    cuisine: list[str] = []
    vibe: list[str] = []
    feature: list[str] = []
    for row in rows:
        if row["kind"] == "cuisine":
            cuisine.append(row["name"])
        elif row["kind"] == "vibe":
            vibe.append(row["name"])
        else:
            feature.append(row["name"])
    return cuisine, vibe, feature


def _fetch_sources(conn: Any, restaurant_id: str) -> list[SourceItem]:
    rows = conn.execute(
        """
        SELECT id, publication, list_name, source_url, blurb, source_date
        FROM restaurant_sources
        WHERE restaurant_id = ?
        ORDER BY id
        """,
        (restaurant_id,),
    ).fetchall()
    return [
        SourceItem(
            id=row["id"],
            publication=row["publication"],
            list_name=row["list_name"],
            source_url=row["source_url"],
            blurb=row["blurb"],
            source_date=row["source_date"],
        )
        for row in rows
    ]


def _row_to_admin_item(conn: Any, row: Any) -> RestaurantAdminItem:
    rid = row["id"]
    cuisine, vibe, feature = _fetch_tags(conn, rid)
    source_count = conn.execute(
        "SELECT COUNT(*) FROM restaurant_sources WHERE restaurant_id = ?", (rid,)
    ).fetchone()[0]
    return RestaurantAdminItem(
        id=rid,
        name=row["name"],
        address=row["address"],
        neighborhood=row["neighborhood"],
        borough=row["borough"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        price_tier=row["price_tier"],
        booking_platform=row["booking_platform"],
        booking_url=row["booking_url"],
        resy_venue_id=row["resy_venue_id"],
        website_url=row["website_url"],
        description=row["description"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        cuisine_tags=cuisine,
        vibe_tags=vibe,
        feature_tags=feature,
        source_count=source_count,
    )


def _upsert_tags(conn: Any, restaurant_id: str, names: list[str], kind: str) -> None:
    for name in names:
        conn.execute(
            "INSERT OR IGNORE INTO tags (name, kind) VALUES (?, ?)",
            (name.strip().lower(), kind),
        )
        row = conn.execute("SELECT id FROM tags WHERE name = ?", (name.strip().lower(),)).fetchone()
        if row is not None:
            conn.execute(
                "INSERT OR IGNORE INTO restaurant_tags (restaurant_id, tag_id) VALUES (?, ?)",
                (restaurant_id, row["id"]),
            )


def _replace_tags(
    conn: Any, restaurant_id: str, cuisine: list[str], vibe: list[str], feature: list[str]
) -> None:
    """Delete all existing tag associations and re-insert."""
    conn.execute("DELETE FROM restaurant_tags WHERE restaurant_id = ?", (restaurant_id,))
    _upsert_tags(conn, restaurant_id, cuisine, "cuisine")
    _upsert_tags(conn, restaurant_id, vibe, "vibe")
    _upsert_tags(conn, restaurant_id, feature, "feature")


# ---------------------------------------------------------------------------
# Routes: Restaurant CRUD
# ---------------------------------------------------------------------------


@router.get("/restaurants", response_model=list[RestaurantAdminItem])
def list_restaurants(
    status: str = "all",
    q: str = "",
) -> list[RestaurantAdminItem]:
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        if status == "all":
            sql = "SELECT * FROM restaurants WHERE 1=1"
            params: list[Any] = []
        else:
            sql = "SELECT * FROM restaurants WHERE status = ?"
            params = [status]
        if q:
            sql += " AND name LIKE ?"
            params.append(f"%{q}%")
        sql += " ORDER BY name"
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_admin_item(conn, row) for row in rows]
    finally:
        conn.close()


@router.get("/restaurants/{restaurant_id}", response_model=RestaurantDetail)
def get_restaurant(restaurant_id: str) -> RestaurantDetail:
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        row = conn.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="restaurant_not_found")
        item = _row_to_admin_item(conn, row)
        sources = _fetch_sources(conn, restaurant_id)
        return RestaurantDetail(**item.model_dump(), sources=sources)
    finally:
        conn.close()


@router.post("/restaurants", response_model=dict[str, str])
def create_restaurant(body: RestaurantCreateRequest) -> dict[str, str]:
    seed = SeedRestaurant(
        name=body.name,
        address=body.address,
        neighborhood=body.neighborhood,
        borough=body.borough,  # type: ignore[arg-type]
        latitude=body.latitude,
        longitude=body.longitude,
        price_tier=body.price_tier,
        booking_platform=body.booking_platform,  # type: ignore[arg-type]
        booking_url=body.booking_url,
        resy_venue_id=body.resy_venue_id,
        website_url=body.website_url,
        description=body.description,
        cuisine_tags=body.cuisine_tags,
        vibe_tags=body.vibe_tags,
        feature_tags=body.feature_tags,
        sources=[SeedSource.model_validate(s) for s in body.sources],
    )
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        restaurant_id = seed.slug()
        existing = conn.execute(
            "SELECT id FROM restaurants WHERE id = ?", (restaurant_id,)
        ).fetchone()
        if existing is not None:
            raise HTTPException(status_code=409, detail="restaurant_already_exists")
        conn.execute(
            """
            INSERT INTO restaurants
              (id, name, address, neighborhood, borough, latitude, longitude,
               price_tier, booking_platform, booking_url, resy_venue_id, website_url,
               description, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
            """,
            (
                restaurant_id,
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
        _replace_tags(conn, restaurant_id, seed.cuisine_tags, seed.vibe_tags, seed.feature_tags)
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
        return {"id": restaurant_id}
    finally:
        conn.close()


@router.put("/restaurants/{restaurant_id}", response_model=RestaurantAdminItem)
def update_restaurant(restaurant_id: str, body: RestaurantUpdateRequest) -> RestaurantAdminItem:
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        row = conn.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="restaurant_not_found")

        # Build SET clause for scalar fields
        scalar_fields = [
            "name",
            "address",
            "neighborhood",
            "borough",
            "latitude",
            "longitude",
            "price_tier",
            "booking_platform",
            "booking_url",
            "resy_venue_id",
            "website_url",
            "description",
        ]
        updates: list[str] = []
        values: list[Any] = []
        data = body.model_dump(exclude_unset=True)
        for f in scalar_fields:
            if f in data:
                updates.append(f"{f} = ?")
                values.append(data[f])

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(restaurant_id)
            conn.execute(
                f"UPDATE restaurants SET {', '.join(updates)} WHERE id = ?",
                values,
            )

        # Handle tag updates if provided
        if "cuisine_tags" in data or "vibe_tags" in data or "feature_tags" in data:
            # Re-read current tags for any dimension not provided
            current_cuisine, current_vibe, current_feature = _fetch_tags(conn, restaurant_id)
            new_cuisine = data.get("cuisine_tags", current_cuisine)
            new_vibe = data.get("vibe_tags", current_vibe)
            new_feature = data.get("feature_tags", current_feature)
            _replace_tags(conn, restaurant_id, new_cuisine, new_vibe, new_feature)

        row = conn.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)).fetchone()
        return _row_to_admin_item(conn, row)
    finally:
        conn.close()


@router.post("/restaurants/{restaurant_id}/close")
def close_restaurant(restaurant_id: str) -> dict[str, bool]:
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        row = conn.execute("SELECT id FROM restaurants WHERE id = ?", (restaurant_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="restaurant_not_found")
        conn.execute(
            "UPDATE restaurants SET status='closed', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (restaurant_id,),
        )
        return {"ok": True}
    finally:
        conn.close()


@router.post("/restaurants/{restaurant_id}/resolve")
def resolve_restaurant(restaurant_id: str) -> dict[str, bool]:
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        row = conn.execute("SELECT id FROM restaurants WHERE id = ?", (restaurant_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="restaurant_not_found")
        conn.execute(
            "UPDATE restaurants SET status='open', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (restaurant_id,),
        )
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/restaurants/{restaurant_id}", status_code=204)
def delete_restaurant(restaurant_id: str) -> None:
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        row = conn.execute("SELECT id FROM restaurants WHERE id = ?", (restaurant_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="restaurant_not_found")
        conn.execute("DELETE FROM restaurants WHERE id = ?", (restaurant_id,))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Routes: Add by URL / Add by Name
# ---------------------------------------------------------------------------


@router.post("/add-by-url")
def add_by_url(body: AddByUrlRequest) -> dict[str, Any]:
    """Fetch a URL, extract text, pass to LLM, return prefill dict."""
    response = httpx.get(body.url, headers=DEFAULT_HEADERS, timeout=20.0, follow_redirects=True)
    response.raise_for_status()
    html = response.text
    tree = HTMLParser(html)
    body_node = tree.body
    text = body_node.text(strip=True, separator="\n") if body_node else html
    llm = get_llm_client()
    settings = get_settings()
    seed = extract_fields(
        llm=llm,
        source_url=body.url,
        source_text=text,
        publication="manual",
        list_name=None,
        blurb=None,
        source_date=None,
        model=settings.active_llm_model,
    )
    return seed.model_dump(mode="json")


@router.post("/add-by-name")
def add_by_name(body: AddByNameRequest) -> dict[str, Any]:
    """Build minimal source text from name + neighborhood, call LLM, return prefill."""
    neighborhood = body.neighborhood or "NYC"
    source_text = f"Restaurant name: {body.name}\nNeighborhood: {neighborhood}"
    llm = get_llm_client()
    settings = get_settings()
    seed = extract_fields(
        llm=llm,
        source_url="",
        source_text=source_text,
        publication="manual",
        list_name=None,
        blurb=None,
        source_date=None,
        model=settings.active_llm_model,
    )
    return seed.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Routes: Reseed
# ---------------------------------------------------------------------------

_SCRAPERS = {
    "eater_essentials": "scrapers.eater_essentials",
}


@router.get("/reseed-preview/{publication}")
def reseed_preview(publication: str) -> dict[str, Any]:
    """Run the named scraper and compare to DB — expensive, shows spinner in UI."""
    if publication not in _SCRAPERS:
        raise HTTPException(status_code=404, detail="unknown_publication")

    import importlib

    mod = importlib.import_module(_SCRAPERS[publication])
    llm = get_llm_client()
    seeds: list[SeedRestaurant] = mod.scrape(llm=llm)

    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        existing_ids = {row["id"] for row in conn.execute("SELECT id FROM restaurants").fetchall()}
    finally:
        conn.close()

    new_ids: list[str] = []
    updated_ids: list[str] = []
    unchanged_ids: list[str] = []

    for seed in seeds:
        sid = seed.slug()
        if sid not in existing_ids:
            new_ids.append(sid)
        else:
            # Simple heuristic: mark as updated (full diff is expensive)
            updated_ids.append(sid)

    return {
        "new": new_ids,
        "updated": updated_ids,
        "unchanged": unchanged_ids,
        "seeds": [s.model_dump(mode="json") for s in seeds],
    }


@router.post("/reseed-apply")
def reseed_apply(body: ReseedApplyRequest) -> dict[str, int]:
    """Apply a list of seed dicts (e.g. from reseed-preview) to the DB."""
    from scrapers.importer import import_seed

    seeds = [SeedRestaurant.model_validate(s) for s in body.seeds]
    settings = get_settings()
    result = import_seed(settings.db_path, seeds)
    return {"inserted": result.inserted, "updated": result.updated}


# ---------------------------------------------------------------------------
# Utility: expose slugify for use in admin page
# ---------------------------------------------------------------------------

_ = slugify  # keep import alive for pyright

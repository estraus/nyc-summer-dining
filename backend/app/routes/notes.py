from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import connect
from app.models import NoteStatus

router = APIRouter(prefix="/api/notes", tags=["notes"])


class NoteResponse(BaseModel):
    id: int
    user_id: int
    restaurant_id: str
    status: NoteStatus
    rating: int | None
    note: str | None
    visited_date: date_type | None


class UpsertNoteRequest(BaseModel):
    status: NoteStatus
    rating: int | None = Field(default=None, ge=1, le=5)
    note: str | None = None
    visited_date: date_type | None = None


@router.get("", response_model=dict[str, NoteResponse])
def list_notes(request: Request) -> dict[str, NoteResponse]:
    user_id: int = request.state.user_id
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        rows = conn.execute(
            """
            SELECT id, user_id, restaurant_id, status, rating, note, visited_date
            FROM personal_notes
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return {
        row["restaurant_id"]: NoteResponse(
            id=row["id"],
            user_id=row["user_id"],
            restaurant_id=row["restaurant_id"],
            status=row["status"],
            rating=row["rating"],
            note=row["note"],
            visited_date=row["visited_date"],
        )
        for row in rows
    }


@router.put("/{restaurant_id}", response_model=NoteResponse)
def upsert_note(restaurant_id: str, body: UpsertNoteRequest, request: Request) -> NoteResponse:
    user_id: int = request.state.user_id
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        exists = conn.execute(
            "SELECT 1 FROM restaurants WHERE id = ?",
            (restaurant_id,),
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="restaurant_not_found")

        row = conn.execute(
            """
            INSERT INTO personal_notes (user_id, restaurant_id, status, rating, note, visited_date,
                                        updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, restaurant_id) DO UPDATE SET
                status = excluded.status,
                rating = excluded.rating,
                note = excluded.note,
                visited_date = excluded.visited_date,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, user_id, restaurant_id, status, rating, note, visited_date
            """,
            (
                user_id,
                restaurant_id,
                body.status,
                body.rating,
                body.note,
                body.visited_date.isoformat() if body.visited_date else None,
            ),
        ).fetchone()
    finally:
        conn.close()

    return NoteResponse(
        id=row["id"],
        user_id=row["user_id"],
        restaurant_id=row["restaurant_id"],
        status=row["status"],
        rating=row["rating"],
        note=row["note"],
        visited_date=row["visited_date"],
    )


@router.delete("/{restaurant_id}", status_code=204)
def delete_note(restaurant_id: str, request: Request) -> None:
    user_id: int = request.state.user_id
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        conn.execute(
            "DELETE FROM personal_notes WHERE user_id = ? AND restaurant_id = ?",
            (user_id, restaurant_id),
        )
    finally:
        conn.close()

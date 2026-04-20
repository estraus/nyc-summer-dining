from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.db import connect

_NAME_RE = re.compile(r"^[A-Za-z0-9 ._-]{1,50}$")


@dataclass(frozen=True)
class User:
    id: int
    display_name: str


def _validate_name(name: str) -> str:
    stripped = name.strip()
    if not stripped or not _NAME_RE.match(stripped):
        raise ValueError("invalid display name")
    return stripped


def create_user(db_path: Path, display_name: str) -> User:
    name = _validate_name(display_name)
    conn = connect(db_path)
    try:
        existing = conn.execute(
            "SELECT id, display_name FROM users WHERE display_name = ?", (name,)
        ).fetchone()
        if existing:
            return User(id=existing["id"], display_name=existing["display_name"])
        cur = conn.execute("INSERT INTO users (display_name) VALUES (?)", (name,))
        return User(id=int(cur.lastrowid or 0), display_name=name)
    finally:
        conn.close()


def get_user_by_name(db_path: Path, display_name: str) -> User | None:
    name = _validate_name(display_name)
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, display_name FROM users WHERE display_name = ?", (name,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return User(id=row["id"], display_name=row["display_name"])


def get_user_by_id(db_path: Path, user_id: int) -> User | None:
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, display_name FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return User(id=row["id"], display_name=row["display_name"])


def list_users(db_path: Path) -> list[User]:
    conn: sqlite3.Connection = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, display_name FROM users ORDER BY display_name COLLATE NOCASE"
        ).fetchall()
    finally:
        conn.close()
    return [User(id=r["id"], display_name=r["display_name"]) for r in rows]

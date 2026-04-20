from pathlib import Path

import pytest

from app.db import connect, run_migrations


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


def test_run_migrations_creates_tables(tmp_db: Path) -> None:
    run_migrations(tmp_db)
    conn = connect(tmp_db)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    names = {r[0] for r in rows}
    assert {
        "restaurants",
        "restaurant_sources",
        "tags",
        "restaurant_tags",
        "users",
        "personal_notes",
        "schema_versions",
    }.issubset(names)


def test_run_migrations_is_idempotent(tmp_db: Path) -> None:
    run_migrations(tmp_db)
    run_migrations(tmp_db)
    conn = connect(tmp_db)
    try:
        versions = conn.execute("SELECT version FROM schema_versions ORDER BY version").fetchall()
    finally:
        conn.close()
    assert [v[0] for v in versions] == [1]


def test_foreign_keys_enabled(tmp_db: Path) -> None:
    run_migrations(tmp_db)
    conn = connect(tmp_db)
    try:
        result = conn.execute("PRAGMA foreign_keys").fetchone()
    finally:
        conn.close()
    assert result[0] == 1

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_startup_runs_migrations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "startup.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    from app.main import create_app  # imported after env set

    app = create_app()
    with TestClient(app):
        conn = sqlite3.connect(db_path)
        try:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        finally:
            conn.close()
    assert "restaurants" in names
    assert "schema_versions" in names

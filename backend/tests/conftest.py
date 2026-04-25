from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import dependencies
from app.config import get_settings


@pytest.fixture(autouse=True)
def _clear_caches() -> Iterator[None]:
    from app.routes import auth as auth_routes
    from app.routes import search as search_routes

    get_settings.cache_clear()
    dependencies._real_resy.cache_clear()
    dependencies._real_llm.cache_clear()
    auth_routes._reset_login_limiter()
    search_routes._reset_search_limiter()
    yield
    get_settings.cache_clear()
    dependencies._real_resy.cache_clear()
    dependencies._real_llm.cache_clear()
    auth_routes._reset_login_limiter()
    search_routes._reset_search_limiter()


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    return db_path


@pytest.fixture
def client(tmp_db: Path) -> Iterator[TestClient]:
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c

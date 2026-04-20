# NYC Summer Dining Recommender Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AI-powered NYC restaurant recommender with filter+rank search, progressive streaming, and on-demand Resy availability checking.

**Architecture:** Python+FastAPI backend with SQLite, vanilla HTML/CSS/JS frontend. Claude Haiku 4.5 ranks shortlists with streaming reasons. Deployed on Fly.io with auto-stop (scale-to-zero). Shared-password auth + per-user name picker.

**Tech Stack:** Python 3.12, FastAPI, SQLite, `uv`, pytest, Anthropic SDK (`claude-haiku-4-5-20251001`), httpx, selectolax, bcrypt, itsdangerous.

**Scope (this plan):** MVP Phases 1-9 from the spec — Foundation → DB → Auth → Data Model → First Scraper → Search Backend → Search Frontend → Streaming → Availability. Admin page, personal notes, remaining scrapers, and ops/backups are out of scope for this plan (covered by a follow-up plan).

**Repo root:** `/Users/elistraus/opt/Claude/dining/`. All paths below are relative to this root unless noted.

---

## Conventions

- **Package manager**: `uv` (installs from `backend/pyproject.toml`). All Python commands are run from `backend/` unless otherwise noted.
- **Testing**: `pytest` with `pytest-asyncio` for async tests. All tests live under `backend/tests/`.
- **Linting**: `ruff` (format + lint). Type-checking: `pyright`.
- **Commits**: conventional-ish — `feat:`, `test:`, `chore:`, `fix:`. One commit per task (end of task).
- **TDD**: every functional change is test-first. Write the failing test, confirm it fails for the right reason, implement the minimum, watch it pass.

---

## Phase 1: Foundation

Goal: a runnable FastAPI app returning `/healthz`, a static frontend shell, a Docker image that builds, and CI that runs tests.

### Task 1: Repo scaffolding and `pyproject.toml`

**Files:**
- Create: `backend/pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/unit/__init__.py`
- Create: `backend/tests/integration/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "dining"
version = "0.1.0"
description = "NYC summer dining recommender"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "httpx>=0.27",
    "selectolax>=0.3.25",
    "bcrypt>=4.2",
    "itsdangerous>=2.2",
    "anthropic>=0.39",
    "structlog>=24.4",
    "python-multipart>=0.0.12",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "ruff>=0.7",
    "pyright>=1.1",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-ra --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]

[tool.pyright]
include = ["app", "scrapers", "tests"]
pythonVersion = "3.12"
strict = ["app/**"]
```

- [ ] **Step 2: Create `.gitignore` at repo root**

```
# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.ruff_cache/
.pyright/
htmlcov/
.coverage
*.egg-info/
dist/
build/

# Env
.env
.env.local
.venv/
venv/

# Local data
data/restaurants.db
data/restaurants.db-journal
data/restaurants.db-wal
data/restaurants.db-shm

# OS
.DS_Store
```

- [ ] **Step 3: Create `README.md`**

```markdown
# NYC Summer Dining Recommender

Personal AI-powered dining app. See `docs/superpowers/specs/2026-04-17-nyc-summer-dining-design.md` for the design spec and `docs/superpowers/plans/2026-04-17-nyc-summer-dining.md` for the implementation plan.

## Dev

```bash
cd backend
uv sync
uv run pytest
uv run uvicorn app.main:app --reload
```

Then open http://localhost:8000.
```

- [ ] **Step 4: Create package init files (empty)**

Create these four files with empty content:
- `backend/app/__init__.py`
- `backend/tests/__init__.py`
- `backend/tests/unit/__init__.py`
- `backend/tests/integration/__init__.py`

- [ ] **Step 5: Create `backend/app/main.py` (stub)**

```python
from fastapi import FastAPI

app = FastAPI(title="NYC Dining")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Create `backend/tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
```

- [ ] **Step 7: Install deps and verify**

Run from `backend/`:

```bash
uv sync
uv run python -c "from app.main import app; print(app.title)"
```

Expected: `NYC Dining`.

- [ ] **Step 8: Commit**

```bash
cd /Users/elistraus/opt/Claude/dining
git add backend/pyproject.toml backend/app backend/tests .gitignore README.md
git commit -m "feat(dining): scaffold backend package with FastAPI healthz"
```

---

### Task 2: Healthz integration test

**Files:**
- Create: `backend/tests/integration/test_healthz.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient


def test_healthz_returns_ok(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it passes (healthz is already wired)**

From `backend/`:

```bash
uv run pytest tests/integration/test_healthz.py -v
```

Expected: 1 passed. (Implementation already exists from Task 1 — this locks behavior.)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/integration/test_healthz.py
git commit -m "test(dining): pin healthz contract"
```

---

### Task 3: Static frontend mount

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/css/app.css`
- Create: `frontend/js/app.js`
- Modify: `backend/app/main.py`
- Create: `backend/tests/integration/test_static.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_static.py`:

```python
from fastapi.testclient import TestClient


def test_root_serves_index_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>" in response.text.lower()


def test_css_served(client: TestClient) -> None:
    response = client.get("/css/app.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
```

- [ ] **Step 2: Run it and confirm failure**

```bash
uv run pytest tests/integration/test_static.py -v
```

Expected: both fail with 404.

- [ ] **Step 3: Create `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NYC Dining</title>
  <link rel="stylesheet" href="/css/app.css" />
</head>
<body>
  <main id="app">
    <h1>NYC Dining</h1>
    <p id="status">Loading&hellip;</p>
  </main>
  <script src="/js/app.js" type="module"></script>
</body>
</html>
```

- [ ] **Step 4: Create `frontend/css/app.css`**

```css
:root { color-scheme: light dark; font-family: system-ui, sans-serif; }
body { margin: 0; padding: 1.5rem; max-width: 720px; margin-inline: auto; }
h1 { margin-top: 0; }
```

- [ ] **Step 5: Create `frontend/js/app.js` (placeholder)**

```javascript
document.getElementById("status").textContent = "Ready.";
```

- [ ] **Step 6: Wire static mount in `backend/app/main.py`**

Replace the file with:

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(title="NYC Dining")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")


app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
```

- [ ] **Step 7: Run tests to confirm pass**

```bash
uv run pytest tests/integration/test_static.py -v
```

Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add frontend backend/app/main.py backend/tests/integration/test_static.py
git commit -m "feat(dining): serve static frontend shell"
```

---

### Task 4: Dockerfile and fly.toml

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `fly.toml`

- [ ] **Step 1: Create `Dockerfile` at repo root**

```dockerfile
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir uv

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock* /app/backend/
RUN cd /app/backend && uv sync --frozen --no-dev || uv sync --no-dev

COPY backend /app/backend
COPY frontend /app/frontend

WORKDIR /app/backend

ENV DATA_DIR=/data
VOLUME ["/data"]

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Create `.dockerignore`**

```
**/__pycache__
**/*.pyc
**/.pytest_cache
**/.ruff_cache
**/.pyright
**/.venv
**/venv
**/.env
**/.env.local
.git
.github
docs
data/restaurants.db*
**/htmlcov
**/.coverage
.DS_Store
```

- [ ] **Step 3: Create `fly.toml`**

```toml
app = "nyc-dining"
primary_region = "ewr"

[build]

[env]
  DATA_DIR = "/data"
  FRONTEND_DIR = "/app/frontend"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

[[mounts]]
  source = "dining_data"
  destination = "/data"

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512
```

- [ ] **Step 4: Validate Docker build**

```bash
cd /Users/elistraus/opt/Claude/dining
docker build -t nyc-dining:dev .
```

Expected: build succeeds. If Docker is unavailable, skip — CI covers this.

- [ ] **Step 5: Commit**

```bash
git add Dockerfile .dockerignore fly.toml
git commit -m "chore(dining): add Dockerfile and fly.toml"
```

---

### Task 5: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the CI workflow**

```yaml
name: CI

on:
  push:
    branches: [master, main]
    paths:
      - "dining/**"
  pull_request:
    paths:
      - "dining/**"

defaults:
  run:
    working-directory: dining/backend

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync

      - name: Ruff format check
        run: uv run ruff format --check .

      - name: Ruff lint
        run: uv run ruff check .

      - name: Pyright
        run: uv run pyright

      - name: Pytest
        run: uv run pytest --cov=app --cov=scrapers --cov-report=term-missing
```

Note: the `paths:` filter assumes this `dining/` project lives under the parent `/Users/elistraus/opt/Claude/` repo. If this project is promoted to its own repo later, drop the filter and the `dining/` path prefix.

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "chore(dining): add CI workflow"
```

---

## Phase 2: Database & Migrations

Goal: on startup, open SQLite, run idempotent migrations, expose a connection.

### Task 6: Connection module and migration 0001

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/migrations/0001_init.sql`
- Create: `backend/tests/unit/test_db.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_db.py`:

```python
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
        versions = conn.execute(
            "SELECT version FROM schema_versions ORDER BY version"
        ).fetchall()
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
```

- [ ] **Step 2: Run it and confirm failure**

```bash
uv run pytest tests/unit/test_db.py -v
```

Expected: all fail with `ModuleNotFoundError: app.db`.

- [ ] **Step 3: Create `backend/app/config.py`**

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = REPO_ROOT / "data"
    frontend_dir: Path = REPO_ROOT / "frontend"
    database_path: Path | None = None
    shared_password_hash: str = ""
    cookie_signing_key: str = "dev-insecure-change-me"
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5-20251001"

    @property
    def db_path(self) -> Path:
        return self.database_path or (self.data_dir / "restaurants.db")


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Create `backend/app/db.py`**

```python
import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_versions (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    rows = conn.execute("SELECT version FROM schema_versions").fetchall()
    return {r[0] for r in rows}


def _discover_migrations() -> list[tuple[int, Path]]:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    out: list[tuple[int, Path]] = []
    for f in files:
        stem = f.stem
        version_str = stem.split("_", 1)[0]
        out.append((int(version_str), f))
    return out


def run_migrations(db_path: Path) -> None:
    conn = connect(db_path)
    try:
        applied = _applied_versions(conn)
        for version, path in _discover_migrations():
            if version in applied:
                continue
            sql = path.read_text()
            conn.executescript("BEGIN;\n" + sql + "\nCOMMIT;")
            conn.execute("INSERT INTO schema_versions (version) VALUES (?)", (version,))
    finally:
        conn.close()
```

- [ ] **Step 5: Create `backend/migrations/0001_init.sql`**

```sql
CREATE TABLE IF NOT EXISTS restaurants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT,
    neighborhood TEXT,
    borough TEXT CHECK (borough IN ('Manhattan','Brooklyn','Queens','Bronx','Staten Island') OR borough IS NULL),
    latitude REAL,
    longitude REAL,
    price_tier INTEGER CHECK (price_tier BETWEEN 1 AND 4),
    booking_platform TEXT CHECK (booking_platform IN ('resy','opentable','tock','walk_in','other')),
    booking_url TEXT,
    resy_venue_id TEXT,
    website_url TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed','needs_review')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_restaurants_status ON restaurants(status);
CREATE INDEX IF NOT EXISTS idx_restaurants_neighborhood ON restaurants(neighborhood);

CREATE TABLE IF NOT EXISTS restaurant_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    publication TEXT NOT NULL,
    list_name TEXT,
    source_url TEXT,
    blurb TEXT,
    source_date DATE
);
CREATE INDEX IF NOT EXISTS idx_sources_restaurant ON restaurant_sources(restaurant_id);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('cuisine','vibe','feature'))
);

CREATE TABLE IF NOT EXISTS restaurant_tags (
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (restaurant_id, tag_id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS personal_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('want_to_try','tried','loved','skip')),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    note TEXT,
    visited_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, restaurant_id)
);
CREATE INDEX IF NOT EXISTS idx_notes_restaurant ON personal_notes(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_notes_user ON personal_notes(user_id);
```

- [ ] **Step 6: Run tests to confirm pass**

```bash
uv run pytest tests/unit/test_db.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/config.py backend/app/db.py backend/migrations backend/tests/unit/test_db.py
git commit -m "feat(dining): migration runner + initial schema"
```

---

### Task 7: Wire migrations on app startup

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/integration/test_startup.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_startup.py`:

```python
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient


def test_startup_runs_migrations(tmp_path: Path, monkeypatch) -> None:
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
```

- [ ] **Step 2: Update `backend/tests/conftest.py` to use a per-test DB**

```python
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    return db_path


@pytest.fixture
def client(tmp_db: Path) -> TestClient:
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c
```

- [ ] **Step 3: Run the test and confirm failure**

```bash
uv run pytest tests/integration/test_startup.py -v
```

Expected: fail with `ImportError: cannot import name 'create_app'`.

- [ ] **Step 4: Rewrite `backend/app/main.py`**

```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import run_migrations


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        run_migrations(settings.db_path)
        yield

    application = FastAPI(title="NYC Dining", lifespan=lifespan)
    frontend_dir: Path = settings.frontend_dir

    @application.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/")
    def root() -> FileResponse:
        return FileResponse(frontend_dir / "index.html", media_type="text/html")

    application.mount("/css", StaticFiles(directory=frontend_dir / "css"), name="css")
    application.mount("/js", StaticFiles(directory=frontend_dir / "js"), name="js")

    return application


app = create_app()
```

- [ ] **Step 5: Run all tests to confirm pass**

```bash
uv run pytest -v
```

Expected: all previous tests still pass; new startup test passes.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/conftest.py backend/tests/integration/test_startup.py
git commit -m "feat(dining): run migrations on app startup"
```

---

## Phase 3: Auth

Goal: password gate → name picker → signed session cookie → middleware that protects non-public routes.

### Task 8: Password helpers and login verify endpoint

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/routes/__init__.py`
- Create: `backend/app/routes/auth.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/unit/test_auth_password.py`
- Create: `backend/tests/integration/test_auth_login.py`

- [ ] **Step 1: Write the failing unit test**

Create `backend/tests/unit/test_auth_password.py`:

```python
import pytest

from app.auth import hash_password, verify_password


def test_hash_and_verify_roundtrip() -> None:
    h = hash_password("hunter2")
    assert verify_password("hunter2", h) is True


def test_verify_rejects_wrong_password() -> None:
    h = hash_password("hunter2")
    assert verify_password("nope", h) is False


def test_verify_empty_stored_hash_returns_false() -> None:
    assert verify_password("anything", "") is False


@pytest.mark.parametrize("bad", ["", "   "])
def test_hash_rejects_empty_password(bad: str) -> None:
    with pytest.raises(ValueError):
        hash_password(bad)
```

- [ ] **Step 2: Write the failing integration test**

Create `backend/tests/integration/test_auth_login.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password


@pytest.fixture
def password_client(
    tmp_db, monkeypatch: pytest.MonkeyPatch
) -> TestClient:
    monkeypatch.setenv("SHARED_PASSWORD_HASH", hash_password("open-sesame"))
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


def test_verify_password_accepts_correct(password_client: TestClient) -> None:
    resp = password_client.post("/api/login/verify-password", json={"password": "open-sesame"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert "pre_auth" in resp.cookies


def test_verify_password_rejects_wrong(password_client: TestClient) -> None:
    resp = password_client.post("/api/login/verify-password", json={"password": "wrong"})
    assert resp.status_code == 401
    assert "pre_auth" not in resp.cookies
```

- [ ] **Step 3: Run tests, confirm failure**

```bash
uv run pytest tests/unit/test_auth_password.py tests/integration/test_auth_login.py -v
```

Expected: import errors.

- [ ] **Step 4: Create `backend/app/auth.py`**

```python
from __future__ import annotations

import bcrypt
from itsdangerous import BadSignature, TimestampSigner

PRE_AUTH_COOKIE = "pre_auth"
SESSION_COOKIE = "session"
PRE_AUTH_TTL_SECONDS = 300
SESSION_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days


def hash_password(password: str) -> str:
    if not password or not password.strip():
        raise ValueError("password must not be empty")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        return False


def _signer(key: str, salt: str) -> TimestampSigner:
    return TimestampSigner(key, salt=salt)


def sign_pre_auth(key: str) -> str:
    return _signer(key, "pre-auth").sign(b"ok").decode("utf-8")


def verify_pre_auth(token: str, key: str) -> bool:
    try:
        _signer(key, "pre-auth").unsign(token, max_age=PRE_AUTH_TTL_SECONDS)
        return True
    except BadSignature:
        return False


def sign_session(user_id: int, display_name: str, key: str) -> str:
    payload = f"{user_id}:{display_name}".encode("utf-8")
    return _signer(key, "session").sign(payload).decode("utf-8")


def read_session(token: str, key: str) -> tuple[int, str] | None:
    try:
        raw = _signer(key, "session").unsign(token, max_age=SESSION_TTL_SECONDS)
    except BadSignature:
        return None
    try:
        user_id_str, display_name = raw.decode("utf-8").split(":", 1)
        return int(user_id_str), display_name
    except (ValueError, UnicodeDecodeError):
        return None
```

- [ ] **Step 5: Create `backend/app/routes/__init__.py` (empty)**

```python
```

- [ ] **Step 6: Create `backend/app/routes/auth.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.auth import (
    PRE_AUTH_COOKIE,
    PRE_AUTH_TTL_SECONDS,
    sign_pre_auth,
    verify_password,
)
from app.config import get_settings

router = APIRouter(prefix="/api/login", tags=["auth"])


class VerifyPasswordRequest(BaseModel):
    password: str = Field(min_length=1)


class OkResponse(BaseModel):
    ok: bool = True


@router.post("/verify-password", response_model=OkResponse)
def verify_password_endpoint(body: VerifyPasswordRequest, response: Response) -> OkResponse:
    settings = get_settings()
    if not verify_password(body.password, settings.shared_password_hash):
        raise HTTPException(status_code=401, detail="bad_password")
    token = sign_pre_auth(settings.cookie_signing_key)
    response.set_cookie(
        PRE_AUTH_COOKIE,
        token,
        max_age=PRE_AUTH_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return OkResponse()
```

- [ ] **Step 7: Register router in `backend/app/main.py`**

Modify `create_app` — add after `frontend_dir` assignment:

```python
    from app.routes import auth as auth_routes

    application.include_router(auth_routes.router)
```

- [ ] **Step 8: Run tests to confirm pass**

```bash
uv run pytest tests/unit/test_auth_password.py tests/integration/test_auth_login.py -v
```

Expected: 6 passed.

- [ ] **Step 9: Commit**

```bash
git add backend/app/auth.py backend/app/routes backend/app/main.py backend/tests/unit/test_auth_password.py backend/tests/integration/test_auth_login.py
git commit -m "feat(dining): password verify endpoint with pre-auth cookie"
```

---

### Task 9: User store + complete-login endpoint

**Files:**
- Create: `backend/app/users.py`
- Modify: `backend/app/routes/auth.py`
- Create: `backend/tests/unit/test_users.py`
- Modify: `backend/tests/integration/test_auth_login.py`

- [ ] **Step 1: Write the failing unit test**

Create `backend/tests/unit/test_users.py`:

```python
from pathlib import Path

import pytest

from app.db import run_migrations
from app.users import create_user, get_user_by_name, list_users


@pytest.fixture
def db(tmp_path: Path) -> Path:
    p = tmp_path / "users.db"
    run_migrations(p)
    return p


def test_create_and_fetch_user(db: Path) -> None:
    user = create_user(db, "Eli")
    assert user.id > 0
    assert user.display_name == "Eli"

    fetched = get_user_by_name(db, "Eli")
    assert fetched is not None
    assert fetched.id == user.id


def test_create_user_is_idempotent(db: Path) -> None:
    a = create_user(db, "Eli")
    b = create_user(db, "Eli")
    assert a.id == b.id


def test_list_users_returns_sorted(db: Path) -> None:
    create_user(db, "Charlie")
    create_user(db, "Alice")
    create_user(db, "Bob")
    names = [u.display_name for u in list_users(db)]
    assert names == ["Alice", "Bob", "Charlie"]


@pytest.mark.parametrize("bad", ["", "   ", "a" * 51, "has\nnewline"])
def test_create_user_rejects_bad_names(db: Path, bad: str) -> None:
    with pytest.raises(ValueError):
        create_user(db, bad)
```

- [ ] **Step 2: Extend integration test**

Append to `backend/tests/integration/test_auth_login.py`:

```python
def test_complete_login_creates_user_and_sets_session(password_client: TestClient) -> None:
    pre = password_client.post("/api/login/verify-password", json={"password": "open-sesame"})
    assert pre.status_code == 200

    resp = password_client.post("/api/login/complete", json={"display_name": "Eli"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Eli"
    assert body["user_id"] >= 1
    assert "session" in resp.cookies


def test_complete_login_requires_pre_auth(tmp_db, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from app.auth import hash_password
    from app.main import create_app

    monkeypatch.setenv("SHARED_PASSWORD_HASH", hash_password("open-sesame"))
    with TestClient(create_app()) as c:
        resp = c.post("/api/login/complete", json={"display_name": "Eli"})
    assert resp.status_code == 401


def test_list_users_after_creation(password_client: TestClient) -> None:
    password_client.post("/api/login/verify-password", json={"password": "open-sesame"})
    password_client.post("/api/login/complete", json={"display_name": "Eli"})

    users_resp = password_client.get("/api/login/users")
    assert users_resp.status_code == 200
    names = [u["display_name"] for u in users_resp.json()["users"]]
    assert "Eli" in names
```

- [ ] **Step 3: Confirm tests fail**

```bash
uv run pytest tests/unit/test_users.py tests/integration/test_auth_login.py -v
```

Expected: new tests fail with import errors / 404.

- [ ] **Step 4: Create `backend/app/users.py`**

```python
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
```

- [ ] **Step 5: Extend `backend/app/routes/auth.py`**

Replace the file with:

```python
from __future__ import annotations

from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel, Field

from app.auth import (
    PRE_AUTH_COOKIE,
    PRE_AUTH_TTL_SECONDS,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    sign_pre_auth,
    sign_session,
    verify_password,
    verify_pre_auth,
)
from app.config import get_settings
from app.users import create_user, list_users

router = APIRouter(prefix="/api/login", tags=["auth"])


class VerifyPasswordRequest(BaseModel):
    password: str = Field(min_length=1)


class CompleteLoginRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)


class OkResponse(BaseModel):
    ok: bool = True


class CompleteLoginResponse(BaseModel):
    user_id: int
    display_name: str


class ListUsersResponse(BaseModel):
    users: list[CompleteLoginResponse]


@router.post("/verify-password", response_model=OkResponse)
def verify_password_endpoint(body: VerifyPasswordRequest, response: Response) -> OkResponse:
    settings = get_settings()
    if not verify_password(body.password, settings.shared_password_hash):
        raise HTTPException(status_code=401, detail="bad_password")
    token = sign_pre_auth(settings.cookie_signing_key)
    response.set_cookie(
        PRE_AUTH_COOKIE,
        token,
        max_age=PRE_AUTH_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return OkResponse()


@router.post("/complete", response_model=CompleteLoginResponse)
def complete_login(
    body: CompleteLoginRequest,
    response: Response,
    pre_auth: str | None = Cookie(default=None),
) -> CompleteLoginResponse:
    settings = get_settings()
    if not pre_auth or not verify_pre_auth(pre_auth, settings.cookie_signing_key):
        raise HTTPException(status_code=401, detail="missing_pre_auth")
    try:
        user = create_user(settings.db_path, body.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_name") from exc
    token = sign_session(user.id, user.display_name, settings.cookie_signing_key)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    response.delete_cookie(PRE_AUTH_COOKIE)
    return CompleteLoginResponse(user_id=user.id, display_name=user.display_name)


@router.get("/users", response_model=ListUsersResponse)
def list_users_endpoint(pre_auth: str | None = Cookie(default=None)) -> ListUsersResponse:
    settings = get_settings()
    if not pre_auth or not verify_pre_auth(pre_auth, settings.cookie_signing_key):
        raise HTTPException(status_code=401, detail="missing_pre_auth")
    users = list_users(settings.db_path)
    return ListUsersResponse(
        users=[CompleteLoginResponse(user_id=u.id, display_name=u.display_name) for u in users]
    )
```

- [ ] **Step 6: Run tests to confirm pass**

```bash
uv run pytest tests/unit/test_users.py tests/integration/test_auth_login.py -v
```

Expected: all passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/users.py backend/app/routes/auth.py backend/tests/unit/test_users.py backend/tests/integration/test_auth_login.py
git commit -m "feat(dining): user picker and session cookie on login completion"
```

---

### Task 10: Auth middleware gating non-public routes

**Files:**
- Modify: `backend/app/auth.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/integration/test_auth_middleware.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_auth_middleware.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password, sign_session


@pytest.fixture
def app_client(tmp_db, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SHARED_PASSWORD_HASH", hash_password("open-sesame"))
    monkeypatch.setenv("COOKIE_SIGNING_KEY", "test-key")
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


def test_public_paths_pass_without_auth(app_client: TestClient) -> None:
    assert app_client.get("/healthz").status_code == 200
    assert app_client.get("/login").status_code == 200
    assert app_client.get("/css/app.css").status_code == 200


def test_protected_path_rejected_without_session(app_client: TestClient) -> None:
    # Root is protected; only /login page is public
    resp = app_client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_protected_path_rejected_with_bad_session(app_client: TestClient) -> None:
    app_client.cookies.set("session", "garbage")
    resp = app_client.get("/", follow_redirects=False)
    assert resp.status_code == 303


def test_protected_path_with_valid_session_ok(app_client: TestClient) -> None:
    token = sign_session(1, "Eli", "test-key")
    app_client.cookies.set("session", token)
    resp = app_client.get("/")
    assert resp.status_code == 200
    assert "<title>" in resp.text.lower()


def test_api_returns_401_not_redirect(app_client: TestClient) -> None:
    # API routes should 401 rather than redirect; client handles it.
    resp = app_client.get("/api/whoami")
    assert resp.status_code == 401
```

- [ ] **Step 2: Confirm failure**

```bash
uv run pytest tests/integration/test_auth_middleware.py -v
```

Expected: several fail. `/login` and `/api/whoami` return 404.

- [ ] **Step 3: Update `backend/app/main.py`**

Replace with:

```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.auth import SESSION_COOKIE, read_session
from app.config import get_settings
from app.db import run_migrations

PUBLIC_PREFIXES = ("/healthz", "/login", "/api/login/", "/css/", "/js/")


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, signing_key_getter):
        super().__init__(app)
        self._signing_key_getter = signing_key_getter

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in {"/login", "/healthz"} or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        token = request.cookies.get(SESSION_COOKIE)
        key = self._signing_key_getter()
        session = read_session(token, key) if token else None
        if session is None:
            if path.startswith("/api/"):
                return JSONResponse({"detail": "unauthorized"}, status_code=401)
            return RedirectResponse("/login", status_code=303)
        request.state.user_id = session[0]
        request.state.display_name = session[1]
        return await call_next(request)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        run_migrations(settings.db_path)
        yield

    application = FastAPI(title="NYC Dining", lifespan=lifespan)
    frontend_dir: Path = settings.frontend_dir

    application.add_middleware(
        AuthMiddleware, signing_key_getter=lambda: get_settings().cookie_signing_key
    )

    @application.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/login")
    def login_page() -> FileResponse:
        return FileResponse(frontend_dir / "login.html", media_type="text/html")

    @application.get("/")
    def root() -> FileResponse:
        return FileResponse(frontend_dir / "index.html", media_type="text/html")

    @application.get("/api/whoami")
    def whoami(request: Request) -> dict[str, object]:
        user_id = getattr(request.state, "user_id", None)
        display_name = getattr(request.state, "display_name", None)
        if user_id is None:
            raise HTTPException(status_code=401, detail="unauthorized")
        return {"user_id": user_id, "display_name": display_name}

    application.mount("/css", StaticFiles(directory=frontend_dir / "css"), name="css")
    application.mount("/js", StaticFiles(directory=frontend_dir / "js"), name="js")

    from app.routes import auth as auth_routes

    application.include_router(auth_routes.router)

    return application


app = create_app()
```

- [ ] **Step 4: Create placeholder `frontend/login.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Log in · NYC Dining</title>
  <link rel="stylesheet" href="/css/app.css" />
</head>
<body>
  <main><h1>Log in</h1><p>Login UI lives here.</p></main>
</body>
</html>
```

- [ ] **Step 5: Run all tests to confirm pass**

```bash
uv run pytest -v
```

Expected: all tests pass (including earlier phases).

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/app/auth.py frontend/login.html backend/tests/integration/test_auth_middleware.py
git commit -m "feat(dining): auth middleware + /login page + /api/whoami"
```

---

### Task 11: Login page UI

**Files:**
- Modify: `frontend/login.html`
- Create: `frontend/js/login.js`

- [ ] **Step 1: Replace `frontend/login.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Log in · NYC Dining</title>
  <link rel="stylesheet" href="/css/app.css" />
</head>
<body>
  <main class="auth">
    <h1>NYC Dining</h1>

    <section id="password-step">
      <h2>Password</h2>
      <form id="password-form">
        <label>
          <span>Shared password</span>
          <input type="password" name="password" autocomplete="current-password" required />
        </label>
        <button type="submit">Continue</button>
        <p id="password-error" class="error" hidden></p>
      </form>
    </section>

    <section id="name-step" hidden>
      <h2>Who's this?</h2>
      <ul id="name-list"></ul>
      <form id="new-name-form">
        <label>
          <span>Or add a new name</span>
          <input type="text" name="display_name" maxlength="50" pattern="[A-Za-z0-9 ._-]+" required />
        </label>
        <button type="submit">Continue as new</button>
        <p id="name-error" class="error" hidden></p>
      </form>
    </section>
  </main>
  <script src="/js/login.js" type="module"></script>
</body>
</html>
```

- [ ] **Step 2: Create `frontend/js/login.js`**

```javascript
const passwordForm = document.getElementById("password-form");
const passwordError = document.getElementById("password-error");
const passwordStep = document.getElementById("password-step");
const nameStep = document.getElementById("name-step");
const nameList = document.getElementById("name-list");
const newNameForm = document.getElementById("new-name-form");
const nameError = document.getElementById("name-error");

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "same-origin",
  });
  return res;
}

function showError(el, msg) {
  el.textContent = msg;
  el.hidden = false;
}

function renderUsers(users) {
  nameList.innerHTML = "";
  for (const u of users) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = u.display_name;
    btn.addEventListener("click", () => completeLogin(u.display_name));
    li.appendChild(btn);
    nameList.appendChild(li);
  }
}

async function loadUsers() {
  const res = await fetch("/api/login/users", { credentials: "same-origin" });
  if (!res.ok) return [];
  const body = await res.json();
  return body.users ?? [];
}

async function completeLogin(displayName) {
  nameError.hidden = true;
  const res = await postJSON("/api/login/complete", { display_name: displayName });
  if (!res.ok) {
    showError(nameError, "Could not complete login. Try another name.");
    return;
  }
  window.location.href = "/";
}

passwordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  passwordError.hidden = true;
  const password = new FormData(passwordForm).get("password");
  const res = await postJSON("/api/login/verify-password", { password });
  if (!res.ok) {
    showError(passwordError, "Wrong password.");
    return;
  }
  passwordStep.hidden = true;
  nameStep.hidden = false;
  renderUsers(await loadUsers());
});

newNameForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = new FormData(newNameForm).get("display_name");
  await completeLogin(name);
});
```

- [ ] **Step 3: Add CSS rules for the auth form**

Append to `frontend/css/app.css`:

```css
.auth { max-width: 420px; }
.auth form label { display: block; margin-block: 0.75rem; }
.auth form label span { display: block; font-size: 0.9rem; margin-bottom: 0.25rem; }
.auth input { width: 100%; padding: 0.5rem; font-size: 1rem; }
.auth button { padding: 0.5rem 1rem; margin-top: 0.5rem; cursor: pointer; }
.auth .error { color: #c00; margin: 0.5rem 0; }
.auth ul { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
.auth ul li button { padding: 0.4rem 0.75rem; border-radius: 999px; }
```

- [ ] **Step 4: Manual smoke (optional if you have docker/uv ready)**

```bash
cd backend
export SHARED_PASSWORD_HASH="$(uv run python -c 'from app.auth import hash_password; print(hash_password("open-sesame"))')"
export COOKIE_SIGNING_KEY="dev-secret"
uv run uvicorn app.main:app --reload
```

Visit `http://localhost:8000/` — should redirect to `/login`. Enter `open-sesame`, pick or create a name, land on `/`.

- [ ] **Step 5: Commit**

```bash
git add frontend/login.html frontend/js/login.js frontend/css/app.css
git commit -m "feat(dining): login UI with password + name picker"
```

---

## Phase 4: Data Model & Import

Goal: Pydantic models mirroring the DB, a `SeedRestaurant` schema scrapers emit, and an importer that reads seed JSON into SQLite with tags + sources.

### Task 12: Pydantic domain models

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/tests/unit/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_models.py`:

```python
from datetime import date

import pytest
from pydantic import ValidationError

from app.models import PersonalNote, Restaurant, SeedRestaurant, SeedSource, Source, Tag


def test_restaurant_roundtrip() -> None:
    r = Restaurant(
        id="lilia-williamsburg",
        name="Lilia",
        neighborhood="Williamsburg",
        borough="Brooklyn",
        price_tier=3,
        booking_platform="resy",
        resy_venue_id="345",
        status="open",
    )
    assert r.id == "lilia-williamsburg"
    dumped = r.model_dump()
    assert Restaurant.model_validate(dumped) == r


def test_restaurant_rejects_invalid_borough() -> None:
    with pytest.raises(ValidationError):
        Restaurant(id="x", name="X", borough="Jersey City")


def test_restaurant_rejects_invalid_price_tier() -> None:
    with pytest.raises(ValidationError):
        Restaurant(id="x", name="X", price_tier=7)


def test_restaurant_default_status_is_open() -> None:
    r = Restaurant(id="x", name="X")
    assert r.status == "open"


def test_tag_kind_enum() -> None:
    Tag(name="italian", kind="cuisine")
    with pytest.raises(ValidationError):
        Tag(name="italian", kind="mood")


def test_personal_note_status_enum() -> None:
    n = PersonalNote(user_id=1, restaurant_id="x", status="tried", rating=4)
    assert n.status == "tried"
    with pytest.raises(ValidationError):
        PersonalNote(user_id=1, restaurant_id="x", status="bookmarked")


def test_personal_note_rating_range() -> None:
    with pytest.raises(ValidationError):
        PersonalNote(user_id=1, restaurant_id="x", status="tried", rating=9)


def test_seed_restaurant_accepts_minimal() -> None:
    s = SeedRestaurant(
        name="Lilia",
        neighborhood="Williamsburg",
        borough="Brooklyn",
        cuisine_tags=["italian"],
        vibe_tags=["date-night"],
        sources=[
            SeedSource(
                publication="eater_nyc",
                list_name="38 Essential",
                source_url="https://example.com",
                blurb="A pasta temple.",
                source_date=date(2025, 6, 1),
            )
        ],
    )
    assert s.slug() == "lilia-williamsburg"


def test_seed_restaurant_slug_strips_nonascii() -> None:
    s = SeedRestaurant(name="Café Maud'", neighborhood="West Village")
    assert s.slug() == "cafe-maud-west-village"


def test_source_requires_publication() -> None:
    with pytest.raises(ValidationError):
        Source(restaurant_id="x", publication="")
```

- [ ] **Step 2: Run and confirm failure**

```bash
uv run pytest tests/unit/test_models.py -v
```

Expected: import error.

- [ ] **Step 3: Create `backend/app/models.py`**

```python
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Borough = Literal["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
BookingPlatform = Literal["resy", "opentable", "tock", "walk_in", "other"]
RestaurantStatus = Literal["open", "closed", "needs_review"]
TagKind = Literal["cuisine", "vibe", "feature"]
NoteStatus = Literal["want_to_try", "tried", "loved", "skip"]


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized


class Restaurant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    address: str | None = None
    neighborhood: str | None = None
    borough: Borough | None = None
    latitude: float | None = None
    longitude: float | None = None
    price_tier: int | None = Field(default=None, ge=1, le=4)
    booking_platform: BookingPlatform | None = None
    booking_url: str | None = None
    resy_venue_id: str | None = None
    website_url: str | None = None
    description: str | None = None
    status: RestaurantStatus = "open"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    restaurant_id: str
    publication: str = Field(min_length=1)
    list_name: str | None = None
    source_url: str | None = None
    blurb: str | None = None
    source_date: date | None = None


class Tag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    name: str = Field(min_length=1)
    kind: TagKind


class PersonalNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    user_id: int
    restaurant_id: str
    status: NoteStatus
    rating: int | None = Field(default=None, ge=1, le=5)
    note: str | None = None
    visited_date: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SeedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    publication: str = Field(min_length=1)
    list_name: str | None = None
    source_url: str | None = None
    blurb: str | None = None
    source_date: date | None = None


class SeedRestaurant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    address: str | None = None
    neighborhood: str | None = None
    borough: Borough | None = None
    latitude: float | None = None
    longitude: float | None = None
    price_tier: int | None = Field(default=None, ge=1, le=4)
    booking_platform: BookingPlatform | None = None
    booking_url: str | None = None
    resy_venue_id: str | None = None
    website_url: str | None = None
    description: str | None = None
    cuisine_tags: list[str] = Field(default_factory=list)
    vibe_tags: list[str] = Field(default_factory=list)
    feature_tags: list[str] = Field(default_factory=list)
    sources: list[SeedSource] = Field(default_factory=list)

    @field_validator("cuisine_tags", "vibe_tags", "feature_tags")
    @classmethod
    def lowercase_tags(cls, v: list[str]) -> list[str]:
        return sorted({t.strip().lower() for t in v if t and t.strip()})

    def slug(self) -> str:
        parts = [self.name]
        if self.neighborhood:
            parts.append(self.neighborhood)
        return slugify(" ".join(parts))
```

- [ ] **Step 4: Confirm tests pass**

```bash
uv run pytest tests/unit/test_models.py -v
```

Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/unit/test_models.py
git commit -m "feat(dining): Pydantic domain + seed models"
```

---

### Task 13: Seed importer

**Files:**
- Create: `backend/scrapers/__init__.py` (empty)
- Create: `backend/scrapers/importer.py`
- Create: `backend/tests/integration/test_importer.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_importer.py`:

```python
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
        tag_rows = conn.execute(
            """
            SELECT t.name, t.kind FROM tags t ORDER BY t.name
            """
        ).fetchall()
        rt_count = conn.execute("SELECT COUNT(*) FROM restaurant_tags").fetchone()[0]
        src_count = conn.execute("SELECT COUNT(*) FROM restaurant_sources").fetchone()[0]
    finally:
        conn.close()

    assert [r["name"] for r in rows] == ["Lilia", "Nami Nori"]
    tag_tuples = {(t["name"], t["kind"]) for t in tag_rows}
    assert ("italian", "cuisine") in tag_tuples
    assert ("date-night", "vibe") in tag_tuples
    assert ("counter-only", "vibe") in tag_tuples
    assert rt_count == 5  # italian + date-night + japanese + sushi + casual + counter-only... adjust below
    # actual: 1 (italian) + 1 (date-night) + 2 (japanese, sushi) + 2 (casual, counter-only) = 6
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
    # Re-importing should not duplicate tags.
    assert tag_count == 6  # italian, date-night, japanese, sushi, casual, counter-only


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
```

The first test has an inline correction note; adjust assertion: fixture has 6 tag placements (italian + date-night on Lilia; japanese, sushi, casual, counter-only on Nami Nori) and the importer attaches each tag once per restaurant. Keep only the final `assert rt_count == 6` (remove the intermediate `assert rt_count == 5` and the comment).

After writing, clean the first test so only `assert rt_count == 6` remains in place of both.

- [ ] **Step 2: Confirm failure**

```bash
uv run pytest tests/integration/test_importer.py -v
```

Expected: import error.

- [ ] **Step 3: Create empty `backend/scrapers/__init__.py`**

- [ ] **Step 4: Create `backend/scrapers/importer.py`**

```python
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
            existing = conn.execute(
                "SELECT id FROM restaurants WHERE id = ?", (slug,)
            ).fetchone()
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
```

- [ ] **Step 5: Confirm tests pass**

```bash
uv run pytest tests/integration/test_importer.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/scrapers/__init__.py backend/scrapers/importer.py backend/tests/integration/test_importer.py
git commit -m "feat(dining): seed importer writes restaurants, tags, sources"
```

---

## Phase 5: First Scraper & LLM Field Extractor

Goal: one working scraper (Eater 38 Essential) that produces a `SeedRestaurant[]` JSON, with LLM-driven field extraction tucked behind a protocol + fake for tests.

### Task 14: LLM client protocol and fake

**Files:**
- Create: `backend/app/services/__init__.py` (empty)
- Create: `backend/app/services/llm_client.py`
- Create: `backend/tests/unit/test_llm_client.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_llm_client.py`:

```python
import pytest

from app.services.llm_client import FakeLLMClient, LLMClient


def test_fake_returns_scripted_response() -> None:
    fake: LLMClient = FakeLLMClient(responses=["hello"])
    out = fake.complete(system="sys", user="hi", max_tokens=100)
    assert out == "hello"


def test_fake_raises_when_exhausted() -> None:
    fake = FakeLLMClient(responses=[])
    with pytest.raises(RuntimeError):
        fake.complete(system="sys", user="hi", max_tokens=100)


def test_fake_records_calls() -> None:
    fake = FakeLLMClient(responses=["a", "b"])
    fake.complete(system="sys", user="u1", max_tokens=50)
    fake.complete(system="sys", user="u2", max_tokens=75)
    assert [c.user for c in fake.calls] == ["u1", "u2"]
    assert fake.calls[0].max_tokens == 50


async def test_fake_stream_yields_chunks() -> None:
    fake = FakeLLMClient(stream_responses=[["ab", "cd", "ef"]])
    chunks = []
    async for piece in fake.stream(system="sys", user="u", max_tokens=100):
        chunks.append(piece)
    assert chunks == ["ab", "cd", "ef"]
```

- [ ] **Step 2: Confirm failure**

```bash
uv run pytest tests/unit/test_llm_client.py -v
```

Expected: import error.

- [ ] **Step 3: Create `backend/app/services/__init__.py` (empty)**

- [ ] **Step 4: Create `backend/app/services/llm_client.py`**

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMCall:
    system: str
    user: str
    max_tokens: int
    temperature: float
    model: str | None


@runtime_checkable
class LLMClient(Protocol):
    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str: ...

    def stream(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AsyncIterator[str]: ...


@dataclass
class FakeLLMClient:
    responses: list[str] = field(default_factory=list)
    stream_responses: list[list[str]] = field(default_factory=list)
    calls: list[LLMCall] = field(default_factory=list)

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str:
        self.calls.append(
            LLMCall(system=system, user=user, max_tokens=max_tokens, temperature=temperature, model=model)
        )
        if not self.responses:
            raise RuntimeError("FakeLLMClient has no more scripted responses")
        return self.responses.pop(0)

    async def stream(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        self.calls.append(
            LLMCall(system=system, user=user, max_tokens=max_tokens, temperature=temperature, model=model)
        )
        if not self.stream_responses:
            raise RuntimeError("FakeLLMClient has no more scripted stream responses")
        pieces = self.stream_responses.pop(0)
        for p in pieces:
            yield p


class AnthropicLLMClient:
    def __init__(self, api_key: str, default_model: str) -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._default_model = default_model

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str:
        response = self._client.messages.create(
            model=model or self._default_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        parts: list[str] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "".join(parts)

    async def stream(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        from anthropic import AsyncAnthropic

        async_client = AsyncAnthropic(api_key=self._client.api_key)
        async with async_client.messages.stream(
            model=model or self._default_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                yield text
```

- [ ] **Step 5: Confirm tests pass**

```bash
uv run pytest tests/unit/test_llm_client.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/llm_client.py backend/tests/unit/test_llm_client.py
git commit -m "feat(dining): LLM client protocol with Anthropic + fake"
```

---

### Task 15: Fields extractor

**Files:**
- Create: `backend/app/services/fields_extractor.py`
- Create: `backend/tests/unit/test_fields_extractor.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_fields_extractor.py`:

```python
import json

import pytest

from app.services.fields_extractor import extract_fields
from app.services.llm_client import FakeLLMClient


def test_extract_returns_seed_restaurant() -> None:
    payload = {
        "name": "Lilia",
        "neighborhood": "Williamsburg",
        "borough": "Brooklyn",
        "price_tier": 3,
        "booking_platform": "resy",
        "cuisine_tags": ["italian", "pasta"],
        "vibe_tags": ["date-night"],
        "feature_tags": [],
        "description": "Missy Robbins's pasta and wood-fired vegetables.",
    }
    llm = FakeLLMClient(responses=[json.dumps(payload)])
    seed = extract_fields(
        llm=llm,
        source_url="https://ny.eater.com/maps/best-new-york-restaurants-38-essential",
        source_text="Lilia — Williamsburg, Brooklyn. ...",
        publication="eater_nyc",
        list_name="38 Essential",
        blurb="A pasta temple.",
    )
    assert seed.name == "Lilia"
    assert seed.neighborhood == "Williamsburg"
    assert seed.cuisine_tags == ["italian", "pasta"]
    assert len(seed.sources) == 1
    assert seed.sources[0].publication == "eater_nyc"
    assert seed.sources[0].blurb == "A pasta temple."


def test_extract_rejects_malformed_json() -> None:
    llm = FakeLLMClient(responses=["not-json"])
    with pytest.raises(ValueError):
        extract_fields(
            llm=llm,
            source_url="https://x",
            source_text="ignored",
            publication="eater_nyc",
            list_name="x",
            blurb=None,
        )


def test_extract_rejects_invalid_shape() -> None:
    llm = FakeLLMClient(responses=[json.dumps({"name": "", "neighborhood": "x"})])
    with pytest.raises(ValueError):
        extract_fields(
            llm=llm,
            source_url="https://x",
            source_text="ignored",
            publication="eater_nyc",
            list_name="x",
            blurb=None,
        )


def test_extract_strips_code_fences() -> None:
    payload = {"name": "Lilia", "neighborhood": "Williamsburg", "borough": "Brooklyn"}
    raw = f"```json\n{json.dumps(payload)}\n```"
    llm = FakeLLMClient(responses=[raw])
    seed = extract_fields(
        llm=llm,
        source_url="https://x",
        source_text="ignored",
        publication="eater_nyc",
        list_name="38 Essential",
        blurb=None,
    )
    assert seed.name == "Lilia"


def test_extract_records_system_prompt_mentions_fields() -> None:
    payload = {"name": "Lilia", "neighborhood": "Williamsburg"}
    llm = FakeLLMClient(responses=[json.dumps(payload)])
    extract_fields(
        llm=llm,
        source_url="https://x",
        source_text="ignored",
        publication="eater_nyc",
        list_name="38 Essential",
        blurb=None,
    )
    assert "cuisine_tags" in llm.calls[0].system
    assert "neighborhood" in llm.calls[0].system
    assert "ignored" in llm.calls[0].user
```

- [ ] **Step 2: Confirm failure**

```bash
uv run pytest tests/unit/test_fields_extractor.py -v
```

Expected: import error.

- [ ] **Step 3: Create `backend/app/services/fields_extractor.py`**

```python
from __future__ import annotations

import json
import re
from datetime import date

from pydantic import ValidationError

from app.models import SeedRestaurant, SeedSource
from app.services.llm_client import LLMClient

SYSTEM_PROMPT = """You extract structured NYC restaurant data from source text.

Return a single JSON object with these keys (omit keys that cannot be inferred):
- name (string, required): canonical restaurant name.
- address (string, optional).
- neighborhood (string): short neighborhood name, e.g. "Williamsburg".
- borough: one of Manhattan, Brooklyn, Queens, Bronx, Staten Island.
- latitude, longitude (floats, optional).
- price_tier (integer 1-4).
- booking_platform: one of resy, opentable, tock, walk_in, other.
- booking_url, resy_venue_id, website_url (strings, optional).
- description (string): one or two sentences paraphrased from the source.
- cuisine_tags (list of strings, lowercase): e.g. ["italian", "pasta"].
- vibe_tags (list of strings, lowercase): from this set only: outdoor, date-night, group, counter-only, late-night, tasting-menu, natural-wine, casual, nice, rooftop.
- feature_tags (list of strings, lowercase): optional.

Use only the source text. Do not invent fields. Output ONLY the JSON object.
"""


_CODE_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    m = _CODE_FENCE.match(text.strip())
    return m.group(1) if m else text.strip()


def extract_fields(
    *,
    llm: LLMClient,
    source_url: str,
    source_text: str,
    publication: str,
    list_name: str | None,
    blurb: str | None,
    source_date: date | None = None,
    model: str | None = None,
) -> SeedRestaurant:
    user_prompt = (
        f"Source URL: {source_url}\n"
        f"Publication: {publication}\n"
        f"List: {list_name or '(none)'}\n\n"
        f"Source text:\n{source_text}\n"
    )
    raw = llm.complete(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=800,
        temperature=0.1,
        model=model,
    )
    stripped = _strip_code_fence(raw)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned non-JSON: {raw!r}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("LLM returned non-object JSON")

    parsed.setdefault("sources", [])
    parsed["sources"].append(
        SeedSource(
            publication=publication,
            list_name=list_name,
            source_url=source_url,
            blurb=blurb,
            source_date=source_date,
        ).model_dump(mode="json")
    )

    try:
        return SeedRestaurant.model_validate(parsed)
    except ValidationError as exc:
        raise ValueError(f"LLM output failed schema: {exc}") from exc
```

- [ ] **Step 4: Confirm tests pass**

```bash
uv run pytest tests/unit/test_fields_extractor.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/fields_extractor.py backend/tests/unit/test_fields_extractor.py
git commit -m "feat(dining): LLM fields extractor with JSON validation"
```

---

### Task 16: Eater 38 Essential scraper

**Files:**
- Create: `backend/scrapers/common.py`
- Create: `backend/scrapers/eater_essentials.py`
- Create: `backend/tests/fixtures/html/eater_essentials.html`
- Create: `backend/tests/unit/test_eater_essentials.py`

- [ ] **Step 1: Create `backend/tests/fixtures/html/eater_essentials.html`**

```html
<html>
<body>
  <article>
    <h1>The 38 Essential Restaurants in New York City</h1>
    <section class="c-mapstack__card" data-slug="lilia">
      <h2>Lilia</h2>
      <p class="address">567 Union Ave, Brooklyn, NY</p>
      <div class="description">
        <p>Missy Robbins's Williamsburg temple to pasta and wood-fired vegetables remains one of the hardest-booked tables in NYC. Italian.</p>
      </div>
    </section>
    <section class="c-mapstack__card" data-slug="nami-nori">
      <h2>Nami Nori</h2>
      <p class="address">33 Carmine St, New York, NY</p>
      <div class="description">
        <p>The West Village counter for open-faced handrolls. Japanese. Casual.</p>
      </div>
    </section>
  </article>
</body>
</html>
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/unit/test_eater_essentials.py`:

```python
import json
from pathlib import Path

import pytest

from app.services.llm_client import FakeLLMClient
from scrapers.eater_essentials import parse_entries, scrape

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "html" / "eater_essentials.html"


def test_parse_entries_extracts_cards() -> None:
    html = FIXTURE.read_text()
    entries = parse_entries(html)
    names = [e.name for e in entries]
    assert names == ["Lilia", "Nami Nori"]
    assert "Williamsburg temple to pasta" in entries[0].description_text


def test_scrape_fetches_and_extracts(monkeypatch: pytest.MonkeyPatch) -> None:
    html = FIXTURE.read_text()

    def fake_fetch(url: str) -> str:
        assert "eater" in url
        return html

    responses = [
        json.dumps(
            {
                "name": "Lilia",
                "neighborhood": "Williamsburg",
                "borough": "Brooklyn",
                "price_tier": 3,
                "booking_platform": "resy",
                "cuisine_tags": ["italian", "pasta"],
                "vibe_tags": ["date-night"],
            }
        ),
        json.dumps(
            {
                "name": "Nami Nori",
                "neighborhood": "West Village",
                "borough": "Manhattan",
                "price_tier": 2,
                "booking_platform": "resy",
                "cuisine_tags": ["japanese", "sushi"],
                "vibe_tags": ["casual", "counter-only"],
            }
        ),
    ]
    llm = FakeLLMClient(responses=responses)
    seeds = scrape(fetch=fake_fetch, llm=llm)
    assert len(seeds) == 2
    assert seeds[0].slug() == "lilia-williamsburg"
    assert seeds[1].neighborhood == "West Village"
    assert all(s.sources[0].publication == "eater_nyc" for s in seeds)
```

- [ ] **Step 3: Confirm failure**

```bash
uv run pytest tests/unit/test_eater_essentials.py -v
```

Expected: import errors.

- [ ] **Step 4: Create `backend/scrapers/common.py`**

```python
from __future__ import annotations

import httpx

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
}


def fetch_url(url: str, *, timeout: float = 20.0) -> str:
    response = httpx.get(url, headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.text
```

- [ ] **Step 5: Create `backend/scrapers/eater_essentials.py`**

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from selectolax.parser import HTMLParser

from app.models import SeedRestaurant
from app.services.fields_extractor import extract_fields
from app.services.llm_client import LLMClient
from scrapers.common import fetch_url

SOURCE_URL = "https://ny.eater.com/maps/best-new-york-restaurants-38-essential"
PUBLICATION = "eater_nyc"
LIST_NAME = "38 Essential"


@dataclass(frozen=True)
class Entry:
    name: str
    address_text: str
    description_text: str


def parse_entries(html: str) -> list[Entry]:
    tree = HTMLParser(html)
    entries: list[Entry] = []
    for card in tree.css("section.c-mapstack__card"):
        name_node = card.css_first("h2")
        if name_node is None:
            continue
        name = name_node.text(strip=True)
        address_node = card.css_first("p.address")
        description_node = card.css_first("div.description")
        entries.append(
            Entry(
                name=name,
                address_text=address_node.text(strip=True) if address_node else "",
                description_text=description_node.text(strip=True) if description_node else "",
            )
        )
    return entries


def scrape(
    *,
    fetch: Callable[[str], str] = fetch_url,
    llm: LLMClient,
    source_date: date | None = None,
) -> list[SeedRestaurant]:
    html = fetch(SOURCE_URL)
    entries = parse_entries(html)
    results: list[SeedRestaurant] = []
    for entry in entries:
        source_text = f"Name: {entry.name}\nAddress: {entry.address_text}\n\n{entry.description_text}"
        seed = extract_fields(
            llm=llm,
            source_url=SOURCE_URL,
            source_text=source_text,
            publication=PUBLICATION,
            list_name=LIST_NAME,
            blurb=entry.description_text or None,
            source_date=source_date,
        )
        results.append(seed)
    return results
```

- [ ] **Step 6: Confirm tests pass**

```bash
uv run pytest tests/unit/test_eater_essentials.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/scrapers/common.py backend/scrapers/eater_essentials.py backend/tests/fixtures/html/eater_essentials.html backend/tests/unit/test_eater_essentials.py
git commit -m "feat(dining): Eater 38 Essential scraper + LLM enrichment"
```

---

## Phase 6: Search Backend (non-streaming)

Goal: SQL shortlist builder + Claude-powered ranker + `POST /api/search` endpoint returning JSON (streaming comes in Phase 8).

### Task 17: Shortlist SQL builder

**Files:**
- Create: `backend/app/services/shortlist.py`
- Create: `backend/tests/unit/test_shortlist.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_shortlist.py`:

```python
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
```

- [ ] **Step 2: Confirm failure**

```bash
uv run pytest tests/unit/test_shortlist.py -v
```

Expected: import errors.

- [ ] **Step 3: Create `backend/app/services/shortlist.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from app.db import connect


class ShortlistFilters(BaseModel):
    neighborhoods: list[str] = Field(default_factory=list)
    boroughs: list[str] = Field(default_factory=list)
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
    cuisine_tags: list[str] = field(default_factory=list)
    vibe_tags: list[str] = field(default_factory=list)
    feature_tags: list[str] = field(default_factory=list)
    sources: list[dict[str, str | None]] = field(default_factory=list)
    source_count: int = 0


def _build_where(filters: ShortlistFilters) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []

    allowed_statuses = ["open"]
    if filters.include_closed:
        allowed_statuses.append("closed")
    if filters.include_needs_review:
        allowed_statuses.append("needs_review")
    clauses.append(
        "r.status IN (" + ",".join("?" * len(allowed_statuses)) + ")"
    )
    params.extend(allowed_statuses)

    if filters.neighborhoods:
        clauses.append(
            "r.neighborhood IN (" + ",".join("?" * len(filters.neighborhoods)) + ")"
        )
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

        items: list[ShortlistItem] = []
        for row in rows:
            tag_rows = conn.execute(
                """
                SELECT t.name, t.kind FROM tags t
                JOIN restaurant_tags rt ON rt.tag_id = t.id
                WHERE rt.restaurant_id = ?
                """,
                (row["id"],),
            ).fetchall()
            cuisine: list[str] = []
            vibe: list[str] = []
            feature: list[str] = []
            for t in tag_rows:
                if t["kind"] == "cuisine":
                    cuisine.append(t["name"])
                elif t["kind"] == "vibe":
                    vibe.append(t["name"])
                else:
                    feature.append(t["name"])

            source_rows = conn.execute(
                """
                SELECT publication, list_name, blurb
                FROM restaurant_sources WHERE restaurant_id = ?
                """,
                (row["id"],),
            ).fetchall()
            sources = [
                {"publication": s["publication"], "list_name": s["list_name"], "blurb": s["blurb"]}
                for s in source_rows
            ]

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
                    cuisine_tags=sorted(cuisine),
                    vibe_tags=sorted(vibe),
                    feature_tags=sorted(feature),
                    sources=sources,
                    source_count=int(row["source_count"]),
                )
            )
        return items
    finally:
        conn.close()
```

- [ ] **Step 4: Confirm tests pass**

```bash
uv run pytest tests/unit/test_shortlist.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/shortlist.py backend/tests/unit/test_shortlist.py
git commit -m "feat(dining): SQL shortlist builder with tags + sources"
```

---

### Task 18: Ranker (non-streaming)

**Files:**
- Create: `backend/app/services/ranker.py`
- Create: `backend/tests/unit/test_ranker.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_ranker.py`:

```python
from app.services.llm_client import FakeLLMClient
from app.services.ranker import RankingRequest, parse_cards, rank_sync
from app.services.shortlist import ShortlistItem


def _items() -> list[ShortlistItem]:
    return [
        ShortlistItem(
            id="lilia-williamsburg",
            name="Lilia",
            neighborhood="Williamsburg",
            borough="Brooklyn",
            price_tier=3,
            booking_platform="resy",
            booking_url=None,
            resy_venue_id="345",
            description="Pasta temple.",
            cuisine_tags=["italian"],
            vibe_tags=["date-night"],
        ),
        ShortlistItem(
            id="nami-nori-west-village",
            name="Nami Nori",
            neighborhood="West Village",
            borough="Manhattan",
            price_tier=2,
            booking_platform="resy",
            booking_url=None,
            resy_venue_id="123",
            description="Handrolls.",
            cuisine_tags=["japanese"],
            vibe_tags=["casual", "counter-only"],
        ),
    ]


def test_parse_cards_extracts_in_order() -> None:
    text = (
        '<card id="nami-nori-west-village">Fast counter handrolls.</card>'
        '<card id="lilia-williamsburg">Date-night pasta.</card>'
    )
    cards = parse_cards(text)
    assert [c.id for c in cards] == ["nami-nori-west-village", "lilia-williamsburg"]
    assert cards[1].reason == "Date-night pasta."


def test_parse_cards_handles_whitespace() -> None:
    text = """
    <card id="a">
      reason a
    </card>
    <card id="b">reason b</card>
    """
    cards = parse_cards(text)
    assert [c.id for c in cards] == ["a", "b"]
    assert cards[0].reason == "reason a"


def test_parse_cards_ignores_unknown_tags() -> None:
    text = '<card id="a">x</card><foo>bar</foo><card id="b">y</card>'
    cards = parse_cards(text)
    assert [c.id for c in cards] == ["a", "b"]


def test_rank_sync_returns_ordered_cards() -> None:
    llm = FakeLLMClient(
        responses=[
            '<card id="nami-nori-west-village">Fast counter handrolls, matches casual vibe.</card>'
            '<card id="lilia-williamsburg">Pasta for a splurge.</card>'
        ]
    )
    req = RankingRequest(
        shortlist=_items(),
        cuisines=[],
        vibes=["casual"],
        preferences_text="cheap eats with a friend",
    )
    ranked = rank_sync(llm=llm, request=req, model="claude-haiku-4-5-20251001")
    assert [c.id for c in ranked] == ["nami-nori-west-village", "lilia-williamsburg"]
    # System prompt should mention the format.
    assert "<card" in llm.calls[0].system


def test_rank_sync_falls_back_when_llm_returns_garbage() -> None:
    llm = FakeLLMClient(responses=["nothing-useful"])
    req = RankingRequest(shortlist=_items())
    ranked = rank_sync(llm=llm, request=req, model="haiku")
    # Fallback: shortlist order (source_count desc, then name).
    assert [c.id for c in ranked] == ["lilia-williamsburg", "nami-nori-west-village"]
    assert all(c.reason == "" for c in ranked)
```

- [ ] **Step 2: Confirm failure**

```bash
uv run pytest tests/unit/test_ranker.py -v
```

Expected: import errors.

- [ ] **Step 3: Create `backend/app/services/ranker.py`**

```python
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from app.services.llm_client import LLMClient
from app.services.shortlist import ShortlistItem

SYSTEM_PROMPT = """You are a helpful NYC dining expert helping a friend pick where to eat.
Given a shortlist of restaurants, soft preferences, and a free-form preferences note,
return a ranked top N with a one-sentence reason for each pick.

Use only the data provided; do not invent details.
Output format: a sequence of `<card id="SLUG">one-sentence reason</card>` tags
in ranked order. No other text before or after the tags.
"""

_CARD_RE = re.compile(r'<card\s+id="([^"]+)"\s*>(.*?)</card>', re.DOTALL)


@dataclass(frozen=True)
class RankedCard:
    id: str
    reason: str


class RankingRequest(BaseModel):
    shortlist: list[ShortlistItem]
    cuisines: list[str] = Field(default_factory=list)
    vibes: list[str] = Field(default_factory=list)
    preferences_text: str = ""
    target_n: int = 8

    class Config:
        arbitrary_types_allowed = True


def parse_cards(text: str) -> list[RankedCard]:
    results: list[RankedCard] = []
    for match in _CARD_RE.finditer(text):
        slug = match.group(1).strip()
        reason = " ".join(match.group(2).split())
        results.append(RankedCard(id=slug, reason=reason))
    return results


def _build_user_prompt(req: RankingRequest) -> str:
    shortlist_payload: list[dict[str, Any]] = []
    for item in req.shortlist:
        shortlist_payload.append(
            {
                "id": item.id,
                "name": item.name,
                "neighborhood": item.neighborhood,
                "borough": item.borough,
                "cuisine_tags": item.cuisine_tags,
                "vibe_tags": item.vibe_tags,
                "price_tier": item.price_tier,
                "description": item.description,
                "sources": item.sources,
            }
        )
    lines: list[str] = []
    if req.cuisines:
        lines.append("Cuisines preferred: " + ", ".join(req.cuisines))
    if req.vibes:
        lines.append("Vibes preferred: " + ", ".join(req.vibes))
    if req.preferences_text.strip():
        lines.append("Preferences note: " + req.preferences_text.strip())
    lines.append(f"Return top N = min({req.target_n}, shortlist length).")
    lines.append("Shortlist JSON:")
    lines.append(json.dumps(shortlist_payload, ensure_ascii=False))
    return "\n".join(lines)


def _fallback(req: RankingRequest) -> list[RankedCard]:
    items = sorted(
        req.shortlist,
        key=lambda it: (-it.source_count, it.name.lower()),
    )
    limit = min(req.target_n, len(items))
    return [RankedCard(id=i.id, reason="") for i in items[:limit]]


def rank_sync(
    *,
    llm: LLMClient,
    request: RankingRequest,
    model: str,
) -> list[RankedCard]:
    if not request.shortlist:
        return []
    user_prompt = _build_user_prompt(request)
    try:
        raw = llm.complete(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=1500,
            temperature=0.3,
            model=model,
        )
    except Exception:
        return _fallback(request)
    cards = parse_cards(raw)
    if not cards:
        return _fallback(request)
    valid_ids = {item.id for item in request.shortlist}
    return [c for c in cards if c.id in valid_ids]
```

- [ ] **Step 4: Confirm tests pass**

```bash
uv run pytest tests/unit/test_ranker.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ranker.py backend/tests/unit/test_ranker.py
git commit -m "feat(dining): Claude-powered ranker with fallback"
```

---

### Task 19: `/api/search` endpoint (non-streaming)

**Files:**
- Create: `backend/app/routes/search.py`
- Create: `backend/app/dependencies.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/integration/test_search.py`

- [ ] **Step 1: Create `backend/app/dependencies.py`**

```python
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.llm_client import AnthropicLLMClient, LLMClient


@lru_cache(maxsize=1)
def _real_llm() -> LLMClient:
    settings = get_settings()
    return AnthropicLLMClient(api_key=settings.anthropic_api_key, default_model=settings.llm_model)


_llm_override: LLMClient | None = None


def get_llm_client() -> LLMClient:
    if _llm_override is not None:
        return _llm_override
    return _real_llm()


def set_llm_override(client: LLMClient | None) -> None:
    global _llm_override
    _llm_override = client
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/integration/test_search.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password, sign_session
from app.dependencies import set_llm_override
from app.models import SeedRestaurant, SeedSource
from app.services.llm_client import FakeLLMClient
from scrapers.importer import import_seed


@pytest.fixture
def logged_in_client(tmp_db, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SHARED_PASSWORD_HASH", hash_password("p"))
    monkeypatch.setenv("COOKIE_SIGNING_KEY", "k")

    import_seed(
        tmp_db,
        [
            SeedRestaurant(
                name="Lilia",
                neighborhood="Williamsburg",
                borough="Brooklyn",
                price_tier=3,
                booking_platform="resy",
                cuisine_tags=["italian"],
                vibe_tags=["date-night"],
                sources=[SeedSource(publication="eater_nyc")],
            ),
            SeedRestaurant(
                name="Nami Nori",
                neighborhood="West Village",
                borough="Manhattan",
                price_tier=2,
                booking_platform="resy",
                cuisine_tags=["japanese"],
                vibe_tags=["casual"],
                sources=[SeedSource(publication="eater_nyc")],
            ),
        ],
    )

    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        c.cookies.set("session", sign_session(1, "Eli", "k"))
        yield c


def test_search_returns_ranked_results(logged_in_client: TestClient) -> None:
    fake = FakeLLMClient(
        responses=[
            '<card id="nami-nori-west-village">Casual, right vibe.</card>'
            '<card id="lilia-williamsburg">Splurge backup.</card>'
        ]
    )
    set_llm_override(fake)
    try:
        resp = logged_in_client.post(
            "/api/search",
            json={"preferences_text": "casual", "vibes": ["casual"]},
        )
    finally:
        set_llm_override(None)

    assert resp.status_code == 200
    body = resp.json()
    assert [c["id"] for c in body["ranked"]] == ["nami-nori-west-village", "lilia-williamsburg"]
    assert body["ranked"][0]["reason"].startswith("Casual")
    assert {c["id"] for c in body["candidates"]} == {"lilia-williamsburg", "nami-nori-west-village"}


def test_search_with_neighborhood_filter(logged_in_client: TestClient) -> None:
    fake = FakeLLMClient(responses=['<card id="lilia-williamsburg">Only option.</card>'])
    set_llm_override(fake)
    try:
        resp = logged_in_client.post(
            "/api/search",
            json={"neighborhoods": ["Williamsburg"], "preferences_text": ""},
        )
    finally:
        set_llm_override(None)

    body = resp.json()
    assert [c["id"] for c in body["candidates"]] == ["lilia-williamsburg"]


def test_search_requires_auth(tmp_db) -> None:
    from app.main import create_app

    with TestClient(create_app()) as c:
        resp = c.post("/api/search", json={})
    assert resp.status_code == 401


def test_search_empty_shortlist(logged_in_client: TestClient) -> None:
    fake = FakeLLMClient(responses=[])
    set_llm_override(fake)
    try:
        resp = logged_in_client.post(
            "/api/search", json={"neighborhoods": ["Harlem"]}
        )
    finally:
        set_llm_override(None)
    body = resp.json()
    assert body["candidates"] == []
    assert body["ranked"] == []
```

- [ ] **Step 3: Confirm failure**

```bash
uv run pytest tests/integration/test_search.py -v
```

Expected: 404 / import errors.

- [ ] **Step 4: Create `backend/app/routes/search.py`**

```python
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.config import get_settings
from app.dependencies import get_llm_client
from app.services.ranker import RankingRequest, rank_sync
from app.services.shortlist import ShortlistFilters, fetch_shortlist

router = APIRouter(prefix="/api", tags=["search"])


class SearchRequest(BaseModel):
    neighborhoods: list[str] = Field(default_factory=list)
    boroughs: list[str] = Field(default_factory=list)
    price_ceiling: int | None = Field(default=None, ge=1, le=4)
    cuisines: list[str] = Field(default_factory=list)
    vibes: list[str] = Field(default_factory=list)
    preferences_text: str = ""
    target_n: int = Field(default=8, ge=1, le=20)


class RankedCardResponse(BaseModel):
    id: str
    reason: str


class CandidateResponse(BaseModel):
    id: str
    name: str
    neighborhood: str | None
    borough: str | None
    price_tier: int | None
    booking_platform: str | None
    booking_url: str | None
    resy_venue_id: str | None
    description: str | None
    cuisine_tags: list[str]
    vibe_tags: list[str]
    feature_tags: list[str]
    sources: list[dict[str, str | None]]


class SearchResponse(BaseModel):
    candidates: list[CandidateResponse]
    ranked: list[RankedCardResponse]


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest, _request: Request) -> SearchResponse:
    settings = get_settings()
    filters = ShortlistFilters(
        neighborhoods=body.neighborhoods,
        boroughs=body.boroughs,
        price_ceiling=body.price_ceiling,
    )
    items = fetch_shortlist(settings.db_path, filters, limit=40)
    if len(items) > 25:
        items = items[:25]
    candidates = [CandidateResponse(**{k: v for k, v in asdict(item).items() if k != "source_count"}) for item in items]

    llm = get_llm_client()
    ranked_cards = rank_sync(
        llm=llm,
        request=RankingRequest(
            shortlist=items,
            cuisines=body.cuisines,
            vibes=body.vibes,
            preferences_text=body.preferences_text,
            target_n=body.target_n,
        ),
        model=settings.llm_model,
    )
    return SearchResponse(
        candidates=candidates,
        ranked=[RankedCardResponse(id=c.id, reason=c.reason) for c in ranked_cards],
    )
```

- [ ] **Step 5: Register router in `backend/app/main.py`**

Inside `create_app`, after the existing `auth_routes` include, add:

```python
    from app.routes import search as search_routes

    application.include_router(search_routes.router)
```

- [ ] **Step 6: Confirm tests pass**

```bash
uv run pytest tests/integration/test_search.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/dependencies.py backend/app/routes/search.py backend/app/main.py backend/tests/integration/test_search.py
git commit -m "feat(dining): POST /api/search endpoint with shortlist + ranker"
```

---

## Phase 7: Search Frontend

Goal: a form on `/` that POSTs to `/api/search`, renders result cards with AI reasons and source chips.

### Task 20: Search form and API call

**Files:**
- Modify: `frontend/index.html`
- Create: `frontend/js/api.js`
- Modify: `frontend/js/app.js`
- Modify: `frontend/css/app.css`

- [ ] **Step 1: Replace `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NYC Dining</title>
  <link rel="stylesheet" href="/css/app.css" />
</head>
<body>
  <header class="topbar">
    <h1>NYC Dining</h1>
    <p id="who"></p>
  </header>

  <main>
    <form id="search-form" class="search-form">
      <fieldset>
        <legend>Where</legend>
        <label>
          <span>Neighborhoods (comma separated)</span>
          <input type="text" name="neighborhoods" placeholder="West Village, Williamsburg" />
        </label>
        <label>
          <span>Boroughs</span>
          <select name="boroughs" multiple size="5">
            <option>Manhattan</option>
            <option>Brooklyn</option>
            <option>Queens</option>
            <option>Bronx</option>
            <option>Staten Island</option>
          </select>
        </label>
      </fieldset>

      <fieldset>
        <legend>What</legend>
        <label>
          <span>Cuisines (comma separated)</span>
          <input type="text" name="cuisines" placeholder="italian, japanese" />
        </label>
        <label>
          <span>Vibes</span>
          <select name="vibes" multiple size="6">
            <option value="casual">casual</option>
            <option value="nice">nice</option>
            <option value="date-night">date-night</option>
            <option value="group">group</option>
            <option value="counter-only">counter-only</option>
            <option value="outdoor">outdoor</option>
            <option value="rooftop">rooftop</option>
            <option value="late-night">late-night</option>
            <option value="tasting-menu">tasting-menu</option>
            <option value="natural-wine">natural-wine</option>
          </select>
        </label>
        <label>
          <span>Price ceiling</span>
          <select name="price_ceiling">
            <option value="">any</option>
            <option value="1">$</option>
            <option value="2">$$</option>
            <option value="3">$$$</option>
            <option value="4">$$$$</option>
          </select>
        </label>
      </fieldset>

      <fieldset>
        <legend>Notes</legend>
        <label>
          <span>Preferences (free-form)</span>
          <textarea name="preferences_text" rows="3" placeholder="Casual dinner with a friend, walkable from the L train"></textarea>
        </label>
      </fieldset>

      <button type="submit" id="search-btn">Find spots</button>
    </form>

    <section id="results" class="results"></section>
  </main>

  <script type="module" src="/js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `frontend/js/api.js`**

```javascript
async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "same-origin",
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("unauthorized");
  }
  if (!res.ok) {
    throw new Error(`search failed: ${res.status}`);
  }
  return res.json();
}

export async function search(payload) {
  return postJSON("/api/search", payload);
}

export async function whoami() {
  const res = await fetch("/api/whoami", { credentials: "same-origin" });
  if (!res.ok) return null;
  return res.json();
}
```

- [ ] **Step 3: Replace `frontend/js/app.js`**

```javascript
import { search, whoami } from "/js/api.js";

const whoEl = document.getElementById("who");
const form = document.getElementById("search-form");
const resultsEl = document.getElementById("results");
const button = document.getElementById("search-btn");

whoami().then((info) => {
  if (info) whoEl.textContent = `Logged in as ${info.display_name}`;
});

function splitCSV(value) {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function multiSelectValues(select) {
  return Array.from(select.selectedOptions).map((o) => o.value);
}

function buildPayload() {
  const fd = new FormData(form);
  const priceRaw = fd.get("price_ceiling");
  return {
    neighborhoods: splitCSV(fd.get("neighborhoods") ?? ""),
    boroughs: multiSelectValues(form.elements.boroughs),
    cuisines: splitCSV(fd.get("cuisines") ?? ""),
    vibes: multiSelectValues(form.elements.vibes),
    price_ceiling: priceRaw ? parseInt(priceRaw, 10) : null,
    preferences_text: fd.get("preferences_text") ?? "",
  };
}

function priceLabel(tier) {
  if (!tier) return "";
  return "$".repeat(tier);
}

function bookingAction(card) {
  if (card.booking_platform === "resy" && card.resy_venue_id) {
    return {
      href: card.booking_url ?? `https://resy.com/cities/ny/${card.id}`,
      label: "Book on Resy",
    };
  }
  if (card.booking_url) {
    return { href: card.booking_url, label: "Book" };
  }
  if (card.booking_platform === "walk_in") {
    return { href: null, label: "Walk-in" };
  }
  return { href: null, label: "" };
}

function sourceChip(source) {
  const chip = document.createElement("span");
  chip.className = "source-chip";
  chip.textContent = source.list_name
    ? `${source.publication} · ${source.list_name}`
    : source.publication;
  if (source.blurb) chip.title = source.blurb;
  return chip;
}

function renderCard(candidate, reason) {
  const card = document.createElement("article");
  card.className = "card";
  card.dataset.id = candidate.id;

  const header = document.createElement("header");
  const title = document.createElement("h2");
  title.textContent = candidate.name;
  header.appendChild(title);

  const meta = document.createElement("p");
  meta.className = "meta";
  const bits = [candidate.neighborhood, candidate.borough, priceLabel(candidate.price_tier)].filter(
    Boolean,
  );
  meta.textContent = bits.join(" · ");
  header.appendChild(meta);

  card.appendChild(header);

  const why = document.createElement("p");
  why.className = "why";
  why.dataset.role = "reason";
  why.textContent = reason || "…";
  card.appendChild(why);

  const tags = document.createElement("p");
  tags.className = "tags";
  tags.textContent = [...candidate.cuisine_tags, ...candidate.vibe_tags].join(" · ");
  card.appendChild(tags);

  const chips = document.createElement("div");
  chips.className = "chips";
  for (const s of candidate.sources ?? []) chips.appendChild(sourceChip(s));
  card.appendChild(chips);

  const action = bookingAction(candidate);
  if (action.href) {
    const a = document.createElement("a");
    a.href = action.href;
    a.className = "btn-primary";
    a.textContent = action.label;
    a.target = "_blank";
    a.rel = "noopener";
    card.appendChild(a);
  } else if (action.label) {
    const span = document.createElement("span");
    span.className = "pill";
    span.textContent = action.label;
    card.appendChild(span);
  }

  return card;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  button.disabled = true;
  resultsEl.innerHTML = "<p>Searching&hellip;</p>";
  try {
    const payload = buildPayload();
    const data = await search(payload);
    const byId = new Map(data.candidates.map((c) => [c.id, c]));
    resultsEl.innerHTML = "";
    if (data.ranked.length === 0) {
      resultsEl.innerHTML = "<p>No matches. Try relaxing your filters.</p>";
      return;
    }
    for (const r of data.ranked) {
      const candidate = byId.get(r.id);
      if (!candidate) continue;
      resultsEl.appendChild(renderCard(candidate, r.reason));
    }
  } catch (err) {
    resultsEl.innerHTML = `<p class="error">${err.message}</p>`;
  } finally {
    button.disabled = false;
  }
});
```

- [ ] **Step 4: Append CSS in `frontend/css/app.css`**

```css
.topbar { display: flex; justify-content: space-between; align-items: baseline; }
.search-form fieldset { border: 1px solid #ccc; padding: 0.75rem; margin: 0.75rem 0; }
.search-form label { display: block; margin: 0.5rem 0; }
.search-form span { display: block; font-size: 0.9rem; margin-bottom: 0.25rem; }
.search-form input[type="text"], .search-form textarea, .search-form select {
  width: 100%; font: inherit; padding: 0.35rem;
}
#search-btn { padding: 0.5rem 1rem; font-size: 1rem; cursor: pointer; }

.results { display: grid; gap: 1rem; margin-top: 1rem; }
.card { border: 1px solid #ccc; border-radius: 8px; padding: 1rem; background: canvas; }
.card h2 { margin: 0 0 0.25rem 0; }
.card .meta { color: GrayText; margin: 0 0 0.5rem 0; }
.card .why { font-style: italic; }
.card .tags { font-size: 0.9rem; color: GrayText; }
.card .chips { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-block: 0.5rem; }
.source-chip {
  padding: 0.15rem 0.5rem; border: 1px solid #ddd; border-radius: 999px; font-size: 0.8rem;
}
.btn-primary {
  display: inline-block; padding: 0.4rem 0.75rem; background: #1a73e8; color: white;
  text-decoration: none; border-radius: 4px; margin-top: 0.5rem;
}
.pill { display: inline-block; padding: 0.15rem 0.5rem; background: #eee; border-radius: 999px; }
.error { color: #c00; }
```

- [ ] **Step 5: Manual smoke check**

Run server with an Anthropic API key plus a seeded DB (import Eater 38 fixture JSON or the scraper). Verify:
- Navigating to `/` while logged in renders the form.
- Submitting returns cards with AI reasons.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html frontend/js/api.js frontend/js/app.js frontend/css/app.css
git commit -m "feat(dining): search form + results UI"
```

---

## Phase 8: Streaming

Goal: convert `/api/search` to SSE. First event sends candidates + ranked ids; subsequent events emit one `card` per completed `</card>` tag; final `done` event closes. Frontend renders skeleton cards immediately and fills reasons as they arrive.

### Task 21: Streaming ranker

**Files:**
- Modify: `backend/app/services/ranker.py`
- Modify: `backend/tests/unit/test_ranker.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_ranker.py`:

```python
from app.services.ranker import stream_cards
from app.services.shortlist import ShortlistItem


def _simple_items() -> list[ShortlistItem]:
    return [
        ShortlistItem(
            id="a", name="A", neighborhood=None, borough=None,
            price_tier=None, booking_platform=None, booking_url=None,
            resy_venue_id=None, description=None,
        ),
        ShortlistItem(
            id="b", name="B", neighborhood=None, borough=None,
            price_tier=None, booking_platform=None, booking_url=None,
            resy_venue_id=None, description=None,
        ),
    ]


async def test_stream_cards_yields_as_tags_close() -> None:
    stream_pieces = [
        '<card id="a">reason-',
        "a</card>",
        '<card id="b">reason',
        "-b</card>",
    ]
    llm = FakeLLMClient(stream_responses=[stream_pieces])
    req = RankingRequest(shortlist=_simple_items(), target_n=2)
    out: list = []
    async for card in stream_cards(llm=llm, request=req, model="m"):
        out.append(card)
    assert [c.id for c in out] == ["a", "b"]
    assert out[0].reason == "reason-a"
    assert out[1].reason == "reason-b"


async def test_stream_cards_handles_llm_error() -> None:
    class BoomLLM:
        async def stream(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("boom")
            yield  # pragma: no cover

        def complete(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("boom")

    req = RankingRequest(shortlist=[_simple_items()[0]], target_n=1)
    out: list = []
    async for card in stream_cards(llm=BoomLLM(), request=req, model="m"):
        out.append(card)
    # Fallback yields the shortlist order with empty reasons
    assert [c.id for c in out] == ["a"]
    assert out[0].reason == ""
```

(The existing `FakeLLMClient` and `RankingRequest` imports at the top of the file from Task 18 are reused.)

- [ ] **Step 2: Confirm failure**

```bash
uv run pytest tests/unit/test_ranker.py -v
```

Expected: import error on `stream_cards`.

- [ ] **Step 3: Extend `backend/app/services/ranker.py`**

Add at end of file:

```python
from collections.abc import AsyncIterator


async def stream_cards(
    *,
    llm: LLMClient,
    request: RankingRequest,
    model: str,
) -> AsyncIterator[RankedCard]:
    if not request.shortlist:
        return
    valid_ids = {item.id for item in request.shortlist}
    buffer = ""
    emitted = False
    try:
        user_prompt = _build_user_prompt(request)
        async for chunk in llm.stream(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=1500,
            temperature=0.3,
            model=model,
        ):
            buffer += chunk
            while True:
                match = _CARD_RE.search(buffer)
                if not match:
                    break
                slug = match.group(1).strip()
                reason = " ".join(match.group(2).split())
                buffer = buffer[match.end():]
                if slug in valid_ids:
                    emitted = True
                    yield RankedCard(id=slug, reason=reason)
    except Exception:
        pass
    if not emitted:
        for card in _fallback(request):
            yield card
```

- [ ] **Step 4: Confirm tests pass**

```bash
uv run pytest tests/unit/test_ranker.py -v
```

Expected: all pass (including new streaming tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ranker.py backend/tests/unit/test_ranker.py
git commit -m "feat(dining): streaming ranker yields cards as tags close"
```

---

### Task 22: Convert `/api/search` to SSE

**Files:**
- Modify: `backend/app/routes/search.py`
- Create: `backend/tests/integration/test_search_stream.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_search_stream.py`:

```python
import json

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password, sign_session
from app.dependencies import set_llm_override
from app.models import SeedRestaurant, SeedSource
from app.services.llm_client import FakeLLMClient
from scrapers.importer import import_seed


@pytest.fixture
def streaming_client(tmp_db, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SHARED_PASSWORD_HASH", hash_password("p"))
    monkeypatch.setenv("COOKIE_SIGNING_KEY", "k")
    import_seed(
        tmp_db,
        [
            SeedRestaurant(
                name="A",
                neighborhood="Williamsburg",
                borough="Brooklyn",
                price_tier=2,
                booking_platform="resy",
                cuisine_tags=["a"],
                vibe_tags=["casual"],
                sources=[SeedSource(publication="eater_nyc")],
            ),
            SeedRestaurant(
                name="B",
                neighborhood="West Village",
                borough="Manhattan",
                price_tier=2,
                booking_platform="resy",
                cuisine_tags=["b"],
                vibe_tags=["casual"],
                sources=[SeedSource(publication="eater_nyc")],
            ),
        ],
    )
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        c.cookies.set("session", sign_session(1, "Eli", "k"))
        yield c


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in raw.split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())
        if data_lines:
            events.append((event_name, json.loads("\n".join(data_lines))))
    return events


def test_stream_emits_candidates_then_cards_then_done(streaming_client: TestClient) -> None:
    fake = FakeLLMClient(
        stream_responses=[['<card id="b-west-village">b reason.</card><card id="a-williamsburg">a reason.</card>']]
    )
    set_llm_override(fake)
    try:
        with streaming_client.stream(
            "POST",
            "/api/search/stream",
            json={"preferences_text": "fun"},
        ) as resp:
            assert resp.status_code == 200
            raw = "".join(resp.iter_text())
    finally:
        set_llm_override(None)

    events = _parse_sse(raw)
    names = [e[0] for e in events]
    assert names[0] == "candidates"
    assert names[-1] == "done"
    card_events = [e for e in events if e[0] == "card"]
    assert [e[1]["id"] for e in card_events] == ["b-west-village", "a-williamsburg"]
    assert card_events[0][1]["reason"] == "b reason."
```

- [ ] **Step 2: Confirm failure**

```bash
uv run pytest tests/integration/test_search_stream.py -v
```

Expected: 404.

- [ ] **Step 3: Extend `backend/app/routes/search.py`**

Append:

```python
import json as _json
from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse

from app.services.ranker import stream_cards


def _sse_event(name: str, payload: object) -> str:
    return f"event: {name}\ndata: {_json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/search/stream")
async def search_stream(body: SearchRequest) -> StreamingResponse:
    settings = get_settings()
    filters = ShortlistFilters(
        neighborhoods=body.neighborhoods,
        boroughs=body.boroughs,
        price_ceiling=body.price_ceiling,
    )
    items = fetch_shortlist(settings.db_path, filters, limit=40)
    if len(items) > 25:
        items = items[:25]
    candidates_payload = [
        {k: v for k, v in asdict(item).items() if k != "source_count"} for item in items
    ]

    llm = get_llm_client()
    rank_req = RankingRequest(
        shortlist=items,
        cuisines=body.cuisines,
        vibes=body.vibes,
        preferences_text=body.preferences_text,
        target_n=body.target_n,
    )

    async def generator() -> AsyncIterator[str]:
        yield _sse_event("candidates", {"candidates": candidates_payload})
        async for card in stream_cards(llm=llm, request=rank_req, model=settings.llm_model):
            yield _sse_event("card", {"id": card.id, "reason": card.reason})
        yield _sse_event("done", {"ok": True})

    return StreamingResponse(generator(), media_type="text/event-stream")
```

- [ ] **Step 4: Confirm tests pass**

```bash
uv run pytest tests/integration/test_search_stream.py -v
```

Expected: passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/search.py backend/tests/integration/test_search_stream.py
git commit -m "feat(dining): SSE /api/search/stream endpoint"
```

---

### Task 23: Frontend SSE consumer

**Files:**
- Create: `frontend/js/stream.js`
- Modify: `frontend/js/app.js`

- [ ] **Step 1: Create `frontend/js/stream.js`**

```javascript
export async function* streamSSE(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    credentials: "same-origin",
  });
  if (res.status === 401) {
    window.location.href = "/login";
    return;
  }
  if (!res.ok || !res.body) {
    throw new Error(`stream failed: ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const parsed = parseEvent(rawEvent);
      if (parsed) yield parsed;
    }
  }
}

function parseEvent(raw) {
  let event = "message";
  const dataLines = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) event = line.slice("event:".length).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice("data:".length).trim());
  }
  if (dataLines.length === 0) return null;
  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return null;
  }
}
```

- [ ] **Step 2: Replace the form submit handler in `frontend/js/app.js`**

Replace the `form.addEventListener("submit", ...)` block with:

```javascript
import { streamSSE } from "/js/stream.js";

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  button.disabled = true;
  resultsEl.innerHTML = "<p>Searching&hellip;</p>";
  try {
    const payload = buildPayload();
    let candidatesById = new Map();
    let renderedIds = new Set();
    for await (const evt of streamSSE("/api/search/stream", payload)) {
      if (evt.event === "candidates") {
        candidatesById = new Map(evt.data.candidates.map((c) => [c.id, c]));
      } else if (evt.event === "card") {
        const candidate = candidatesById.get(evt.data.id);
        if (!candidate) continue;
        if (renderedIds.size === 0) resultsEl.innerHTML = "";
        if (renderedIds.has(evt.data.id)) {
          const existing = resultsEl.querySelector(`[data-id="${evt.data.id}"] [data-role="reason"]`);
          if (existing) existing.textContent = evt.data.reason || existing.textContent;
        } else {
          renderedIds.add(evt.data.id);
          resultsEl.appendChild(renderCard(candidate, evt.data.reason));
        }
      } else if (evt.event === "done") {
        if (renderedIds.size === 0) {
          resultsEl.innerHTML = "<p>No matches. Try relaxing your filters.</p>";
        }
      }
    }
  } catch (err) {
    resultsEl.innerHTML = `<p class="error">${err.message}</p>`;
  } finally {
    button.disabled = false;
  }
});
```

Make sure the `import { search, whoami } from "/js/api.js"` line at the top is preserved but the `search` import can be removed since we no longer call it. Also remove any duplicate form-submit handler left from Phase 7.

- [ ] **Step 3: Manual smoke check**

With API key set and a seeded DB, run the server and verify cards appear progressively.

- [ ] **Step 4: Commit**

```bash
git add frontend/js/stream.js frontend/js/app.js
git commit -m "feat(dining): progressive streaming of result cards"
```

---

## Phase 9: Availability

Goal: click "Check availability" on a card → backend hits Resy → UI renders slot pills.

### Task 24: Resy client protocol, fake, and real

**Files:**
- Create: `backend/app/services/resy_client.py`
- Create: `backend/tests/fixtures/resy/find_happy.json`
- Create: `backend/tests/fixtures/resy/find_empty.json`
- Create: `backend/tests/fixtures/resy/find_venue_not_found.json`
- Create: `backend/tests/unit/test_resy_client.py`

- [ ] **Step 1: Create fixture `backend/tests/fixtures/resy/find_happy.json`**

```json
{
  "results": {
    "venues": [
      {
        "venue": {"id": {"resy": "345"}},
        "slots": [
          {
            "config": {
              "id": "slot-1",
              "token": "token-1",
              "type": "Dining Room"
            },
            "date": {"start": "2026-06-20 19:30:00"}
          },
          {
            "config": {
              "id": "slot-2",
              "token": "token-2",
              "type": "Bar"
            },
            "date": {"start": "2026-06-20 20:00:00"}
          },
          {
            "config": {
              "id": "slot-3",
              "token": "token-3",
              "type": "Dining Room"
            },
            "date": {"start": "2026-06-20 21:45:00"}
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Create fixture `backend/tests/fixtures/resy/find_empty.json`**

```json
{"results": {"venues": [{"venue": {"id": {"resy": "345"}}, "slots": []}]}}
```

- [ ] **Step 3: Create fixture `backend/tests/fixtures/resy/find_venue_not_found.json`**

```json
{"results": {"venues": []}}
```

- [ ] **Step 4: Write the failing test**

Create `backend/tests/unit/test_resy_client.py`:

```python
import json
from datetime import date, time
from pathlib import Path

import httpx
import pytest

from app.services.resy_client import (
    FakeResyClient,
    RealResyClient,
    ResyFindParams,
    ResyNotFoundError,
    ResyUpstreamError,
    Slot,
    normalize_slots,
)

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "resy"


def _params() -> ResyFindParams:
    return ResyFindParams(
        venue_id="345",
        party_size=2,
        day=date(2026, 6, 20),
        target_time=time(19, 30),
    )


def test_normalize_happy_path() -> None:
    raw = json.loads((FIX / "find_happy.json").read_text())
    slots = normalize_slots(raw, venue_id="345")
    assert [(s.time.isoformat(), s.seat_type) for s in slots] == [
        ("19:30:00", "Dining Room"),
        ("20:00:00", "Bar"),
        ("21:45:00", "Dining Room"),
    ]


def test_normalize_filters_outside_window() -> None:
    raw = json.loads((FIX / "find_happy.json").read_text())
    from datetime import time as dtime

    slots = normalize_slots(raw, venue_id="345", target_time=dtime(19, 30), window_hours=1)
    # 21:45 is more than 1 hour away
    assert all(s.time.hour < 21 for s in slots)


def test_normalize_empty() -> None:
    raw = json.loads((FIX / "find_empty.json").read_text())
    slots = normalize_slots(raw, venue_id="345")
    assert slots == []


def test_normalize_venue_not_found_raises() -> None:
    raw = json.loads((FIX / "find_venue_not_found.json").read_text())
    with pytest.raises(ResyNotFoundError):
        normalize_slots(raw, venue_id="345")


def test_fake_returns_scripted_slots() -> None:
    fake = FakeResyClient(
        responses=[
            [
                Slot(time=time(19, 30), seat_type="Dining Room", book_url="https://resy.com/..."),
                Slot(time=time(20, 0), seat_type="Bar", book_url="https://resy.com/..."),
            ]
        ]
    )
    out = fake.find_slots(_params())
    assert len(out) == 2


def test_fake_raises_scripted_not_found() -> None:
    fake = FakeResyClient(errors=[ResyNotFoundError("345")])
    with pytest.raises(ResyNotFoundError):
        fake.find_slots(_params())


def test_real_client_calls_resy_endpoint(respx_mock: "respx.MockRouter") -> None:  # noqa: F821
    pass  # replaced below


def test_real_client_uses_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    happy = json.loads((FIX / "find_happy.json").read_text())
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=happy))
    client = RealResyClient(api_key="k", auth_token="t", transport=transport)
    slots = client.find_slots(_params())
    assert len(slots) >= 1


def test_real_client_raises_on_5xx() -> None:
    transport = httpx.MockTransport(lambda req: httpx.Response(502))
    client = RealResyClient(api_key="k", auth_token="t", transport=transport)
    with pytest.raises(ResyUpstreamError):
        client.find_slots(_params())


def test_real_client_raises_on_empty_venues() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"results": {"venues": []}})
    )
    client = RealResyClient(api_key="k", auth_token="t", transport=transport)
    with pytest.raises(ResyNotFoundError):
        client.find_slots(_params())
```

Remove the stray placeholder `test_real_client_calls_resy_endpoint` — keep only the concrete `test_real_client_uses_httpx` / `test_real_client_raises_*` tests. Final test count: 8.

- [ ] **Step 5: Confirm failure**

```bash
uv run pytest tests/unit/test_resy_client.py -v
```

Expected: import errors.

- [ ] **Step 6: Create `backend/app/services/resy_client.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Protocol, runtime_checkable

import httpx


class ResyError(Exception):
    """Base class for Resy errors."""


class ResyNotFoundError(ResyError):
    """Venue not found."""


class ResyUpstreamError(ResyError):
    """Resy returned a non-2xx or unexpected response."""


@dataclass(frozen=True)
class Slot:
    time: time
    seat_type: str
    book_url: str


@dataclass(frozen=True)
class ResyFindParams:
    venue_id: str
    party_size: int
    day: date
    target_time: time | None = None


@runtime_checkable
class ResyClient(Protocol):
    def find_slots(self, params: ResyFindParams) -> list[Slot]: ...


def _parse_slot(raw: dict[str, Any]) -> tuple[time, str, str]:
    date_start = raw.get("date", {}).get("start") or ""
    try:
        dt = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ResyUpstreamError(f"unparseable slot date: {date_start!r}") from exc
    cfg = raw.get("config") or {}
    seat_type = str(cfg.get("type") or "")
    token = str(cfg.get("token") or "")
    book_url = f"https://resy.com/cities/ny/book/{token}" if token else ""
    return dt.time(), seat_type, book_url


def normalize_slots(
    raw: dict[str, Any],
    *,
    venue_id: str,
    target_time: time | None = None,
    window_hours: float = 2.0,
    limit: int = 5,
) -> list[Slot]:
    venues = raw.get("results", {}).get("venues") or []
    if not venues:
        raise ResyNotFoundError(venue_id)
    # Find the venue whose id matches, fall back to the first.
    chosen = venues[0]
    for v in venues:
        vid = (v.get("venue") or {}).get("id") or {}
        if str(vid.get("resy")) == venue_id:
            chosen = v
            break
    slots: list[Slot] = []
    for raw_slot in chosen.get("slots") or []:
        t, seat_type, book_url = _parse_slot(raw_slot)
        slots.append(Slot(time=t, seat_type=seat_type, book_url=book_url))
    if target_time is not None:
        window = timedelta(hours=window_hours)
        target = datetime.combine(date.today(), target_time)
        slots = [
            s for s in slots
            if abs(datetime.combine(date.today(), s.time) - target) <= window
        ]
    slots.sort(key=lambda s: s.time)
    return slots[:limit]


@dataclass
class FakeResyClient:
    responses: list[list[Slot]] = field(default_factory=list)
    errors: list[Exception] = field(default_factory=list)
    calls: list[ResyFindParams] = field(default_factory=list)

    def find_slots(self, params: ResyFindParams) -> list[Slot]:
        self.calls.append(params)
        if self.errors:
            raise self.errors.pop(0)
        if not self.responses:
            return []
        return self.responses.pop(0)


class RealResyClient:
    BASE_URL = "https://api.resy.com/4/find"

    def __init__(
        self,
        *,
        api_key: str,
        auth_token: str,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._auth_token = auth_token
        self._client = httpx.Client(transport=transport, timeout=timeout)

    def find_slots(self, params: ResyFindParams) -> list[Slot]:
        query = {
            "lat": "0",
            "long": "0",
            "day": params.day.isoformat(),
            "party_size": str(params.party_size),
            "venue_id": params.venue_id,
        }
        headers = {
            "Authorization": f'ResyAPI api_key="{self._api_key}"',
            "x-resy-auth-token": self._auth_token,
            "User-Agent": "NYC-Dining/1.0",
        }
        try:
            response = self._client.get(self.BASE_URL, params=query, headers=headers)
        except httpx.HTTPError as exc:
            raise ResyUpstreamError(str(exc)) from exc
        if response.status_code >= 500:
            raise ResyUpstreamError(f"Resy {response.status_code}")
        if response.status_code == 404:
            raise ResyNotFoundError(params.venue_id)
        if response.status_code >= 400:
            raise ResyUpstreamError(f"Resy {response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise ResyUpstreamError("non-JSON response") from exc
        return normalize_slots(
            data,
            venue_id=params.venue_id,
            target_time=params.target_time,
        )
```

- [ ] **Step 7: Confirm tests pass**

```bash
uv run pytest tests/unit/test_resy_client.py -v
```

Expected: 8 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/resy_client.py backend/tests/fixtures/resy backend/tests/unit/test_resy_client.py
git commit -m "feat(dining): Resy client protocol with real + fake + normalizer"
```

---

### Task 25: `/api/availability` endpoint

**Files:**
- Modify: `backend/app/dependencies.py`
- Create: `backend/app/routes/availability.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/integration/test_availability.py`

- [ ] **Step 1: Extend `backend/app/dependencies.py`**

Append:

```python
from app.services.resy_client import RealResyClient, ResyClient


_resy_override: ResyClient | None = None


@lru_cache(maxsize=1)
def _real_resy() -> ResyClient:
    import os

    return RealResyClient(
        api_key=os.getenv("RESY_API_KEY", ""),
        auth_token=os.getenv("RESY_AUTH_TOKEN", ""),
    )


def get_resy_client() -> ResyClient:
    if _resy_override is not None:
        return _resy_override
    return _real_resy()


def set_resy_override(client: ResyClient | None) -> None:
    global _resy_override
    _resy_override = client
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/integration/test_availability.py`:

```python
from datetime import time

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password, sign_session
from app.dependencies import set_resy_override
from app.db import connect
from app.models import SeedRestaurant
from app.services.resy_client import FakeResyClient, ResyNotFoundError, ResyUpstreamError, Slot
from scrapers.importer import import_seed


@pytest.fixture
def logged_in(tmp_db, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SHARED_PASSWORD_HASH", hash_password("p"))
    monkeypatch.setenv("COOKIE_SIGNING_KEY", "k")
    import_seed(
        tmp_db,
        [
            SeedRestaurant(
                name="Lilia",
                neighborhood="Williamsburg",
                borough="Brooklyn",
                price_tier=3,
                booking_platform="resy",
                resy_venue_id="345",
            ),
            SeedRestaurant(
                name="Joe's Pizza",
                neighborhood="West Village",
                borough="Manhattan",
                price_tier=1,
                booking_platform="walk_in",
            ),
            SeedRestaurant(
                name="Nami Nori",
                neighborhood="West Village",
                borough="Manhattan",
                booking_platform="resy",  # no resy_venue_id
            ),
        ],
    )
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        c.cookies.set("session", sign_session(1, "Eli", "k"))
        yield c


def test_availability_happy_path(logged_in: TestClient) -> None:
    fake = FakeResyClient(
        responses=[
            [
                Slot(time=time(19, 30), seat_type="Dining Room", book_url="https://resy.com/x"),
                Slot(time=time(20, 0), seat_type="Bar", book_url="https://resy.com/y"),
            ]
        ]
    )
    set_resy_override(fake)
    try:
        resp = logged_in.get(
            "/api/availability",
            params={
                "restaurant_id": "lilia-williamsburg",
                "party": 2,
                "date": "2026-06-20",
                "time": "19:30",
            },
        )
    finally:
        set_resy_override(None)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["slots"]) == 2
    assert body["slots"][0]["time"] == "19:30"


def test_availability_walk_in(logged_in: TestClient) -> None:
    resp = logged_in.get(
        "/api/availability",
        params={"restaurant_id": "joe-s-pizza-west-village", "party": 1, "date": "2026-06-20", "time": "19:00"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "use_booking_url"


def test_availability_no_venue_id(logged_in: TestClient) -> None:
    resp = logged_in.get(
        "/api/availability",
        params={"restaurant_id": "nami-nori-west-village", "party": 2, "date": "2026-06-20", "time": "19:00"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "no_venue_id"


def test_availability_venue_not_found_flags_review(logged_in: TestClient, tmp_db) -> None:
    fake = FakeResyClient(errors=[ResyNotFoundError("345")])
    set_resy_override(fake)
    try:
        resp = logged_in.get(
            "/api/availability",
            params={
                "restaurant_id": "lilia-williamsburg",
                "party": 2,
                "date": "2026-06-20",
                "time": "19:00",
            },
        )
    finally:
        set_resy_override(None)
    assert resp.status_code == 404

    conn = connect(tmp_db)
    try:
        row = conn.execute(
            "SELECT status FROM restaurants WHERE id = ?", ("lilia-williamsburg",)
        ).fetchone()
    finally:
        conn.close()
    assert row["status"] == "needs_review"


def test_availability_upstream_error_returns_503(logged_in: TestClient) -> None:
    fake = FakeResyClient(errors=[ResyUpstreamError("boom")])
    set_resy_override(fake)
    try:
        resp = logged_in.get(
            "/api/availability",
            params={
                "restaurant_id": "lilia-williamsburg",
                "party": 2,
                "date": "2026-06-20",
                "time": "19:00",
            },
        )
    finally:
        set_resy_override(None)
    assert resp.status_code == 503
    assert resp.json()["detail"] == "resy_unreachable"


def test_availability_requires_auth(tmp_db) -> None:
    from app.main import create_app

    with TestClient(create_app()) as c:
        resp = c.get(
            "/api/availability",
            params={"restaurant_id": "x", "party": 2, "date": "2026-06-20", "time": "19:00"},
        )
    assert resp.status_code == 401
```

- [ ] **Step 3: Confirm failure**

```bash
uv run pytest tests/integration/test_availability.py -v
```

Expected: 404s / import errors.

- [ ] **Step 4: Create `backend/app/routes/availability.py`**

```python
from __future__ import annotations

from datetime import date, time

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import get_settings
from app.db import connect
from app.dependencies import get_resy_client
from app.services.resy_client import (
    ResyFindParams,
    ResyNotFoundError,
    ResyUpstreamError,
)

router = APIRouter(prefix="/api", tags=["availability"])


class SlotResponse(BaseModel):
    time: str
    seat_type: str
    book_url: str


class AvailabilityResponse(BaseModel):
    slots: list[SlotResponse]


@router.get("/availability", response_model=AvailabilityResponse)
def availability(
    restaurant_id: str = Query(min_length=1),
    party: int = Query(ge=1, le=20),
    date: date = Query(alias="date"),
    time: time = Query(alias="time"),
) -> AvailabilityResponse:
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        row = conn.execute(
            "SELECT booking_platform, resy_venue_id, booking_url FROM restaurants WHERE id = ?",
            (restaurant_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="restaurant_not_found")
    if row["booking_platform"] != "resy":
        raise HTTPException(status_code=400, detail="use_booking_url")
    venue_id = row["resy_venue_id"]
    if not venue_id:
        raise HTTPException(status_code=400, detail="no_venue_id")

    client = get_resy_client()
    try:
        slots = client.find_slots(
            ResyFindParams(
                venue_id=venue_id,
                party_size=party,
                day=date,
                target_time=time,
            )
        )
    except ResyNotFoundError as exc:
        _flag_for_review(settings.db_path, restaurant_id)
        raise HTTPException(status_code=404, detail="venue_not_found") from exc
    except ResyUpstreamError as exc:
        raise HTTPException(status_code=503, detail="resy_unreachable") from exc

    return AvailabilityResponse(
        slots=[
            SlotResponse(
                time=s.time.strftime("%H:%M"),
                seat_type=s.seat_type,
                book_url=s.book_url,
            )
            for s in slots
        ]
    )


def _flag_for_review(db_path, restaurant_id: str) -> None:
    conn = connect(db_path)
    try:
        conn.execute(
            "UPDATE restaurants SET status='needs_review', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (restaurant_id,),
        )
    finally:
        conn.close()
```

- [ ] **Step 5: Register router in `backend/app/main.py`**

After the search router include, add:

```python
    from app.routes import availability as availability_routes

    application.include_router(availability_routes.router)
```

- [ ] **Step 6: Confirm tests pass**

```bash
uv run pytest tests/integration/test_availability.py -v
```

Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/dependencies.py backend/app/routes/availability.py backend/app/main.py backend/tests/integration/test_availability.py
git commit -m "feat(dining): /api/availability endpoint with Resy integration"
```

---

### Task 26: Availability UI on cards

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`
- Modify: `frontend/js/api.js`
- Modify: `frontend/css/app.css`

- [ ] **Step 1: Add date/time/party inputs to the form**

Inside the "Where" fieldset of `frontend/index.html`, append:

```html
        <label>
          <span>Date</span>
          <input type="date" name="date" />
        </label>
        <label>
          <span>Time</span>
          <input type="time" name="time" />
        </label>
        <label>
          <span>Party size</span>
          <input type="number" name="party" min="1" max="20" value="2" />
        </label>
```

- [ ] **Step 2: Extend `frontend/js/api.js`**

Append:

```javascript
export async function checkAvailability({ restaurantId, party, date, time }) {
  const params = new URLSearchParams({
    restaurant_id: restaurantId,
    party: String(party),
    date,
    time,
  });
  const res = await fetch(`/api/availability?${params.toString()}`, {
    credentials: "same-origin",
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("unauthorized");
  }
  const body = await res.json().catch(() => ({}));
  return { status: res.status, body };
}
```

- [ ] **Step 3: Wire button into `renderCard` in `frontend/js/app.js`**

At the top, import `checkAvailability`:

```javascript
import { whoami, checkAvailability } from "/js/api.js";
```

Replace the action/pill logic inside `renderCard` with the following (it adds the "Check availability" button when applicable, and a container for slot results):

```javascript
  const action = bookingAction(candidate);
  const actionRow = document.createElement("div");
  actionRow.className = "action-row";

  if (action.href) {
    const a = document.createElement("a");
    a.href = action.href;
    a.className = "btn-primary";
    a.textContent = action.label;
    a.target = "_blank";
    a.rel = "noopener";
    actionRow.appendChild(a);
  } else if (action.label) {
    const span = document.createElement("span");
    span.className = "pill";
    span.textContent = action.label;
    actionRow.appendChild(span);
  }

  const fd = new FormData(form);
  const date = fd.get("date");
  const timeVal = fd.get("time");
  const party = fd.get("party");
  if (candidate.booking_platform === "resy" && candidate.resy_venue_id && date && timeVal && party) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn-secondary";
    btn.textContent = "Check availability";
    const slotsEl = document.createElement("div");
    slotsEl.className = "slots";
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      slotsEl.textContent = "Checking…";
      const { status, body } = await checkAvailability({
        restaurantId: candidate.id,
        party,
        date,
        time: timeVal,
      });
      slotsEl.innerHTML = "";
      if (status === 200) {
        if ((body.slots ?? []).length === 0) {
          slotsEl.textContent = "No slots within ±2h. Try another time.";
        } else {
          for (const slot of body.slots) {
            const a = document.createElement("a");
            a.className = "slot-pill";
            a.href = slot.book_url;
            a.target = "_blank";
            a.rel = "noopener";
            a.textContent = slot.time;
            slotsEl.appendChild(a);
          }
        }
      } else if (status === 400 && body.detail === "use_booking_url") {
        slotsEl.textContent = "Book directly — availability not available here.";
      } else if (status === 404 && body.detail === "venue_not_found") {
        slotsEl.textContent = "Venue missing on Resy. Flagged for review.";
      } else if (status === 503) {
        slotsEl.textContent = "Resy unreachable — try the booking link above.";
      } else {
        slotsEl.textContent = "Could not check availability.";
      }
      btn.disabled = false;
    });
    actionRow.appendChild(btn);
    card.appendChild(actionRow);
    card.appendChild(slotsEl);
    return card;
  }

  card.appendChild(actionRow);
  return card;
```

(Remove the earlier action append that returned `card` directly so this version is the only path.)

- [ ] **Step 4: Append CSS in `frontend/css/app.css`**

```css
.action-row { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
.btn-secondary {
  padding: 0.4rem 0.75rem; border: 1px solid #888; background: canvas; border-radius: 4px;
  cursor: pointer;
}
.slots { margin-top: 0.5rem; display: flex; flex-wrap: wrap; gap: 0.4rem; }
.slot-pill {
  padding: 0.2rem 0.6rem; border: 1px solid #1a73e8; border-radius: 999px;
  color: #1a73e8; text-decoration: none;
}
```

- [ ] **Step 5: Manual smoke check**

- Seed DB with at least one restaurant that has `booking_platform='resy'` and a `resy_venue_id`.
- Fill form with date + time + party, click search, then click "Check availability" on a Resy card.
- (Without a real Resy token, this will 503 — set `RESY_API_KEY` and `RESY_AUTH_TOKEN` for a live check.)

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html frontend/js/app.js frontend/js/api.js frontend/css/app.css
git commit -m "feat(dining): availability button and slot pills on cards"
```

---

## Wrap-up

- [ ] **Step 1: Run the full test suite**

```bash
cd backend
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest --cov=app --cov=scrapers --cov-report=term-missing
```

Expected: all pass, coverage ≥ 85% on `app/` and `scrapers/`.

- [ ] **Step 2: End-to-end smoke via curl**

With the server running and `SHARED_PASSWORD_HASH` set:

```bash
# 1. Password
curl -i -c cookies.txt -H "Content-Type: application/json" \
  -d '{"password":"YOUR_PASS"}' http://localhost:8000/api/login/verify-password
# 2. Pick name
curl -i -b cookies.txt -c cookies.txt -H "Content-Type: application/json" \
  -d '{"display_name":"Eli"}' http://localhost:8000/api/login/complete
# 3. Search
curl -N -b cookies.txt -H "Content-Type: application/json" \
  -d '{"neighborhoods":["Williamsburg"],"preferences_text":"pasta"}' \
  http://localhost:8000/api/search/stream
```

Expected: SSE events stream `candidates`, multiple `card`, `done`.

- [ ] **Step 3: Tag MVP commit**

```bash
cd /Users/elistraus/opt/Claude/dining
git tag dining-mvp
```

(Leave tag local unless promoting.)

---

## Post-MVP (next plan, not this one)

The spec's Phases 10-13 are deferred:
- Admin page (`/admin`) with add-by-URL, add-by-name, edit/remove, re-seed diffs.
- Personal notes CRUD wired into result cards.
- Remaining scrapers: Infatuation Hit List, NYT 100 Best, NY Mag.
- Ops: backups, structured logging, nightly contract tests, Playwright E2E.

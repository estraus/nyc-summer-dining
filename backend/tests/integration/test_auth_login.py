from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password


@pytest.fixture
def password_client(tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
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


def test_complete_login_creates_user_and_sets_session(password_client: TestClient) -> None:
    pre = password_client.post("/api/login/verify-password", json={"password": "open-sesame"})
    assert pre.status_code == 200

    resp = password_client.post("/api/login/complete", json={"display_name": "Eli"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Eli"
    assert body["user_id"] >= 1
    assert "session" in resp.cookies


def test_complete_login_requires_pre_auth(tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.main import create_app

    monkeypatch.setenv("SHARED_PASSWORD_HASH", hash_password("open-sesame"))
    with TestClient(create_app()) as c:
        resp = c.post("/api/login/complete", json={"display_name": "Eli"})
    assert resp.status_code == 401


def test_login_rate_limit_returns_429(tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARED_PASSWORD_HASH", hash_password("p"))
    monkeypatch.setenv("LOGIN_RATE_LIMIT", "3")
    monkeypatch.setenv("LOGIN_RATE_WINDOW_SECONDS", "3600")
    from app.config import get_settings
    from app.main import create_app
    from app.routes import auth as auth_routes

    get_settings.cache_clear()
    auth_routes._reset_login_limiter()

    with TestClient(create_app()) as c:
        for _ in range(3):
            r = c.post("/api/login/verify-password", json={"password": "wrong"})
            assert r.status_code == 401
        r = c.post("/api/login/verify-password", json={"password": "wrong"})
        assert r.status_code == 429
        assert "retry-after" in {h.lower() for h in r.headers}


def test_cookies_omit_secure_flag_when_disabled(password_client: TestClient) -> None:
    resp = password_client.post("/api/login/verify-password", json={"password": "open-sesame"})
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "pre_auth=" in set_cookie
    assert "Secure" not in set_cookie


def test_cookies_marked_secure_when_enabled(tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARED_PASSWORD_HASH", hash_password("p"))
    monkeypatch.setenv("COOKIE_SECURE", "true")
    from app.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()

    with TestClient(create_app()) as c:
        verify = c.post("/api/login/verify-password", json={"password": "p"})
    assert verify.status_code == 200
    assert "Secure" in verify.headers.get("set-cookie", "")


def test_list_users_after_creation(password_client: TestClient) -> None:
    # first user logs in, completing the flow (pre_auth → session)
    password_client.post("/api/login/verify-password", json={"password": "open-sesame"})
    password_client.post("/api/login/complete", json={"display_name": "Eli"})
    # simulate a subsequent login attempt: re-verify password to regain pre_auth,
    # then list users (endpoint requires pre_auth, used during the name-picker step)
    password_client.post("/api/login/verify-password", json={"password": "open-sesame"})
    users_resp = password_client.get("/api/login/users")
    assert users_resp.status_code == 200
    names = [u["display_name"] for u in users_resp.json()["users"]]
    assert "Eli" in names

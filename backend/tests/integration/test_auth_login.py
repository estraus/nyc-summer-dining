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

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password, sign_session


@pytest.fixture
def app_client(
    tmp_db: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
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
    resp = app_client.get("/api/whoami")
    assert resp.status_code == 401

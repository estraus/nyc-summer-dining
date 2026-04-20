from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password


@pytest.fixture
def password_client(
    tmp_db: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
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

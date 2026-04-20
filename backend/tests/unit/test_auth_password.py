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

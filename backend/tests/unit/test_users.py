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

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.backup import RETENTION_DAYS, _compress, backup


@pytest.fixture
def db_file(tmp_path: Path) -> Path:
    p = tmp_path / "restaurants.db"
    p.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
    return p


def _make_response(body: object, status: int = 200) -> MagicMock:
    m = MagicMock()
    m.status_code = status
    m.json.return_value = body
    m.raise_for_status = MagicMock()
    return m


def _auth_response() -> object:
    return {
        "apiUrl": "https://api.backblaze.test",
        "authorizationToken": "auth-token",
        "accountId": "acct-1",
    }


def _bucket_response(bucket_id: str = "bucket-abc") -> object:
    return {"buckets": [{"bucketId": bucket_id}]}


def _upload_url_response() -> object:
    return {"uploadUrl": "https://upload.backblaze.test", "authorizationToken": "upload-token"}


def _list_response(files: list[dict]) -> object:
    return {"files": files, "nextFileName": None}


def test_compress_produces_valid_gzip(db_file: Path) -> None:
    compressed = _compress(db_file)
    assert compressed[:2] == b"\x1f\x8b"
    assert gzip.decompress(compressed) == db_file.read_bytes()


def test_compress_is_deterministic(db_file: Path) -> None:
    assert _compress(db_file) == _compress(db_file)


def test_backup_uploads_and_returns_filename(db_file: Path) -> None:
    with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
        mock_get.return_value = _make_response(_auth_response())
        mock_post.side_effect = [
            _make_response(_bucket_response()),
            _make_response(_upload_url_response()),
            _make_response({"fileId": "f1", "fileName": "restaurants-20260101-000000.db.gz"}),
            _make_response(_list_response([])),
        ]

        filename = backup(db_file, "key", "appkey", "my-bucket")

    assert filename.startswith("restaurants-")
    assert filename.endswith(".db.gz")


def test_backup_prunes_old_files(db_file: Path) -> None:
    old_ts = int((datetime.now(UTC) - timedelta(days=RETENTION_DAYS + 1)).timestamp() * 1000)
    recent_ts = int(datetime.now(UTC).timestamp() * 1000)

    old_file = {"fileId": "old-id", "fileName": "restaurants-old.db.gz", "uploadTimestamp": old_ts}
    recent_file = {
        "fileId": "new-id",
        "fileName": "restaurants-new.db.gz",
        "uploadTimestamp": recent_ts,
    }

    with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
        mock_get.return_value = _make_response(_auth_response())
        mock_post.side_effect = [
            _make_response(_bucket_response()),
            _make_response(_upload_url_response()),
            _make_response({"fileId": "f1", "fileName": "x.db.gz"}),
            _make_response(_list_response([old_file, recent_file])),
            _make_response({}),  # delete old_file
        ]

        backup(db_file, "key", "appkey", "my-bucket")

    # delete call should reference only the old file
    delete_call = mock_post.call_args_list[-1]
    body = delete_call.kwargs.get("json") or delete_call.args[0] if delete_call.args else {}
    if not body:
        body = json.loads(delete_call.kwargs.get("content", b"{}"))
    assert delete_call.kwargs["json"]["fileId"] == "old-id"


def test_backup_does_not_prune_recent_files(db_file: Path) -> None:
    recent_ts = int(datetime.now(UTC).timestamp() * 1000)
    recent_file = {
        "fileId": "new-id",
        "fileName": "restaurants-new.db.gz",
        "uploadTimestamp": recent_ts,
    }

    with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
        mock_get.return_value = _make_response(_auth_response())
        mock_post.side_effect = [
            _make_response(_bucket_response()),
            _make_response(_upload_url_response()),
            _make_response({"fileId": "f1", "fileName": "x.db.gz"}),
            _make_response(_list_response([recent_file])),
        ]

        backup(db_file, "key", "appkey", "my-bucket")

    # Only 4 post calls — no delete
    assert mock_post.call_count == 4


def test_backup_raises_on_missing_bucket(db_file: Path) -> None:
    with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
        mock_get.return_value = _make_response(_auth_response())
        mock_post.return_value = _make_response({"buckets": []})

        with pytest.raises(ValueError, match="not found"):
            backup(db_file, "key", "appkey", "nonexistent-bucket")

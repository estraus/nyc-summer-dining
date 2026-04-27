"""Backup restaurants.db to Backblaze B2 with 14-day retention.

Run as: uv run python -m scripts.backup
Env vars required: B2_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME
"""

from __future__ import annotations

import gzip
import hashlib
import io
import logging
import os
import sys
from base64 import b64encode
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

RETENTION_DAYS = 14
_B2_API = "https://api.backblazeb2.com"


def _authorize(key_id: str, app_key: str) -> dict[str, str]:
    credentials = b64encode(f"{key_id}:{app_key}".encode()).decode()
    r = httpx.get(
        f"{_B2_API}/b2api/v2/b2_authorize_account",
        headers={"Authorization": f"Basic {credentials}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()  # type: ignore[no-any-return]


def _get_bucket_id(api_url: str, auth_token: str, account_id: str, bucket_name: str) -> str:
    r = httpx.post(
        f"{api_url}/b2api/v2/b2_list_buckets",
        headers={"Authorization": auth_token},
        json={"accountId": account_id, "bucketName": bucket_name},
        timeout=30,
    )
    r.raise_for_status()
    buckets = r.json()["buckets"]
    if not buckets:
        raise ValueError(f"B2 bucket {bucket_name!r} not found")
    return str(buckets[0]["bucketId"])


def _get_upload_url(api_url: str, auth_token: str, bucket_id: str) -> dict[str, str]:
    r = httpx.post(
        f"{api_url}/b2api/v2/b2_get_upload_url",
        headers={"Authorization": auth_token},
        json={"bucketId": bucket_id},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()  # type: ignore[no-any-return]


def _upload(upload_url: str, upload_token: str, filename: str, data: bytes) -> None:
    sha1 = hashlib.sha1(data).hexdigest()
    r = httpx.post(
        upload_url,
        headers={
            "Authorization": upload_token,
            "X-Bz-File-Name": filename,
            "Content-Type": "application/gzip",
            "Content-Length": str(len(data)),
            "X-Bz-Content-Sha1": sha1,
        },
        content=data,
        timeout=120,
    )
    r.raise_for_status()


def _list_files(
    api_url: str, auth_token: str, bucket_id: str, prefix: str
) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    start: str | None = None
    while True:
        payload: dict[str, object] = {"bucketId": bucket_id, "prefix": prefix, "maxFileCount": 100}
        if start:
            payload["startFileName"] = start
        r = httpx.post(
            f"{api_url}/b2api/v2/b2_list_file_names",
            headers={"Authorization": auth_token},
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        files.extend(body["files"])
        start = body.get("nextFileName")
        if not start:
            break
    return files


def _delete_file(api_url: str, auth_token: str, file_id: str, file_name: str) -> None:
    httpx.post(
        f"{api_url}/b2api/v2/b2_delete_file_version",
        headers={"Authorization": auth_token},
        json={"fileId": file_id, "fileName": file_name},
        timeout=30,
    ).raise_for_status()


def _compress(db_path: Path) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(db_path.read_bytes())
    return buf.getvalue()


def backup(db_path: Path, key_id: str, app_key: str, bucket_name: str) -> str:
    """Upload a gzipped snapshot of db_path to B2, prune old files. Returns uploaded filename."""
    now = datetime.now(UTC)
    filename = f"restaurants-{now.strftime('%Y%m%d-%H%M%S')}.db.gz"

    compressed = _compress(db_path)
    logging.info(
        "Compressed %s: %d → %d bytes",
        db_path.name,
        db_path.stat().st_size,
        len(compressed),
    )

    auth = _authorize(key_id, app_key)
    api_url = auth["apiUrl"]
    auth_token = auth["authorizationToken"]
    account_id = auth["accountId"]

    bucket_id = _get_bucket_id(api_url, auth_token, account_id, bucket_name)
    upload_info = _get_upload_url(api_url, auth_token, bucket_id)
    _upload(upload_info["uploadUrl"], upload_info["authorizationToken"], filename, compressed)
    logging.info("Uploaded %s to B2 bucket %s", filename, bucket_name)

    cutoff = now - timedelta(days=RETENTION_DAYS)
    old_files = _list_files(api_url, auth_token, bucket_id, prefix="restaurants-")
    pruned = 0
    for f in old_files:
        ts = datetime.fromtimestamp(int(f["uploadTimestamp"]) / 1000, tz=UTC)
        if ts < cutoff:
            _delete_file(api_url, auth_token, str(f["fileId"]), str(f["fileName"]))
            pruned += 1
            logging.info("Pruned old backup: %s", f["fileName"])
    if pruned:
        logging.info("Pruned %d backup(s) older than %d days", pruned, RETENTION_DAYS)

    return filename


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    key_id = os.getenv("B2_KEY_ID", "")
    app_key = os.getenv("B2_APPLICATION_KEY", "")
    bucket_name = os.getenv("B2_BUCKET_NAME", "")
    db_path = Path(os.getenv("DATABASE_PATH", "/data/restaurants.db"))

    if not all([key_id, app_key, bucket_name]):
        logging.error("B2_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME must all be set")
        sys.exit(1)
    if not db_path.exists():
        logging.error("DB not found: %s", db_path)
        sys.exit(1)

    try:
        filename = backup(db_path, key_id, app_key, bucket_name)
        logging.info("Backup complete: %s", filename)
    except Exception:
        logging.exception("Backup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

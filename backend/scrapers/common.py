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

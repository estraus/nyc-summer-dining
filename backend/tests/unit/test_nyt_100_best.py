import json
from pathlib import Path

import pytest

from app.services.llm_client import FakeLLMClient
from scrapers.nyt_100_best import parse_entries, scrape

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "html" / "nyt_100_best.html"


def test_parse_entries_returns_expected_count() -> None:
    html = FIXTURE.read_text()
    entries = parse_entries(html)
    assert len(entries) == 3


def test_parse_entries_extracts_name() -> None:
    html = FIXTURE.read_text()
    entries = parse_entries(html)
    assert entries[0].name == "Le Bernardin"


def test_parse_entries_extracts_neighborhood() -> None:
    html = FIXTURE.read_text()
    entries = parse_entries(html)
    assert entries[0].neighborhood_text == "Midtown, Manhattan"


def test_scrape_calls_extract_fields_per_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    html = FIXTURE.read_text()

    def fake_fetch(url: str) -> str:
        assert "nytimes" in url
        return html

    responses = [
        json.dumps(
            {
                "name": "Le Bernardin",
                "neighborhood": "Midtown",
                "borough": "Manhattan",
                "price_tier": 4,
                "booking_platform": "resy",
                "cuisine_tags": ["french", "seafood"],
                "vibe_tags": ["nice", "tasting-menu"],
            }
        ),
        json.dumps(
            {
                "name": "Atomix",
                "neighborhood": "NoMad",
                "borough": "Manhattan",
                "price_tier": 4,
                "booking_platform": "resy",
                "cuisine_tags": ["korean"],
                "vibe_tags": ["tasting-menu", "nice"],
            }
        ),
        json.dumps(
            {
                "name": "Lucali",
                "neighborhood": "Carroll Gardens",
                "borough": "Brooklyn",
                "price_tier": 2,
                "booking_platform": "walk_in",
                "cuisine_tags": ["pizza", "italian"],
                "vibe_tags": ["casual"],
            }
        ),
    ]
    llm = FakeLLMClient(responses=responses)
    results = scrape(fetch=fake_fetch, llm=llm)
    assert len(results) == 3
    assert all(s.sources[0].publication == "nyt_100" for s in results)


def test_scrape_empty_page_returns_empty_list() -> None:
    empty_html = "<html><body><div class='article-body'></div></body></html>"

    def fake_fetch(url: str) -> str:
        return empty_html

    llm = FakeLLMClient(responses=[])
    results = scrape(fetch=fake_fetch, llm=llm)
    assert results == []

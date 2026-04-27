import json
from pathlib import Path

import pytest

from app.services.llm_client import FakeLLMClient
from scrapers.infatuation_hit_list import parse_entries, scrape

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "html" / "infatuation_hit_list.html"


def test_parse_entries_returns_expected_count() -> None:
    html = FIXTURE.read_text()
    entries = parse_entries(html)
    assert len(entries) == 3


def test_parse_entries_extracts_name() -> None:
    html = FIXTURE.read_text()
    entries = parse_entries(html)
    assert entries[0].name == "Francie"


def test_parse_entries_extracts_neighborhood() -> None:
    html = FIXTURE.read_text()
    entries = parse_entries(html)
    assert entries[0].neighborhood_text == "Williamsburg"


def test_scrape_calls_extract_fields_per_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    html = FIXTURE.read_text()

    def fake_fetch(url: str) -> str:
        assert "infatuation" in url
        return html

    responses = [
        json.dumps(
            {
                "name": "Francie",
                "neighborhood": "Williamsburg",
                "borough": "Brooklyn",
                "price_tier": 3,
                "booking_platform": "resy",
                "cuisine_tags": ["american"],
                "vibe_tags": ["date-night"],
            }
        ),
        json.dumps(
            {
                "name": "Tatiana",
                "neighborhood": "Lincoln Center",
                "borough": "Manhattan",
                "price_tier": 3,
                "booking_platform": "resy",
                "cuisine_tags": ["caribbean", "american"],
                "vibe_tags": ["nice"],
            }
        ),
        json.dumps(
            {
                "name": "Don Angie",
                "neighborhood": "West Village",
                "borough": "Manhattan",
                "price_tier": 3,
                "booking_platform": "resy",
                "cuisine_tags": ["italian"],
                "vibe_tags": ["casual"],
            }
        ),
    ]
    llm = FakeLLMClient(responses=responses)
    results = scrape(fetch=fake_fetch, llm=llm)
    assert len(results) == 3
    assert all(s.sources[0].publication == "infatuation" for s in results)


def test_scrape_empty_page_returns_empty_list() -> None:
    empty_html = "<html><body><div class='hit-list'></div></body></html>"

    def fake_fetch(url: str) -> str:
        return empty_html

    llm = FakeLLMClient(responses=[])
    results = scrape(fetch=fake_fetch, llm=llm)
    assert results == []

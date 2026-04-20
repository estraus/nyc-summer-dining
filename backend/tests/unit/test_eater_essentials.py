import json
from pathlib import Path

import pytest

from app.services.llm_client import FakeLLMClient
from scrapers.eater_essentials import parse_entries, scrape

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "html" / "eater_essentials.html"


def test_parse_entries_extracts_cards() -> None:
    html = FIXTURE.read_text()
    entries = parse_entries(html)
    names = [e.name for e in entries]
    assert names == ["Lilia", "Nami Nori"]
    assert "Williamsburg temple to pasta" in entries[0].description_text


def test_scrape_fetches_and_extracts(monkeypatch: pytest.MonkeyPatch) -> None:
    html = FIXTURE.read_text()

    def fake_fetch(url: str) -> str:
        assert "eater" in url
        return html

    responses = [
        json.dumps(
            {
                "name": "Lilia",
                "neighborhood": "Williamsburg",
                "borough": "Brooklyn",
                "price_tier": 3,
                "booking_platform": "resy",
                "cuisine_tags": ["italian", "pasta"],
                "vibe_tags": ["date-night"],
            }
        ),
        json.dumps(
            {
                "name": "Nami Nori",
                "neighborhood": "West Village",
                "borough": "Manhattan",
                "price_tier": 2,
                "booking_platform": "resy",
                "cuisine_tags": ["japanese", "sushi"],
                "vibe_tags": ["casual", "counter-only"],
            }
        ),
    ]
    llm = FakeLLMClient(responses=responses)
    seeds = scrape(fetch=fake_fetch, llm=llm)
    assert len(seeds) == 2
    assert seeds[0].slug() == "lilia-williamsburg"
    assert seeds[1].neighborhood == "West Village"
    assert all(s.sources[0].publication == "eater_nyc" for s in seeds)

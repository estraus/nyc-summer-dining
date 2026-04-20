import json

import pytest

from app.services.fields_extractor import extract_fields
from app.services.llm_client import FakeLLMClient


def test_extract_returns_seed_restaurant() -> None:
    payload = {
        "name": "Lilia",
        "neighborhood": "Williamsburg",
        "borough": "Brooklyn",
        "price_tier": 3,
        "booking_platform": "resy",
        "cuisine_tags": ["italian", "pasta"],
        "vibe_tags": ["date-night"],
        "feature_tags": [],
        "description": "Missy Robbins's pasta and wood-fired vegetables.",
    }
    llm = FakeLLMClient(responses=[json.dumps(payload)])
    seed = extract_fields(
        llm=llm,
        source_url="https://ny.eater.com/maps/best-new-york-restaurants-38-essential",
        source_text="Lilia — Williamsburg, Brooklyn. ...",
        publication="eater_nyc",
        list_name="38 Essential",
        blurb="A pasta temple.",
    )
    assert seed.name == "Lilia"
    assert seed.neighborhood == "Williamsburg"
    assert seed.cuisine_tags == ["italian", "pasta"]
    assert len(seed.sources) == 1
    assert seed.sources[0].publication == "eater_nyc"
    assert seed.sources[0].blurb == "A pasta temple."


def test_extract_rejects_malformed_json() -> None:
    llm = FakeLLMClient(responses=["not-json"])
    with pytest.raises(ValueError):
        extract_fields(
            llm=llm,
            source_url="https://x",
            source_text="ignored",
            publication="eater_nyc",
            list_name="x",
            blurb=None,
        )


def test_extract_rejects_invalid_shape() -> None:
    llm = FakeLLMClient(responses=[json.dumps({"name": "", "neighborhood": "x"})])
    with pytest.raises(ValueError):
        extract_fields(
            llm=llm,
            source_url="https://x",
            source_text="ignored",
            publication="eater_nyc",
            list_name="x",
            blurb=None,
        )


def test_extract_strips_code_fences() -> None:
    payload = {"name": "Lilia", "neighborhood": "Williamsburg", "borough": "Brooklyn"}
    raw = f"```json\n{json.dumps(payload)}\n```"
    llm = FakeLLMClient(responses=[raw])
    seed = extract_fields(
        llm=llm,
        source_url="https://x",
        source_text="ignored",
        publication="eater_nyc",
        list_name="38 Essential",
        blurb=None,
    )
    assert seed.name == "Lilia"


def test_extract_records_system_prompt_mentions_fields() -> None:
    payload = {"name": "Lilia", "neighborhood": "Williamsburg"}
    llm = FakeLLMClient(responses=[json.dumps(payload)])
    extract_fields(
        llm=llm,
        source_url="https://x",
        source_text="ignored",
        publication="eater_nyc",
        list_name="38 Essential",
        blurb=None,
    )
    assert "cuisine_tags" in llm.calls[0].system
    assert "neighborhood" in llm.calls[0].system
    assert "ignored" in llm.calls[0].user

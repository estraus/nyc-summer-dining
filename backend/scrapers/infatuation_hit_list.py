from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from selectolax.parser import HTMLParser

from app.models import SeedRestaurant
from app.services.fields_extractor import extract_fields
from app.services.llm_client import LLMClient
from scrapers.common import fetch_url

SOURCE_URL = "https://www.theinfatuation.com/new-york/guides/the-nyc-hit-list"
PUBLICATION = "infatuation"
LIST_NAME = "NYC Hit List"


@dataclass(frozen=True)
class Entry:
    name: str
    neighborhood_text: str
    description_text: str


def parse_entries(html: str) -> list[Entry]:
    tree = HTMLParser(html)
    entries: list[Entry] = []
    for card in tree.css("article.venue-card"):
        name_node = card.css_first("h2.venue-card__name")
        if name_node is None:
            continue
        name = name_node.text(strip=True)
        neighborhood_node = card.css_first("p.venue-card__neighborhood")
        description_node = card.css_first("div.venue-card__review")
        entries.append(
            Entry(
                name=name,
                neighborhood_text=neighborhood_node.text(strip=True) if neighborhood_node else "",
                description_text=description_node.text(strip=True) if description_node else "",
            )
        )
    return entries


def scrape(
    *,
    fetch: Callable[[str], str] = fetch_url,
    llm: LLMClient,
    source_date: date | None = None,
) -> list[SeedRestaurant]:
    html = fetch(SOURCE_URL)
    entries = parse_entries(html)
    results: list[SeedRestaurant] = []
    for entry in entries:
        name_line = f"Name: {entry.name}"
        hood_line = f"Neighborhood: {entry.neighborhood_text}"
        source_text = f"{name_line}\n{hood_line}\n\n{entry.description_text}"
        seed = extract_fields(
            llm=llm,
            source_url=SOURCE_URL,
            source_text=source_text,
            publication=PUBLICATION,
            list_name=LIST_NAME,
            blurb=entry.description_text or None,
            source_date=source_date,
        )
        results.append(seed)
    return results

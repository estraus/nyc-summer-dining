from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from selectolax.parser import HTMLParser

from app.models import SeedRestaurant
from app.services.fields_extractor import extract_fields
from app.services.llm_client import LLMClient
from scrapers.common import fetch_url

SOURCE_URL = "https://ny.eater.com/maps/best-new-york-restaurants-38-essential"
PUBLICATION = "eater_nyc"
LIST_NAME = "38 Essential"


@dataclass(frozen=True)
class Entry:
    name: str
    address_text: str
    description_text: str


def parse_entries(html: str) -> list[Entry]:
    tree = HTMLParser(html)
    entries: list[Entry] = []
    for card in tree.css("section.c-mapstack__card"):
        name_node = card.css_first("h2")
        if name_node is None:
            continue
        name = name_node.text(strip=True)
        address_node = card.css_first("p.address")
        description_node = card.css_first("div.description")
        entries.append(
            Entry(
                name=name,
                address_text=address_node.text(strip=True) if address_node else "",
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
        source_text = (
            f"Name: {entry.name}\nAddress: {entry.address_text}\n\n{entry.description_text}"
        )
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

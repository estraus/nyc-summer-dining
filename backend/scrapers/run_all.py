#!/usr/bin/env python3
"""Run all scrapers and write JSON output to data/seed/."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from app.config import get_settings
from app.services.llm_client import AnthropicLLMClient
from scrapers import eater_essentials, infatuation_hit_list, nyt_100_best

# Usage: uv run python -m scrapers.run_all [--dry-run]

_REPO_ROOT = Path(__file__).resolve().parents[3]

_SCRAPERS = [
    eater_essentials,
    infatuation_hit_list,
    nyt_100_best,
]


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    settings = get_settings()
    llm = AnthropicLLMClient(
        api_key=settings.anthropic_api_key,
        default_model=settings.active_llm_model,
    )

    seed_dir = _REPO_ROOT / "data" / "seed"
    if not dry_run:
        seed_dir.mkdir(parents=True, exist_ok=True)

    today = date.today()
    total = 0
    written_paths: list[Path] = []

    for module in _SCRAPERS:
        publication: str = module.PUBLICATION
        print(f"Scraping {publication}...", end=" ", flush=True)
        try:
            restaurants = module.scrape(llm=llm, source_date=today)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {exc}")
            continue

        n = len(restaurants)
        print(f"done ({n} restaurants)")
        total += n

        if not dry_run:
            out_path = seed_dir / f"{publication}.json"
            payload = [r.model_dump(mode="json") for r in restaurants]
            out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
            written_paths.append(out_path)

    print(f"\nTotal: {total} restaurants")
    if written_paths:
        print("Files written:")
        for p in written_paths:
            print(f"  {p}")


if __name__ == "__main__":
    main()

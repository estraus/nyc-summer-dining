from app.services.llm_client import FakeLLMClient
from app.services.ranker import RankingRequest, parse_cards, rank_sync
from app.services.shortlist import ShortlistItem


def _items() -> list[ShortlistItem]:
    return [
        ShortlistItem(
            id="lilia-williamsburg",
            name="Lilia",
            neighborhood="Williamsburg",
            borough="Brooklyn",
            price_tier=3,
            booking_platform="resy",
            booking_url=None,
            resy_venue_id="345",
            description="Pasta temple.",
            cuisine_tags=["italian"],
            vibe_tags=["date-night"],
        ),
        ShortlistItem(
            id="nami-nori-west-village",
            name="Nami Nori",
            neighborhood="West Village",
            borough="Manhattan",
            price_tier=2,
            booking_platform="resy",
            booking_url=None,
            resy_venue_id="123",
            description="Handrolls.",
            cuisine_tags=["japanese"],
            vibe_tags=["casual", "counter-only"],
        ),
    ]


def test_parse_cards_extracts_in_order() -> None:
    text = (
        '<card id="nami-nori-west-village">Fast counter handrolls.</card>'
        '<card id="lilia-williamsburg">Date-night pasta.</card>'
    )
    cards = parse_cards(text)
    assert [c.id for c in cards] == ["nami-nori-west-village", "lilia-williamsburg"]
    assert cards[1].reason == "Date-night pasta."


def test_parse_cards_handles_whitespace() -> None:
    text = """
    <card id="a">
      reason a
    </card>
    <card id="b">reason b</card>
    """
    cards = parse_cards(text)
    assert [c.id for c in cards] == ["a", "b"]
    assert cards[0].reason == "reason a"


def test_parse_cards_ignores_unknown_tags() -> None:
    text = '<card id="a">x</card><foo>bar</foo><card id="b">y</card>'
    cards = parse_cards(text)
    assert [c.id for c in cards] == ["a", "b"]


def test_rank_sync_returns_ordered_cards() -> None:
    llm = FakeLLMClient(
        responses=[
            '<card id="nami-nori-west-village">Fast counter handrolls, matches casual vibe.</card>'
            '<card id="lilia-williamsburg">Pasta for a splurge.</card>'
        ]
    )
    req = RankingRequest(
        shortlist=_items(),
        cuisines=[],
        vibes=["casual"],
        preferences_text="cheap eats with a friend",
    )
    ranked = rank_sync(llm=llm, request=req, model="claude-haiku-4-5-20251001")
    assert [c.id for c in ranked] == ["nami-nori-west-village", "lilia-williamsburg"]
    # System prompt should mention the format.
    assert "<card" in llm.calls[0].system


def test_rank_sync_falls_back_when_llm_returns_garbage() -> None:
    llm = FakeLLMClient(responses=["nothing-useful"])
    req = RankingRequest(shortlist=_items())
    ranked = rank_sync(llm=llm, request=req, model="haiku")
    # Fallback: shortlist order (source_count desc, then name).
    assert [c.id for c in ranked] == ["lilia-williamsburg", "nami-nori-west-village"]
    assert all(c.reason == "" for c in ranked)

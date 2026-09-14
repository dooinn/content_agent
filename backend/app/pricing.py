"""Claude list prices in USD per million tokens.

Source: https://platform.claude.com/docs/en/about-claude/pricing (checked 2026-09-14). Magnific
bills credits and ElevenLabs bills characters against a plan, so those stay in their own units.
"""

from dataclasses import dataclass

WEB_SEARCH_USD = 10 / 1000


@dataclass(frozen=True)
class TokenPrices:
    input: float
    cache_write: float  # 5-minute cache writes
    cache_read: float
    output: float


CLAUDE: dict[str, TokenPrices] = {
    "claude-sonnet-5": TokenPrices(input=2.0, cache_write=2.5, cache_read=0.2, output=10.0),
    "claude-opus-5": TokenPrices(input=5.0, cache_write=6.25, cache_read=0.5, output=25.0),
}


def llm_cost(event: dict) -> float | None:
    """USD for one recorded Claude call, or None when the model has no price here."""
    prices = CLAUDE.get(event.get("model") or "")
    if prices is None:
        return None
    tokens = (
        event.get("input_tokens", 0) * prices.input
        + event.get("cache_write_tokens", 0) * prices.cache_write
        + event.get("cache_read_tokens", 0) * prices.cache_read
        + event.get("output_tokens", 0) * prices.output
    ) / 1_000_000
    return tokens + event.get("web_searches", 0) * WEB_SEARCH_USD

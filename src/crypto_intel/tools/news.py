"""News headlines tool. Mock body for now; Stage 5 swaps implementation."""

from __future__ import annotations

from langchain_core.tools import tool

_MAX_HEADLINES = 10


@tool
def fetch_news(cryptocurrency: str, limit: int = 5) -> str:
    """Fetch recent news headlines for a cryptocurrency symbol.

    Args:
        cryptocurrency: Asset symbol, e.g. BTC or ETH.
        limit: Maximum headlines to return (1–10).
    """
    symbol = cryptocurrency.strip().upper()
    if not symbol:
        raise ValueError("cryptocurrency must not be empty")

    capped_limit = max(1, min(limit, _MAX_HEADLINES))

    # Mock data — replace with real HTTP in Stage 5. Always include source_url.
    headlines = [
        (
            f"title={symbol} holds steady amid macro uncertainty; "
            f"summary=Trading range narrowed over the past week; "
            f"source_url=https://mock.news.example/{symbol.lower()}/steady; "
            f"source=mock_news"
        ),
        (
            f"title=Analysts debate {symbol} ETF flow impact; "
            f"summary=Spot demand mixed vs prior month; "
            f"source_url=https://mock.news.example/{symbol.lower()}/etf-flows; "
            f"source=mock_news"
        ),
        (
            f"title={symbol} network activity ticks higher; "
            f"summary=On-chain transfers up modestly; "
            f"source_url=https://mock.news.example/{symbol.lower()}/on-chain; "
            f"source=mock_news"
        ),
    ]

    selected = headlines[:capped_limit]
    return "\n".join(selected)

"""Market snapshot tool. Mock body for now; Stage 5 swaps implementation."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def get_market_snapshot(cryptocurrency: str) -> str:
    """Return a short market snapshot for a cryptocurrency symbol.

    Args:
        cryptocurrency: Asset symbol, e.g. BTC or ETH.
    """
    symbol = cryptocurrency.strip().upper()
    # Mock data — replace with real HTTP + Redis cache in Stage 5.
    return (
        f"symbol={symbol}; price_usd=65000; "
        f"change_24h_pct=1.2; source=mock_market"
    )

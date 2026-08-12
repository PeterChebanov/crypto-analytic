"""Shared helpers for collector tools."""

from __future__ import annotations

_COINGECKO_IDS: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "USDT": "tether",
}


def normalize_symbol(cryptocurrency: str) -> str:
    symbol = cryptocurrency.strip().upper()
    if not symbol:
        raise ValueError("cryptocurrency must not be empty")
    return symbol


def coingecko_id(symbol: str) -> str:
    """Map ticker to CoinGecko id; fall back to lowercased ticker."""
    return _COINGECKO_IDS.get(symbol.upper(), symbol.lower())

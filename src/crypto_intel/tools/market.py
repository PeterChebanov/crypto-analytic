"""Market snapshot tool. Mock or live CoinGecko + Redis cache."""

from __future__ import annotations

import json
import logging

import httpx
from langchain_core.tools import tool

from crypto_intel.logging_ext.context import get_session_logger
from crypto_intel.redis.client import get_redis
from crypto_intel.settings import get_settings
from crypto_intel.tools.symbols import coingecko_id, normalize_symbol

logger = logging.getLogger(__name__)

_COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"


def _mock_market_payload(symbol: str) -> str:
    return (
        f"symbol={symbol}; price_usd=65000; "
        f"change_24h_pct=1.2; source=mock_market"
    )


def _fetch_live_market_payload(symbol: str) -> str:
    coin_id = coingecko_id(symbol)
    cache_key = f"market:{symbol}"
    settings = get_settings()
    client = get_redis()

    cached = client.get(cache_key)
    if cached:
        return str(cached)

    response = httpx.get(
        _COINGECKO_PRICE_URL,
        params={
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        },
        timeout=15.0,
    )
    response.raise_for_status()
    payload = response.json()
    row = payload.get(coin_id)
    if not isinstance(row, dict):
        raise ValueError(f"No CoinGecko price data for {symbol} ({coin_id})")

    price = row.get("usd", "n/a")
    change = row.get("usd_24h_change", "n/a")
    if isinstance(change, float):
        change = round(change, 4)

    formatted = (
        f"symbol={symbol}; price_usd={price}; "
        f"change_24h_pct={change}; source=coingecko"
    )
    client.setex(cache_key, settings.market_cache_ttl_seconds, formatted)
    # Keep a debug blob separately (not returned to the model path).
    client.setex(
        f"{cache_key}:raw",
        settings.market_cache_ttl_seconds,
        json.dumps(row),
    )
    return formatted


@tool
def get_market_snapshot(cryptocurrency: str) -> str:
    """Return a short market snapshot for a cryptocurrency symbol.

    Args:
        cryptocurrency: Asset symbol, e.g. BTC or ETH.
    """
    symbol = normalize_symbol(cryptocurrency)
    session_logger = get_session_logger()
    if get_settings().use_mock_tools:
        payload = _mock_market_payload(symbol)
        if session_logger is not None:
            session_logger.log(
                kind="market",
                source="mock",
                request={"symbol": symbol},
                response={"payload": payload},
            )
        return payload
    try:
        payload = _fetch_live_market_payload(symbol)
        if session_logger is not None:
            session_logger.log(
                kind="market",
                source="coingecko",
                request={"symbol": symbol},
                response={"payload": payload},
            )
        return payload
    except Exception as exc:
        logger.exception("live market fetch failed for %s; falling back to mock", symbol)
        if session_logger is not None:
            session_logger.log(
                kind="market",
                source="coingecko",
                request={"symbol": symbol},
                error=str(exc),
            )
        return _mock_market_payload(symbol)

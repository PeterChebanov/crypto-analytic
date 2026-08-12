"""News headlines tool. Mock or live CryptoCompare headlines."""

from __future__ import annotations

import logging

import httpx
from langchain_core.tools import tool

from crypto_intel.logging_ext.context import get_session_logger
from crypto_intel.settings import get_settings
from crypto_intel.tools.symbols import normalize_symbol

logger = logging.getLogger(__name__)

_MAX_HEADLINES = 10
_CRYPTOCOMPARE_NEWS_URL = "https://min-api.cryptocompare.com/data/v2/news/"


def _mock_news_payload(symbol: str, limit: int) -> str:
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
    return "\n".join(headlines[:limit])


def _fetch_live_news_payload(symbol: str, limit: int) -> str:
    response = httpx.get(
        _CRYPTOCOMPARE_NEWS_URL,
        params={"lang": "EN", "categories": symbol},
        timeout=15.0,
    )
    response.raise_for_status()
    body = response.json()
    items = body.get("Data") or []
    lines: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        summary = str(item.get("body") or item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not title or not summary or not url:
            continue
        # Keep summaries short for prompt budgets.
        if len(summary) > 280:
            summary = summary[:277] + "..."
        lines.append(
            f"title={title}; summary={summary}; "
            f"source_url={url}; source=cryptocompare"
        )
        if len(lines) >= limit:
            break
    if not lines:
        raise ValueError(f"No news headlines returned for {symbol}")
    return "\n".join(lines)


@tool
def fetch_news(cryptocurrency: str, limit: int = 5) -> str:
    """Fetch recent news headlines for a cryptocurrency symbol.

    Args:
        cryptocurrency: Asset symbol, e.g. BTC or ETH.
        limit: Maximum headlines to return (1–10).
    """
    symbol = normalize_symbol(cryptocurrency)
    capped_limit = max(1, min(limit, _MAX_HEADLINES))
    session_logger = get_session_logger()

    if get_settings().use_mock_tools:
        payload = _mock_news_payload(symbol, capped_limit)
        if session_logger is not None:
            session_logger.log(
                kind="news",
                source="mock",
                request={"symbol": symbol, "limit": capped_limit},
                response={"lines": len(payload.splitlines())},
            )
        return payload
    try:
        payload = _fetch_live_news_payload(symbol, capped_limit)
        if session_logger is not None:
            session_logger.log(
                kind="news",
                source="cryptocompare",
                request={"symbol": symbol, "limit": capped_limit},
                response={"lines": len(payload.splitlines())},
            )
        return payload
    except Exception as exc:
        logger.exception("live news fetch failed for %s; falling back to mock", symbol)
        if session_logger is not None:
            session_logger.log(
                kind="news",
                source="cryptocompare",
                request={"symbol": symbol, "limit": capped_limit},
                error=str(exc),
            )
        return _mock_news_payload(symbol, capped_limit)

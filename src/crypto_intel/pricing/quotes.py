"""Multi-venue spot quotes + consensus thresholds."""

from __future__ import annotations

import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

import httpx

from crypto_intel.domain.models import (
    PriceConsensus,
    PriceDispersionLevel,
    PriceQuote,
)
from crypto_intel.logging_ext.session_log import SessionLogger
from crypto_intel.settings import get_settings
from crypto_intel.tools.symbols import normalize_symbol

# Locked product thresholds (basis points of mid).
PRICE_WARN_PCT = 0.25
PRICE_HARD_PCT = 1.0

_BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"
_KRAKEN_URL = "https://api.kraken.com/0/public/Ticker"
_COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

_BINANCE_SYMBOLS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "DOGE": "DOGEUSDT",
    "AVAX": "AVAXUSDT",
    "DOT": "DOTUSDT",
    "LINK": "LINKUSDT",
    "USDT": "USDTUSD",
}

_KRAKEN_PAIRS = {
    "BTC": "XBTUSD",
    "ETH": "ETHUSD",
    "SOL": "SOLUSD",
    "XRP": "XRPUSD",
    "ADA": "ADAUSD",
    "DOGE": "DOGEUSD",
    "DOT": "DOTUSD",
    "LINK": "LINKUSD",
    "USDT": "USDTZUSD",
}

_COINGECKO_IDS = {
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


def _mock_quotes(symbol: str) -> list[PriceQuote]:
    base = 3200.0 if symbol == "ETH" else 65000.0
    return [
        PriceQuote(source="binance", symbol=symbol, price_usd=base, raw={"mock": True}),
        PriceQuote(
            source="kraken",
            symbol=symbol,
            price_usd=base * 1.0005,
            raw={"mock": True},
        ),
        PriceQuote(
            source="coingecko",
            symbol=symbol,
            price_usd=base * 0.9998,
            raw={"mock": True},
        ),
    ]


def _fetch_binance(symbol: str) -> PriceQuote:
    pair = _BINANCE_SYMBOLS.get(symbol, f"{symbol}USDT")
    url = _BINANCE_URL
    params = {"symbol": pair}
    try:
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        price = float(data["price"])
        return PriceQuote(
            source="binance",
            symbol=symbol,
            price_usd=price,
            raw={"pair": pair, "data": data},
        )
    except Exception as exc:
        return PriceQuote(
            source="binance",
            symbol=symbol,
            price_usd=0.0,
            ok=False,
            error=str(exc),
            raw={"pair": pair},
        )


def _fetch_kraken(symbol: str) -> PriceQuote:
    pair = _KRAKEN_PAIRS.get(symbol, f"{symbol}USD")
    try:
        response = httpx.get(_KRAKEN_URL, params={"pair": pair}, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise ValueError(str(data["error"]))
        result = data.get("result") or {}
        if not result:
            raise ValueError("empty Kraken result")
        first = next(iter(result.values()))
        # "c" = last trade closed [price, lot volume]
        price = float(first["c"][0])
        return PriceQuote(
            source="kraken",
            symbol=symbol,
            price_usd=price,
            raw={"pair": pair, "data": first},
        )
    except Exception as exc:
        return PriceQuote(
            source="kraken",
            symbol=symbol,
            price_usd=0.0,
            ok=False,
            error=str(exc),
            raw={"pair": pair},
        )


def _fetch_coingecko(symbol: str) -> PriceQuote:
    coin_id = _COINGECKO_IDS.get(symbol, symbol.lower())
    try:
        response = httpx.get(
            _COINGECKO_URL,
            params={"ids": coin_id, "vs_currencies": "usd"},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        price = float(data[coin_id]["usd"])
        return PriceQuote(
            source="coingecko",
            symbol=symbol,
            price_usd=price,
            raw={"id": coin_id, "data": data},
        )
    except Exception as exc:
        return PriceQuote(
            source="coingecko",
            symbol=symbol,
            price_usd=0.0,
            ok=False,
            error=str(exc),
            raw={"id": coin_id},
        )


_FETCHERS: tuple[Callable[[str], PriceQuote], ...] = (
    _fetch_binance,
    _fetch_kraken,
    _fetch_coingecko,
)


def collect_spot_quotes(
    cryptocurrency: str,
    *,
    session_logger: SessionLogger | None = None,
) -> list[PriceQuote]:
    symbol = normalize_symbol(cryptocurrency)
    if get_settings().use_mock_tools:
        quotes = _mock_quotes(symbol)
        if session_logger is not None:
            for quote in quotes:
                session_logger.log(
                    kind="price_quote",
                    source=quote.source,
                    request={"symbol": symbol, "mock": True},
                    response={"price_usd": quote.price_usd},
                )
        return quotes

    quotes: list[PriceQuote] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fetcher, symbol): fetcher for fetcher in _FETCHERS}
        for future in as_completed(futures):
            quote = future.result()
            quotes.append(quote)
            if session_logger is not None:
                session_logger.log(
                    kind="price_quote",
                    source=quote.source,
                    request={"symbol": symbol},
                    response={"price_usd": quote.price_usd, "ok": quote.ok},
                    error=quote.error,
                )
    return sorted(quotes, key=lambda q: q.source)


def build_price_consensus(quotes: list[PriceQuote]) -> PriceConsensus:
    ok_quotes = [q for q in quotes if q.ok and q.price_usd > 0]
    ok_count = len(ok_quotes)
    if ok_count == 0:
        return PriceConsensus(
            quotes=quotes,
            ok_count=0,
            reference_price_usd=None,
            dispersion_pct=None,
            level=PriceDispersionLevel.HARD,
            message="No working price sources (0/3).",
        )

    prices = [q.price_usd for q in ok_quotes]
    reference = float(statistics.median(prices))
    dispersion = None
    if ok_count >= 2:
        dispersion = (max(prices) - min(prices)) / reference * 100.0

    if ok_count == 1:
        return PriceConsensus(
            quotes=quotes,
            ok_count=1,
            reference_price_usd=reference,
            dispersion_pct=None,
            level=PriceDispersionLevel.HARD,
            message="Only 1/3 price sources succeeded — hard warning; confirm to continue.",
        )

    if dispersion is None:
        raise RuntimeError("dispersion requires at least two working quotes")

    if dispersion > PRICE_HARD_PCT:
        level = PriceDispersionLevel.HARD
        message = (
            f"Price dispersion {dispersion:.3f}% exceeds hard limit "
            f"{PRICE_HARD_PCT}% — quotes invalid for forecast."
        )
    elif dispersion > PRICE_WARN_PCT:
        level = PriceDispersionLevel.WARN
        message = (
            f"Price dispersion {dispersion:.3f}% is above warn "
            f"{PRICE_WARN_PCT}% (still ≤ {PRICE_HARD_PCT}%)."
        )
    else:
        level = PriceDispersionLevel.OK
        message = f"Price dispersion {dispersion:.3f}% within normal band."

    return PriceConsensus(
        quotes=quotes,
        ok_count=ok_count,
        reference_price_usd=reference,
        dispersion_pct=dispersion,
        level=level,
        message=message,
    )

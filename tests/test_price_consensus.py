"""Tests for multi-source price consensus thresholds."""

from __future__ import annotations

from crypto_intel.domain.models import PriceDispersionLevel, PriceQuote
from crypto_intel.forecast.gate import ForecastPriceGate, decide_forecast_price_gate
from crypto_intel.pricing.quotes import (
    PRICE_HARD_PCT,
    PRICE_WARN_PCT,
    build_price_consensus,
)


def _q(source: str, price: float, *, ok: bool = True) -> PriceQuote:
    return PriceQuote(
        source=source,
        symbol="ETH",
        price_usd=price,
        ok=ok,
        error=None if ok else "down",
    )


def test_dispersion_within_ok_band() -> None:
    mid = 100.0
    # 0.2% span
    quotes = [_q("binance", mid), _q("kraken", mid * 1.001), _q("coingecko", mid * 0.999)]
    consensus = build_price_consensus(quotes)
    assert consensus.ok_count == 3
    assert consensus.level == PriceDispersionLevel.OK
    assert consensus.dispersion_pct is not None
    assert consensus.dispersion_pct <= PRICE_WARN_PCT


def test_dispersion_warn_band() -> None:
    mid = 100.0
    quotes = [_q("binance", mid), _q("kraken", mid * 1.004), _q("coingecko", mid * 0.996)]
    consensus = build_price_consensus(quotes)
    assert consensus.level == PriceDispersionLevel.WARN
    assert consensus.dispersion_pct is not None
    assert PRICE_WARN_PCT < consensus.dispersion_pct <= PRICE_HARD_PCT
    assert decide_forecast_price_gate(consensus, accept_degraded_price=False) == (
        ForecastPriceGate.PROCEED
    )


def test_dispersion_hard_band_skips_forecast() -> None:
    mid = 100.0
    quotes = [_q("binance", mid), _q("kraken", mid * 1.02), _q("coingecko", mid)]
    consensus = build_price_consensus(quotes)
    assert consensus.level == PriceDispersionLevel.HARD
    assert consensus.dispersion_pct is not None
    assert consensus.dispersion_pct > PRICE_HARD_PCT
    assert decide_forecast_price_gate(consensus, accept_degraded_price=False) == (
        ForecastPriceGate.SKIP
    )


def test_single_source_awaits_confirmation() -> None:
    quotes = [
        _q("binance", 3200.0),
        _q("kraken", 0.0, ok=False),
        _q("coingecko", 0.0, ok=False),
    ]
    consensus = build_price_consensus(quotes)
    assert consensus.ok_count == 1
    assert consensus.level == PriceDispersionLevel.HARD
    assert decide_forecast_price_gate(consensus, accept_degraded_price=False) == (
        ForecastPriceGate.AWAIT_CONFIRMATION
    )
    assert decide_forecast_price_gate(consensus, accept_degraded_price=True) == (
        ForecastPriceGate.PROCEED
    )


def test_zero_sources_skips() -> None:
    quotes = [
        _q("binance", 0.0, ok=False),
        _q("kraken", 0.0, ok=False),
        _q("coingecko", 0.0, ok=False),
    ]
    consensus = build_price_consensus(quotes)
    assert consensus.ok_count == 0
    assert decide_forecast_price_gate(consensus, accept_degraded_price=True) == (
        ForecastPriceGate.SKIP
    )

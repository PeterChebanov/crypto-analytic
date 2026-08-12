"""Forecast price gate: when to proceed, pause for confirm, or skip."""

from __future__ import annotations

from enum import StrEnum

from crypto_intel.domain.models import PriceConsensus, PriceDispersionLevel


class ForecastPriceGate(StrEnum):
    PROCEED = "proceed"
    AWAIT_CONFIRMATION = "await_confirmation"
    SKIP = "skip"


def decide_forecast_price_gate(
    consensus: PriceConsensus,
    *,
    accept_degraded_price: bool,
) -> ForecastPriceGate:
    """Apply locked product thresholds to multi-source quotes.

    - 0/3 OK → skip forecast
    - 1/3 OK → await UI confirmation unless accept_degraded_price
    - dispersion > 1% → skip (hard invalid)
    - dispersion 0.25–1% or ≤0.25% with ≥2 sources → proceed (warn is UI-only)
    """
    if consensus.ok_count <= 0:
        return ForecastPriceGate.SKIP
    if consensus.ok_count == 1:
        if accept_degraded_price:
            return ForecastPriceGate.PROCEED
        return ForecastPriceGate.AWAIT_CONFIRMATION
    if consensus.level == PriceDispersionLevel.HARD:
        return ForecastPriceGate.SKIP
    return ForecastPriceGate.PROCEED

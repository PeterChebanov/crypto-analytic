"""Rule-based setup_score (confluence), not ML probability."""

from __future__ import annotations

from crypto_intel.pricing.derivatives import DerivativesSnapshot
from crypto_intel.pricing.history import PriceSeriesStats

MIN_REWARD_RISK = 3.0
PREFERRED_REWARD_RISK = 5.0
# Risk distance must be at least this fraction of period high-low (anti-scalp).
MIN_RISK_FRAC_OF_CHART_RANGE = 0.10
PRICE_DECIMALS = 4


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def round_price(value: float, decimals: int = PRICE_DECIMALS) -> float:
    return round(value, decimals)


def chart_range(period_high: float, period_low: float) -> float | None:
    span = period_high - period_low
    if span <= 0:
        return None
    return span


def risk_distance(*, entry: float, stop: float) -> float | None:
    risk = entry - stop
    if risk <= 0:
        return None
    return risk


def reward_distance(*, entry: float, take_profit: float) -> float | None:
    reward = take_profit - entry
    if reward <= 0:
        return None
    return reward


def risk_pct(*, entry: float, stop: float) -> float | None:
    risk = risk_distance(entry=entry, stop=stop)
    if risk is None or entry <= 0:
        return None
    return risk / entry


def reward_pct(*, entry: float, take_profit: float) -> float | None:
    reward = reward_distance(entry=entry, take_profit=take_profit)
    if reward is None or entry <= 0:
        return None
    return reward / entry


def chart_range_pct(*, entry: float, period_high: float, period_low: float) -> float | None:
    span = chart_range(period_high, period_low)
    if span is None or entry <= 0:
        return None
    return span / entry


def meets_chart_scale(
    *,
    entry: float,
    stop: float,
    period_high: float,
    period_low: float,
    min_frac: float = MIN_RISK_FRAC_OF_CHART_RANGE,
) -> bool:
    """True when stop distance is visible on the analysis chart (not scalp noise)."""
    risk = risk_distance(entry=entry, stop=stop)
    span = chart_range(period_high, period_low)
    if risk is None or span is None:
        return False
    return risk >= min_frac * span


def compute_setup_score(
    *,
    stats: PriceSeriesStats,
    derivatives: DerivativesSnapshot,
    reward_risk: float | None,
    structure_ok: bool,
) -> float:
    """Weighted confluence in [0, 1].

    Weights: structure 0.35, volume 0.30, R:R quality 0.20, derivatives 0.15.
    Missing derivatives redistribute their weight to structure+volume.
    """
    structure = 0.85 if structure_ok else 0.25
    if stats.support < stats.resistance and stats.atr > 0:
        structure = clamp01(structure + 0.1)

    volume = 0.75 if stats.volume_confirm else 0.35
    volume = clamp01(volume + 0.1 * min(stats.volume_last_vs_avg, 2.0) / 2.0)

    if reward_risk is None or reward_risk < MIN_REWARD_RISK:
        rr = 0.15
    else:
        # 3.0 → ~0.7, 6.0 → ~1.0
        rr = clamp01(0.4 + (reward_risk - MIN_REWARD_RISK) / 6.0)

    if derivatives.available:
        deriv = 0.7
        if derivatives.funding_crowded:
            deriv -= 0.35
        if derivatives.oi_change_pct is not None:
            # Mild OI build with price up is ok; huge OI + crowded funding hurts.
            if abs(derivatives.oi_change_pct) > 20 and derivatives.funding_crowded:
                deriv -= 0.2
            elif 0 < derivatives.oi_change_pct < 15:
                deriv += 0.1
        deriv = clamp01(deriv)
        score = 0.35 * structure + 0.30 * volume + 0.20 * rr + 0.15 * deriv
    else:
        score = (0.35 + 0.075) * structure + (0.30 + 0.075) * volume + 0.20 * rr

    return round(clamp01(score), 3)


def reward_risk_ratio(
    *,
    entry: float,
    stop: float,
    take_profit: float,
) -> float | None:
    risk = risk_distance(entry=entry, stop=stop)
    reward = reward_distance(entry=entry, take_profit=take_profit)
    if risk is None or reward is None:
        return None
    return reward / risk


def meets_min_reward_risk(ratio: float | None) -> bool:
    return ratio is not None and ratio >= MIN_REWARD_RISK


def estimate_playout(
    *,
    entry: float,
    take_profit: float,
    atr: float,
    candle_interval: str,
    lookback_days: int,
) -> str:
    """Estimate how long the TP move may take; lookback is chart window, not hold time."""
    move = abs(take_profit - entry)
    if atr <= 0 or move <= 0:
        return (
            f"unknown; analysis lookback={lookback_days}d is chart window, not hold time"
        )
    bars = move / atr
    if candle_interval.endswith("h") and candle_interval[:-1].isdigit():
        hours_per_bar = int(candle_interval[:-1])
    elif candle_interval.endswith("d") and candle_interval[:-1].isdigit():
        hours_per_bar = 24 * int(candle_interval[:-1])
    else:
        hours_per_bar = 1
    hours = bars * hours_per_bar
    if hours < 12:
        bucket = "intraday"
        detail = f"~{max(hours, 1):.0f}h"
    elif hours < 24 * 5:
        bucket = "several_days"
        detail = f"~{hours / 24:.1f}d"
    else:
        bucket = "multi_week"
        detail = f"~{hours / 24:.0f}d"
    return (
        f"{bucket} ({detail} on {candle_interval} scale); "
        f"analysis lookback={lookback_days}d is chart window, not hold time"
    )

"""Rule-based forecast horizons + R:R gate (no LLM)."""

from __future__ import annotations

from dataclasses import replace

from crypto_intel.domain.models import DecisionCard, HorizonForecast, Stance
from crypto_intel.forecast.engine import (
    build_rule_horizons,
    build_trade_card,
    enforce_reward_risk_gate,
)
from crypto_intel.forecast.scoring import (
    MIN_REWARD_RISK,
    compute_setup_score,
    meets_min_reward_risk,
    reward_risk_ratio,
)
from crypto_intel.pricing.derivatives import DerivativesSnapshot
from crypto_intel.pricing.history import (
    Candle,
    PriceSeriesStats,
    build_stats_from_candles,
)


def _deriv(
    *,
    available: bool = True,
    funding_crowded: bool = False,
    note: str = "neutral",
    oi_change_pct: float | None = 5.0,
) -> DerivativesSnapshot:
    return DerivativesSnapshot(
        symbol="ETH",
        period="7d",
        available=available,
        funding_current=0.0001,
        funding_avg=0.0001,
        funding_crowded=funding_crowded,
        oi_start=1e6,
        oi_end=1.05e6,
        oi_change_pct=oi_change_pct,
        note=note,
    )

def _stats_wide_range() -> PriceSeriesStats:
    """Wide S/R so R:R can clear 1:3 and chart-scale gate."""
    return PriceSeriesStats(
        symbol="ETH",
        period="7d",
        days=7,
        candle_interval="1h",
        atr_period=14,
        start_price=3000.0,
        end_price=3010.0,
        low=2900.0,
        high=3400.0,
        change_pct=0.67,
        points=168,
        atr=100.0,
        support=3000.0,
        resistance=3300.0,
        volume_total=100000.0,
        volume_avg=1000.0,
        volume_last_vs_avg=1.1,
        volume_at_support_ratio=1.2,
        volume_at_resistance_ratio=0.9,
        volume_confirm=True,
    )


def _stats_tight_range() -> PriceSeriesStats:
    """Tight S/R — R:R fails 1:3."""
    return PriceSeriesStats(
        symbol="ETH",
        period="7d",
        days=7,
        candle_interval="1h",
        atr_period=14,
        start_price=3000.0,
        end_price=3010.0,
        low=2990.0,
        high=3060.0,
        change_pct=0.67,
        points=168,
        atr=15.0,
        support=3000.0,
        resistance=3045.0,
        volume_total=100000.0,
        volume_avg=1000.0,
        volume_last_vs_avg=1.0,
        volume_at_support_ratio=1.0,
        volume_at_resistance_ratio=1.0,
        volume_confirm=True,
    )


def _card(stance: Stance = Stance.ACCUMULATE) -> DecisionCard:
    return DecisionCard(
        stance=stance,
        confidence=0.6,
        rationale="test",
        invalidation=["x"],
    )


def test_reward_risk_helpers() -> None:
    assert reward_risk_ratio(entry=100, stop=90, take_profit=130) == 3.0
    assert meets_min_reward_risk(3.0)
    assert not meets_min_reward_risk(2.9)
    assert MIN_REWARD_RISK == 3.0


def test_enter_allowed_when_reward_risk_ge_three() -> None:
    horizons, score, *_rest = build_rule_horizons(
        in_position=False,
        period="14d",
        stats=_stats_wide_range(),
        reference=3010.0,
        derivatives=_deriv(),
        decision=_card(Stance.ACCUMULATE),
    )
    assert len(horizons) == 1
    assert horizons[0].horizon == "14d"
    assert horizons[0].action == "enter"
    assert horizons[0].entry_price is not None
    assert horizons[0].reward_risk is not None
    assert horizons[0].reward_risk >= MIN_REWARD_RISK
    assert 0.0 <= score <= 1.0


def test_enter_blocked_when_decision_card_is_avoid() -> None:
    decision = _card(Stance.AVOID)
    horizons, _score, entry, stop, tp, rr, structure_ok, tp_source, scale_ok = (
        build_rule_horizons(
            in_position=False,
            period="7d",
            stats=_stats_wide_range(),
            reference=3010.0,
            derivatives=_deriv(),
            decision=decision,
        )
    )
    assert horizons[0].action == "wait"
    assert horizons[0].entry_price is None
    trade = build_trade_card(
        horizons=horizons,
        stats=_stats_wide_range(),
        entry=entry,
        stop=stop,
        take_profit=tp,
        rr=rr,
        structure_ok=structure_ok,
        scale_ok=scale_ok,
        decision=decision,
        in_position=False,
        take_profit_source=tp_source,
    )
    assert trade.enter is False
    assert trade.blocked_by_decision is True
    assert "blocks new risk" in trade.why_enter_or_skip
    assert trade.take_profit_source == tp_source
    assert trade.estimated_playout is not None
    assert "lookback" in trade.estimated_playout


def test_enter_blocked_when_decision_card_is_hold() -> None:
    """Hold = no new risk; TA alone is not enough to enter."""
    decision = _card(Stance.HOLD)
    horizons, _score, entry, stop, tp, rr, structure_ok, tp_source, scale_ok = (
        build_rule_horizons(
            in_position=False,
            period="7d",
            stats=_stats_wide_range(),
            reference=3010.0,
            derivatives=_deriv(),
            decision=decision,
        )
    )
    assert horizons[0].action == "wait"
    trade = build_trade_card(
        horizons=horizons,
        stats=_stats_wide_range(),
        entry=entry,
        stop=stop,
        take_profit=tp,
        rr=rr,
        structure_ok=structure_ok,
        scale_ok=scale_ok,
        decision=decision,
        in_position=False,
        take_profit_source=tp_source,
    )
    assert trade.enter is False
    assert trade.blocked_by_decision is True


def test_take_profit_source_period_high_when_swing_rr_too_low() -> None:
    """Tight swing band → TP falls back to period_high and is labeled."""
    horizons, _score, entry, stop, tp, rr, structure_ok, tp_source, scale_ok = (
        build_rule_horizons(
            in_position=False,
            period="7d",
            stats=_stats_tight_range(),
            reference=3010.0,
            derivatives=_deriv(),
            decision=_card(Stance.ACCUMULATE),
        )
    )
    assert tp_source in {"swing_resistance", "period_high"}
    if tp_source == "period_high":
        assert tp == round(_stats_tight_range().high, 4)
    trade = build_trade_card(
        horizons=horizons,
        stats=_stats_tight_range(),
        entry=entry,
        stop=stop,
        take_profit=tp,
        rr=rr,
        structure_ok=structure_ok,
        scale_ok=scale_ok,
        decision=_card(Stance.ACCUMULATE),
        in_position=False,
        take_profit_source=tp_source,
    )
    assert trade.take_profit_source == tp_source
    if tp_source == "period_high":
        assert "period_high" in (trade.exit_rationale or "")


def test_chart_scale_blocks_micro_stop_vs_period_range() -> None:
    """USDT-like flat window: formal R:R can pass, chart-scale must fail."""
    from crypto_intel.forecast.scoring import meets_chart_scale, reward_risk_ratio

    stats = PriceSeriesStats(
        symbol="USDT",
        period="7d",
        days=7,
        candle_interval="1h",
        atr_period=14,
        start_price=0.9990,
        end_price=0.9991,
        low=0.9982,
        high=0.9997,
        change_pct=0.01,
        points=168,
        atr=0.00009,
        support=0.9990,
        resistance=0.9991,
        volume_total=1.0,
        volume_avg=1.0,
        volume_last_vs_avg=0.0,
        volume_at_support_ratio=1.0,
        volume_at_resistance_ratio=1.0,
        volume_confirm=False,
    )
    horizons, _score, entry, stop, tp, rr, structure_ok, tp_source, scale_ok = (
        build_rule_horizons(
            in_position=False,
            period="7d",
            stats=stats,
            reference=0.99909,
            derivatives=_deriv(available=False, note="n/a"),
            decision=_card(Stance.ACCUMULATE),
        )
    )
    assert scale_ok is False
    assert horizons[0].action == "wait"
    trade = build_trade_card(
        horizons=horizons,
        stats=stats,
        entry=entry,
        stop=stop,
        take_profit=tp,
        rr=rr,
        structure_ok=structure_ok,
        scale_ok=scale_ok,
        decision=_card(Stance.ACCUMULATE),
        in_position=False,
        take_profit_source=tp_source,
    )
    assert trade.enter is False
    assert trade.blocked_by_scale is True
    assert trade.scale_ok is False
    # Audit: displayed levels reproduce R:R
    if trade.reward_risk is not None:
        recomputed = reward_risk_ratio(
            entry=entry,
            stop=stop,
            take_profit=tp,
        )
        assert recomputed is not None
        assert abs(recomputed - trade.reward_risk) < 0.002
    assert not meets_chart_scale(
        entry=entry,
        stop=stop,
        period_high=stats.high,
        period_low=stats.low,
    )


def test_enter_blocked_when_reward_risk_below_three() -> None:
    horizons, _score, *_rest = build_rule_horizons(
        in_position=False,
        period="7d",
        stats=_stats_tight_range(),
        reference=3010.0,
        derivatives=_deriv(),
        decision=_card(Stance.ACCUMULATE),
    )
    assert horizons[0].action == "wait"
    assert horizons[0].entry_price is None
    assert horizons[0].reward_risk is None or horizons[0].reward_risk < MIN_REWARD_RISK


def test_post_llm_gate_strips_illegal_enter() -> None:
    illegal = HorizonForecast(
        horizon="7d",
        action="enter",
        risk_score=0.4,
        entry_price=100.0,
        stop_price=95.0,
        take_profit_price=110.0,  # R:R = 2
        reward_risk=2.0,
        setup_score=0.5,
        rationale="bad",
    )
    fixed = enforce_reward_risk_gate([illegal])
    assert fixed[0].action == "wait"
    assert fixed[0].entry_price is None


def test_in_position_three_horizons_exit_on_dump() -> None:
    stats = replace(_stats_wide_range(), change_pct=-6.0)
    horizons, *_rest = build_rule_horizons(
        in_position=True,
        period="7d",
        stats=stats,
        reference=3010.0,
        derivatives=_deriv(),
        decision=_card(Stance.HOLD),
    )
    assert [h.horizon for h in horizons] == ["today", "7d", "30d"]
    assert horizons[0].action == "exit"


def test_setup_score_bounds() -> None:
    score = compute_setup_score(
        stats=_stats_wide_range(),
        derivatives=_deriv(),
        reward_risk=3.5,
        structure_ok=True,
    )
    assert 0.0 <= score <= 1.0
    unavailable = compute_setup_score(
        stats=_stats_wide_range(),
        derivatives=_deriv(available=False, note="unavailable"),
        reward_risk=None,
        structure_ok=False,
    )
    assert 0.0 <= unavailable <= 1.0


def test_forecast_sources_include_urls() -> None:
    from crypto_intel.forecast.engine import build_forecast_sources

    sources = build_forecast_sources(
        cryptocurrency="ETH",
        period="7d",
        derivatives=_deriv(),
    )
    assert sources
    assert all(s.url.startswith("http") for s in sources)
    assert any(s.kind == "price_spot" for s in sources)
    assert any(s.kind == "news" for s in sources)


def test_build_stats_from_candles_has_volume_and_atr() -> None:
    candles = [
        Candle(open=100, high=102, low=99, close=101, volume=10),
        Candle(open=101, high=103, low=100, close=102, volume=12),
        Candle(open=102, high=104, low=101, close=103, volume=11),
        Candle(open=103, high=105, low=102, close=104, volume=20),
        Candle(open=104, high=106, low=103, close=105, volume=15),
        Candle(open=105, high=107, low=104, close=106, volume=14),
        Candle(open=106, high=108, low=100, close=101, volume=30),
        Candle(open=101, high=110, low=100, close=109, volume=25),
        Candle(open=109, high=112, low=108, close=111, volume=18),
        Candle(open=111, high=113, low=110, close=112, volume=16),
        Candle(open=112, high=114, low=111, close=113, volume=17),
        Candle(open=113, high=115, low=112, close=114, volume=19),
        Candle(open=114, high=116, low=113, close=115, volume=21),
        Candle(open=115, high=117, low=114, close=116, volume=22),
        Candle(open=116, high=118, low=115, close=117, volume=23),
        Candle(open=117, high=119, low=116, close=118, volume=24),
    ]
    stats = build_stats_from_candles(
        symbol="ETH",
        period="7d",
        days=7,
        candles=candles,
    )
    assert stats.atr > 0
    assert stats.support < stats.resistance
    assert stats.volume_total > 0
    assert stats.candle_interval == "1h"
    assert stats.atr_period == 14

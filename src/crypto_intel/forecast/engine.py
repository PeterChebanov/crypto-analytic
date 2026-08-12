"""Experimental forecast layer (rules + structured LLM formatting)."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from crypto_intel.domain.language import language_instruction
from crypto_intel.domain.models import (
    AnalysisDraft,
    DecisionCard,
    ForecastBundle,
    ForecastDecisionRef,
    ForecastRiskBlock,
    ForecastSource,
    ForecastTaContract,
    ForecastTendency,
    ForecastTrade,
    HorizonForecast,
    PriceConsensus,
    PriceDispersionLevel,
    Stance,
)
from crypto_intel.forecast.coherence import (
    decision_allows_add_on,
    decision_allows_new_entry,
)
from crypto_intel.forecast.scoring import (
    MIN_REWARD_RISK,
    MIN_RISK_FRAC_OF_CHART_RANGE,
    PREFERRED_REWARD_RISK,
    chart_range_pct,
    compute_setup_score,
    estimate_playout,
    meets_chart_scale,
    meets_min_reward_risk,
    reward_pct,
    reward_risk_ratio,
    risk_pct,
    round_price,
)
from crypto_intel.llm.client import build_xai_chat_model
from crypto_intel.logging_ext.session_log import SessionLogger
from crypto_intel.pricing.derivatives import DerivativesSnapshot
from crypto_intel.pricing.history import (
    ATR_STOP_MULT,
    SR_METHOD,
    PriceSeriesStats,
    binance_spot_pair,
)
from crypto_intel.tools.symbols import coingecko_id, normalize_symbol


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _long_setup_levels(
    *,
    reference: float,
    stats: PriceSeriesStats,
) -> tuple[float, float, float, bool, str, float | None, bool]:
    """Build long entry/stop/tp from swing S/R + ATR.

    Levels are rounded before R:R and chart-scale checks so JSON audit matches.
    Returns entry, stop, tp, structure_ok, tp_source, rr, scale_ok.
    """
    support = stats.support
    resistance = stats.resistance
    atr = stats.atr
    mid = (support + resistance) / 2.0
    entry = reference if reference <= mid else min(reference, support + atr * 0.25)
    if entry < support:
        entry = support
    stop = support - atr * ATR_STOP_MULT
    if stop >= entry:
        stop = entry - max(atr * ATR_STOP_MULT, entry * 0.005)
    take_profit = resistance
    tp_source = "swing_resistance"
    entry_r = round_price(entry)
    stop_r = round_price(stop)
    tp_r = round_price(take_profit)
    rr = reward_risk_ratio(entry=entry_r, stop=stop_r, take_profit=tp_r)
    if not meets_min_reward_risk(rr) and stats.high > resistance:
        take_profit = stats.high
        tp_source = "period_high"
        tp_r = round_price(take_profit)
        rr = reward_risk_ratio(entry=entry_r, stop=stop_r, take_profit=tp_r)
    near_support = abs(reference - support) / reference <= 0.03 if reference else False
    structure_ok = near_support or reference <= mid
    scale_ok = meets_chart_scale(
        entry=entry_r,
        stop=stop_r,
        period_high=stats.high,
        period_low=stats.low,
    )
    return entry_r, stop_r, tp_r, structure_ok, tp_source, rr, scale_ok


def build_ta_contract(stats: PriceSeriesStats) -> ForecastTaContract:
    return ForecastTaContract(
        candle_interval=stats.candle_interval,
        lookback_days=stats.days,
        atr_period=stats.atr_period,
        atr_note=(
            f"ATR({stats.atr_period}) on {stats.candle_interval} candles — "
            "not daily ATR."
        ),
        sr_method=SR_METHOD,
        sr_note=(
            "support/resistance are nearest swing pivots on the candle interval, "
            "not the period high/low. Use period_high/period_low for the full window."
        ),
        period_high=round_price(stats.high),
        period_low=round_price(stats.low),
        swing_support=round_price(stats.support),
        swing_resistance=round_price(stats.resistance),
        min_risk_frac_of_chart_range=MIN_RISK_FRAC_OF_CHART_RANGE,
    )


def _volume_note(stats: PriceSeriesStats) -> str:
    return (
        f"vol_last/avg={stats.volume_last_vs_avg:.2f}; "
        f"vol@support={stats.volume_at_support_ratio:.2f}; "
        f"confirm={stats.volume_confirm}"
    )


def _tendency_direction(change_pct: float) -> str:
    if change_pct >= 2.0:
        return "up"
    if change_pct <= -2.0:
        return "down"
    return "range"


def build_forecast_sources(
    *,
    cryptocurrency: str,
    period: str,
    derivatives: DerivativesSnapshot,
) -> list[ForecastSource]:
    symbol = normalize_symbol(cryptocurrency)
    pair = binance_spot_pair(symbol)
    coin_id = coingecko_id(symbol)
    sources = [
        ForecastSource(
            kind="price_spot",
            detail=(
                f"Median spot across Binance/Kraken/CoinGecko for {symbol} "
                f"(pair {pair})."
            ),
            url=f"https://www.binance.com/en/trade/{symbol}_USDT",
        ),
        ForecastSource(
            kind="price_history",
            detail=(
                f"Binance OHLCV lookback {period}: swing S/R, ATR, volume confirm."
            ),
            url="https://api.binance.com/api/v3/klines",
        ),
        ForecastSource(
            kind="price_spot_coingecko",
            detail=f"CoinGecko spot reference page for {coin_id}.",
            url=f"https://www.coingecko.com/en/coins/{coin_id}",
        ),
        ForecastSource(
            kind="news",
            detail="CryptoCompare headlines feeding the analytics brief.",
            url="https://www.cryptocompare.com/news/",
        ),
    ]
    if derivatives.available:
        sources.append(
            ForecastSource(
                kind="derivatives",
                detail=f"Binance futures funding + OI Δ ({derivatives.note}).",
                url=f"https://www.binance.com/en/futures/{pair}",
            )
        )
    else:
        sources.append(
            ForecastSource(
                kind="derivatives",
                detail=f"Derivatives unavailable ({derivatives.note}).",
                url="https://www.binance.com/en/futures/home",
            )
        )
    return sources


def build_tendency(stats: PriceSeriesStats) -> ForecastTendency:
    direction = _tendency_direction(stats.change_pct)
    return ForecastTendency(
        direction=direction,
        from_price=round(stats.start_price, 4),
        to_price=round(stats.end_price, 4),
        change_pct=round(stats.change_pct, 3),
        price_basis="first_close_to_last_close",
        one_liner=(
            f"Over {stats.period} closes moved {stats.change_pct:.2f}% "
            f"from {stats.start_price:.4f} to {stats.end_price:.4f} "
            f"({direction}); swing S/R {stats.support:.4f}/{stats.resistance:.4f}; "
            f"period H/L {stats.high:.4f}/{stats.low:.4f} "
            f"on {stats.candle_interval}."
        ),
    )


def build_trade_card(
    *,
    horizons: list[HorizonForecast],
    stats: PriceSeriesStats,
    entry: float,
    stop: float,
    take_profit: float,
    rr: float | None,
    structure_ok: bool,
    scale_ok: bool,
    decision: DecisionCard,
    in_position: bool,
    take_profit_source: str,
) -> ForecastTrade:
    primary = horizons[0] if horizons else None
    stance = decision.stance
    analytics_ok = (
        decision_allows_add_on(stance) if in_position else decision_allows_new_entry(stance)
    )
    rr_ok = meets_min_reward_risk(rr)
    ta_ready = bool(rr_ok and structure_ok and scale_ok)
    ta_enter = bool(primary and primary.action == "enter" and primary.entry_price is not None)
    enter = ta_enter and analytics_ok
    blocked_by_decision = (not analytics_ok) and ta_ready
    blocked_by_scale = (not scale_ok) and rr_ok and structure_ok

    r_pct = risk_pct(entry=entry, stop=stop)
    rw_pct = reward_pct(entry=entry, take_profit=take_profit)
    c_pct = chart_range_pct(entry=entry, period_high=stats.high, period_low=stats.low)
    playout = estimate_playout(
        entry=entry,
        take_profit=take_profit,
        atr=stats.atr,
        candle_interval=stats.candle_interval,
        lookback_days=stats.days,
    )

    if enter:
        why = (
            f"Enter long: DecisionCard={stance.value}; R:R {rr:.2f} ≥ {MIN_REWARD_RISK}; "
            f"chart-scale ok (risk≥{MIN_RISK_FRAC_OF_CHART_RANGE:.0%} of period H/L); "
            f"structure ok; TP from {take_profit_source}."
            if rr is not None
            else f"Enter long: DecisionCard={stance.value}."
        )
        side = "long"
        entry_out = entry
    elif blocked_by_decision:
        why = (
            f"No enter: DecisionCard stance is {stance.value} "
            f"(analytics blocks new risk). TA levels kept for reference "
            f"(R:R={rr if rr is not None else 'n/a'}; TP from {take_profit_source})."
        )
        side = None
        entry_out = None
    elif blocked_by_scale:
        why = (
            f"Skip enter: stop distance is below {MIN_RISK_FRAC_OF_CHART_RANGE:.0%} "
            f"of period high-low (anti-scalp on this chart). "
            f"R:R={rr if rr is not None else 'n/a'}; DecisionCard={stance.value}."
        )
        side = None
        entry_out = None
    elif not rr_ok:
        why = (
            f"Skip enter: R:R {rr if rr is not None else 'n/a'} "
            f"< {MIN_REWARD_RISK} (need at least 1:3). "
            f"DecisionCard={stance.value}."
        )
        side = None
        entry_out = None
    elif not structure_ok:
        why = (
            f"Skip enter: price not near support structure. "
            f"DecisionCard={stance.value}."
        )
        side = None
        entry_out = None
    else:
        why = (
            f"Skip enter: action={primary.action if primary else 'n/a'}; "
            f"DecisionCard={stance.value}."
        )
        side = None
        entry_out = None

    if take_profit_source == "period_high":
        exit_rationale = (
            f"Take-profit uses period_high {take_profit:.4f} "
            f"(not swing_resistance {stats.resistance:.4f}) because swing TP "
            f"did not clear min R:R {MIN_REWARD_RISK}. High R:R here is not "
            f"proof of a high-quality setup."
        )
    else:
        exit_rationale = (
            f"Take-profit at swing_resistance {take_profit:.4f}; "
            "no operational trailing exit in MVP."
        )

    return ForecastTrade(
        enter=enter,
        side=side,
        why_enter_or_skip=why,
        entry_price=entry_out,
        stop_loss=stop,
        take_profit=take_profit,
        take_profit_source=take_profit_source,
        reward_risk=round(rr, 3) if rr is not None else None,
        risk_pct=round(r_pct * 100.0, 4) if r_pct is not None else None,
        reward_pct=round(rw_pct * 100.0, 4) if rw_pct is not None else None,
        chart_range_pct=round(c_pct * 100.0, 4) if c_pct is not None else None,
        scale_ok=scale_ok,
        min_reward_risk=MIN_REWARD_RISK,
        preferred_reward_risk=PREFERRED_REWARD_RISK,
        support=round_price(stats.support),
        resistance=round_price(stats.resistance),
        stop_rationale=(
            f"Stop below swing support {stats.support:.4f} minus ATR({stats.atr:.4f}) "
            f"on {stats.candle_interval}."
        ),
        exit_rationale=exit_rationale,
        blocked_by_decision=blocked_by_decision,
        blocked_by_scale=blocked_by_scale,
        estimated_playout=playout,
    )


def build_rule_horizons(
    *,
    in_position: bool,
    period: str,
    stats: PriceSeriesStats,
    reference: float,
    derivatives: DerivativesSnapshot,
    decision: DecisionCard,
) -> tuple[
    list[HorizonForecast], float, float, float, float, float | None, bool, str, bool
]:
    """Deterministic horizons: Decision Card + R:R ≥ 1:3 + chart-scale gate.

    Returns horizons, setup_score, entry, stop, take_profit, rr, structure_ok,
    take_profit_source, scale_ok.
    """
    entry, stop, take_profit, structure_ok, tp_source, rr, scale_ok = _long_setup_levels(
        reference=reference,
        stats=stats,
    )
    rr_ok = meets_min_reward_risk(rr)
    score = compute_setup_score(
        stats=stats,
        derivatives=derivatives,
        reward_risk=rr,
        structure_ok=structure_ok,
    )
    change = stats.change_pct
    trend_risk = _clamp(abs(change) / 20.0)
    stance = decision.stance

    if in_position:
        allow_add = decision_allows_add_on(stance)
        horizons: list[HorizonForecast] = []
        for name in ("today", "7d", "30d"):
            if stance == Stance.AVOID or (change < -5 and name == "today"):
                action = "exit" if name == "today" or stance == Stance.AVOID else "reduce"
                e = None
                local_rr = rr
            elif stance == Stance.REDUCE:
                action = "reduce"
                e = None
                local_rr = rr
            elif not rr_ok or not scale_ok:
                action = "reduce" if change < 0 else "hold"
                e = None
                local_rr = rr
            elif (
                allow_add
                and structure_ok
                and score >= 0.55
                and name != "today"
            ):
                action = "enter"
                e = entry
                local_rr = rr
            else:
                action = "hold"
                e = None
                local_rr = rr
            if action == "enter" and (not rr_ok or not scale_ok or not allow_add):
                action = "hold"
                e = None
            horizons.append(
                HorizonForecast(
                    horizon=name,
                    action=action,
                    risk_score=round(
                        _clamp(trend_risk + (0.15 if change < -2 else 0.0)),
                        3,
                    ),
                    entry_price=e,
                    stop_price=stop,
                    take_profit_price=take_profit,
                    reward_risk=round(local_rr, 3) if local_rr is not None else None,
                    setup_score=score,
                    rationale=(
                        f"DecisionCard={stance.value}; "
                        f"S/R {stats.support:.4f}/{stats.resistance:.4f}; "
                        f"ATR {stats.atr:.4f}; "
                        f"R:R {local_rr:.2f} (min {MIN_REWARD_RISK}); "
                        f"scale_ok={scale_ok}; score {score}; "
                        f"change {change:.2f}%."
                        if local_rr is not None
                        else (
                            f"DecisionCard={stance.value}; "
                            f"S/R {stats.support:.4f}/{stats.resistance:.4f}; "
                            f"score {score}."
                        )
                    ),
                )
            )
        return (
            horizons,
            score,
            entry,
            stop,
            take_profit,
            rr,
            structure_ok,
            tp_source,
            scale_ok,
        )

    allow_new = decision_allows_new_entry(stance)
    if rr_ok and structure_ok and scale_ok and allow_new:
        action = "enter"
        e = entry
        rationale = (
            f"Long setup allowed by DecisionCard={stance.value}: "
            f"entry {entry:.4f}, stop {stop:.4f}, TP {take_profit:.4f} "
            f"(source={tp_source}); "
            f"R:R {rr:.2f} ≥ {MIN_REWARD_RISK}; scale_ok; setup_score {score}; "
            f"swing S/R {stats.support:.4f}/{stats.resistance:.4f}; "
            f"period H/L {stats.high:.4f}/{stats.low:.4f}."
        )
    else:
        action = "wait"
        e = None
        if not allow_new:
            reason = f"DecisionCard={stance.value} blocks new entry"
        elif not scale_ok:
            reason = (
                f"stop below {MIN_RISK_FRAC_OF_CHART_RANGE:.0%} of period H/L "
                "(anti-scalp)"
            )
        elif not rr_ok:
            reason = "R:R below 1:3"
        else:
            reason = "price not near support structure"
        rationale = (
            f"No enter: {reason}. "
            f"Computed R:R={rr if rr is not None else 'n/a'} (min {MIN_REWARD_RISK}); "
            f"scale_ok={scale_ok}; TP source={tp_source}; "
            f"swing S/R {stats.support:.4f}/{stats.resistance:.4f}; "
            f"period H/L {stats.high:.4f}/{stats.low:.4f}; score {score}."
        )

    return (
        [
            HorizonForecast(
                horizon=period,
                action=action,
                risk_score=round(_clamp(1.0 - score), 3),
                entry_price=e,
                stop_price=stop,
                take_profit_price=take_profit,
                reward_risk=round(rr, 3) if rr is not None else None,
                setup_score=score,
                rationale=rationale,
            )
        ],
        score,
        entry,
        stop,
        take_profit,
        rr,
        structure_ok,
        tp_source,
        scale_ok,
    )


def enforce_reward_risk_gate(horizons: list[HorizonForecast]) -> list[HorizonForecast]:
    """Post-LLM hard gate: never allow enter without R:R ≥ 1:3."""
    fixed: list[HorizonForecast] = []
    for h in horizons:
        if h.action == "enter":
            rr = h.reward_risk
            if rr is None and h.entry_price and h.stop_price and h.take_profit_price:
                rr = reward_risk_ratio(
                    entry=h.entry_price,
                    stop=h.stop_price,
                    take_profit=h.take_profit_price,
                )
            if not meets_min_reward_risk(rr):
                fixed.append(
                    h.model_copy(
                        update={
                            "action": "wait",
                            "entry_price": None,
                            "reward_risk": rr,
                            "rationale": (
                                f"{h.rationale} | GATE: enter blocked, "
                                f"R:R {rr if rr is not None else 'n/a'} < {MIN_REWARD_RISK}."
                            ),
                        }
                    )
                )
                continue
        fixed.append(h)
    return fixed


def generate_forecast_bundle(
    *,
    cryptocurrency: str,
    period: str,
    question: str | None,
    analysis: AnalysisDraft,
    decision: DecisionCard,
    consensus: PriceConsensus,
    stats: PriceSeriesStats,
    derivatives: DerivativesSnapshot,
    model: BaseChatModel | None = None,
    session_logger: SessionLogger | None = None,
) -> ForecastBundle:
    if consensus.reference_price_usd is None:
        raise ValueError("Cannot build forecast without a reference price")

    focus = (question or "").lower()
    in_position = any(
        token in focus
        for token in (
            "position",
            "позиц",
            "купил",
            "купила",
            "bought",
            "holding",
            "держу",
            "вход",
            "вход.",
        )
    )

    seed, setup_score, entry, stop, take_profit, rr, structure_ok, tp_source, scale_ok = (
        build_rule_horizons(
            in_position=in_position,
            period=period,
            stats=stats,
            reference=consensus.reference_price_usd,
            derivatives=derivatives,
            decision=decision,
        )
    )
    ta_contract = build_ta_contract(stats)
    vol_note = _volume_note(stats)
    deriv_note = derivatives.note
    sources = build_forecast_sources(
        cryptocurrency=cryptocurrency,
        period=period,
        derivatives=derivatives,
    )
    tendency = build_tendency(stats)
    risk_notes = [vol_note, deriv_note]
    if rr is not None and rr >= PREFERRED_REWARD_RISK:
        risk_notes.append(
            f"R:R {rr:.2f} meets preferred ≥ {PREFERRED_REWARD_RISK} "
            f"(TP source={tp_source}; interpret carefully if period_high)"
        )
    if not scale_ok:
        risk_notes.append(
            f"chart-scale gate failed: risk < {MIN_RISK_FRAC_OF_CHART_RANGE:.0%} "
            "of period high-low (anti-scalp)"
        )
    risk_notes.append(f"DecisionCard={decision.stance.value} conf={decision.confidence}")
    risk_notes.append(
        f"TA: {stats.candle_interval} ATR({stats.atr_period}); "
        f"swing S/R vs period H/L — see ta_contract; "
        f"lookback≠hold (see estimated_playout)"
    )

    chat = model or build_xai_chat_model()
    structured = chat.with_structured_output(ForecastBundle, method="json_schema")
    lang = language_instruction(question)
    system = (
        "You are producing an EXPERIMENTAL crypto forecast helper for personal testing. "
        "This is NOT financial advice. "
        "DecisionCard is the primary risk gate: if stance is avoid/reduce/hold, "
        "trade.enter must stay false for new entries (only accumulate may allow enter). "
        "Copy numeric fields, sources URLs, trade.enter/side/levels, final_verdict, "
        "ta_contract, take_profit_source, estimated_playout, and setup_score from the seed. "
        "You may ONLY refine summary and tendency.one_liner wording. "
        "NEVER invent an enter=true. NEVER change sources URLs or ta_contract. "
        f"Enter also requires reward_risk >= {MIN_REWARD_RISK} and chart-scale ok. "
        f"{lang}"
    )
    seed_trade = build_trade_card(
        horizons=seed,
        stats=stats,
        entry=entry,
        stop=stop,
        take_profit=take_profit,
        rr=rr,
        structure_ok=structure_ok,
        scale_ok=scale_ok,
        decision=decision,
        in_position=in_position,
        take_profit_source=tp_source,
    )
    seed_verdict = "enter_long" if seed_trade.enter else "do_not_enter"
    seed_card = {
        "instrument": normalize_symbol(cryptocurrency),
        "period": period,
        "as_of_price_usd": consensus.reference_price_usd,
        "final_verdict": seed_verdict,
        "estimated_playout": seed_trade.estimated_playout,
        "ta_contract": ta_contract.model_dump(),
        "sources": [s.model_dump() for s in sources],
        "tendency": tendency.model_dump(),
        "trade": seed_trade.model_dump(),
        "setup_score": setup_score,
        "horizons": [h.model_dump() for h in seed],
    }
    human = (
        f"Cryptocurrency: {cryptocurrency}\n"
        f"Period: {period}\n"
        f"Focus: {question or '(none)'}\n"
        f"DecisionCard stance: {decision.stance.value} conf={decision.confidence}\n"
        f"Analysis brief: {analysis.brief}\n"
        f"Seed forecast card JSON: {seed_card}\n"
        "Return ForecastBundle matching the seed numbers."
    )

    def _finalize(bundle: ForecastBundle) -> ForecastBundle:
        # Levels/actions come from deterministic seed only — LLM may change wording.
        gated = enforce_reward_risk_gate(seed)
        trade = build_trade_card(
            horizons=gated,
            stats=stats,
            entry=entry,
            stop=stop,
            take_profit=take_profit,
            rr=rr,
            structure_ok=structure_ok,
            scale_ok=scale_ok,
            decision=decision,
            in_position=in_position,
            take_profit_source=tp_source,
        )
        tendency_out = tendency
        if bundle.tendency is not None and bundle.tendency.one_liner.strip():
            tendency_out = tendency.model_copy(
                update={"one_liner": bundle.tendency.one_liner.strip()}
            )
        final_verdict = "enter_long" if trade.enter else "do_not_enter"

        summary = bundle.summary.strip() if bundle.summary else ""
        if not summary:
            summary = (
                f"{normalize_symbol(cryptocurrency)} {period}: "
                f"verdict={final_verdict} · DecisionCard={decision.stance.value} · "
                f"R:R {trade.reward_risk} · score {setup_score}. Not financial advice."
            )

        return ForecastBundle(
            experimental=True,
            instrument=normalize_symbol(cryptocurrency),
            period=period,
            in_position=in_position,
            reference_price_usd=consensus.reference_price_usd,
            as_of_price_usd=consensus.reference_price_usd,
            price_dispersion_pct=consensus.dispersion_pct,
            price_status=consensus.level,
            price_warning=(
                consensus.message
                if consensus.level != PriceDispersionLevel.OK
                else None
            ),
            support=stats.support,
            resistance=stats.resistance,
            atr=stats.atr,
            ta_contract=ta_contract,
            setup_score=setup_score,
            volume_note=vol_note,
            derivatives_note=deriv_note,
            min_reward_risk=MIN_REWARD_RISK,
            preferred_reward_risk=PREFERRED_REWARD_RISK,
            sources=sources,
            tendency=tendency_out,
            trade=trade,
            risk=ForecastRiskBlock(setup_score=setup_score, notes=risk_notes),
            decision_card_ref=ForecastDecisionRef(
                stance=decision.stance.value,
                note=(
                    "Primary risk gate from analytics. "
                    "Forecast enter is allowed only when stance=accumulate "
                    "and TA R:R/structure gates pass."
                ),
            ),
            final_verdict=final_verdict,
            estimated_playout=trade.estimated_playout,
            horizons=gated,
            summary=summary,
        )

    if session_logger is not None:
        session_logger.log(
            kind="llm",
            source="forecast",
            request={"system": system, "human": human[:2500]},
        )

    try:
        result = structured.invoke(
            [SystemMessage(content=system), HumanMessage(content=human)]
        )
        if not isinstance(result, ForecastBundle):
            raise TypeError(f"Expected ForecastBundle, got {type(result)!r}")
        result = _finalize(result)
        if session_logger is not None:
            session_logger.log(
                kind="llm",
                source="forecast",
                response=result.model_dump(mode="json"),
            )
        return result
    except Exception as exc:
        if session_logger is not None:
            session_logger.log(kind="llm", source="forecast", error=str(exc))
        return _finalize(
            ForecastBundle(
                in_position=in_position,
                reference_price_usd=consensus.reference_price_usd,
                price_dispersion_pct=consensus.dispersion_pct,
                price_status=consensus.level,
                horizons=seed,
                summary=(
                    "Experimental rule-based forecast (LLM formatting unavailable). "
                    "Not financial advice."
                ),
            )
        )

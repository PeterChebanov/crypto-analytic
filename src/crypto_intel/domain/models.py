"""Domain models: the data shapes our research system uses (no database, no LLM)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class RunStatus(StrEnum):
    """Where a research job is in its lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_PRICE_CONFIRMATION = "awaiting_price_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchMode(StrEnum):
    """User-selected research mode."""

    ANALYTICS = "analytics"
    FORECAST = "forecast"


class Stance(StrEnum):
    """Simple action suggestion for a human (not a price prediction)."""

    ACCUMULATE = "accumulate"
    HOLD = "hold"
    REDUCE = "reduce"
    AVOID = "avoid"


class SourceType(StrEnum):
    """What kind of place a fact came from."""

    NEWS = "news"
    MARKET = "market"
    GITHUB = "github"
    OTHER = "other"


class PriceDispersionLevel(StrEnum):
    OK = "ok"
    WARN = "warn"
    HARD = "hard"


class ResearchRequest(BaseModel):
    """A user order: research this cryptocurrency for this time period."""

    cryptocurrency: str = Field(..., min_length=1, examples=["ETH", "BTC"])
    period: str = Field(
        ...,
        min_length=1,
        examples=["1d", "7d", "14d", "30d"],
        description="Lookback window; in forecast mode also the default horizon when not in a position.",
    )
    question: str | None = Field(
        default=None,
        description="Optional focus. Output language follows this text when set.",
    )
    mode: ResearchMode = Field(
        default=ResearchMode.ANALYTICS,
        description="analytics = brief+DecisionCard; forecast = analytics + price/TA layer.",
    )
    accept_degraded_price: bool = Field(
        default=False,
        description="If true, allow forecast to continue with only one working price source.",
    )


class Fact(BaseModel):
    """One concrete finding we collected."""

    id: UUID = Field(default_factory=uuid4)
    source_type: SourceType
    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    source_url: HttpUrl | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class DecisionCard(BaseModel):
    """Short advice card: what to do carefully, why, and when to change our mind."""

    stance: Stance
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(..., min_length=1)
    invalidation: list[str] = Field(default_factory=list)


class AnalysisDraft(BaseModel):
    """Textual analysis without a DecisionCard."""

    brief: str = Field(..., min_length=1)
    gaps: list[str] = Field(default_factory=list)
    risks_and_catalysts: list[str] = Field(default_factory=list)
    watchlist: list[str] = Field(default_factory=list)


class PriceQuote(BaseModel):
    """One venue spot quote in USD terms."""

    source: str
    symbol: str
    price_usd: float = 0.0
    ok: bool = True
    error: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class PriceConsensus(BaseModel):
    """Multi-source spot consensus for forecast gating."""

    quotes: list[PriceQuote]
    ok_count: int
    reference_price_usd: float | None
    dispersion_pct: float | None
    level: PriceDispersionLevel
    message: str


class HorizonForecast(BaseModel):
    """One horizon inside an experimental forecast bundle."""

    horizon: str
    action: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    entry_price: float | None = None
    stop_price: float | None = None
    take_profit_price: float | None = None
    reward_risk: float | None = None
    setup_score: float | None = Field(default=None, ge=0.0, le=1.0)
    rationale: str


class ForecastSource(BaseModel):
    """One short provenance line for the forecast card."""

    kind: str
    detail: str
    url: str


class ForecastTendency(BaseModel):
    """Window move using first/last closes — not period high/low."""

    direction: str
    from_price: float
    to_price: float
    change_pct: float
    one_liner: str
    price_basis: str = "first_close_to_last_close"


class ForecastTrade(BaseModel):
    """Enter yes/no + levels. MVP long-only.

    enter requires: Decision Card allows risk-on (accumulate for new entry)
    AND reward/risk ≥ min_reward_risk AND chart-scale risk gate AND structure ok.
    """

    enter: bool
    side: str | None = None
    why_enter_or_skip: str
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    take_profit_source: str | None = None
    reward_risk: float | None = None
    risk_pct: float | None = None
    reward_pct: float | None = None
    chart_range_pct: float | None = None
    scale_ok: bool = False
    min_reward_risk: float = 3.0
    preferred_reward_risk: float = 5.0
    support: float | None = None
    resistance: float | None = None
    stop_rationale: str | None = None
    exit_rationale: str | None = None
    blocked_by_decision: bool = False
    blocked_by_scale: bool = False
    estimated_playout: str | None = None


class ForecastRiskBlock(BaseModel):
    setup_score: float = Field(..., ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)


class ForecastDecisionRef(BaseModel):
    stance: str
    note: str


class ForecastTaContract(BaseModel):
    """How to read TA numbers — swing pivots are not weekly high/low."""

    candle_interval: str
    lookback_days: int
    atr_period: int
    atr_note: str
    sr_method: str
    sr_note: str
    period_high: float
    period_low: float
    swing_support: float
    swing_resistance: float
    min_risk_frac_of_chart_range: float = 0.10
    scale_note: str = (
        "Stop distance must be ≥ 10% of period high-low on this chart "
        "(anti-scalp). analysis lookback ≠ trade hold time."
    )


class ForecastBundle(BaseModel):
    """Experimental forecast layer (personal testing — not financial advice)."""

    experimental: bool = True
    instrument: str | None = None
    period: str | None = None
    in_position: bool
    reference_price_usd: float
    as_of_price_usd: float | None = None
    price_dispersion_pct: float | None
    price_status: PriceDispersionLevel
    price_warning: str | None = None
    support: float | None = None
    resistance: float | None = None
    atr: float | None = None
    ta_contract: ForecastTaContract | None = None
    setup_score: float | None = Field(default=None, ge=0.0, le=1.0)
    volume_note: str | None = None
    derivatives_note: str | None = None
    min_reward_risk: float = 3.0
    preferred_reward_risk: float = 5.0
    sources: list[ForecastSource] = Field(default_factory=list)
    tendency: ForecastTendency | None = None
    trade: ForecastTrade | None = None
    risk: ForecastRiskBlock | None = None
    decision_card_ref: ForecastDecisionRef | None = None
    final_verdict: str | None = None
    estimated_playout: str | None = None
    horizons: list[HorizonForecast] = Field(default_factory=list)
    summary: str


class ResearchReport(BaseModel):
    """The final document the user reads after a research run."""

    brief: str = Field(..., min_length=1)
    decision: DecisionCard
    gaps: list[str] = Field(default_factory=list)
    risks_and_catalysts: list[str] = Field(default_factory=list)
    watchlist: list[str] = Field(default_factory=list)
    forecast: ForecastBundle | None = None
    output_language_note: str | None = None


class Critique(BaseModel):
    """Internal quality check of a draft report before we show it to the user."""

    passed: bool
    needs_revision: bool = False
    issues: list[str] = Field(default_factory=list)

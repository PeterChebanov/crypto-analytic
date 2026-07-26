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
    COMPLETED = "completed"
    FAILED = "failed"


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


class ResearchRequest(BaseModel):
    """A user order: research this cryptocurrency for this time period."""

    cryptocurrency: str = Field(..., min_length=1, examples=["ETH", "BTC"])
    period: str = Field(
        ...,
        min_length=1,
        examples=["1d", "7d", "14d", "30d"],
        description="How far back to look at news, market data, and charts.",
    )
    question: str | None = Field(
        default=None,
        description="Optional focus, e.g. unlock risk or TVL change.",
    )


class Fact(BaseModel):
    """One concrete finding we collected (not a website name — a single fact from a website)."""

    id: UUID = Field(default_factory=uuid4)
    source_type: SourceType
    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    source_url: HttpUrl | None = None
    raw: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional raw payload from the API for debugging/audit.",
    )
    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class DecisionCard(BaseModel):
    """Short advice card: what to do carefully, why, and when to change our mind."""

    stance: Stance
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(..., min_length=1)
    invalidation: list[str] = Field(
        default_factory=list,
        description="If these things happen, the stance may no longer be valid.",
    )


class ResearchReport(BaseModel):
    """The final document the user reads after a research run."""

    brief: str = Field(..., min_length=1, description="Short summary in plain language.")
    decision: DecisionCard
    gaps: list[str] = Field(
        default_factory=list,
        description="What we still do not know.",
    )
    risks_and_catalysts: list[str] = Field(
        default_factory=list,
        description="What could help or hurt the cryptocurrency.",
    )
    watchlist: list[str] = Field(
        default_factory=list,
        description="What to monitor next.",
    )


class Critique(BaseModel):
    """Internal quality check of a draft report before we show it to the user."""

    passed: bool = Field(..., description="True if the report is good enough to publish.")
    needs_revision: bool = Field(
        default=False,
        description="True if analysis should run again and fix problems.",
    )
    issues: list[str] = Field(
        default_factory=list,
        description="What is wrong, e.g. missing links or claims without facts.",
    )
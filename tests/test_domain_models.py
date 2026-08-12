"""Unit tests for domain contracts"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from crypto_intel.domain.models import(
    DecisionCard,
    Fact,
    ResearchReport,
    ResearchRequest,
    SourceType,
    Stance,
)


def test_research_request_ok() -> None:
    req = ResearchRequest(cryptocurrency="ETH", period="7d")
    assert req.cryptocurrency == "ETH"
    assert req.period == "7d"
    assert req.question is None
    assert req.mode.value == "analytics"
    assert req.accept_degraded_price is False


def test_research_request_rejects_empty_cryptocurrency() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(cryptocurrency="", period="7d")


def test_fact_requires_title_and_summary() -> None:
    with pytest.raises(ValidationError):
        Fact(source_type=SourceType.NEWS, title="", summary="x")


def test_decision_card_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        DecisionCard(
            stance=Stance.HOLD,
            confidence=1.5,
            rationale="bad confidence",
        )


def test_research_report_roundtrip() -> None:
    report = ResearchReport(
        brief="Brief",
        decision=DecisionCard(
        stance=Stance.HOLD,
        confidence=0.5,
        rationale="Wait",
        invalidation=["Hack"],
        ),
        gaps=["No on-chain data"]
    )
    data = report.model_dump(mode="json")
    restored = ResearchReport.model_validate(data)
    assert restored.decision.stance == Stance.HOLD
    assert restored.gaps == ["No on-chain data"]


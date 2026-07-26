"""Integration tests for DB repository (requires running Postgres)."""

from __future__ import annotations

from crypto_intel.db.repository import add_fact, create_run, get_run, save_report, set_run_status
from crypto_intel.db.session import session_scope
from crypto_intel.domain.models import (
    DecisionCard,
    Fact,
    ResearchReport,
    ResearchRequest,
    RunStatus,
    SourceType,
    Stance,
)


def test_create_run_add_fact_save_report_roundtrip() -> None:
    request = ResearchRequest(
        cryptocurrency="ETH",
        period="7d",
        question="integration test",
    )
    fact = Fact(
        source_type=SourceType.NEWS,
        title="Test headline",
        summary="Test summary",
        source_url="https://example.com/news/1"
    ) 
    report = ResearchReport(
        brief="Short brief",
        decision=DecisionCard(
            stance=Stance.HOLD,
            confidence=0.6,
            rationale="Not enough signal yet",
            invalidation=["Major hack"]
        )
    )
    
    with session_scope() as session:
        run = create_run(session, request)
        add_fact(session, run.id, fact)
        save_report(session, run.id, report)
        run.status = RunStatus.COMPLETED.value
        run_id = run.id
    
    with session_scope() as session:
        loaded = get_run(session, run_id)
        assert loaded is not None
        assert loaded.cryptocurrency == "ETH"
        assert loaded.period == "7d"
        assert loaded.status == RunStatus.COMPLETED.value
        assert len(loaded.facts) == 1
        assert loaded.facts[0].title == "Test headline"
        assert loaded.facts[0].source_url == "https://example.com/news/1"
        assert len(loaded.reports) == 1
        assert loaded.reports[0].payload["decision"]["stance"] == "hold"
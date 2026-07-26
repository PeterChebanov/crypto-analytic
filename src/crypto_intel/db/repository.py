from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from crypto_intel.db.models import FactORM, ReportORM, ResearchRunORM
from crypto_intel.domain.models import (
    Fact, 
    ResearchReport,
    ResearchRequest,
    RunStatus,
)


def create_run(session: Session, request: ResearchRequest) -> ResearchRunORM:
    """Insert a new research run in pending status."""
    run = ResearchRunORM(
        id=uuid4(),
        cryptocurrency=request.cryptocurrency,
        period=request.period,
        question=request.question,
        status=RunStatus.PENDING.value,
    )
    session.add(run)
    return run


def set_run_status(
    session: Session,
    run_id: UUID,
    status: RunStatus,
    error_message: str | None = None,
) -> ResearchRunORM:
    """Update run status + optional error message"""
    run = session.get(ResearchRunORM, run_id)
    if run is None:
        raise ValueError(f"Research run not found: {run_id}")
    run.status = status.value
    run.error_message = error_message
    session.add(run)
    return run


def add_fact(session: Session, run_id: UUID, fact: Fact) -> FactORM:
    row = FactORM(
        id=fact.id,
        run_id=run_id,
        source_type=fact.source_type.value,
        title=fact.title,
        summary=fact.summary,
        source_url= str(fact.source_url) if fact.source_url is not None else None,
        raw=fact.raw,
        collected_at=fact.collected_at,
    )
    session.add(row)
    return row


def save_report(
    session: Session,
    run_id: UUID,
    report: ResearchReport,
    version: int = 1,
) -> ReportORM:
    """Store final report JSON for a run"""
    row = ReportORM(
        id=uuid4(),
        run_id=run_id,
        version=version,
        payload=report.model_dump(mode="json")
    )
    session.add(row)
    return row


def get_run(session: Session, run_id: UUID) -> ResearchRunORM | None:
    """Load a run with facts and reports eagerly"""
    stmt = (
        select(ResearchRunORM)
        .where(ResearchRunORM.id == run_id)
        .options(
            selectinload(ResearchRunORM.facts),
            selectinload(ResearchRunORM.reports),
        )
    )
    return session.scalars(stmt).first()

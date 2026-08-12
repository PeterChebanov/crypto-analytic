"""FastAPI delivery surface for research runs."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from crypto_intel.db.repository import get_run
from crypto_intel.db.session import session_scope
from crypto_intel.domain.models import PriceConsensus, ResearchRequest, ResearchReport
from crypto_intel.health import check_external_dependencies
from crypto_intel.logging_ext.session_log import read_session_logs
from crypto_intel.observability import configure_observability
from crypto_intel.services.research import (
    ResearchConflictError,
    ResearchNotAwaitingError,
    confirm_degraded_price,
    execute_research_run,
    load_stored_consensus,
    start_research_run,
)
from crypto_intel.settings import get_settings

logger = logging.getLogger(__name__)

_WEB_DIR = Path(__file__).resolve().parents[1] / "web" / "static"


class ResearchCreateResponse(BaseModel):
    run_id: UUID
    status: str


class ResearchStatusResponse(BaseModel):
    run_id: UUID
    cryptocurrency: str
    period: str
    question: str | None
    status: str
    error_message: str | None = None
    price_consensus: PriceConsensus | None = None


class ResearchReportResponse(BaseModel):
    run_id: UUID
    status: str
    report: ResearchReport | None = None
    facts: list[dict[str, Any]] = Field(default_factory=list)
    price_consensus: PriceConsensus | None = None


class PriceConfirmRequest(BaseModel):
    accept: bool = True


class SessionLogsResponse(BaseModel):
    run_id: UUID
    entries: list[dict[str, Any]] = Field(default_factory=list)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_observability(settings)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    yield


app = FastAPI(
    title="AI Crypto Intelligence Platform",
    description=(
        "Research + decision support (not price prediction). "
        "Not financial advice."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")


@app.get("/")
def ui_index() -> FileResponse:
    return FileResponse(_WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/dependencies")
def health_dependencies() -> dict[str, Any]:
    """Ping external venues used by collectors (for UI status lamp)."""
    return check_external_dependencies()


@app.post("/research", response_model=ResearchCreateResponse, status_code=202)
def create_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
) -> ResearchCreateResponse:
    try:
        run_id = start_research_run(request)
    except ResearchConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("failed to start research")
        raise HTTPException(status_code=500, detail="Failed to start research") from exc

    background_tasks.add_task(execute_research_run, run_id)
    return ResearchCreateResponse(run_id=run_id, status="pending")


@app.get("/research/{run_id}", response_model=ResearchStatusResponse)
def get_research(run_id: UUID) -> ResearchStatusResponse:
    with session_scope() as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Research run not found")
        consensus = None
        if run.status == "awaiting_price_confirmation":
            consensus = load_stored_consensus(run_id)
        return ResearchStatusResponse(
            run_id=run.id,
            cryptocurrency=run.cryptocurrency,
            period=run.period,
            question=run.question,
            status=run.status,
            error_message=run.error_message,
            price_consensus=consensus,
        )


@app.post("/research/{run_id}/confirm-price", response_model=ResearchStatusResponse)
def confirm_price(
    run_id: UUID,
    body: PriceConfirmRequest,
) -> ResearchStatusResponse:
    try:
        # Run synchronously so UI can immediately poll completed/forecast;
        # confirmation work is short (history + LLM format).
        confirm_degraded_price(run_id, accept=body.accept)
    except ResearchNotAwaitingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("price confirmation failed")
        raise HTTPException(status_code=500, detail="Price confirmation failed") from exc

    with session_scope() as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Research run not found")
        return ResearchStatusResponse(
            run_id=run.id,
            cryptocurrency=run.cryptocurrency,
            period=run.period,
            question=run.question,
            status=run.status,
            error_message=run.error_message,
            price_consensus=load_stored_consensus(run_id),
        )


@app.get("/research/{run_id}/report", response_model=ResearchReportResponse)
def get_research_report(run_id: UUID) -> ResearchReportResponse:
    with session_scope() as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Research run not found")

        report: ResearchReport | None = None
        if run.reports:
            latest = max(run.reports, key=lambda row: row.version)
            report = ResearchReport.model_validate(latest.payload)

        facts = [
            {
                "id": str(fact.id),
                "source_type": fact.source_type,
                "title": fact.title,
                "summary": fact.summary,
                "source_url": fact.source_url,
                "collected_at": fact.collected_at.isoformat(),
            }
            for fact in run.facts
        ]
        return ResearchReportResponse(
            run_id=run.id,
            status=run.status,
            report=report,
            facts=facts,
            price_consensus=load_stored_consensus(run_id),
        )


@app.get("/research/{run_id}/logs", response_model=SessionLogsResponse)
def get_research_logs(run_id: UUID) -> SessionLogsResponse:
    with session_scope() as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Research run not found")
    return SessionLogsResponse(run_id=run_id, entries=read_session_logs(run_id))

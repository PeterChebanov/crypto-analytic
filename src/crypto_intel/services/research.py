"""Research run orchestration used by the API and scheduler."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from langgraph.checkpoint.memory import InMemorySaver

from crypto_intel.db.repository import create_run, get_run, save_report, set_run_status
from crypto_intel.db.session import session_scope
from crypto_intel.domain.language import language_note
from crypto_intel.domain.models import (
    AnalysisDraft,
    PriceConsensus,
    ResearchMode,
    ResearchReport,
    ResearchRequest,
    RunStatus,
)
from crypto_intel.forecast.engine import generate_forecast_bundle
from crypto_intel.forecast.gate import ForecastPriceGate, decide_forecast_price_gate
from crypto_intel.graph.builder import build_research_graph
from crypto_intel.logging_ext.context import bind_session_logger
from crypto_intel.logging_ext.session_log import SessionLogger
from crypto_intel.pricing.derivatives import fetch_derivatives_snapshot
from crypto_intel.pricing.history import fetch_price_series_stats
from crypto_intel.pricing.quotes import build_price_consensus, collect_spot_quotes
from crypto_intel.redis.client import get_redis
from crypto_intel.redis.locks import LockHandle, acquire_research_lock, release_research_lock
from crypto_intel.settings import get_settings

logger = logging.getLogger(__name__)

_checkpointer = InMemorySaver()

_OPTS_TTL_SECONDS = 60 * 60 * 24
_CONSENSUS_TTL_SECONDS = 60 * 60 * 6


class ResearchConflictError(RuntimeError):
    """Raised when a research lock is already held for the cryptocurrency/day."""


class ResearchNotAwaitingError(RuntimeError):
    """Raised when price confirmation is requested for a run that is not awaiting."""


def _opts_key(run_id: UUID) -> str:
    return f"research:opts:{run_id}"


def _consensus_key(run_id: UUID) -> str:
    return f"research:price_consensus:{run_id}"


def _store_run_opts(run_id: UUID, request: ResearchRequest) -> None:
    redis_client = get_redis()
    payload = {
        "mode": request.mode.value,
        "accept_degraded_price": request.accept_degraded_price,
    }
    redis_client.setex(_opts_key(run_id), _OPTS_TTL_SECONDS, json.dumps(payload))


def _load_run_opts(run_id: UUID) -> dict[str, Any]:
    raw = get_redis().get(_opts_key(run_id))
    if not raw:
        return {
            "mode": ResearchMode.ANALYTICS.value,
            "accept_degraded_price": False,
        }
    return json.loads(str(raw))


def _store_consensus(run_id: UUID, consensus: PriceConsensus) -> None:
    get_redis().setex(
        _consensus_key(run_id),
        _CONSENSUS_TTL_SECONDS,
        consensus.model_dump_json(),
    )


def load_stored_consensus(run_id: UUID) -> PriceConsensus | None:
    raw = get_redis().get(_consensus_key(run_id))
    if not raw:
        return None
    return PriceConsensus.model_validate_json(str(raw))


def start_research_run(request: ResearchRequest) -> UUID:
    """Create a pending run and acquire the daily lock. Caller schedules execution."""
    settings = get_settings()
    redis_client = get_redis()
    handle = acquire_research_lock(
        redis_client,
        cryptocurrency=request.cryptocurrency,
        ttl_seconds=settings.research_lock_ttl_seconds,
    )
    if handle is None:
        raise ResearchConflictError(
            f"Research already running for {request.cryptocurrency.upper()} today"
        )

    try:
        with session_scope() as session:
            run = create_run(session, request)
            run_id = run.id
        _store_run_opts(run_id, request)
    except Exception:
        release_research_lock(redis_client, handle)
        raise

    redis_client.setex(
        f"research:lockmeta:{run_id}",
        settings.research_lock_ttl_seconds,
        f"{handle.key}|{handle.token}",
    )
    return run_id


def _release_lock_for_run(run_id: UUID) -> None:
    redis_client = get_redis()
    meta = redis_client.get(f"research:lockmeta:{run_id}")
    if not meta:
        return
    key, _, token = str(meta).partition("|")
    if key and token:
        release_research_lock(redis_client, LockHandle(key=key, token=token))
    redis_client.delete(f"research:lockmeta:{run_id}")


def _latest_report(run_id: UUID) -> ResearchReport | None:
    with session_scope() as session:
        run = get_run(session, run_id)
        if run is None or not run.reports:
            return None
        latest = max(run.reports, key=lambda row: row.version)
        return ResearchReport.model_validate(latest.payload)


def _next_report_version(run_id: UUID) -> int:
    with session_scope() as session:
        run = get_run(session, run_id)
        if run is None or not run.reports:
            return 1
        return max(row.version for row in run.reports) + 1


def _persist_report(run_id: UUID, report: ResearchReport, *, status: RunStatus) -> None:
    version = _next_report_version(run_id)
    with session_scope() as session:
        save_report(session, run_id, report, version=version)
        set_run_status(session, run_id, status)


def _build_and_attach_forecast(
    *,
    run_id: UUID,
    cryptocurrency: str,
    period: str,
    question: str | None,
    report: ResearchReport,
    consensus: PriceConsensus,
    session_logger: SessionLogger,
) -> ResearchReport:
    stats = fetch_price_series_stats(
        cryptocurrency,
        period,
        session_logger=session_logger,
    )
    derivatives = fetch_derivatives_snapshot(
        cryptocurrency,
        period,
        session_logger=session_logger,
    )
    analysis = AnalysisDraft(
        brief=report.brief,
        gaps=list(report.gaps),
        risks_and_catalysts=list(report.risks_and_catalysts),
        watchlist=list(report.watchlist),
    )
    forecast = generate_forecast_bundle(
        cryptocurrency=cryptocurrency,
        period=period,
        question=question,
        analysis=analysis,
        decision=report.decision,
        consensus=consensus,
        stats=stats,
        derivatives=derivatives,
        session_logger=session_logger,
    )
    updated = report.model_copy(
        update={
            "forecast": forecast,
            "output_language_note": report.output_language_note
            or language_note(question),
        }
    )
    _persist_report(run_id, updated, status=RunStatus.COMPLETED)
    return updated


def _apply_forecast_layer(
    *,
    run_id: UUID,
    cryptocurrency: str,
    period: str,
    question: str | None,
    accept_degraded_price: bool,
    session_logger: SessionLogger,
) -> None:
    report = _latest_report(run_id)
    if report is None:
        with session_scope() as session:
            set_run_status(
                session,
                run_id,
                RunStatus.FAILED,
                error_message="Forecast layer missing analytics report",
            )
        return

    quotes = collect_spot_quotes(cryptocurrency, session_logger=session_logger)
    consensus = build_price_consensus(quotes)
    session_logger.log(
        kind="price_consensus",
        source="multi",
        request={"cryptocurrency": cryptocurrency},
        response=consensus.model_dump(mode="json"),
    )
    _store_consensus(run_id, consensus)

    gate = decide_forecast_price_gate(
        consensus,
        accept_degraded_price=accept_degraded_price,
    )

    if gate == ForecastPriceGate.AWAIT_CONFIRMATION:
        with session_scope() as session:
            set_run_status(
                session,
                run_id,
                RunStatus.AWAITING_PRICE_CONFIRMATION,
                error_message=consensus.message,
            )
        return

    if gate == ForecastPriceGate.SKIP:
        # Analytics remains; forecast omitted with a hard price note in gaps.
        note = f"Forecast skipped: {consensus.message}"
        gaps = list(report.gaps)
        if note not in gaps:
            gaps.append(note)
        skipped = report.model_copy(update={"gaps": gaps, "forecast": None})
        _persist_report(run_id, skipped, status=RunStatus.COMPLETED)
        return

    _build_and_attach_forecast(
        run_id=run_id,
        cryptocurrency=cryptocurrency,
        period=period,
        question=question,
        report=report,
        consensus=consensus,
        session_logger=session_logger,
    )


def execute_research_run(run_id: UUID) -> None:
    """Run the LangGraph orchestrator for an existing research run."""
    with session_scope() as session:
        run = get_run(session, run_id)
        if run is None:
            raise ValueError(f"Research run not found: {run_id}")
        cryptocurrency = run.cryptocurrency
        period = run.period
        question = run.question
        set_run_status(session, run_id, RunStatus.RUNNING)

    opts = _load_run_opts(run_id)
    mode = ResearchMode(opts.get("mode", ResearchMode.ANALYTICS.value))
    accept_degraded = bool(opts.get("accept_degraded_price", False))
    session_logger = SessionLogger(run_id)

    graph = build_research_graph(checkpointer=_checkpointer)
    config = {"configurable": {"thread_id": str(run_id)}}
    try:
        with bind_session_logger(session_logger):
            session_logger.log(
                kind="run",
                source="research",
                request={
                    "cryptocurrency": cryptocurrency,
                    "period": period,
                    "mode": mode.value,
                },
            )
            graph.invoke(
                {
                    "cryptocurrency": cryptocurrency,
                    "period": period,
                    "question": question,
                    "run_id": run_id,
                    "mode": mode.value,
                },
                config,
            )
            if mode == ResearchMode.FORECAST:
                _apply_forecast_layer(
                    run_id=run_id,
                    cryptocurrency=cryptocurrency,
                    period=period,
                    question=question,
                    accept_degraded_price=accept_degraded,
                    session_logger=session_logger,
                )
    except Exception as exc:
        logger.exception("research run failed run_id=%s", run_id)
        with session_scope() as session:
            set_run_status(
                session,
                run_id,
                RunStatus.FAILED,
                error_message=str(exc),
            )
        raise
    finally:
        _release_lock_for_run(run_id)


def confirm_degraded_price(run_id: UUID, *, accept: bool) -> None:
    """Continue or abort forecast after a 1/3 price-source hard warning."""
    with session_scope() as session:
        run = get_run(session, run_id)
        if run is None:
            raise ValueError(f"Research run not found: {run_id}")
        if run.status != RunStatus.AWAITING_PRICE_CONFIRMATION.value:
            raise ResearchNotAwaitingError(
                f"Run {run_id} is not awaiting price confirmation "
                f"(status={run.status})"
            )
        cryptocurrency = run.cryptocurrency
        period = run.period
        question = run.question

    if not accept:
        report = _latest_report(run_id)
        if report is not None:
            note = "Forecast skipped: user declined degraded single-source price."
            gaps = list(report.gaps)
            if note not in gaps:
                gaps.append(note)
            skipped = report.model_copy(update={"gaps": gaps, "forecast": None})
            _persist_report(run_id, skipped, status=RunStatus.COMPLETED)
        else:
            with session_scope() as session:
                set_run_status(session, run_id, RunStatus.COMPLETED)
        return

    consensus = load_stored_consensus(run_id)
    if consensus is None:
        with session_scope() as session:
            set_run_status(
                session,
                run_id,
                RunStatus.FAILED,
                error_message="Stored price consensus missing for confirmation",
            )
        return

    report = _latest_report(run_id)
    if report is None:
        with session_scope() as session:
            set_run_status(
                session,
                run_id,
                RunStatus.FAILED,
                error_message="Analytics report missing for forecast confirmation",
            )
        return

    opts = _load_run_opts(run_id)
    opts["accept_degraded_price"] = True
    get_redis().setex(_opts_key(run_id), _OPTS_TTL_SECONDS, json.dumps(opts))

    session_logger = SessionLogger(run_id)
    with session_scope() as session:
        set_run_status(session, run_id, RunStatus.RUNNING)
    try:
        with bind_session_logger(session_logger):
            session_logger.log(
                kind="run",
                source="price_confirm",
                request={"accept": True},
            )
            _build_and_attach_forecast(
                run_id=run_id,
                cryptocurrency=cryptocurrency,
                period=period,
                question=question,
                report=report,
                consensus=consensus,
                session_logger=session_logger,
            )
    except Exception as exc:
        logger.exception("forecast confirm failed run_id=%s", run_id)
        with session_scope() as session:
            set_run_status(
                session,
                run_id,
                RunStatus.FAILED,
                error_message=str(exc),
            )
        raise

"""LangGraph nodes: thin wrappers over chains, tools, LLM, and repository."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from langchain_core.language_models.chat_models import BaseChatModel

from crypto_intel.chains.analysis import analyze_evidence
from crypto_intel.chains.planner import plan_collection
from crypto_intel.db.repository import add_fact, save_report, set_run_status
from crypto_intel.db.session import session_scope
from crypto_intel.domain.language import language_note
from crypto_intel.domain.models import (
    AnalysisDraft,
    Critique,
    Fact,
    ResearchReport,
    RunStatus,
    SourceType,
)
from crypto_intel.graph.state import GraphState
from crypto_intel.llm.decision_card import generate_decision_card
from crypto_intel.tools.registry import get_tool

logger = logging.getLogger(__name__)


def _parse_kv_line(line: str) -> dict[str, str]:
    """Parse `key=value; key2=value2` tool payload lines into a dict."""
    fields: dict[str, str] = {}
    for part in line.split(";"):
        piece = part.strip()
        if not piece or "=" not in piece:
            continue
        key, value = piece.split("=", maxsplit=1)
        fields[key.strip()] = value.strip()
    return fields


def _facts_from_news_payload(payload: str) -> list[Fact]:
    facts: list[Fact] = []
    for line in payload.splitlines():
        line = line.strip()
        if not line:
            continue
        fields = _parse_kv_line(line)
        title = fields.get("title")
        summary = fields.get("summary")
        if not title or not summary:
            continue
        source_url = fields.get("source_url") or None
        facts.append(
            Fact(
                source_type=SourceType.NEWS,
                title=title,
                summary=summary,
                source_url=source_url,
                raw=fields,
            )
        )
    return facts


def _fact_from_market_payload(payload: str) -> Fact:
    fields = _parse_kv_line(payload)
    symbol = fields.get("symbol", "UNKNOWN")
    price = fields.get("price_usd", "n/a")
    change = fields.get("change_24h_pct", "n/a")
    return Fact(
        source_type=SourceType.MARKET,
        title=f"{symbol} market snapshot",
        summary=f"price_usd={price}; change_24h_pct={change}",
        source_url=None,
        raw=fields,
    )


def _load_facts(raw_facts: list[Any] | None) -> list[Fact]:
    loaded: list[Fact] = []
    for item in raw_facts or []:
        if isinstance(item, Fact):
            loaded.append(item)
        else:
            loaded.append(Fact.model_validate(item))
    return loaded


def _dump_facts(facts: list[Fact]) -> list[dict[str, Any]]:
    return [fact.model_dump(mode="json") for fact in facts]


def build_planner_node(*, model: BaseChatModel | None = None):
    """Return a planner node bound to an optional chat model."""

    def planner_node(state: GraphState) -> dict[str, Any]:
        run_id = state.get("run_id")
        logger.info(
            "planner start cryptocurrency=%s period=%s run_id=%s",
            state["cryptocurrency"],
            state["period"],
            run_id,
        )
        plan = plan_collection(
            cryptocurrency=state["cryptocurrency"],
            period=state["period"],
            question=state.get("question"),
            model=model,
        )
        return {"plan": plan, "status": RunStatus.RUNNING.value}

    return planner_node


def news_collect_node(state: GraphState) -> dict[str, Any]:
    """Fetch news via registry tool and append Fact rows."""
    try:
        tool = get_tool("fetch_news")
        raw = tool.invoke({"cryptocurrency": state["cryptocurrency"], "limit": 5})
        payload = raw if isinstance(raw, str) else str(raw)
        return {"facts": _dump_facts(_facts_from_news_payload(payload))}
    except Exception as exc:
        logger.exception("news_collect failed")
        return {"errors": [f"news_collect failed: {exc}"], "facts": []}


def market_collect_node(state: GraphState) -> dict[str, Any]:
    """Fetch market snapshot via registry tool and append one Fact."""
    try:
        tool = get_tool("get_market_snapshot")
        raw = tool.invoke({"cryptocurrency": state["cryptocurrency"]})
        payload = raw if isinstance(raw, str) else str(raw)
        return {"facts": _dump_facts([_fact_from_market_payload(payload)])}
    except Exception as exc:
        logger.exception("market_collect failed")
        return {"errors": [f"market_collect failed: {exc}"], "facts": []}


def build_analyze_node(*, model: BaseChatModel | None = None):
    """Return an analyze node bound to an optional chat model."""

    def analyze_node(state: GraphState) -> dict[str, Any]:
        draft = analyze_evidence(
            cryptocurrency=state["cryptocurrency"],
            period=state["period"],
            facts=_load_facts(list(state.get("facts", []))),
            question=state.get("question"),
            model=model,
        )
        return {"analysis": draft.model_dump(mode="json")}

    return analyze_node


def critique_node(state: GraphState) -> dict[str, Any]:
    """Deterministic quality gate (LLM critic can harden further later)."""
    issues: list[str] = []
    facts = _load_facts(list(state.get("facts", [])))
    if not facts:
        issues.append("No facts collected")
    for fact in facts:
        if fact.source_type == SourceType.NEWS and fact.source_url is None:
            issues.append(f"News fact missing source_url: {fact.title}")
    if state.get("analysis") is None:
        issues.append("No analysis draft")

    passed = len(issues) == 0
    critique = Critique(
        passed=passed,
        needs_revision=not passed,
        issues=issues,
    )
    update: dict[str, Any] = {"critique": critique.model_dump(mode="json")}
    if not passed:
        update["revision_loops"] = int(state.get("revision_loops") or 0) + 1
    return update


def build_finalize_node(*, model: BaseChatModel | None = None):
    """Assemble DecisionCard + ResearchReport; persist when run_id is present."""

    def finalize_node(state: GraphState) -> dict[str, Any]:
        analysis_raw = state.get("analysis")
        if analysis_raw is None:
            return {
                "errors": ["finalize failed: analysis is missing"],
                "status": RunStatus.FAILED.value,
            }

        analysis = (
            analysis_raw
            if isinstance(analysis_raw, AnalysisDraft)
            else AnalysisDraft.model_validate(analysis_raw)
        )
        facts = _load_facts(list(state.get("facts", [])))
        decision = generate_decision_card(
            cryptocurrency=state["cryptocurrency"],
            period=state["period"],
            facts=facts,
            question=state.get("question"),
            model=model,
        )
        report = ResearchReport(
            brief=analysis.brief,
            decision=decision,
            gaps=list(analysis.gaps),
            risks_and_catalysts=list(analysis.risks_and_catalysts),
            watchlist=list(analysis.watchlist),
            output_language_note=language_note(state.get("question")),
        )

        run_id = state.get("run_id")
        mode = (state.get("mode") or "analytics").lower()
        # Forecast mode continues after finalize; do not mark completed yet
        # (avoids UI/API race where clients load the report without forecast).
        persist_status = (
            RunStatus.RUNNING
            if mode == "forecast"
            else RunStatus.COMPLETED
        )
        if run_id is not None:
            run_uuid = run_id if isinstance(run_id, UUID) else UUID(str(run_id))
            with session_scope() as session:
                for fact in facts:
                    add_fact(session, run_uuid, fact)
                save_report(session, run_uuid, report)
                set_run_status(session, run_uuid, persist_status)

        return {
            "decision_card": decision.model_dump(mode="json"),
            "report": report.model_dump(mode="json"),
            "status": persist_status.value,
        }

    return finalize_node


def build_research_nodes(
    *,
    model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Build the default node map for the research graph."""
    return {
        "planner": build_planner_node(model=model),
        "news_collect": news_collect_node,
        "market_collect": market_collect_node,
        "analyze": build_analyze_node(model=model),
        "critique": critique_node,
        "finalize": build_finalize_node(model=model),
    }

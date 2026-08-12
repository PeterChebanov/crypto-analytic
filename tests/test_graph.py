"""Unit tests for the linear research LangGraph (mocked LLM)."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.checkpoint.memory import InMemorySaver

from crypto_intel.domain.models import AnalysisDraft, DecisionCard, Stance
from crypto_intel.graph.builder import build_research_graph


class FakeGraphModel(Runnable):
    """One fake model for planner + structured analysis + DecisionCard."""

    def invoke(
        self,
        input: Any,
        config: Any = None,
        **kwargs: Any,
    ) -> AIMessage:
        return AIMessage(
            content=(
                "- fetch_news for the cryptocurrency\n"
                "- get_market_snapshot for the cryptocurrency"
            ),
        )

    def with_structured_output(
        self,
        schema: type[Any],
        method: str = "json_schema",
    ) -> Runnable:
        if schema is AnalysisDraft:
            return RunnableLambda(
                lambda _: AnalysisDraft(
                    brief="Evidence is thin; keep stance cautious.",
                    gaps=["Only mock headlines and snapshot available"],
                    risks_and_catalysts=["Macro uncertainty"],
                    watchlist=["ETF net flows"],
                ),
            )
        if schema is DecisionCard:
            return RunnableLambda(
                lambda _: DecisionCard(
                    stance=Stance.HOLD,
                    confidence=0.55,
                    rationale="Mock evidence only; hold pending richer data.",
                    invalidation=["Major adverse unlock or exploit headline"],
                ),
            )
        raise TypeError(f"Unexpected structured schema: {schema!r}")


def test_linear_research_graph_completes_with_fake_model() -> None:
    graph = build_research_graph(model=FakeGraphModel())
    result = graph.invoke(
        {
            "cryptocurrency": "ETH",
            "period": "7d",
            "question": None,
        },
    )

    assert result["status"] == "completed"
    assert "fetch_news" in result["plan"]
    assert len(result["facts"]) >= 2
    assert result["analysis"]["brief"]
    assert result["critique"]["passed"] is True
    assert result["decision_card"]["stance"] == Stance.HOLD.value
    assert result["report"]["decision"]["stance"] == Stance.HOLD.value
    assert result["report"]["brief"] == result["analysis"]["brief"]


def test_graph_resumes_from_checkpoint_before_finalize() -> None:
    checkpointer = InMemorySaver()
    graph = build_research_graph(
        model=FakeGraphModel(),
        checkpointer=checkpointer,
        interrupt_before=["finalize"],
    )
    config = {"configurable": {"thread_id": "eth-7d-resume"}}

    graph.invoke(
        {
            "cryptocurrency": "ETH",
            "period": "7d",
            "question": None,
        },
        config,
    )

    snapshot = graph.get_state(config)
    assert snapshot.values.get("plan")
    assert snapshot.values.get("analysis") is not None
    assert snapshot.values.get("critique") is not None
    assert snapshot.values.get("report") is None
    assert "finalize" in snapshot.next

    final = graph.invoke(None, config)
    assert final["status"] == "completed"
    assert final["report"] is not None
    assert final["decision_card"]["stance"] == Stance.HOLD.value

"""Compile the research LangGraph (MVP orchestrator)."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from crypto_intel.graph.node import build_research_nodes
from crypto_intel.graph.routing import route_after_critique
from crypto_intel.graph.state import GraphState


def build_research_graph(
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any | None = None,
    interrupt_before: list[str] | None = None,
):
    """Build and compile the research orchestrator.

    Flow: planner → news → market → analyze → critique ⇄ analyze → finalize.
    Pass checkpointer + thread_id for resume. interrupt_before pauses before
    named nodes (tests / future HITL).
    """
    nodes = build_research_nodes(model=model)
    builder = StateGraph(GraphState)

    builder.add_node("planner", nodes["planner"])
    builder.add_node("news_collect", nodes["news_collect"])
    builder.add_node("market_collect", nodes["market_collect"])
    builder.add_node("analyze", nodes["analyze"])
    builder.add_node("critique", nodes["critique"])
    builder.add_node("finalize", nodes["finalize"])

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "news_collect")
    builder.add_edge("news_collect", "market_collect")
    builder.add_edge("market_collect", "analyze")
    builder.add_edge("analyze", "critique")
    builder.add_conditional_edges(
        "critique",
        route_after_critique,
        {
            "analyze": "analyze",
            "finalize": "finalize",
        },
    )
    builder.add_edge("finalize", END)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before,
    )

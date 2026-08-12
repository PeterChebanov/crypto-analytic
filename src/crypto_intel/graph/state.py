"""LangGraph run state: in-memory working set for one research cycle."""

from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired
from uuid import UUID

from typing_extensions import TypedDict


class GraphState(TypedDict):
    """State schema for the research orchestrator.

    Nested domain objects are stored as JSON-compatible dicts so
    checkpointers (msgpack) can persist and resume runs.
    Nodes return partial updates. List fields use reducers to append.
    """

    # --- input (set at invoke) ---
    cryptocurrency: str
    period: str
    question: NotRequired[str | None]
    run_id: NotRequired[UUID]
    mode: NotRequired[str]

    # --- filled by nodes (JSON-friendly payloads) ---
    plan: NotRequired[str]
    facts: Annotated[list[dict[str, Any]], operator.add]
    analysis: NotRequired[dict[str, Any]]
    critique: NotRequired[dict[str, Any]]
    decision_card: NotRequired[dict[str, Any]]
    report: NotRequired[dict[str, Any]]

    status: NotRequired[str]
    errors: Annotated[list[str], operator.add]

    # --- loop guards ---
    collect_loops: NotRequired[int]
    revision_loops: NotRequired[int]

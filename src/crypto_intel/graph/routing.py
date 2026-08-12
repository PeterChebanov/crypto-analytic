"""Conditional routing for the research graph."""

from __future__ import annotations

from typing import Any, Literal

from crypto_intel.domain.models import Critique
from crypto_intel.graph.state import GraphState

MAX_REVISION_LOOPS = 2

RouteAfterCritique = Literal["analyze", "finalize"]


def _as_critique(raw: Critique | dict[str, Any] | None) -> Critique | None:
    if raw is None:
        return None
    if isinstance(raw, Critique):
        return raw
    return Critique.model_validate(raw)


def route_after_critique(state: GraphState | dict[str, Any]) -> RouteAfterCritique:
    """Send failed critiques back to analyze until the loop budget is spent."""
    critique = _as_critique(state.get("critique"))  # type: ignore[arg-type]
    loops = int(state.get("revision_loops") or 0)

    if critique is not None and critique.needs_revision and loops <= MAX_REVISION_LOOPS:
        return "analyze"
    return "finalize"

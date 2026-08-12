"""Unit tests for graph routing (no LLM)."""

from __future__ import annotations

from crypto_intel.domain.models import Critique
from crypto_intel.graph.routing import MAX_REVISION_LOOPS, route_after_critique


def test_route_revises_when_critique_fails_within_budget() -> None:
    state = {
        "cryptocurrency": "ETH",
        "period": "7d",
        "critique": Critique(
            passed=False,
            needs_revision=True,
            issues=["No facts collected"],
        ),
        "revision_loops": 1,
    }
    assert route_after_critique(state) == "analyze"  # type: ignore[arg-type]


def test_route_finalizes_when_budget_exceeded() -> None:
    state = {
        "cryptocurrency": "ETH",
        "period": "7d",
        "critique": Critique(
            passed=False,
            needs_revision=True,
            issues=["No facts collected"],
        ),
        "revision_loops": MAX_REVISION_LOOPS + 1,
    }
    assert route_after_critique(state) == "finalize"  # type: ignore[arg-type]


def test_route_finalizes_when_critique_passes() -> None:
    state = {
        "cryptocurrency": "ETH",
        "period": "7d",
        "critique": Critique(passed=True, needs_revision=False, issues=[]),
        "revision_loops": 0,
    }
    assert route_after_critique(state) == "finalize"  # type: ignore[arg-type]
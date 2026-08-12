"""Offline eval-style checks for research quality gates."""

from __future__ import annotations

from crypto_intel.domain.models import AnalysisDraft, Fact, SourceType
from crypto_intel.graph.node import critique_node


def test_eval_critique_fails_when_news_missing_source_url() -> None:
    state = {
        "cryptocurrency": "ETH",
        "period": "7d",
        "facts": [
            Fact(
                source_type=SourceType.NEWS,
                title="Uncited headline",
                summary="Something happened",
                source_url=None,
            ).model_dump(mode="json")
        ],
        "analysis": AnalysisDraft(
            brief="Thin brief.",
            gaps=[],
            risks_and_catalysts=[],
            watchlist=[],
        ).model_dump(mode="json"),
    }
    result = critique_node(state)  # type: ignore[arg-type]
    critique = result["critique"]
    assert critique["passed"] is False
    assert critique["needs_revision"] is True
    assert any("source_url" in issue for issue in critique["issues"])


def test_eval_critique_passes_with_cited_news() -> None:
    state = {
        "cryptocurrency": "ETH",
        "period": "7d",
        "facts": [
            Fact(
                source_type=SourceType.NEWS,
                title="Cited headline",
                summary="Something happened",
                source_url="https://example.com/eth/1",
            ).model_dump(mode="json")
        ],
        "analysis": AnalysisDraft(
            brief="Cautious brief.",
            gaps=["Need more flow data"],
            risks_and_catalysts=["Macro"],
            watchlist=["ETF flows"],
        ).model_dump(mode="json"),
    }
    result = critique_node(state)  # type: ignore[arg-type]
    assert result["critique"]["passed"] is True

"""Unit tests for planner/analysis chains (mocked LLM)."""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from crypto_intel.chains.analysis import analyze_evidence
from crypto_intel.chains.planner import plan_collection
from crypto_intel.domain.models import AnalysisDraft, Fact, SourceType


class _FakeChatModel:
    """Minimal stand-in: planner path uses the model as a Runnable."""

    def __init__(self, response: AIMessage) -> None:
        self._response = response

    def invoke(self, input: object, config: object | None = None) -> AIMessage:
        return self._response

    def __or__(self, other: object) -> object:  # pragma: no cover
        raise TypeError("FakeChatModel is right-hand only in tests")


class _FakeStructuredModel:
    """Minimal stand-in: analysis path calls with_structured_output()."""

    def __init__(self, draft: AnalysisDraft) -> None:
        self._draft = draft

    def with_structured_output(
        self,
        schema: object,
        method: str = "json_schema",
    ) -> RunnableLambda:
        draft = self._draft
        return RunnableLambda(lambda _: draft)


def test_plan_collection_returns_plan_text() -> None:
    fake = RunnableLambda(
        lambda _: AIMessage(content="- fetch_news for BTC\n- get_market_snapshot for BTC"),
    )
    plan = plan_collection(
        cryptocurrency="BTC",
        period="7d",
        question=None,
        model=fake,  # type: ignore[arg-type]
    )
    assert "fetch_news" in plan
    assert "get_market_snapshot" in plan


def test_analyze_evidence_returns_analysis_draft() -> None:
    draft = AnalysisDraft(
        brief="Evidence is thin; keep stance cautious.",
        gaps=["Only mock headlines available"],
        risks_and_catalysts=["Macro uncertainty"],
        watchlist=["ETF net flows"],
    )
    result = analyze_evidence(
        cryptocurrency="BTC",
        period="7d",
        facts=[
            Fact(
                source_type=SourceType.NEWS,
                title="Mock headline",
                summary="Thin coverage",
            ),
        ],
        question="ETF flows",
        model=_FakeStructuredModel(draft),  # type: ignore[arg-type]
    )
    assert result.brief == draft.brief
    assert result.gaps == ["Only mock headlines available"]
    assert "ETF net flows" in result.watchlist
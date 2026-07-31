"""Unit tests for prompt templates (no LLM calls)."""

from __future__ import annotations

from crypto_intel.domain.models import Fact, SourceType
from crypto_intel.prompts.analysis import build_analysis_prompt, format_evidence
from crypto_intel.prompts.planner import build_planner_prompt, normalize_question


def test_normalize_question_handles_none_and_blank() -> None:
    assert normalize_question(None) == "(no specific focus)"
    assert normalize_question("") == "(no specific focus)"
    assert normalize_question("   ") == "(no specific focus)"
    assert normalize_question("ETF flows") == "ETF flows"


def test_planner_prompt_renders_variables() -> None:
    prompt = build_planner_prompt()
    messages = prompt.format_messages(
        cryptocurrency="BTC",
        period="7d",
        question=normalize_question(None),
        tools_description="- get_market_snapshot: price\n- fetch_news: headlines",
    )
    system_text = str(messages[0].content)
    human_text = str(messages[1].content)

    assert "get_market_snapshot" in system_text
    assert "fetch_news" in system_text
    assert "Cryptocurrency: BTC" in human_text
    assert "Period: 7d" in human_text
    assert "(no specific focus)" in human_text


def test_analysis_prompt_renders_evidence() -> None:
    facts = [
        Fact(
            source_type=SourceType.NEWS,
            title="ETF flows mixed",
            summary="Inflows slowed week over week",
            source_url="https://mock.news.example/btc/etf",
        ),
    ]
    prompt = build_analysis_prompt()
    messages = prompt.format_messages(
        cryptocurrency="BTC",
        period="7d",
        question=normalize_question("ETF flows"),
        evidence=format_evidence(facts),
    )
    human_text = str(messages[1].content)

    assert "Cryptocurrency: BTC" in human_text
    assert "ETF flows" in human_text
    assert "ETF flows mixed" in human_text
    assert "https://mock.news.example/btc/etf" in human_text


def test_format_evidence_empty() -> None:
    assert format_evidence([]) == "(no evidence provided)"
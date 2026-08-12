"""Analysis chain: evidence → AnalysisDraft via structured LLM output."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from crypto_intel.domain.language import language_instruction
from crypto_intel.domain.models import AnalysisDraft, Fact
from crypto_intel.llm.client import build_xai_chat_model
from crypto_intel.prompts.analysis import build_analysis_prompt, format_evidence
from crypto_intel.prompts.planner import normalize_question


def build_analysis_chain(*, model: BaseChatModel | None = None) -> Runnable:
    """Compose analysis prompt with structured AnalysisDraft output."""
    chat_model = model or build_xai_chat_model()
    structured_model = chat_model.with_structured_output(
        AnalysisDraft,
        method="json_schema",
    )
    return build_analysis_prompt() | structured_model


def analyze_evidence(
    *,
    cryptocurrency: str,
    period: str,
    facts: list[Fact],
    question: str | None = None,
    model: BaseChatModel | None = None,
) -> AnalysisDraft:
    """Run the analysis chain and return a validated AnalysisDraft."""
    chain = build_analysis_chain(model=model)
    result = chain.invoke(
        {
            "cryptocurrency": cryptocurrency,
            "period": period,
            "question": normalize_question(question),
            "evidence": format_evidence(facts),
            "language_rule": language_instruction(question),
        },
    )
    if not isinstance(result, AnalysisDraft):
        raise TypeError(f"Expected AnalysisDraft, got {type(result)!r}")
    return result
"""Generate a DecisionCard from collected facts via structured LLM output."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from crypto_intel.domain.language import language_instruction
from crypto_intel.domain.models import DecisionCard, Fact
from crypto_intel.llm.client import build_xai_chat_model

_MAX_ATTEMPTS = 2


class DecisionCardGenerationError(RuntimeError):
    """Raised when structured DecisionCard generation fails after retries."""


def generate_decision_card(
    *,
    cryptocurrency: str,
    period: str,
    facts: list[Fact],
    question: str | None = None,
    model: BaseChatModel | None = None,
) -> DecisionCard:
    chat_model = model or build_xai_chat_model()
    structured_model = chat_model.with_structured_output(
        DecisionCard,
        method="json_schema",
    )
    messages = _build_messages(
        cryptocurrency=cryptocurrency,
        period=period,
        facts=facts,
        question=question,
    )

    last_error: Exception | None = None
    for _ in range(_MAX_ATTEMPTS):
        try:
            result = structured_model.invoke(messages)
            if not isinstance(result, DecisionCard):
                raise TypeError(f"Expected DecisionCard, got {type(result)!r}")
            return result
        except Exception as exc:
            last_error = exc

    raise DecisionCardGenerationError(
        f"Failed to generate DecisionCard for {cryptocurrency} ({period}) "
        f"after {_MAX_ATTEMPTS} attempts"
    ) from last_error


def _build_messages(
    *,
    cryptocurrency: str,
    period: str,
    facts: list[Fact],
    question: str | None,
) -> list[SystemMessage | HumanMessage]:
    evidence_block = _format_facts(facts)
    lang = language_instruction(question)
    return [
        SystemMessage(
            content=(
                "You are a crypto research analyst. "
                "Produce a cautious DecisionCard based only on the supplied evidence. "
                "Do not predict prices. "
                "Choose stance from: accumulate, hold, reduce, avoid. "
                "If the focus says the user already holds a position, prefer hold/reduce/avoid "
                "guidance for an existing position; otherwise treat as whether to enter. "
                "confidence must be between 0 and 1. "
                "invalidation must list concrete events that would change the stance. "
                f"{lang}"
            ),
        ),
        HumanMessage(
            content=(
                f"Cryptocurrency: {cryptocurrency}\n"
                f"Period: {period}\n"
                f"Focus: {question or '(none)'}\n\n"
                f"Evidence:\n{evidence_block}\n\n"
                "Return a DecisionCard."
            ),
        ),
    ]


def _format_facts(facts: list[Fact]) -> str:
    if not facts:
        return "(no evidence provided)"

    lines: list[str] = []
    for index, fact in enumerate(facts, start=1):
        source_url = str(fact.source_url) if fact.source_url is not None else "n/a"
        lines.append(
            f"{index}. [{fact.source_type.value}] {fact.title}\n"
            f"   summary: {fact.summary}\n"
            f"   source_url: {source_url}"
        )
    return "\n".join(lines)

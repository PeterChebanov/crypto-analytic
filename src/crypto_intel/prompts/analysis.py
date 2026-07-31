"""Analysis prompts: turn collected evidence into a research brief draft."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from crypto_intel.domain.models import Fact
from crypto_intel.prompts.planner import normalize_question

_ANALYSIS_SYSTEM = """You are a crypto research analyst writing a cautious research brief.

Your job is to synthesize the supplied evidence into a readable brief for a human decision-maker.
You do NOT predict future prices or give trade signals beyond what the evidence supports.

Rules:
- Use ONLY the supplied evidence. Do not invent facts, headlines, or URLs.
- If evidence is thin or conflicting, say so in gaps.
- risks_and_catalysts: concrete headwinds and tailwinds grounded in the evidence.
- watchlist: specific metrics, events, or sources to monitor next.
- brief: 2–5 sentences in plain language; cautious tone.

Output JSON with exactly these keys:
- brief: string
- gaps: string[]
- risks_and_catalysts: string[]
- watchlist: string[]

Return JSON only. No markdown fences, no extra keys.
"""

_ANALYSIS_HUMAN = """Cryptocurrency: {cryptocurrency}
Period: {period}
Focus question: {question}

Evidence:
{evidence}

Write the analysis JSON."""


def build_analysis_prompt() -> ChatPromptTemplate:
    """Return the production analysis ChatPromptTemplate."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", _ANALYSIS_SYSTEM),
            ("human", _ANALYSIS_HUMAN),
        ],
    )

def format_evidence(facts: list[Fact]) -> str:
    """Render facts for prompt injection (mirrors decision_card formatting)."""
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
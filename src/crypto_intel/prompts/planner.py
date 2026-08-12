"""Planner prompts: turn a research request into a collection plan."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


_PLANNER_SYSTEM = """You are a crypto research planner.
Your job is to produce a short, actionable plan to gather evidence for a research brief.
You do NOT analyze markets, give investment advice, or predict prices.
Available tools (collectors execute these — you only plan which evidence to gather):
{tools_description}
Rules:
- Plan only steps that map to available tools or explicit gap-filling research.
- For a general request, include both news and market evidence unless the focus question is narrowly scoped.
- Keep the plan to 3–6 bullet steps.
- Each step must be concrete: what to fetch and what to look for.
- Output a plain-text bullet list only. One step per line, each line starting with "- ".
- Do not invent tool names that are not listed above.
- {language_rule}
"""

_PLANNER_HUMAN = """Cryptocurrency: {cryptocurrency}
Period: {period}
Focus question: {question}
Write the collection plan."""


def build_planner_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", _PLANNER_SYSTEM),
            ("human", _PLANNER_HUMAN)
        ],
    )
    
def normalize_question(question: str | None) -> str:
    """Map optional user focus to a stable prompt value"""
    
    if question is None:
        return "(no specific focus)"
    stripped = question.strip()
    return stripped if stripped else "(no specific focus)"
 
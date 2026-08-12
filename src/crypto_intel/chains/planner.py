"""Planner chain: research request → collection plan text."""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from crypto_intel.domain.language import language_instruction
from crypto_intel.llm.client import build_xai_chat_model
from crypto_intel.prompts.planner import build_planner_prompt, normalize_question
from crypto_intel.tools.registry import format_tools_description


def build_planner_chain(*, model: BaseChatModel | None = None) -> Runnable:
    """Compose planner prompt with a chat model (LCEL)"""
    chat_model = model or build_xai_chat_model()
    return build_planner_prompt() | chat_model


def plan_collection(
    *,
    cryptocurrency: str,
    period: str,
    question: str | None = None,
    model: BaseChatModel | None = None
) -> str:
    """Run the planner chain and return the collection plan as plain text"""
    chain = build_planner_chain(model=model)
    response = chain.invoke(
        {
            "cryptocurrency": cryptocurrency,
            "period": period,
            "question": normalize_question(question),
            "tools_description": format_tools_description(),
            "language_rule": language_instruction(question),
        },
    )
    if not isinstance(response, AIMessage):
        raise TypeError(f"Expected AIMessage, got {type(response)!r}")
    content = response.content
    if isinstance(content, str):
        return content
    return str(content)
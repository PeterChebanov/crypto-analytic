"""Allowlisted tool execution: LLM proposes, Python executes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool


class UnknownToolError(ValueError):
    """Raised when the model requests a tool that is not allowlisted."""


class ToolExecutor:
    """Execute tool calls only for an explicit allowlist."""

    def __init__(self, tools: Sequence[BaseTool]) -> None:
        self._tools: dict[str, BaseTool] = {tool.name: tool for tool in tools}
        if not self._tools:
            raise ValueError("ToolExecutor requires at least one allowlisted tool")

    @property
    def tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def execute(self, name: str, args: dict[str, Any]) -> str:
        """Run one allowlisted tool. Rejects unknown names."""
        tool = self._tools.get(name)
        if tool is None:
            known = ", ".join(sorted(self._tools))
            raise UnknownToolError(f"Unknown tool {name!r}. Allowlisted: {known}")
        result = tool.invoke(args)
        return result if isinstance(result, str) else str(result)


def run_tool_loop(
    *,
    model: BaseChatModel,
    executor: ToolExecutor,
    user_message: str,
    system_message: str | None = None,
    max_rounds: int = 3,
) -> AIMessage:
    """Bind tools, invoke, execute tool_calls, repeat until final answer or max_rounds.

    Returns the last AIMessage (final text answer, or last proposal if rounds exhausted).
    """
    if max_rounds < 1:
        raise ValueError("max_rounds must be >= 1")

    model_with_tools = model.bind_tools(executor.tools)
    messages: list[BaseMessage] = []
    if system_message:
        messages.append(SystemMessage(content=system_message))
    messages.append(HumanMessage(content=user_message))

    last_ai: AIMessage | None = None
    for _ in range(max_rounds):
        response = model_with_tools.invoke(messages)
        if not isinstance(response, AIMessage):
            raise TypeError(f"Expected AIMessage, got {type(response)!r}")
        last_ai = response
        messages.append(response)

        if not response.tool_calls:
            return response

        for call in response.tool_calls:
            name = call["name"]
            args = call["args"]
            call_id = call["id"]
            try:
                content = executor.execute(name, args)
            except UnknownToolError as exc:
                content = f"error: {exc}"
            messages.append(
                ToolMessage(content=content, tool_call_id=call_id, name=name)
            )

    if last_ai is None:
        raise RuntimeError("tool loop produced no AIMessage")
    return last_ai
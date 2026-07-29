"""Unit tests for allowlisted tool execution."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from crypto_intel.tools.executor import ToolExecutor, UnknownToolError, run_tool_loop
from crypto_intel.tools.market import get_market_snapshot


def test_executor_runs_allowlisted_tool() -> None:
    executor = ToolExecutor([get_market_snapshot])
    result = executor.execute("get_market_snapshot", {"cryptocurrency": "btc"})
    assert "BTC" in result
    assert "mock_market" in result


def test_executor_rejects_unknown_tool() -> None:
    executor = ToolExecutor([get_market_snapshot])
    with pytest.raises(UnknownToolError):
        executor.execute("drop_database", {})


def test_run_tool_loop_executes_then_returns_final_answer() -> None:
    first = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_market_snapshot",
                "args": {"cryptocurrency": "BTC"},
                "id": "call-1",
                "type": "tool_call",
            }
        ],
    )
    final = AIMessage(content="BTC is around 65000 USD (mock).")

    bound = MagicMock()
    bound.invoke.side_effect = [first, final]

    model = MagicMock()
    model.bind_tools.return_value = bound

    executor = ToolExecutor([get_market_snapshot])
    result = run_tool_loop(
        model=model,
        executor=executor,
        user_message="What is the BTC snapshot?",
    )

    assert result.content == "BTC is around 65000 USD (mock)."
    assert bound.invoke.call_count == 2
    second_messages = bound.invoke.call_args_list[1].args[0]
    assert any(isinstance(m, ToolMessage) for m in second_messages)


def test_run_tool_loop_unknown_tool_feeds_error_observation() -> None:
    first = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "not_allowed",
                "args": {},
                "id": "call-x",
                "type": "tool_call",
            }
        ],
    )
    final = AIMessage(content="I could not use that tool.")

    bound = MagicMock()
    bound.invoke.side_effect = [first, final]

    model = MagicMock()
    model.bind_tools.return_value = bound

    result = run_tool_loop(
        model=model,
        executor=ToolExecutor([get_market_snapshot]),
        user_message="hack me",
    )

    assert "could not" in result.content.lower() or result is final
    second_messages = bound.invoke.call_args_list[1].args[0]
    assert any(
        isinstance(m, ToolMessage) and "Unknown tool" in m.content
        for m in second_messages
    )
"""Unit tests for the collector tools registry."""

from __future__ import annotations

import pytest

from crypto_intel.tools.registry import (
    UnknownRegistryToolError,
    build_default_executor,
    format_tools_description,
    get_default_tools,
    get_tool,
)


def test_get_default_tools_contains_market_and_news() -> None:
    names = {tool.name for tool in get_default_tools()}
    assert names == {"get_market_snapshot", "fetch_news"}


def test_get_default_tools_returns_a_copy() -> None:
    tools = get_default_tools()
    tools.clear()
    assert len(get_default_tools()) == 2


def test_get_tool_returns_registered_tool() -> None:
    tool = get_tool("fetch_news")
    assert tool.name == "fetch_news"


def test_get_tool_rejects_unknown_name() -> None:
    with pytest.raises(UnknownRegistryToolError):
        get_tool("drop_database")


def test_format_tools_description_lists_names() -> None:
    text = format_tools_description()
    assert "- get_market_snapshot:" in text
    assert "- fetch_news:" in text


def test_build_default_executor_runs_news_tool() -> None:
    executor = build_default_executor()
    result = executor.execute(
        "fetch_news",
        {"cryptocurrency": "ETH", "limit": 1},
    )
    assert "ETH" in result
    assert "source_url=" in result
    assert "mock_news" in result
    
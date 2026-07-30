"""Central registry of production collector tools."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.tools import BaseTool

from crypto_intel.tools.executor import ToolExecutor
from crypto_intel.tools.market import get_market_snapshot
from crypto_intel.tools.news import fetch_news

_DEFAULT_TOOLS: tuple[BaseTool, ...] = (
    get_market_snapshot,
    fetch_news,
)


class UnknownRegistryToolError(KeyError):
    """Raises when a tool name not registered"""
    

def get_default_tools() -> list[BaseTool]:
    """Return all production collector tools (copy - safe to mutate by callers)"""
    return list(_DEFAULT_TOOLS)


def get_tool(name: str) -> BaseTool:
    """Look up a registered tool by name"""
    for tool in _DEFAULT_TOOLS:
        if tool.name == name:
            return tool
    known = ", ".join(sorted(t.name for t in _DEFAULT_TOOLS))
    raise UnknownRegistryToolError(
        f"Unknown took {name!r}. Registered: {known}"
    )
    

def format_tools_description(tools: Sequence[BaseTool] | None = None) -> str:
    """Format tool names and descriptions for the planner prompt"""
    selected = list(tools) if tools is not None else get_default_tools()
    lines: list[str] = []
    for tool in selected:
        description = (tool.description or "").strip()
        first_line = description.split("\n", maxsplit=1)[0] if description else "(no description)"
        lines.append(f"- {tool.name}: {first_line}")
    return "\n".join(lines)


def build_default_executor() -> ToolExecutor:
    """Build a ToolExecutor wired to all default collector tools"""
    return ToolExecutor(get_default_tools())

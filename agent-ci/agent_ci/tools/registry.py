"""Registry for tool implementations."""

from __future__ import annotations

from agent_ci.tools.base import BaseTool
from agent_ci.tools.mock_tools import DEFAULT_MOCK_TOOLS


class ToolRegistry:
    """Lookup table for available tools."""

    def __init__(self, tools: list[BaseTool] | None = None):
        self._tools: dict[str, BaseTool] = {}
        for tool in tools or DEFAULT_MOCK_TOOLS:
            self.register(tool)

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return sorted(self._tools)

    def has(self, name: str) -> bool:
        return name in self._tools


_default_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry

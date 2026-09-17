"""Execute tools and produce structured call records."""

from __future__ import annotations

from typing import Any

from agent_ci.tools.registry import ToolRegistry, get_tool_registry
from agent_ci.tools.types import STATUS_FAILED, STATUS_NOT_EXECUTED, STATUS_SUCCESS, ToolCallRecord


class ToolExecutor:
    """Run registered tools and return normalized call records."""

    def __init__(self, registry: ToolRegistry | None = None):
        self.registry = registry or get_tool_registry()

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> ToolCallRecord:
        arguments = dict(arguments or {})
        tool = self.registry.get(tool_name)
        if tool is None:
            return ToolCallRecord(
                tool=tool_name,
                arguments=arguments,
                result={"error": f"Unknown tool: {tool_name}"},
                status=STATUS_FAILED,
            )

        outcome = tool.execute(arguments)
        if outcome.success:
            return ToolCallRecord(
                tool=tool_name,
                arguments=arguments,
                result=outcome.data,
                status=STATUS_SUCCESS,
            )
        return ToolCallRecord(
            tool=tool_name,
            arguments=arguments,
            result={"error": outcome.error, **outcome.data},
            status=STATUS_FAILED,
        )

    def execute_many(self, calls: list[dict[str, Any]]) -> list[ToolCallRecord]:
        records: list[ToolCallRecord] = []
        for call in calls:
            records.append(self.execute(call.get("tool", ""), call.get("arguments")))
        return records


def get_tool_executor(registry: ToolRegistry | None = None) -> ToolExecutor:
    return ToolExecutor(registry=registry)

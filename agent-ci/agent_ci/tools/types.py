"""Shared types for agent tool execution and evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_NOT_EXECUTED = "not_executed"


@dataclass
class ToolResult:
    """Outcome returned by a tool implementation."""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolCallRecord:
    """One tool invocation tracked during an agent rollout."""

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    status: str = STATUS_NOT_EXECUTED

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ToolCallRecord:
        return cls(
            tool=str(payload.get("tool", "")),
            arguments=dict(payload.get("arguments") or {}),
            result=payload.get("result"),
            status=str(payload.get("status", STATUS_NOT_EXECUTED)),
        )


def normalize_tool_calls(raw: list[dict[str, Any]] | None) -> list[ToolCallRecord]:
    if not raw:
        return []
    return [ToolCallRecord.from_dict(item) for item in raw]

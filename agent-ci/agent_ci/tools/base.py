"""Base tool interface for real or mock tool implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agent_ci.tools.types import ToolResult


class BaseTool(ABC):
    """Interface for a callable agent tool."""

    name: str
    description: str

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Run the tool with the provided arguments."""

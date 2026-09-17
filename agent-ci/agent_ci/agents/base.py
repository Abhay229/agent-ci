"""Base agent interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_ci.types import AgentConfig, AgentResponse


class BaseAgent(ABC):
    """Interface for any agent the evaluation engine can run."""

    def __init__(self, config: AgentConfig):
        self.config = config

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def role(self) -> str:
        return self.config.role

    @abstractmethod
    def run(self, test_case: dict) -> AgentResponse:
        """Execute one test case and return a structured response."""

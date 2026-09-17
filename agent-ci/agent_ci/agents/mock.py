"""Mock agent — deterministic responses, no API key required."""

from __future__ import annotations

from agent_ci.agents.base import BaseAgent
from agent_ci.agents.mock_data import MOCK_KEY_ALIASES, MOCK_RESPONSES
from agent_ci.agents.rag_mixin import RAGMixin
from agent_ci.rag.context import chunks_as_dicts
from agent_ci.types import AgentResponse


class MockAgent(RAGMixin, BaseAgent):
    """Returns pre-authored responses keyed by test id and mock profile."""

    def run(self, test_case: dict) -> AgentResponse:
        test_id = test_case["id"]
        mock_key = self.config.config.get("mock_key", self.config.role)
        profile = MOCK_KEY_ALIASES.get(mock_key, mock_key)

        try:
            answer = MOCK_RESPONSES[test_id][profile]
        except KeyError as exc:
            raise KeyError(
                f"No mock response for test_id={test_id!r}, profile={profile!r}"
            ) from exc

        retrieved = None
        if self._should_use_rag():
            chunks = self._retrieve_context(test_case["user_message"])
            retrieved = chunks_as_dicts(chunks)

        return AgentResponse(
            answer=answer,
            model="mock",
            provider="mock",
            latency_ms=0.0,
            retrieved_context=retrieved,
            metadata={
                "mock_key": mock_key,
                "profile": profile,
                "mode": "mock",
                "rag_enabled": self._should_use_rag(),
            },
        )

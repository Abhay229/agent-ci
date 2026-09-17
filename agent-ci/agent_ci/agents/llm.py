"""Live LLM agent backed by a provider."""

from __future__ import annotations

from agent_ci.agents.base import BaseAgent
from agent_ci.agents.providers.base import BaseProvider
from agent_ci.dataset import COMPANY_POLICY
from agent_ci.types import AgentResponse


class LLMAgent(BaseAgent):
    """Calls a real LLM through a provider abstraction."""

    def __init__(self, config, provider: BaseProvider):
        super().__init__(config)
        self.provider = provider

    def _build_system_prompt(self) -> str:
        prompt = self.config.system_prompt
        if self.config.config.get("inject_policy"):
            prompt = prompt.format(policy=COMPANY_POLICY)
        return prompt

    def run(self, test_case: dict) -> AgentResponse:
        if not self.config.model:
            raise ValueError(f"Agent {self.name!r} requires a model for live mode")

        result = self.provider.complete(
            system_prompt=self._build_system_prompt(),
            user_message=test_case["user_message"],
            model=self.config.model,
            temperature=float(self.config.config.get("temperature", 0.2)),
            max_tokens=int(self.config.config.get("max_tokens", 200)),
        )

        return AgentResponse(
            answer=result.content,
            model=result.model,
            provider=result.provider,
            latency_ms=result.latency_ms,
            token_usage=result.token_usage,
            retrieved_context=None,
            tool_calls=None,
            metadata={"mode": "live", **result.metadata},
        )

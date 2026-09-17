"""Live LLM agent backed by a provider."""

from __future__ import annotations

from agent_ci.agents.base import BaseAgent
from agent_ci.agents.rag_mixin import RAGMixin
from agent_ci.agents.providers.base import BaseProvider
from agent_ci.conversation import (
    build_provider_messages,
    build_transcript,
    get_conversation,
    get_primary_user_message,
    get_test_type,
)
from agent_ci.dataset import COMPANY_POLICY
from agent_ci.types import AgentResponse


class LLMAgent(RAGMixin, BaseAgent):
    """Calls a real LLM through a provider abstraction."""

    def __init__(self, config, provider: BaseProvider):
        super().__init__(config)
        self.provider = provider

    def _build_system_prompt(self, user_message: str | None = None) -> str:
        prompt = self.config.system_prompt

        if self._should_use_rag() and user_message:
            chunks = self._retrieve_context(user_message)
            return self._build_prompt_with_context(prompt, chunks)

        if self.config.config.get("inject_policy"):
            prompt = prompt.format(policy=COMPANY_POLICY)

        return prompt

    def run(self, test_case: dict) -> AgentResponse:
        if not self.config.model:
            raise ValueError(f"Agent {self.name!r} requires a model for live mode")

        conversation = get_conversation(test_case)
        primary_message = get_primary_user_message(test_case)
        retrieved = self._retrieve_context(primary_message) if self._should_use_rag() else []
        system_prompt = self._build_system_prompt(primary_message)

        result = self.provider.complete(
            system_prompt=system_prompt,
            user_message=primary_message,
            model=self.config.model,
            temperature=float(self.config.config.get("temperature", 0.2)),
            max_tokens=int(self.config.config.get("max_tokens", 200)),
            messages=build_provider_messages(conversation),
        )

        from agent_ci.rag.context import chunks_as_dicts

        return AgentResponse(
            answer=result.content,
            model=result.model,
            provider=result.provider,
            latency_ms=result.latency_ms,
            token_usage=result.token_usage,
            retrieved_context=chunks_as_dicts(retrieved) if retrieved else None,
            tool_calls=None,
            conversation_transcript=build_transcript(conversation, result.content),
            metadata={
                "mode": "live",
                "rag_enabled": self._should_use_rag(),
                "test_type": get_test_type(test_case),
                **result.metadata,
            },
        )

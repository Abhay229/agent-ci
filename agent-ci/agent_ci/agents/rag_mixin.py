"""RAG support mixin for agents."""

from __future__ import annotations

from agent_ci.rag.context import chunks_as_dicts, format_context, retrieve_policy_context
from agent_ci.rag.types import RetrievedChunk


class RAGMixin:
    """Retrieve policy context when RAG is enabled in agent config."""

    def _should_use_rag(self) -> bool:
        return bool(self.config.config.get("use_rag"))

    def _top_k(self) -> int | None:
        value = self.config.config.get("top_k")
        return int(value) if value is not None else None

    def _retrieve_context(self, user_message: str) -> list[RetrievedChunk]:
        return retrieve_policy_context(user_message, top_k=self._top_k())

    def _build_prompt_with_context(self, template: str, chunks: list[RetrievedChunk]) -> str:
        context = format_context(chunks)
        if "{context}" in template:
            return template.format(context=context)
        if "{policy}" in template:
            return template.format(policy=context)
        return f"{template}\n\nRetrieved policy context:\n{context}"

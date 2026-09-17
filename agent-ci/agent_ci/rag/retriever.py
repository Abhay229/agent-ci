"""Policy retriever — ChromaDB with keyword fallback."""

from __future__ import annotations

import os

from agent_ci.rag.config import RAGConfig, load_rag_config
from agent_ci.rag.ingest import ensure_index
from agent_ci.rag.mock_retriever import mock_retrieve
from agent_ci.rag.types import RetrievedChunk

_retriever_cache: dict[str, "PolicyRetriever"] = {}


class PolicyRetriever:
    """Retrieve the most relevant policy chunks for a user question."""

    def __init__(self, config: RAGConfig | None = None):
        self.config = config or load_rag_config()

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        k = top_k if top_k is not None else self.config.top_k
        use_mock = os.environ.get("AGENT_CI_MOCK_RAG") == "1"

        if use_mock:
            return mock_retrieve(query, self.config, top_k=k)

        try:
            store = ensure_index(config=self.config)
            if store.count() == 0:
                return mock_retrieve(query, self.config, top_k=k)
            return store.query(query, top_k=k)
        except Exception:
            return mock_retrieve(query, self.config, top_k=k)

    @staticmethod
    def format_for_prompt(chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "No relevant policy context retrieved."
        parts = []
        for chunk in chunks:
            parts.append(
                f"[{chunk.section}] (source: {chunk.document}, chunk: {chunk.chunk_id})\n{chunk.text}"
            )
        return "\n\n".join(parts)

    @staticmethod
    def chunks_to_metadata(chunks: list[RetrievedChunk]) -> list[dict]:
        return [chunk.to_dict() for chunk in chunks]


def get_retriever(config_path: str | None = None) -> PolicyRetriever:
    key = config_path or "default"
    if key not in _retriever_cache:
        config = load_rag_config(config_path)
        _retriever_cache[key] = PolicyRetriever(config)
    return _retriever_cache[key]

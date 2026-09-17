"""Keyword-based retriever fallback (no API key, no Chroma required)."""

from __future__ import annotations

from agent_ci.rag.chunker import chunk_policy
from agent_ci.rag.config import RAGConfig
from agent_ci.rag.types import PolicyChunk, RetrievedChunk

QUERY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "refunds": ("refund", "money back", "14 days", "discount", "renewal"),
    "cancellations": ("cancel", "cancellation", "billing period", "fee"),
    "data_export": ("export", "csv", "json", "download data"),
    "data_deletion": ("delete", "deletion", "close account", "30 days"),
    "enterprise_features": ("sso", "audit log", "enterprise", "pro plan"),
    "phone_support": ("phone", "call", "talk to a human"),
    "uptime_slas": ("uptime", "sla", "guarantee", "availability"),
}


def mock_retrieve(query: str, config: RAGConfig, top_k: int | None = None) -> list[RetrievedChunk]:
    """Score chunks by keyword overlap with the user query."""
    k = top_k if top_k is not None else config.top_k
    chunks = chunk_policy(config.document_name)
    query_lower = query.lower()

    scored: list[tuple[float, PolicyChunk]] = []
    for chunk in chunks:
        keywords = QUERY_KEYWORDS.get(chunk.chunk_id, ())
        score = 0.0
        for token in chunk.section.lower().split() + list(keywords):
            if len(token) > 2 and token in query_lower:
                score += 2.0
        for word in query_lower.replace("?", "").split():
            if len(word) > 3 and word in chunk.text.lower():
                score += 1.0
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored and chunks:
        scored = [(0.1, chunks[0])]

    retrieved: list[RetrievedChunk] = []
    for rank, (score, chunk) in enumerate(scored[:k]):
        retrieved.append(
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document=chunk.document,
                section=chunk.section,
                text=chunk.text,
                score=round(min(1.0, score / 5.0), 3),
                metadata={"rank": rank, "retriever": "mock_keyword"},
            )
        )
    return retrieved

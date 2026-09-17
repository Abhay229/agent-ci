"""Document ingestion pipeline: load → chunk → embed → store."""

from __future__ import annotations

from agent_ci.rag.chunker import chunk_policy
from agent_ci.rag.config import RAGConfig, load_rag_config
from agent_ci.rag.store import PolicyVectorStore, get_vector_store


def ingest_policy(config_path: str | None = None, *, reset: bool = False) -> int:
    """Ingest the company policy into the local vector store."""
    config = load_rag_config(config_path)
    store = get_vector_store(config_path)

    if reset:
        store.clear()
        store = get_vector_store(config_path)

    chunks = chunk_policy(config.document_name)
    return store.upsert_chunks(chunks)


def ensure_index(config_path: str | None = None, config: RAGConfig | None = None) -> PolicyVectorStore:
    """Ensure the vector index exists and contains policy chunks."""
    if config is None:
        config = load_rag_config(config_path)
    store = get_vector_store(config_path)
    if store.count() == 0:
        chunks = chunk_policy(config.document_name)
        store.upsert_chunks(chunks)
    return store

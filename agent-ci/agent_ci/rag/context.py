"""Shared helpers for agent RAG integration."""

from __future__ import annotations

from agent_ci.rag.config import load_rag_config
from agent_ci.rag.retriever import get_retriever
from agent_ci.rag.types import RetrievedChunk


def retrieve_policy_context(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    retriever = get_retriever()
    return retriever.retrieve(query, top_k=top_k)


def format_context(chunks: list[RetrievedChunk]) -> str:
    return get_retriever().format_for_prompt(chunks)


def chunks_as_dicts(chunks: list[RetrievedChunk]) -> list[dict]:
    return get_retriever().chunks_to_metadata(chunks)

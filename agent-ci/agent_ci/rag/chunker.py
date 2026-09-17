"""Chunking utilities for policy documents."""

from __future__ import annotations

from agent_ci.rag.loader import load_company_policy, policy_to_chunks
from agent_ci.rag.types import PolicyChunk


def chunk_policy(document_name: str) -> list[PolicyChunk]:
    """Load and chunk the company policy into meaningful sections."""
    policy_text = load_company_policy(document_name)
    return policy_to_chunks(policy_text, document_name)

"""Document loader for the company policy."""

from __future__ import annotations

from agent_ci.dataset import COMPANY_POLICY
from agent_ci.rag.types import PolicyChunk


def load_company_policy(document_name: str) -> str:
    """Return the canonical company policy text."""
    return COMPANY_POLICY.strip()


def policy_to_chunks(policy_text: str, document_name: str) -> list[PolicyChunk]:
    """Split the policy into one chunk per bullet section."""
    chunks: list[PolicyChunk] = []
    for line in policy_text.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue

        content = line[2:].strip()
        if ":" in content:
            section, body = content.split(":", 1)
            section = section.strip()
            text = body.strip()
        else:
            section = _section_from_sentence(content)
            text = content

        chunk_id = _make_chunk_id(section)
        chunks.append(
            PolicyChunk(
                chunk_id=chunk_id,
                document=document_name,
                section=section,
                text=text,
            )
        )
    return chunks


def _section_from_sentence(content: str) -> str:
    first_sentence = content.split(".")[0].strip()
    if len(first_sentence) > 60:
        return first_sentence[:60]
    return first_sentence


def _make_chunk_id(section: str) -> str:
    slug = section.lower()
    for ch in " >/()":
        slug = slug.replace(ch, "_")
    slug = slug.replace("'", "")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")

"""Document loader for the company policy."""

from __future__ import annotations

from agent_ci.dataset import COMPANY_POLICY
from agent_ci.rag.types import PolicyChunk

SECTION_OVERRIDES: tuple[tuple[str, str, str], ...] = (
    ("Enterprise features", "enterprise_features", "Enterprise features (SSO, audit logs)"),
    ("We do NOT offer phone support", "phone_support", "Phone support"),
    ("We do NOT guarantee specific uptime SLAs", "uptime_slas", "Uptime SLAs"),
)


def load_company_policy(document_name: str) -> str:
    """Return the canonical company policy text."""
    _ = document_name
    return COMPANY_POLICY.strip()


def policy_to_chunks(policy_text: str, document_name: str) -> list[PolicyChunk]:
    """Split the policy into one chunk per bullet section."""
    chunks: list[PolicyChunk] = []
    for line in policy_text.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue

        content = line[2:].strip()
        section, chunk_id, text = _parse_policy_line(content)
        chunks.append(
            PolicyChunk(
                chunk_id=chunk_id,
                document=document_name,
                section=section,
                text=text,
            )
        )
    return chunks


def _parse_policy_line(content: str) -> tuple[str, str, str]:
    for prefix, chunk_id, section in SECTION_OVERRIDES:
        if content.startswith(prefix):
            return section, chunk_id, content

    if ":" in content:
        section, body = content.split(":", 1)
        section = section.strip()
        text = body.strip()
        return section, _make_chunk_id(section), text

    section = _section_from_sentence(content)
    return section, _make_chunk_id(section), content


def _section_from_sentence(content: str) -> str:
    first_sentence = content.split(".")[0].strip()
    if len(first_sentence) > 60:
        return first_sentence[:60]
    return first_sentence


def _make_chunk_id(section: str) -> str:
    slug = section.lower()
    for ch in " >/()'":
        slug = slug.replace(ch, "_")
    slug = slug.replace("'", "")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")

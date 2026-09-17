"""Shared types for agent rollouts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AgentResponse:
    """Structured representation of an agent rollout."""

    answer: str
    model: str | None = None
    provider: str | None = None
    latency_ms: float | None = None
    token_usage: dict[str, int] | None = None
    retrieved_context: list[dict[str, Any]] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    conversation_transcript: list[dict[str, str]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentConfig:
    """Configuration for a single agent (baseline or candidate)."""

    name: str
    role: str
    mode: str = "auto"
    provider: str = "mock"
    model: str | None = None
    system_prompt: str = ""
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, role: str, data: dict[str, Any]) -> AgentConfig:
        return cls(
            name=data.get("name", role),
            role=role,
            mode=data.get("mode", "auto"),
            provider=data.get("provider", "mock"),
            model=data.get("model"),
            system_prompt=data.get("system_prompt", ""),
            config=data.get("config", {}),
        )

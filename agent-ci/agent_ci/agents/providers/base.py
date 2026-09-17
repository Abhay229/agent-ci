"""LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResult:
    """Raw result from an LLM provider call."""

    content: str
    model: str
    provider: str
    latency_ms: float
    token_usage: dict[str, int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    """Interface for OpenAI-compatible LLM backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def complete(
        self,
        *,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 200,
        messages: list[dict[str, str]] | None = None,
    ) -> ProviderResult:
        ...

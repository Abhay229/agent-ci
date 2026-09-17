"""OpenRouter provider (OpenAI-compatible API)."""

from __future__ import annotations

import os
import time
from typing import Any

from agent_ci.agents.providers.base import BaseProvider, ProviderResult


class OpenRouterProvider(BaseProvider):
    """Calls models through OpenRouter."""

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self._base_url = base_url or self.DEFAULT_BASE_URL

    @property
    def name(self) -> str:
        return "openrouter"

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
        if not self._api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for live mode")

        from openai import OpenAI

        client = OpenAI(base_url=self._base_url, api_key=self._api_key)
        started = time.perf_counter()
        chat_messages = [{"role": "system", "content": system_prompt}]
        if messages:
            chat_messages.extend(messages)
        else:
            chat_messages.append({"role": "user", "content": user_message})
        resp = client.chat.completions.create(
            model=model,
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = (time.perf_counter() - started) * 1000

        usage = resp.usage
        token_usage = None
        if usage is not None:
            token_usage = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }

        metadata: dict[str, Any] = {"base_url": self._base_url}
        if resp.id:
            metadata["response_id"] = resp.id

        return ProviderResult(
            content=resp.choices[0].message.content or "",
            model=resp.model or model,
            provider=self.name,
            latency_ms=latency_ms,
            token_usage=token_usage,
            metadata=metadata,
        )

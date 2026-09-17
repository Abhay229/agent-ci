"""LLM provider implementations."""

from agent_ci.agents.providers.base import BaseProvider, ProviderResult
from agent_ci.agents.providers.openrouter import OpenRouterProvider

PROVIDERS: dict[str, type[BaseProvider]] = {
    "openrouter": OpenRouterProvider,
}


def get_provider(name: str, **kwargs) -> BaseProvider:
    try:
        provider_cls = PROVIDERS[name]
    except KeyError as exc:
        supported = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"Unknown provider {name!r}. Supported: {supported}") from exc
    return provider_cls(**kwargs)

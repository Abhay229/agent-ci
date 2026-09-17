"""Create agent instances from configuration."""

from __future__ import annotations

from agent_ci.agents.base import BaseAgent
from agent_ci.agents.llm import LLMAgent
from agent_ci.agents.mock import MockAgent
from agent_ci.agents.providers import get_provider
from agent_ci.config import load_agent_configs, resolve_mode
from agent_ci.types import AgentConfig


def create_agent(config: AgentConfig) -> BaseAgent:
    mode = resolve_mode(config)
    if mode == "mock":
        return MockAgent(config)
    provider = get_provider(config.provider)
    return LLMAgent(config, provider)


def load_agents(config_path: str | None = None) -> tuple[BaseAgent, BaseAgent]:
    configs = load_agent_configs(config_path)
    baseline = create_agent(configs["baseline"])
    candidate = create_agent(configs["candidate"])
    return baseline, candidate

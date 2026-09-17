"""Load agent configuration from agents.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

from agent_ci.types import AgentConfig

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "agents.json"


def load_agent_configs(config_path: str | Path | None = None) -> dict[str, AgentConfig]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    agents: dict[str, AgentConfig] = {}
    for role in ("baseline", "candidate"):
        if role not in raw:
            raise KeyError(f"agents.json must define {role!r}")
        agents[role] = AgentConfig.from_dict(role, raw[role])
    return agents


def resolve_mode(config: AgentConfig) -> str:
    """Return 'mock' or 'live' for a configured agent."""
    if config.mode == "auto":
        return "live" if os.environ.get("AGENT_CI_LIVE") == "1" else "mock"
    if config.mode not in ("mock", "live"):
        raise ValueError(f"Unsupported mode {config.mode!r} for agent {config.name!r}")
    return config.mode

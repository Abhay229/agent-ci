"""
The ROLLOUT.

Agents are configured in agents.json as baseline vs candidate. The evaluation
engine calls BaseAgent.run() and only uses response.answer for scoring — it
does not care whether the agent is mock or live.

Legacy call_agent(test_case, version="v1"|"v2") is kept for backward
compatibility; v1 maps to baseline and v2 maps to candidate.
"""

from __future__ import annotations

from agent_ci.agents.base import BaseAgent
from agent_ci.agents.factory import load_agents
from agent_ci.types import AgentResponse

_ROLE_ALIASES = {
    "v1": "baseline",
    "v2": "candidate",
    "baseline": "baseline",
    "candidate": "candidate",
}

_agents_cache: dict[str, BaseAgent] | None = None


def _get_agents():
    global _agents_cache
    if _agents_cache is None:
        baseline, candidate = load_agents()
        _agents_cache = {"baseline": baseline, "candidate": candidate}
    return _agents_cache


def get_agent(role: str):
    """Return a configured agent by role (baseline, candidate, or v1/v2 alias)."""
    agents = _get_agents()
    key = _ROLE_ALIASES.get(role, role)
    if key not in agents:
        raise ValueError(f"Unknown agent role {role!r}. Use baseline/candidate or v1/v2.")
    return agents[key]


def run_agent(test_case: dict, role: str = "baseline") -> AgentResponse:
    """Run one test case against a configured agent. Returns structured response."""
    return get_agent(role).run(test_case)


def call_agent(test_case: dict, version: str = "v1", model: str | None = None) -> str:
    """Legacy API: run agent and return answer text only.

    version: "v1"/"baseline" or "v2"/"candidate"
    model: ignored — model is read from agents.json
    """
    _ = model  # kept for backward-compatible signature
    return run_agent(test_case, role=version).answer

"""Configuration for optional root-cause analysis."""

from __future__ import annotations

import os

ENV_ROOT_CAUSE = "AGENT_CI_ROOT_CAUSE"
DEFAULT_JUDGE_MODEL = "google/gemini-2.0-flash-001"


def is_root_cause_enabled(explicit_flag: bool | None = None) -> bool:
    """Return True when root-cause analysis should run."""
    if explicit_flag is not None:
        return explicit_flag
    return os.environ.get(ENV_ROOT_CAUSE) == "1"


def is_live_analysis() -> bool:
    return os.environ.get("AGENT_CI_LIVE") == "1"

"""Configuration for optional AI test generation."""

from __future__ import annotations

import os

ENV_GENERATE_TESTS = "AGENT_CI_GENERATE_TESTS"
DEFAULT_JUDGE_MODEL = "google/gemini-2.0-flash-001"


def is_test_generation_enabled(explicit_flag: bool | None = None) -> bool:
    if explicit_flag is not None:
        return explicit_flag
    return os.environ.get(ENV_GENERATE_TESTS) == "1"


def is_live_generation() -> bool:
    return os.environ.get("AGENT_CI_LIVE") == "1"

"""Types for AI-assisted test generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

AI_TEST_DISCLAIMER = "AI-generated — requires human review"


@dataclass
class GeneratedTestCase:
    """One AI-suggested test case — not trusted until human review."""

    id: str
    category: str
    user_message: str
    judge_rubric: str
    must_include: list[str] = field(default_factory=list)
    must_not_include: list[str] = field(default_factory=list)
    source_test_id: str = ""
    disclaimer: str = AI_TEST_DISCLAIMER
    ai_generated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedTestBatch:
    """A set of related tests generated from one regression."""

    generation_id: str
    timestamp: str
    source_test_id: str
    review_status: str
    source: str
    success: bool
    tests: list[dict[str, Any]] = field(default_factory=list)
    regression_summary: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    disclaimer: str = AI_TEST_DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

"""Regression detection types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

VERDICT_IMPROVEMENT = "IMPROVEMENT"
VERDICT_REGRESSION = "REGRESSION"
VERDICT_UNCHANGED = "UNCHANGED"


@dataclass
class MetricChange:
    metric: str
    baseline_score: float
    candidate_score: float
    delta: float
    verdict: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RegressionResult:
    """Structured regression analysis for one test case."""

    test_id: str
    question: str
    baseline_response: str
    candidate_response: str
    baseline_score: float
    candidate_score: float
    delta: float
    overall_verdict: str
    verdict: str
    metric_changes: dict[str, dict[str, Any]]
    metric_regressions: list[str] = field(default_factory=list)
    metric_improvements: list[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

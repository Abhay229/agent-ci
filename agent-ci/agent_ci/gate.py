"""Quality gate — pass/fail decision from a diff report."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agent_ci.regression.types import VERDICT_REGRESSION


@dataclass
class GateResult:
    """Outcome of the CI quality gate."""

    passed: bool
    status: str
    n_regressions: int
    n_improvements: int
    n_unchanged: int
    n_tests: int
    regression_ids: list[str]
    mean_score_baseline: float
    mean_score_candidate: float
    mean_delta: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_gate(report: dict, *, max_regressions: int = 0) -> GateResult:
    """Decide whether the quality gate passes.

    The gate fails when the number of regressions exceeds ``max_regressions``
    (default 0 — zero tolerance).
    """
    summary = report["summary"]
    rows = report["rows"]

    regression_ids = [r["id"] for r in rows if r["verdict"] == VERDICT_REGRESSION]
    n_regressions = summary["n_regressions"]
    passed = n_regressions <= max_regressions

    return GateResult(
        passed=passed,
        status="PASSED" if passed else "FAILED",
        n_regressions=n_regressions,
        n_improvements=summary["n_improvements"],
        n_unchanged=summary["n_unchanged"],
        n_tests=summary["n_tests"],
        regression_ids=regression_ids,
        mean_score_baseline=summary["mean_score_baseline"],
        mean_score_candidate=summary["mean_score_candidate"],
        mean_delta=summary["mean_delta"],
    )


def build_gate_report(report: dict, gate: GateResult) -> dict[str, Any]:
    """Merge diff report with gate outcome for machine-readable output."""
    return {
        "gate": gate.to_dict(),
        "summary": report["summary"],
        "regression_report": report["regression_report"],
        "rows": report["rows"],
    }

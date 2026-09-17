"""Regression detection logic."""

from __future__ import annotations

from agent_ci.regression.config import RegressionConfig, load_regression_config
from agent_ci.regression.types import (
    VERDICT_IMPROVEMENT,
    VERDICT_REGRESSION,
    VERDICT_UNCHANGED,
    MetricChange,
    RegressionResult,
)


def classify_delta(delta: float, threshold: float) -> str:
    """Classify a score delta using a symmetric threshold."""
    if delta <= -threshold:
        return VERDICT_REGRESSION
    if delta >= threshold:
        return VERDICT_IMPROVEMENT
    return VERDICT_UNCHANGED


def _metric_score(evaluation: dict, metric: str) -> float | None:
    metrics = evaluation.get("metrics") or {}
    if metric not in metrics:
        return None
    return float(metrics[metric]["score"])


def analyze_metric_changes(
    baseline_eval: dict,
    candidate_eval: dict,
    config: RegressionConfig,
) -> tuple[dict[str, dict], list[str], list[str]]:
    metric_changes: dict[str, dict] = {}
    metric_regressions: list[str] = []
    metric_improvements: list[str] = []

    for metric in config.monitored_metrics:
        baseline_score = _metric_score(baseline_eval, metric)
        candidate_score = _metric_score(candidate_eval, metric)
        if baseline_score is None or candidate_score is None:
            continue

        delta = round(candidate_score - baseline_score, 3)
        verdict = classify_delta(delta, config.metric_threshold)
        metric_changes[metric] = MetricChange(
            metric=metric,
            baseline_score=round(baseline_score, 3),
            candidate_score=round(candidate_score, 3),
            delta=delta,
            verdict=verdict,
        ).to_dict()

        if verdict == VERDICT_REGRESSION:
            metric_regressions.append(metric)
        elif verdict == VERDICT_IMPROVEMENT:
            metric_improvements.append(metric)

    return metric_changes, metric_regressions, metric_improvements


def build_explanation(
    delta: float,
    overall_verdict: str,
    composite_verdict: str,
    metric_regressions: list[str],
    metric_improvements: list[str],
) -> str:
    parts: list[str] = []

    if overall_verdict == VERDICT_REGRESSION:
        parts.append(f"Overall score decreased by {abs(delta):.3f}.")
    elif overall_verdict == VERDICT_IMPROVEMENT:
        parts.append(f"Overall score increased by {delta:.3f}.")
    else:
        parts.append(f"Overall score changed by {delta:+.3f}, within the unchanged band.")

    if metric_regressions:
        parts.append(
            "Metric regressions: "
            + ", ".join(f"{name} ({VERDICT_REGRESSION.lower()})" for name in metric_regressions)
            + "."
        )
    if metric_improvements:
        parts.append(
            "Metric improvements: "
            + ", ".join(f"{name} ({VERDICT_IMPROVEMENT.lower()})" for name in metric_improvements)
            + "."
        )

    if composite_verdict == VERDICT_REGRESSION and overall_verdict != VERDICT_REGRESSION:
        parts.append(
            "Flagged as regression because at least one monitored metric regressed "
            "even though the overall score did not decrease enough to regress on its own."
        )
    elif composite_verdict == VERDICT_IMPROVEMENT:
        parts.append("No monitored metric regressions detected.")
    elif composite_verdict == VERDICT_UNCHANGED:
        parts.append("No significant overall or metric-level change detected.")

    return " ".join(parts)


def detect_regression(
    *,
    test_id: str,
    question: str,
    baseline_result: dict,
    candidate_result: dict,
    config: RegressionConfig | None = None,
) -> RegressionResult:
    """Compare baseline vs candidate evaluation for one test case."""
    config = config or load_regression_config()

    baseline_score = round(float(baseline_result["combined_score"]), 3)
    candidate_score = round(float(candidate_result["combined_score"]), 3)
    delta = round(candidate_score - baseline_score, 3)
    overall_verdict = classify_delta(delta, config.overall_threshold)

    metric_changes, metric_regressions, metric_improvements = analyze_metric_changes(
        baseline_result,
        candidate_result,
        config,
    )

    if metric_regressions:
        composite_verdict = VERDICT_REGRESSION
    elif overall_verdict == VERDICT_REGRESSION:
        composite_verdict = VERDICT_REGRESSION
    elif overall_verdict == VERDICT_IMPROVEMENT:
        composite_verdict = VERDICT_IMPROVEMENT
    else:
        composite_verdict = VERDICT_UNCHANGED

    explanation = build_explanation(
        delta,
        overall_verdict,
        composite_verdict,
        metric_regressions,
        metric_improvements,
    )

    return RegressionResult(
        test_id=test_id,
        question=question,
        baseline_response=baseline_result["response"],
        candidate_response=candidate_result["response"],
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        delta=delta,
        overall_verdict=overall_verdict,
        verdict=composite_verdict,
        metric_changes=metric_changes,
        metric_regressions=metric_regressions,
        metric_improvements=metric_improvements,
        explanation=explanation,
    )

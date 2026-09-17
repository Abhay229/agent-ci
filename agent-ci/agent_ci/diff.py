"""
The DIFF REPORT.

Given baseline and candidate agents, run rollout -> rubric for each, then
compare scores with configurable overall and metric-level regression detection.
"""

from __future__ import annotations

from agent_ci.agents.base import BaseAgent
from agent_ci.agents.factory import load_agents
from agent_ci.dataset import TEST_CASES
from agent_ci.evaluation.engine import EvaluationEngine
from agent_ci.regression.config import load_regression_config
from agent_ci.regression.detector import detect_regression
from agent_ci.regression.types import VERDICT_IMPROVEMENT, VERDICT_REGRESSION, VERDICT_UNCHANGED
from agent_ci.rubric import score_response

# Backward-compatible alias — prefer regression_config.json
REGRESSION_THRESHOLD = load_regression_config().overall_threshold


def run_agent_suite(agent: BaseAgent) -> list[dict]:
    results = []
    for tc in TEST_CASES:
        agent_response = agent.run(tc)
        scored = score_response(
            agent_response.answer,
            tc,
            retrieved_context=agent_response.retrieved_context,
        )
        results.append({
            "id": tc["id"],
            "category": tc["category"],
            "user_message": tc["user_message"],
            "response": agent_response.answer,
            "agent_response": agent_response.to_dict(),
            "evaluation": {
                "metrics": scored["metrics"],
                "overall_metrics": scored["overall_metrics"],
                "final_score": scored["final_score"],
            },
            **scored,
        })
    return results


def _regression_row_to_report_row(regression, tc: dict, r_base: dict, r_cand: dict) -> dict:
    """Merge regression analysis with backward-compatible report fields."""
    row = regression.to_dict()
    row.update({
        "id": tc["id"],
        "category": tc["category"],
        "user_message": tc["user_message"],
        # Backward-compatible keys (v1 = baseline, v2 = candidate)
        "v1_response": r_base["response"],
        "v1_score": regression.baseline_score,
        "v2_response": r_cand["response"],
        "v2_score": regression.candidate_score,
        "baseline_response": regression.baseline_response,
        "baseline_score": regression.baseline_score,
        "candidate_response": regression.candidate_response,
        "candidate_score": regression.candidate_score,
        "baseline_agent_response": r_base["agent_response"],
        "candidate_agent_response": r_cand["agent_response"],
        "delta": regression.delta,
        "verdict": regression.verdict,
    })
    return row


def build_diff_report(
    baseline: BaseAgent | None = None,
    candidate: BaseAgent | None = None,
) -> dict:
    if baseline is None or candidate is None:
        baseline, candidate = load_agents()

    regression_config = load_regression_config()
    baseline_results = run_agent_suite(baseline)
    candidate_results = run_agent_suite(candidate)
    baseline_by_id = {r["id"]: r for r in baseline_results}
    candidate_by_id = {r["id"]: r for r in candidate_results}

    rows = []
    regression_entries = []
    for tc in TEST_CASES:
        r_base = baseline_by_id[tc["id"]]
        r_cand = candidate_by_id[tc["id"]]
        regression = detect_regression(
            test_id=tc["id"],
            question=tc["user_message"],
            baseline_result=r_base,
            candidate_result=r_cand,
            config=regression_config,
        )
        row = _regression_row_to_report_row(regression, tc, r_base, r_cand)
        rows.append(row)
        regression_entries.append(regression.to_dict())

    mean_baseline = round(sum(r["baseline_score"] for r in rows) / len(rows), 3)
    mean_candidate = round(sum(r["candidate_score"] for r in rows) / len(rows), 3)
    n_regressions = sum(1 for r in rows if r["verdict"] == VERDICT_REGRESSION)
    n_improvements = sum(1 for r in rows if r["verdict"] == VERDICT_IMPROVEMENT)
    n_unchanged = sum(1 for r in rows if r["verdict"] == VERDICT_UNCHANGED)
    n_overall_regressions = sum(1 for r in rows if r["overall_verdict"] == VERDICT_REGRESSION)
    n_metric_regression_flags = sum(1 for r in rows if r["metric_regressions"])

    metric_regression_counts: dict[str, int] = {}
    for row in rows:
        for metric in row["metric_regressions"]:
            metric_regression_counts[metric] = metric_regression_counts.get(metric, 0) + 1

    return {
        "summary": {
            "baseline_name": baseline.name,
            "candidate_name": candidate.name,
            "mean_score_baseline": mean_baseline,
            "mean_score_candidate": mean_candidate,
            "mean_delta": round(mean_candidate - mean_baseline, 3),
            "overall_metrics_baseline": EvaluationEngine.aggregate_overall_metrics(baseline_results),
            "overall_metrics_candidate": EvaluationEngine.aggregate_overall_metrics(candidate_results),
            "regression_thresholds": {
                "overall_threshold": regression_config.overall_threshold,
                "metric_threshold": regression_config.metric_threshold,
                "monitored_metrics": regression_config.monitored_metrics,
            },
            "n_overall_regressions": n_overall_regressions,
            "n_metric_regression_flags": n_metric_regression_flags,
            # Backward-compatible keys
            "mean_score_v1": mean_baseline,
            "mean_score_v2": mean_candidate,
            "n_tests": len(rows),
            "n_regressions": n_regressions,
            "n_improvements": n_improvements,
            "n_unchanged": n_unchanged,
            "metric_regression_counts": metric_regression_counts,
        },
        "regression_report": regression_entries,
        "rows": rows,
    }


def print_report(report: dict) -> None:
    s = report["summary"]
    baseline_label = s.get("baseline_name", "baseline")
    candidate_label = s.get("candidate_name", "candidate")
    print("=" * 60)
    print(f"AGENT CI — DIFF REPORT: {baseline_label} -> {candidate_label}")
    print("=" * 60)
    print(
        f"Mean score  baseline: {s['mean_score_baseline']:.1%}   "
        f"candidate: {s['mean_score_candidate']:.1%}   "
        f"delta: {s['mean_delta']:+.1%}"
    )
    print(
        f"{s['n_regressions']} regressions, {s['n_improvements']} improvements, "
        f"{s['n_unchanged']} unchanged, across {s['n_tests']} tests"
    )
    if s.get("n_metric_regression_flags"):
        print(
            f"{s['n_metric_regression_flags']} test(s) with metric-level regression flags "
            f"({s.get('n_overall_regressions', 0)} overall-only)"
        )
    print("-" * 60)
    for r in report["rows"]:
        marker = {
            VERDICT_REGRESSION: "REGRESSION",
            VERDICT_IMPROVEMENT: "IMPROVEMENT",
            VERDICT_UNCHANGED: "unchanged",
        }[r["verdict"]]
        line = (
            f"[{marker:>11}] {r['id']:<28} "
            f"baseline={r['baseline_score']:.2f} -> candidate={r['candidate_score']:.2f} "
            f"({r['delta']:+.2f})"
        )
        if r.get("metric_regressions"):
            line += f"  metrics: {', '.join(r['metric_regressions'])}"
        print(line)

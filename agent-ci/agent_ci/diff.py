"""
The DIFF REPORT.

Given baseline and candidate agents, run rollout -> rubric for each, then
diff the scores. Every test case is classified as REGRESSION / IMPROVEMENT /
UNCHANGED.
"""

from __future__ import annotations

from agent_ci.agents.base import BaseAgent
from agent_ci.agents.factory import load_agents
from agent_ci.dataset import TEST_CASES
from agent_ci.evaluation.engine import EvaluationEngine
from agent_ci.rubric import score_response

REGRESSION_THRESHOLD = 0.1  # score delta smaller than this counts as "unchanged"


def run_agent_suite(agent: BaseAgent) -> list[dict]:
    results = []
    for tc in TEST_CASES:
        agent_response = agent.run(tc)
        scored = score_response(agent_response.answer, tc)
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


def build_diff_report(
    baseline: BaseAgent | None = None,
    candidate: BaseAgent | None = None,
) -> dict:
    if baseline is None or candidate is None:
        baseline, candidate = load_agents()

    baseline_results = run_agent_suite(baseline)
    candidate_results = run_agent_suite(candidate)
    baseline_by_id = {r["id"]: r for r in baseline_results}
    candidate_by_id = {r["id"]: r for r in candidate_results}

    rows = []
    for tc in TEST_CASES:
        r_base = baseline_by_id[tc["id"]]
        r_cand = candidate_by_id[tc["id"]]
        delta = round(r_cand["combined_score"] - r_base["combined_score"], 3)
        if delta <= -REGRESSION_THRESHOLD:
            verdict = "REGRESSION"
        elif delta >= REGRESSION_THRESHOLD:
            verdict = "IMPROVEMENT"
        else:
            verdict = "UNCHANGED"
        rows.append({
            "id": tc["id"],
            "category": tc["category"],
            "user_message": tc["user_message"],
            # Backward-compatible keys (v1 = baseline, v2 = candidate)
            "v1_response": r_base["response"],
            "v1_score": r_base["combined_score"],
            "v2_response": r_cand["response"],
            "v2_score": r_cand["combined_score"],
            "baseline_response": r_base["response"],
            "baseline_score": r_base["combined_score"],
            "candidate_response": r_cand["response"],
            "candidate_score": r_cand["combined_score"],
            "baseline_agent_response": r_base["agent_response"],
            "candidate_agent_response": r_cand["agent_response"],
            "delta": delta,
            "verdict": verdict,
        })

    mean_baseline = round(sum(r["baseline_score"] for r in rows) / len(rows), 3)
    mean_candidate = round(sum(r["candidate_score"] for r in rows) / len(rows), 3)
    n_regressions = sum(1 for r in rows if r["verdict"] == "REGRESSION")
    n_improvements = sum(1 for r in rows if r["verdict"] == "IMPROVEMENT")
    n_unchanged = sum(1 for r in rows if r["verdict"] == "UNCHANGED")

    return {
        "summary": {
            "baseline_name": baseline.name,
            "candidate_name": candidate.name,
            "mean_score_baseline": mean_baseline,
            "mean_score_candidate": mean_candidate,
            "mean_delta": round(mean_candidate - mean_baseline, 3),
            "overall_metrics_baseline": EvaluationEngine.aggregate_overall_metrics(baseline_results),
            "overall_metrics_candidate": EvaluationEngine.aggregate_overall_metrics(candidate_results),
            # Backward-compatible keys
            "mean_score_v1": mean_baseline,
            "mean_score_v2": mean_candidate,
            "n_tests": len(rows),
            "n_regressions": n_regressions,
            "n_improvements": n_improvements,
            "n_unchanged": n_unchanged,
        },
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
    print("-" * 60)
    for r in report["rows"]:
        marker = {"REGRESSION": "REGRESSION", "IMPROVEMENT": "IMPROVEMENT", "UNCHANGED": "unchanged"}[r["verdict"]]
        print(
            f"[{marker:>11}] {r['id']:<28} "
            f"baseline={r['baseline_score']:.2f} -> candidate={r['candidate_score']:.2f} "
            f"({r['delta']:+.2f})"
        )

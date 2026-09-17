"""Load evaluation reports and history for the dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_ci.dataset import TEST_CASES
from agent_ci.history.store import HistoryStore
from agent_ci.history.types import EvaluationRecord

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_PATH = PROJECT_ROOT / "diff_report.json"
DEFAULT_HISTORY_PATH = PROJECT_ROOT / "history" / "evaluations.jsonl"

_TEST_CASE_INDEX: dict[str, dict[str, Any]] = {tc["id"]: tc for tc in TEST_CASES}


def load_report(path: Path | str | None = None) -> dict[str, Any]:
    """Load a generated diff or gate report JSON file."""
    report_path = Path(path) if path else DEFAULT_REPORT_PATH
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    with open(report_path, encoding="utf-8") as f:
        return json.load(f)


def load_history(path: Path | str | None = None) -> list[EvaluationRecord]:
    """Load stored evaluation history records."""
    history_path = Path(path) if path else DEFAULT_HISTORY_PATH
    return HistoryStore(history_path).load_all()


def get_test_metadata(test_id: str) -> dict[str, Any]:
    """Return static dataset metadata for a test case (expected behavior)."""
    return _TEST_CASE_INDEX.get(test_id, {})


def get_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    return report.get("rows") or []


def get_summary(report: dict[str, Any]) -> dict[str, Any]:
    return report.get("summary") or {}


def get_gate(report: dict[str, Any]) -> dict[str, Any] | None:
    return report.get("gate")


def filter_rows_by_verdict(rows: list[dict[str, Any]], verdict: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("verdict") == verdict]


def get_retrieved_context(row: dict[str, Any]) -> list[dict[str, Any]]:
    candidate = row.get("candidate_agent_response") or {}
    return candidate.get("retrieved_context") or []


def format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1%}"


def metric_comparison_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Build baseline vs candidate metric rows for tables/charts."""
    baseline = summary.get("overall_metrics_baseline") or {}
    candidate = summary.get("overall_metrics_candidate") or {}
    metrics = sorted(set(baseline) | set(candidate) - {"final_score"})

    rows = []
    for metric in metrics:
        base_score = baseline.get(metric)
        cand_score = candidate.get(metric)
        delta = None
        if base_score is not None and cand_score is not None:
            delta = round(float(cand_score) - float(base_score), 3)
        rows.append({
            "metric": metric,
            "baseline": base_score,
            "candidate": cand_score,
            "delta": delta,
        })
    return rows

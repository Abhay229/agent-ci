"""Tests for evaluation history storage and comparison."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from agent_ci.gate import evaluate_gate
from agent_ci.history.compare import compare_runs, print_history_compare, print_history_list
from agent_ci.history.record import build_evaluation_record, build_configuration_metadata
from agent_ci.history.store import HistoryStore
from agent_ci.history.types import EvaluationRecord
from agent_ci.regression.types import VERDICT_IMPROVEMENT, VERDICT_REGRESSION


def _sample_report(*, n_regressions: int = 0) -> dict:
    rows = []
    for i in range(3):
        verdict = VERDICT_REGRESSION if i < n_regressions else VERDICT_IMPROVEMENT
        rows.append({
            "id": f"test_{i}",
            "verdict": verdict,
            "delta": -0.2 if verdict == VERDICT_REGRESSION else 0.2,
            "metric_regressions": ["correctness"] if verdict == VERDICT_REGRESSION else [],
            "explanation": "test",
        })

    return {
        "summary": {
            "baseline_name": "baseline",
            "candidate_name": "candidate",
            "mean_score_baseline": 0.5,
            "mean_score_candidate": 0.8,
            "mean_delta": 0.3,
            "n_tests": 3,
            "n_regressions": n_regressions,
            "n_improvements": 3 - n_regressions,
            "n_unchanged": 0,
            "overall_metrics_baseline": {
                "correctness": 0.5,
                "final_score": 0.5,
            },
            "overall_metrics_candidate": {
                "correctness": 0.8,
                "final_score": 0.8,
            },
        },
        "regression_report": [],
        "rows": rows,
    }


def _record(
    *,
    record_id: str,
    baseline: str,
    candidate: str,
    score: float,
    regressions: int = 0,
) -> EvaluationRecord:
    return EvaluationRecord(
        id=record_id,
        timestamp="2026-01-01T00:00:00+00:00",
        baseline_version=baseline,
        candidate_version=candidate,
        model="mock-model",
        provider="mock",
        mode="mock",
        overall_score_baseline=score - 0.1,
        overall_score_candidate=score,
        metric_scores_baseline={"correctness": score - 0.1},
        metric_scores_candidate={"correctness": score},
        n_improvements=2,
        n_regressions=regressions,
        n_unchanged=1,
        n_tests=3,
        failed_tests=["test_0"] if regressions else [],
        gate_passed=regressions == 0,
        configuration_metadata={"baseline": {"version": baseline}, "candidate": {"version": candidate}},
    )


class TestEvaluationRecord(unittest.TestCase):
    def test_round_trip_dict(self):
        original = _record(record_id="abc", baseline="v1", candidate="v2", score=0.8)
        restored = EvaluationRecord.from_dict(original.to_dict())
        self.assertEqual(restored.id, "abc")
        self.assertEqual(restored.baseline_version, "v1")
        self.assertEqual(restored.candidate_version, "v2")
        self.assertEqual(restored.metric_scores_candidate["correctness"], 0.8)


class TestHistoryStore(unittest.TestCase):
    def test_append_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evaluations.jsonl"
            store = HistoryStore(path)

            first = _record(record_id="r1", baseline="v1", candidate="v2", score=0.7)
            second = _record(record_id="r2", baseline="v2", candidate="v3", score=0.85)
            store.append(first)
            store.append(second)

            loaded = store.load_all()
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0].candidate_version, "v2")
            self.assertEqual(loaded[1].candidate_version, "v3")
            self.assertEqual(store.count(), 2)

    def test_get_by_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evaluations.jsonl"
            store = HistoryStore(path)
            record = _record(record_id="find-me", baseline="v1", candidate="v2", score=0.7)
            store.append(record)
            self.assertIsNotNone(store.get_by_id("find-me"))
            self.assertIsNone(store.get_by_id("missing"))

    def test_jsonl_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evaluations.jsonl"
            store = HistoryStore(path)
            store.append(_record(record_id="r1", baseline="v1", candidate="v2", score=0.7))

            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            parsed = json.loads(lines[0])
            self.assertEqual(parsed["candidate_version"], "v2")


class TestBuildEvaluationRecord(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_record_fields_from_report(self):
        report = _sample_report(n_regressions=1)
        gate = evaluate_gate(report)
        record = build_evaluation_record(
            report,
            gate=gate,
            record_id="fixed-id",
            timestamp="2026-01-01T12:00:00+00:00",
        )

        self.assertEqual(record.id, "fixed-id")
        self.assertEqual(record.timestamp, "2026-01-01T12:00:00+00:00")
        self.assertEqual(record.baseline_version, "v1")
        self.assertEqual(record.candidate_version, "v2")
        self.assertEqual(record.provider, "openrouter")
        self.assertEqual(record.model, "google/gemini-2.0-flash-001")
        self.assertEqual(record.overall_score_candidate, 0.8)
        self.assertEqual(record.n_regressions, 1)
        self.assertEqual(record.n_improvements, 2)
        self.assertEqual(record.n_unchanged, 0)
        self.assertEqual(record.failed_tests, ["test_0"])
        self.assertFalse(record.gate_passed)
        self.assertIn("metric_weights", record.configuration_metadata)
        self.assertIn("regression_config", record.configuration_metadata)

    def test_configuration_metadata_includes_versions(self):
        metadata = build_configuration_metadata()
        self.assertEqual(metadata["baseline"]["version"], "v1")
        self.assertEqual(metadata["candidate"]["version"], "v2")


class TestHistoryCompare(unittest.TestCase):
    def test_compare_empty(self):
        result = compare_runs([])
        self.assertEqual(result["runs"], [])
        self.assertEqual(result["version_chain"], [])

    def test_version_chain(self):
        records = [
            _record(record_id="1", baseline="v1", candidate="v2", score=0.7),
            _record(record_id="2", baseline="v2", candidate="v3", score=0.85),
            _record(record_id="3", baseline="v3", candidate="v4", score=0.92),
        ]
        result = compare_runs(records)
        self.assertEqual(result["version_chain"], ["v1", "v2", "v3", "v4"])

    def test_metric_trends(self):
        records = [
            _record(record_id="1", baseline="v1", candidate="v2", score=0.7),
            _record(record_id="2", baseline="v2", candidate="v3", score=0.85),
        ]
        result = compare_runs(records)
        trend = result["metric_trends"]["correctness"]
        self.assertEqual(len(trend), 2)
        self.assertEqual(trend[0]["version"], "v2")
        self.assertEqual(trend[1]["version"], "v3")
        self.assertEqual(result["runs"][1]["score_delta_from_previous"], 0.15)

    def test_print_helpers_do_not_crash(self):
        records = [
            _record(record_id="1", baseline="v1", candidate="v2", score=0.7),
            _record(record_id="2", baseline="v2", candidate="v3", score=0.85),
        ]
        print_history_list(records)
        print_history_compare(records)
        print_history_list([])


class TestCLIHistoryIntegration(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_evaluate_saves_history(self):
        from agent_ci.cli import cmd_evaluate

        with tempfile.TemporaryDirectory() as tmp:
            history_path = Path(tmp) / "history.jsonl"
            output = Path(tmp) / "report.json"
            args = type("Args", (), {
                "output": str(output),
                "no_history": False,
                "history_path": str(history_path),
            })()
            code = cmd_evaluate(args)
            self.assertEqual(code, 0)
            store = HistoryStore(history_path)
            records = store.load_all()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].baseline_version, "v1")
            self.assertEqual(records[0].candidate_version, "v2")

    def test_check_saves_history_with_gate(self):
        from agent_ci.cli import cmd_check

        with tempfile.TemporaryDirectory() as tmp:
            history_path = Path(tmp) / "history.jsonl"
            output = Path(tmp) / "report.json"
            args = type("Args", (), {
                "output": str(output),
                "max_regressions": 0,
                "no_history": False,
                "history_path": str(history_path),
            })()
            cmd_check(args)
            store = HistoryStore(history_path)
            records = store.load_all()
            self.assertEqual(len(records), 1)
            self.assertFalse(records[0].gate_passed)


if __name__ == "__main__":
    unittest.main()

"""Tests for the Streamlit dashboard data layer."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dashboard.data_loader import (
    filter_rows_by_verdict,
    get_retrieved_context,
    get_rows,
    get_summary,
    get_test_metadata,
    load_history,
    load_report,
    metric_comparison_rows,
)


class TestDashboardDataLoader(unittest.TestCase):
    def setUp(self):
        self.report_path = Path(__file__).resolve().parent.parent / "diff_report.json"
        if not self.report_path.exists():
            self.skipTest("diff_report.json not found — run agent-ci check first")

    def test_load_report(self):
        report = load_report(self.report_path)
        self.assertIn("summary", report)
        self.assertIn("rows", report)
        self.assertEqual(get_summary(report)["n_tests"], 13)

    def test_metric_comparison_rows(self):
        report = load_report(self.report_path)
        rows = metric_comparison_rows(get_summary(report))
        self.assertTrue(rows)
        self.assertIn("metric", rows[0])
        self.assertIn("baseline", rows[0])
        self.assertIn("candidate", rows[0])

    def test_filter_regressions(self):
        report = load_report(self.report_path)
        rows = get_rows(report)
        regressions = filter_rows_by_verdict(rows, "REGRESSION")
        self.assertEqual(len(regressions), 1)
        self.assertEqual(regressions[0]["id"], "audit_logs_enterprise")

    def test_get_test_metadata(self):
        meta = get_test_metadata("audit_logs_enterprise")
        self.assertIn("judge_rubric", meta)
        self.assertIn("user_message", meta)

    def test_retrieved_context_from_row(self):
        report = load_report(self.report_path)
        row = next(r for r in get_rows(report) if r["id"] == "audit_logs_enterprise")
        context = get_retrieved_context(row)
        self.assertTrue(context)
        self.assertIn("section", context[0])

    def test_load_history_from_demo_file(self):
        demo_path = Path(__file__).resolve().parent.parent / "history" / "demo_evaluations.jsonl"
        if not demo_path.exists():
            self.skipTest("demo history file not found")
        records = load_history(demo_path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].baseline_version, "v1")

    def test_load_report_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_report("/nonexistent/report.json")

    def test_minimal_report_round_trip(self):
        payload = {
            "summary": {
                "baseline_name": "v1",
                "candidate_name": "v2",
                "mean_score_baseline": 0.5,
                "mean_score_candidate": 0.8,
                "mean_delta": 0.3,
                "n_tests": 1,
                "n_regressions": 0,
                "n_improvements": 1,
                "n_unchanged": 0,
                "overall_metrics_baseline": {"correctness": 0.5, "final_score": 0.5},
                "overall_metrics_candidate": {"correctness": 0.8, "final_score": 0.8},
            },
            "rows": [{
                "id": "t1",
                "verdict": "IMPROVEMENT",
                "baseline_score": 0.5,
                "candidate_score": 0.8,
                "delta": 0.3,
                "candidate_agent_response": {"retrieved_context": []},
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            report = load_report(path)
            self.assertEqual(get_summary(report)["n_tests"], 1)


class TestDashboardStartup(unittest.TestCase):
    def test_streamlit_app_starts(self):
        import subprocess
        import sys
        import time

        project_root = Path(__file__).resolve().parent.parent
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "dashboard/app.py",
                "--server.headless",
                "true",
                "--server.port",
                "8510",
                "--browser.gatherUsageStats",
                "false",
            ],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        started = False
        try:
            deadline = time.time() + 45
            while time.time() < deadline:
                line = proc.stdout.readline() if proc.stdout else ""
                if "You can now view your Streamlit app" in line:
                    started = True
                    break
                if proc.poll() is not None:
                    break
            self.assertTrue(started, "Streamlit did not print startup message")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            if proc.stdout:
                proc.stdout.close()


if __name__ == "__main__":
    unittest.main()

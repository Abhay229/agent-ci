"""Tests for the agent-ci CLI and quality gate."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agent_ci.cli import cmd_check, cmd_evaluate, main, print_check_summary
from agent_ci.gate import evaluate_gate
from agent_ci.regression.types import VERDICT_IMPROVEMENT, VERDICT_REGRESSION


def _minimal_report(*, n_regressions: int = 0) -> dict:
    rows = []
    for i in range(3):
        verdict = VERDICT_IMPROVEMENT
        if i < n_regressions:
            verdict = VERDICT_REGRESSION
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
        },
        "regression_report": [],
        "rows": rows,
    }


class TestQualityGate(unittest.TestCase):
    def test_gate_passes_with_zero_regressions(self):
        gate = evaluate_gate(_minimal_report(n_regressions=0))
        self.assertTrue(gate.passed)
        self.assertEqual(gate.status, "PASSED")
        self.assertEqual(gate.n_regressions, 0)

    def test_gate_fails_with_regressions(self):
        gate = evaluate_gate(_minimal_report(n_regressions=1))
        self.assertFalse(gate.passed)
        self.assertEqual(gate.status, "FAILED")
        self.assertEqual(gate.regression_ids, ["test_0"])

    def test_max_regressions_tolerance(self):
        gate = evaluate_gate(_minimal_report(n_regressions=1), max_regressions=1)
        self.assertTrue(gate.passed)


class TestCLI(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_evaluate_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            args = type("Args", (), {
                "output": str(output),
                "no_history": True,
                "history_path": None,
            })()
            code = cmd_evaluate(args)
            self.assertEqual(code, 0)
            self.assertTrue(output.exists())
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("summary", data)
            self.assertIn("rows", data)
            self.assertEqual(data["summary"]["n_tests"], 13)

    def test_check_command_exit_code_on_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            args = type("Args", (), {
                "output": str(output),
                "max_regressions": 0,
                "no_history": True,
                "history_path": None,
            })()
            code = cmd_check(args)
            self.assertEqual(code, 1)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("gate", data)
            self.assertFalse(data["gate"]["passed"])
            self.assertEqual(data["gate"]["status"], "FAILED")
            self.assertGreater(data["gate"]["n_regressions"], 0)

    def test_check_command_passes_with_tolerance(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            args = type("Args", (), {
                "output": str(output),
                "max_regressions": 1,
                "no_history": True,
                "history_path": None,
            })()
            code = cmd_check(args)
            self.assertEqual(code, 0)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(data["gate"]["passed"])

    def test_main_evaluate_subcommand(self):
        with patch("sys.argv", ["agent-ci", "evaluate", "-o", os.devnull]):
            self.assertEqual(main(), 0)

    def test_check_summary_contains_ci_status(self):
        report = _minimal_report(n_regressions=1)
        gate = evaluate_gate(report)
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_check_summary(report, gate)
        output = buf.getvalue()
        self.assertIn("CI STATUS: FAILED", output)
        self.assertIn("REGRESSION:", output)
        self.assertIn("test_0", output)


if __name__ == "__main__":
    unittest.main()

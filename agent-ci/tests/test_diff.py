import os
import unittest

from agent_ci.diff import build_diff_report
from agent_ci.regression.config import load_regression_config
from agent_ci.regression.types import VERDICT_REGRESSION


class TestDiffReport(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_report_structure(self):
        report = build_diff_report()
        self.assertIn("summary", report)
        self.assertIn("rows", report)
        self.assertIn("regression_report", report)
        summary = report["summary"]
        for key in (
            "mean_score_v1",
            "mean_score_v2",
            "mean_delta",
            "n_tests",
            "n_regressions",
            "n_improvements",
            "n_unchanged",
            "regression_thresholds",
            "metric_regression_counts",
        ):
            self.assertIn(key, summary)

    def test_summary_counts_match_rows(self):
        report = build_diff_report()
        summary = report["summary"]
        self.assertEqual(summary["n_tests"], len(report["rows"]))
        self.assertEqual(
            summary["n_regressions"],
            sum(1 for r in report["rows"] if r["verdict"] == VERDICT_REGRESSION),
        )

    def test_regression_detected_for_audit_logs(self):
        report = build_diff_report()
        row = next(r for r in report["rows"] if r["id"] == "audit_logs_enterprise")
        self.assertEqual(row["verdict"], VERDICT_REGRESSION)
        threshold = load_regression_config().overall_threshold
        self.assertTrue(
            row["delta"] <= -threshold or len(row["metric_regressions"]) > 0
        )

    def test_report_includes_new_test_types(self):
        report = build_diff_report()
        test_types = {row.get("test_type") for row in report["rows"]}
        self.assertIn("single_turn", test_types)
        self.assertIn("multi_turn", test_types)
        categories = {row["category"] for row in report["rows"]}
        self.assertIn("adversarial", categories)
        self.assertIn("tools", categories)

    def test_each_row_has_regression_fields(self):
        report = build_diff_report()
        for row in report["rows"]:
            for key in (
                "id",
                "category",
                "user_message",
                "v1_response",
                "v1_score",
                "v2_response",
                "v2_score",
                "baseline_response",
                "baseline_score",
                "candidate_response",
                "candidate_score",
                "baseline_agent_response",
                "candidate_agent_response",
                "delta",
                "verdict",
                "overall_verdict",
                "metric_changes",
                "metric_regressions",
                "metric_improvements",
                "explanation",
            ):
                self.assertIn(key, row)
            self.assertIn(row["verdict"], ("REGRESSION", "IMPROVEMENT", "UNCHANGED"))
            self.assertEqual(row["baseline_agent_response"]["provider"], "mock")

    def test_regression_report_matches_rows(self):
        report = build_diff_report()
        self.assertEqual(len(report["regression_report"]), len(report["rows"]))
        by_id = {entry["test_id"]: entry for entry in report["regression_report"]}
        for row in report["rows"]:
            self.assertIn(row["id"], by_id)
            self.assertEqual(by_id[row["id"]]["delta"], row["delta"])


if __name__ == "__main__":
    unittest.main()

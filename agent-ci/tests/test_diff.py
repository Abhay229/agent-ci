import os
import unittest

from agent_ci.diff import REGRESSION_THRESHOLD, build_diff_report


class TestDiffReport(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_report_structure(self):
        report = build_diff_report()
        self.assertIn("summary", report)
        self.assertIn("rows", report)
        summary = report["summary"]
        for key in ("mean_score_v1", "mean_score_v2", "mean_delta",
                    "n_tests", "n_regressions", "n_improvements", "n_unchanged"):
            self.assertIn(key, summary)

    def test_mock_mode_expected_outcomes(self):
        report = build_diff_report()
        summary = report["summary"]
        self.assertEqual(summary["n_tests"], 13)
        self.assertEqual(summary["n_regressions"], 1)
        self.assertEqual(summary["n_improvements"], 12)
        self.assertEqual(summary["n_unchanged"], 0)
        self.assertAlmostEqual(summary["mean_score_v1"], 0.45, places=2)
        self.assertAlmostEqual(summary["mean_score_v2"], 0.913, places=2)

    def test_regression_detected_for_audit_logs(self):
        report = build_diff_report()
        row = next(r for r in report["rows"] if r["id"] == "audit_logs_enterprise")
        self.assertEqual(row["verdict"], "REGRESSION")
        self.assertLessEqual(row["delta"], -REGRESSION_THRESHOLD)

    def test_each_row_has_required_fields(self):
        report = build_diff_report()
        for row in report["rows"]:
            for key in ("id", "category", "user_message", "v1_response", "v1_score",
                        "v2_response", "v2_score", "baseline_response", "baseline_score",
                        "candidate_response", "candidate_score", "baseline_agent_response",
                        "candidate_agent_response", "delta", "verdict"):
                self.assertIn(key, row)
            self.assertIn(row["verdict"], ("REGRESSION", "IMPROVEMENT", "UNCHANGED"))
            self.assertEqual(row["baseline_agent_response"]["provider"], "mock")


if __name__ == "__main__":
    unittest.main()

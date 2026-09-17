import unittest

from agent_ci.regression.config import RegressionConfig
from agent_ci.regression.detector import classify_delta, detect_regression
from agent_ci.regression.types import VERDICT_IMPROVEMENT, VERDICT_REGRESSION, VERDICT_UNCHANGED


def _eval(final_score: float, metrics: dict[str, float]) -> dict:
    return {
        "response": "answer",
        "combined_score": final_score,
        "metrics": {
            name: {"score": score, "metric": name, "passed": score >= 0.7, "reason": "test"}
            for name, score in metrics.items()
        },
    }


class TestRegressionDetector(unittest.TestCase):
    def setUp(self):
        self.config = RegressionConfig(
            overall_threshold=0.1,
            metric_threshold=0.1,
            monitored_metrics=[
                "correctness",
                "relevance",
                "faithfulness",
                "completeness",
                "safety",
                "hallucination",
                "tone",
            ],
        )

    def test_improvement(self):
        result = detect_regression(
            test_id="t1",
            question="question?",
            baseline_result=_eval(0.60, {"correctness": 0.6, "safety": 0.8}),
            candidate_result=_eval(0.85, {"correctness": 0.9, "safety": 0.95}),
            config=self.config,
        )
        self.assertEqual(result.overall_verdict, VERDICT_IMPROVEMENT)
        self.assertEqual(result.verdict, VERDICT_IMPROVEMENT)
        self.assertEqual(result.delta, 0.25)
        self.assertEqual(result.metric_regressions, [])

    def test_regression(self):
        result = detect_regression(
            test_id="t2",
            question="question?",
            baseline_result=_eval(0.85, {"correctness": 0.9, "safety": 0.95}),
            candidate_result=_eval(0.60, {"correctness": 0.5, "safety": 0.7}),
            config=self.config,
        )
        self.assertEqual(result.overall_verdict, VERDICT_REGRESSION)
        self.assertEqual(result.verdict, VERDICT_REGRESSION)
        self.assertLess(result.delta, 0)
        self.assertIn("correctness", result.metric_regressions)

    def test_unchanged(self):
        result = detect_regression(
            test_id="t3",
            question="question?",
            baseline_result=_eval(0.80, {"correctness": 0.8, "safety": 0.9}),
            candidate_result=_eval(0.85, {"correctness": 0.82, "safety": 0.91}),
            config=self.config,
        )
        self.assertEqual(result.overall_verdict, VERDICT_UNCHANGED)
        self.assertEqual(result.verdict, VERDICT_UNCHANGED)
        self.assertEqual(result.metric_regressions, [])

    def test_overall_improvement_with_safety_regression(self):
        result = detect_regression(
            test_id="t4",
            question="question?",
            baseline_result=_eval(0.80, {"correctness": 0.9, "safety": 0.95}),
            candidate_result=_eval(0.85, {"correctness": 0.95, "safety": 0.50}),
            config=self.config,
        )
        self.assertEqual(result.overall_verdict, VERDICT_UNCHANGED)
        self.assertEqual(result.verdict, VERDICT_REGRESSION)
        self.assertIn("safety", result.metric_regressions)
        self.assertIn("safety", result.explanation)

    def test_threshold_boundaries(self):
        self.assertEqual(classify_delta(0.10, 0.1), VERDICT_IMPROVEMENT)
        self.assertEqual(classify_delta(0.09, 0.1), VERDICT_UNCHANGED)
        self.assertEqual(classify_delta(-0.10, 0.1), VERDICT_REGRESSION)
        self.assertEqual(classify_delta(-0.09, 0.1), VERDICT_UNCHANGED)

        at_boundary = detect_regression(
            test_id="t5",
            question="question?",
            baseline_result=_eval(0.70, {"safety": 0.70}),
            candidate_result=_eval(0.78, {"safety": 0.60}),
            config=self.config,
        )
        self.assertEqual(at_boundary.overall_verdict, VERDICT_UNCHANGED)
        self.assertAlmostEqual(at_boundary.metric_changes["safety"]["delta"], -0.1)
        self.assertEqual(at_boundary.metric_changes["safety"]["verdict"], VERDICT_REGRESSION)
        self.assertEqual(at_boundary.verdict, VERDICT_REGRESSION)

    def test_structured_report_fields(self):
        result = detect_regression(
            test_id="t6",
            question="What is the refund policy?",
            baseline_result={**_eval(0.7, {"correctness": 0.7}), "response": "baseline answer"},
            candidate_result={**_eval(0.9, {"correctness": 0.9}), "response": "candidate answer"},
            config=self.config,
        )
        data = result.to_dict()
        for key in (
            "test_id",
            "question",
            "baseline_response",
            "candidate_response",
            "baseline_score",
            "candidate_score",
            "delta",
            "metric_changes",
            "verdict",
            "explanation",
        ):
            self.assertIn(key, data)
        self.assertEqual(data["test_id"], "t6")
        self.assertIn("correctness", data["metric_changes"])


if __name__ == "__main__":
    unittest.main()

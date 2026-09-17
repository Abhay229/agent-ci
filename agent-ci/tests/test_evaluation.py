import os
import unittest

from agent_ci.evaluation.engine import EvaluationEngine
from agent_ci.evaluation.hard_rules import HardRuleEvaluator
from agent_ci.evaluation.metrics import CorrectnessEvaluator
from agent_ci.evaluation.types import EvaluationResult
from agent_ci.rubric import score_response


class TestEvaluationEngine(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_structured_metric_result(self):
        tc = {
            "user_message": "test",
            "must_include": ["refund"],
            "must_not_include": [],
            "judge_rubric": "Should mention refund.",
        }
        result = score_response("You are eligible for a refund.", tc)
        correctness = result["metrics"]["correctness"]
        for key in ("metric", "score", "passed", "reason"):
            self.assertIn(key, correctness)
        self.assertEqual(correctness["metric"], "correctness")

    def test_final_score_uses_configured_weights(self):
        engine = EvaluationEngine(
            evaluators=[HardRuleEvaluator(), CorrectnessEvaluator()],
            weights={"hard_rules": 0.6, "correctness": 0.4},
        )
        tc = {
            "user_message": "test",
            "must_include": ["yes"],
            "must_not_include": [],
            "judge_rubric": "Should say yes.",
        }
        result = engine.evaluate("yes, confirmed", tc)
        expected = round(0.6 * 1.0 + 0.4 * result["metrics"]["correctness"]["score"], 3)
        self.assertEqual(result["final_score"], expected)

    def test_failed_evaluator_does_not_crash_run(self):
        class BrokenEvaluator(CorrectnessEvaluator):
            def evaluate(self, response: str, test_case: dict) -> EvaluationResult:
                raise RuntimeError("boom")

        engine = EvaluationEngine(
            evaluators=[HardRuleEvaluator(), BrokenEvaluator()],
            weights={"hard_rules": 0.5, "correctness": 0.5},
        )
        tc = {
            "user_message": "test",
            "must_include": [],
            "must_not_include": [],
            "judge_rubric": "n/a",
        }
        result = engine.evaluate("hello", tc)
        self.assertEqual(result["metrics"]["correctness"]["score"], 0.0)
        self.assertEqual(result["metrics"]["correctness"]["error"], "boom")
        self.assertIn("final_score", result)

    def test_malformed_live_judge_json_is_handled(self):
        from agent_ci.evaluation.llm_judge import parse_judge_response

        result = parse_judge_response("not json at all", "correctness")
        self.assertEqual(result.score, 0.5)
        self.assertEqual(result.error, "malformed_json")

    def test_valid_judge_json_is_parsed(self):
        from agent_ci.evaluation.llm_judge import parse_judge_response

        result = parse_judge_response(
            '{"score": 0.9, "passed": true, "reason": "Looks correct."}',
            "correctness",
        )
        self.assertEqual(result.score, 0.9)
        self.assertTrue(result.passed)
        self.assertEqual(result.reason, "Looks correct.")

    def test_overall_metrics_aggregation(self):
        per_test = [
            {"metrics": {"correctness": {"score": 0.8}}, "final_score": 0.8},
            {"metrics": {"correctness": {"score": 1.0}}, "final_score": 1.0},
        ]
        overall = EvaluationEngine.aggregate_overall_metrics(per_test)
        self.assertEqual(overall["correctness"], 0.9)
        self.assertEqual(overall["final_score"], 0.9)


if __name__ == "__main__":
    unittest.main()

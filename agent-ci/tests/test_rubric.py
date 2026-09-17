import os
import unittest

from agent_ci.rubric import hard_check, score_response


class TestHardCheck(unittest.TestCase):
    def test_all_required_present_no_violations(self):
        tc = {"must_include": ["refund", "14 days"], "must_not_include": ["no refunds"]}
        result = hard_check("You get a full refund within 14 days.", tc)
        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["missing_required"], [])
        self.assertEqual(result["violated_forbidden"], [])

    def test_missing_required_lowers_score(self):
        tc = {"must_include": ["refund", "14 days"], "must_not_include": []}
        result = hard_check("You get a full refund.", tc)
        self.assertEqual(result["score"], 0.5)
        self.assertEqual(result["missing_required"], ["14 days"])

    def test_forbidden_phrase_lowers_score(self):
        tc = {"must_include": [], "must_not_include": ["99.9%"]}
        result = hard_check("We guarantee 99.9% uptime.", tc)
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["violated_forbidden"], ["99.9%"])

    def test_no_hard_checks_scores_full(self):
        tc = {"must_include": [], "must_not_include": []}
        result = hard_check("Any response.", tc)
        self.assertEqual(result["score"], 1.0)


class TestScoreResponse(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_combined_score_matches_final_score(self):
        tc = {
            "user_message": "test",
            "must_include": ["yes"],
            "must_not_include": [],
            "judge_rubric": "Should say yes.",
        }
        result = score_response("yes, confirmed", tc)
        self.assertIn("combined_score", result)
        self.assertIn("final_score", result)
        self.assertIn("metrics", result)
        self.assertIn("hard_check", result)
        self.assertIn("llm_judge", result)
        self.assertEqual(result["combined_score"], result["final_score"])
        self.assertIn("hard_rules", result["metrics"])


if __name__ == "__main__":
    unittest.main()

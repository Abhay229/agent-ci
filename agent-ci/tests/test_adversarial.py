"""Tests for adversarial evaluation scenarios."""

from __future__ import annotations

import os
import unittest

from agent_ci.agent import run_agent
from agent_ci.conversation import get_test_type
from agent_ci.dataset import ADVERSARIAL_TEST_CASES, TEST_CASES
from agent_ci.diff import build_diff_report
from agent_ci.rubric import score_response


class TestAdversarialDataset(unittest.TestCase):
    def test_adversarial_category_present(self):
        adversarial = [tc for tc in TEST_CASES if tc["category"] == "adversarial"]
        self.assertEqual(len(adversarial), 5)
        self.assertEqual(len(ADVERSARIAL_TEST_CASES), 5)

    def test_all_adversarial_are_single_turn(self):
        for tc in ADVERSARIAL_TEST_CASES:
            self.assertEqual(get_test_type(tc), "single_turn")
            self.assertIn("user_message", tc)

    def test_required_adversarial_ids(self):
        ids = {tc["id"] for tc in ADVERSARIAL_TEST_CASES}
        expected = {
            "adv_prompt_injection",
            "adv_invent_unsupported_info",
            "adv_false_completion_claim",
            "adv_bypass_plan_restrictions",
            "adv_misleading_policy_claim",
        }
        self.assertEqual(ids, expected)


class TestAdversarialEvaluation(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ["AGENT_CI_MOCK_RAG"] = "1"

    def test_baseline_fails_adversarial_hard_rules(self):
        tc = next(t for t in ADVERSARIAL_TEST_CASES if t["id"] == "adv_prompt_injection")
        response = run_agent(tc, role="baseline")
        scored = score_response(response.answer, tc, retrieved_context=response.retrieved_context)
        self.assertLess(scored["final_score"], 0.7)

    def test_candidate_passes_adversarial_hard_rules(self):
        tc = next(t for t in ADVERSARIAL_TEST_CASES if t["id"] == "adv_prompt_injection")
        response = run_agent(tc, role="candidate")
        scored = score_response(response.answer, tc, retrieved_context=response.retrieved_context)
        self.assertGreaterEqual(scored["final_score"], 0.7)

    def test_adversarial_improvements_in_diff_report(self):
        report = build_diff_report()
        adv_rows = [r for r in report["rows"] if r["category"] == "adversarial"]
        self.assertEqual(len(adv_rows), 5)
        improvements = sum(1 for r in adv_rows if r["verdict"] == "IMPROVEMENT")
        self.assertGreaterEqual(improvements, 4)


if __name__ == "__main__":
    unittest.main()

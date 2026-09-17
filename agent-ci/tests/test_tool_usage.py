"""Tests for tool usage evaluation."""

from __future__ import annotations

import os
import unittest

from agent_ci.agent import run_agent
from agent_ci.dataset import TOOL_TEST_CASES
from agent_ci.diff import build_diff_report
from agent_ci.evaluation.tool_usage import ToolUsageEvaluator, evaluate_tool_usage
from agent_ci.rubric import score_response


class TestToolUsageEvaluator(unittest.TestCase):
    def test_no_expectations_scores_neutral(self):
        result = evaluate_tool_usage("hello", {"id": "x"})
        self.assertEqual(result.score, 1.0)
        self.assertTrue(result.passed)

    def test_correct_tool_passes(self):
        test_case = TOOL_TEST_CASES[0]
        tool_calls = [
            {
                "tool": "cancel_subscription",
                "arguments": {"at_period_end": True},
                "result": {"message": "ok"},
                "status": "success",
            }
        ]
        result = evaluate_tool_usage(
            "Cancellation scheduled at period end.",
            test_case,
            tool_calls=tool_calls,
        )
        self.assertEqual(result.score, 1.0)
        self.assertTrue(result.passed)

    def test_wrong_tool_fails(self):
        test_case = TOOL_TEST_CASES[0]
        tool_calls = [
            {
                "tool": "refund_customer",
                "arguments": {},
                "result": {"message": "ok"},
                "status": "success",
            }
        ]
        result = evaluate_tool_usage(
            "Refund processed.",
            test_case,
            tool_calls=tool_calls,
        )
        self.assertLess(result.score, 1.0)
        self.assertFalse(result.passed)
        self.assertIn("Forbidden tool", result.reason)

    def test_phantom_action_detected(self):
        test_case = next(t for t in TOOL_TEST_CASES if t["id"] == "tool_phantom_cancellation")
        result = evaluate_tool_usage(
            "Done — I've cancelled your subscription at period end.",
            test_case,
            tool_calls=None,
        )
        self.assertFalse(result.passed)
        self.assertIn("no tool was successfully executed", result.reason.lower())

    def test_wrong_arguments_fail(self):
        test_case = TOOL_TEST_CASES[0]
        tool_calls = [
            {
                "tool": "cancel_subscription",
                "arguments": {"at_period_end": False},
                "result": {"message": "ok"},
                "status": "success",
            }
        ]
        result = evaluate_tool_usage("Cancelled.", test_case, tool_calls=tool_calls)
        self.assertFalse(result.passed)
        self.assertIn("Expected arguments", result.reason)

    def test_evaluator_reads_context(self):
        test_case = TOOL_TEST_CASES[0]
        evaluator = ToolUsageEvaluator()
        result = evaluator.evaluate(
            "Scheduled at period end.",
            test_case,
            context={
                "tool_calls": [
                    {
                        "tool": "cancel_subscription",
                        "arguments": {"at_period_end": True},
                        "status": "success",
                    }
                ]
            },
        )
        self.assertTrue(result.passed)


class TestToolUsageIntegration(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ["AGENT_CI_MOCK_RAG"] = "1"

    def test_baseline_fails_tool_expectations(self):
        tc = TOOL_TEST_CASES[0]
        response = run_agent(tc, role="baseline")
        scored = score_response(
            response.answer,
            tc,
            tool_calls=response.tool_calls,
        )
        self.assertLess(scored["metrics"]["tool_usage"]["score"], 1.0)

    def test_candidate_passes_tool_expectations(self):
        tc = TOOL_TEST_CASES[0]
        response = run_agent(tc, role="candidate")
        scored = score_response(
            response.answer,
            tc,
            tool_calls=response.tool_calls,
        )
        self.assertEqual(scored["metrics"]["tool_usage"]["score"], 1.0)

    def test_existing_tests_unaffected_by_tool_metric(self):
        from agent_ci.dataset import SINGLE_TURN_TEST_CASES

        tc = SINGLE_TURN_TEST_CASES[0]
        response = run_agent(tc, role="baseline")
        scored = score_response(response.answer, tc, tool_calls=response.tool_calls)
        self.assertEqual(scored["metrics"]["tool_usage"]["score"], 1.0)
        self.assertTrue(scored["metrics"]["tool_usage"]["passed"])
        self.assertNotIn("tool_expectations", tc)

    def test_diff_report_includes_tool_rows(self):
        report = build_diff_report()
        tool_rows = [r for r in report["rows"] if r["category"] == "tools"]
        self.assertEqual(len(tool_rows), len(TOOL_TEST_CASES))
        cancel_row = next(r for r in tool_rows if r["id"] == "tool_cancel_subscription")
        self.assertEqual(cancel_row["verdict"], "IMPROVEMENT")
        candidate_calls = cancel_row["candidate_agent_response"].get("tool_calls") or []
        self.assertEqual(candidate_calls[0]["tool"], "cancel_subscription")


if __name__ == "__main__":
    unittest.main()

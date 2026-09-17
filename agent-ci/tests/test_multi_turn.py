"""Tests for multi-turn conversation evaluation."""

from __future__ import annotations

import os
import unittest

from agent_ci.agent import run_agent
from agent_ci.conversation import get_test_type
from agent_ci.dataset import MULTI_TURN_TEST_CASES, TEST_CASES
from agent_ci.diff import build_diff_report
from agent_ci.rubric import score_response
from agent_ci.types import AgentConfig


class TestMultiTurnDataset(unittest.TestCase):
    def test_multi_turn_cases_in_benchmark(self):
        multi = [tc for tc in TEST_CASES if get_test_type(tc) == "multi_turn"]
        self.assertEqual(len(multi), len(MULTI_TURN_TEST_CASES))
        self.assertEqual(len(MULTI_TURN_TEST_CASES), 3)

    def test_multi_turn_has_conversation(self):
        for tc in MULTI_TURN_TEST_CASES:
            self.assertIn("conversation", tc)
            self.assertEqual(tc["conversation"][-1]["role"], "user")


class TestMultiTurnAgents(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ["AGENT_CI_MOCK_RAG"] = "1"

    def test_mock_agent_returns_transcript(self):
        tc = MULTI_TURN_TEST_CASES[0]
        response = run_agent(tc, role="candidate")
        self.assertIsNotNone(response.conversation_transcript)
        self.assertEqual(response.conversation_transcript[-1]["role"], "assistant")
        self.assertEqual(len(response.conversation_transcript), 4)

    def test_candidate_answers_with_conversation_context(self):
        tc = MULTI_TURN_TEST_CASES[0]
        response = run_agent(tc, role="candidate")
        self.assertIn("20%", response.answer.lower())

    def test_evaluation_uses_conversation_context(self):
        tc = MULTI_TURN_TEST_CASES[0]
        response = run_agent(tc, role="candidate")
        scored = score_response(
            response.answer,
            tc,
            retrieved_context=response.retrieved_context,
            conversation_transcript=response.conversation_transcript,
        )
        self.assertGreaterEqual(scored["final_score"], 0.7)

    def test_llm_agent_sends_full_conversation(self):
        from agent_ci.agents.llm import LLMAgent
        from agent_ci.agents.providers.base import ProviderResult

        tc = MULTI_TURN_TEST_CASES[0]
        config = AgentConfig(name="candidate", role="candidate", mode="live", model="test-model")
        captured: dict = {}

        class FakeProvider:
            name = "fake"

            def complete(self, **kwargs):
                captured.update(kwargs)
                return ProviderResult(
                    content="Since it was two months ago, I can offer a 20% renewal discount.",
                    model="test-model",
                    provider="fake",
                    latency_ms=1.0,
                )

        agent = LLMAgent(config, FakeProvider())
        response = agent.run(tc)

        self.assertIsNotNone(captured.get("messages"))
        self.assertEqual(len(captured["messages"]), 3)
        self.assertEqual(captured["messages"][-1]["content"], "Two months ago.")
        self.assertIn("20%", response.answer.lower())


class TestMultiTurnDiffReport(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_diff_report_includes_multi_turn_rows(self):
        report = build_diff_report()
        multi_rows = [r for r in report["rows"] if r.get("test_type") == "multi_turn"]
        self.assertEqual(len(multi_rows), 3)
        for row in multi_rows:
            self.assertIn("User:", row["user_message"])
            self.assertIn("Assistant:", row["user_message"])

    def test_existing_single_turn_rows_unchanged(self):
        report = build_diff_report()
        single = next(r for r in report["rows"] if r["id"] == "refund_within_window")
        self.assertEqual(single.get("test_type"), "single_turn")
        self.assertNotIn("Assistant:", single["user_message"])


if __name__ == "__main__":
    unittest.main()

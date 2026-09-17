import os
import unittest

from agent_ci.agent import call_agent, run_agent
from agent_ci.dataset import TEST_CASES


class TestMockAgent(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ.pop("OPENROUTER_API_KEY", None)

    def test_mock_mode_returns_baseline_and_candidate_responses(self):
        tc = next(t for t in TEST_CASES if t["id"] == "refund_within_window")
        baseline = run_agent(tc, role="baseline").answer
        candidate = run_agent(tc, role="candidate").answer
        self.assertIn("refund", baseline.lower())
        self.assertIn("14-day", candidate.lower())

    def test_all_test_cases_have_mock_responses(self):
        for tc in TEST_CASES:
            baseline = call_agent(tc, version="v1")
            candidate = call_agent(tc, version="v2")
            self.assertIsInstance(baseline, str)
            self.assertIsInstance(candidate, str)
            self.assertTrue(len(baseline) > 0)
            self.assertTrue(len(candidate) > 0)


if __name__ == "__main__":
    unittest.main()

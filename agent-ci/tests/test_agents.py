import os
import unittest

from agent_ci.agent import call_agent, get_agent, run_agent
from agent_ci.agents.factory import create_agent, load_agents
from agent_ci.config import load_agent_configs, resolve_mode
from agent_ci.dataset import TEST_CASES
from agent_ci.types import AgentConfig, AgentResponse


class TestAgentConfig(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_load_agent_configs(self):
        configs = load_agent_configs()
        self.assertIn("baseline", configs)
        self.assertIn("candidate", configs)
        self.assertEqual(configs["baseline"].role, "baseline")
        self.assertEqual(configs["candidate"].role, "candidate")

    def test_auto_mode_resolves_to_mock_without_env(self):
        config = AgentConfig(name="test", role="baseline", mode="auto")
        self.assertEqual(resolve_mode(config), "mock")

    def test_auto_mode_resolves_to_live_with_env(self):
        os.environ["AGENT_CI_LIVE"] = "1"
        config = AgentConfig(name="test", role="baseline", mode="auto")
        self.assertEqual(resolve_mode(config), "live")


class TestMockAgents(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ.pop("OPENROUTER_API_KEY", None)

    def test_load_agents_returns_mock_implementations(self):
        baseline, candidate = load_agents()
        self.assertEqual(baseline.name, "baseline")
        self.assertEqual(candidate.name, "candidate")

    def test_structured_response_fields(self):
        tc = next(t for t in TEST_CASES if t["id"] == "refund_within_window")
        response = run_agent(tc, role="baseline")
        self.assertIsInstance(response, AgentResponse)
        self.assertIn("refund", response.answer.lower())
        self.assertEqual(response.provider, "mock")
        self.assertEqual(response.model, "mock")
        data = response.to_dict()
        for key in ("answer", "model", "provider", "latency_ms", "token_usage",
                    "retrieved_context", "tool_calls", "conversation_transcript", "metadata"):
            self.assertIn(key, data)

    def test_baseline_and_candidate_differ(self):
        tc = next(t for t in TEST_CASES if t["id"] == "refund_within_window")
        baseline = run_agent(tc, role="baseline")
        candidate = run_agent(tc, role="candidate")
        self.assertNotEqual(baseline.answer, candidate.answer)

    def test_legacy_call_agent_aliases(self):
        tc = next(t for t in TEST_CASES if t["id"] == "refund_within_window")
        v1 = call_agent(tc, version="v1")
        v2 = call_agent(tc, version="v2")
        self.assertEqual(v1, get_agent("baseline").run(tc).answer)
        self.assertEqual(v2, get_agent("candidate").run(tc).answer)

    def test_create_agent_respects_mock_mode(self):
        config = AgentConfig(name="baseline", role="baseline", mode="mock")
        agent = create_agent(config)
        self.assertEqual(agent.__class__.__name__, "MockAgent")


if __name__ == "__main__":
    unittest.main()

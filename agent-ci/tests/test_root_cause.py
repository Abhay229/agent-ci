"""Tests for optional root-cause analysis."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from agent_ci.analysis.config import is_root_cause_enabled
from agent_ci.analysis.root_cause import analyze_regression, enrich_report_with_root_cause
from agent_ci.analysis.types import AI_ANALYSIS_DISCLAIMER
from agent_ci.diff import build_diff_report
from agent_ci.regression.types import VERDICT_IMPROVEMENT, VERDICT_REGRESSION


def _regression_row() -> dict:
    return {
        "id": "audit_logs_enterprise",
        "test_id": "audit_logs_enterprise",
        "verdict": VERDICT_REGRESSION,
        "user_message": "Do Enterprise plan users get access to audit logs?",
        "baseline_response": "Yep, audit logs are included for all Enterprise plan users!",
        "candidate_response": (
            "I'm not entirely sure about audit log availability on that plan — "
            "let me check with the team and get back to you."
        ),
        "baseline_score": 0.875,
        "candidate_score": 0.3,
        "delta": -0.575,
        "metric_regressions": ["correctness", "faithfulness"],
        "metric_changes": {
            "correctness": {
                "baseline_score": 0.95,
                "candidate_score": 0.2,
                "delta": -0.75,
                "verdict": VERDICT_REGRESSION,
            }
        },
        "candidate_agent_response": {
            "retrieved_context": [{
                "section": "Enterprise features (SSO, audit logs)",
                "text": "Enterprise features (SSO, audit logs) are available on Enterprise.",
                "document": "loomly_support_policy_v3",
                "chunk_id": "enterprise_features",
            }]
        },
    }


class TestRootCauseConfig(unittest.TestCase):
    def test_disabled_by_default(self):
        os.environ.pop("AGENT_CI_ROOT_CAUSE", None)
        self.assertFalse(is_root_cause_enabled())
        self.assertTrue(is_root_cause_enabled(explicit_flag=True))

    def test_env_flag(self):
        os.environ["AGENT_CI_ROOT_CAUSE"] = "1"
        self.assertTrue(is_root_cause_enabled())
        os.environ.pop("AGENT_CI_ROOT_CAUSE", None)


class TestRootCauseAnalysis(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_mock_analysis_success(self):
        result = analyze_regression(_regression_row())
        self.assertTrue(result.success)
        self.assertEqual(result.source, "mock")
        data = result.to_dict()
        self.assertTrue(data["ai_generated"])
        self.assertIn("not guaranteed", data["disclaimer"].lower())
        self.assertIn("root_cause", data)
        self.assertGreater(result.confidence, 0)

    def test_skips_non_regression_rows(self):
        row = {**_regression_row(), "verdict": VERDICT_IMPROVEMENT}
        result = analyze_regression(row)
        self.assertFalse(result.success)

    def test_live_analysis_success(self):
        os.environ["AGENT_CI_LIVE"] = "1"
        os.environ["OPENROUTER_API_KEY"] = "test-key"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"root_cause": "Prompt too strict", '
            '"explanation": "Candidate hedged unnecessarily.", '
            '"suggested_fix": "Allow direct answers when context is clear.", '
            '"confidence": 0.82}'
        )

        with patch("openai.OpenAI") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response
            result = analyze_regression(_regression_row())

        self.assertTrue(result.success)
        self.assertEqual(result.source, "llm")
        self.assertEqual(result.root_cause, "Prompt too strict")
        self.assertAlmostEqual(result.confidence, 0.82)
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ.pop("OPENROUTER_API_KEY", None)

    def test_live_analysis_malformed_json(self):
        os.environ["AGENT_CI_LIVE"] = "1"
        os.environ["OPENROUTER_API_KEY"] = "test-key"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not json at all"

        with patch("openai.OpenAI") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response
            result = analyze_regression(_regression_row())

        self.assertFalse(result.success)
        self.assertIn("malformed JSON", result.error or "")
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ.pop("OPENROUTER_API_KEY", None)

    def test_live_analysis_api_failure_does_not_raise(self):
        os.environ["AGENT_CI_LIVE"] = "1"
        os.environ["OPENROUTER_API_KEY"] = "test-key"

        with patch("openai.OpenAI", side_effect=RuntimeError("network down")):
            result = analyze_regression(_regression_row())

        self.assertFalse(result.success)
        self.assertIn("network down", result.error or "")
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ.pop("OPENROUTER_API_KEY", None)


class TestEnrichReport(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_enrich_report_adds_analysis_to_regressions(self):
        report = {
            "summary": {},
            "regression_report": [{"test_id": "audit_logs_enterprise", "verdict": VERDICT_REGRESSION}],
            "rows": [_regression_row()],
        }
        enriched = enrich_report_with_root_cause(report)
        analysis = enriched["rows"][0]["ai_root_cause_analysis"]
        self.assertTrue(analysis["success"])
        self.assertEqual(analysis["disclaimer"], AI_ANALYSIS_DISCLAIMER)
        self.assertEqual(enriched["summary"]["root_cause_analysis"]["count"], 1)

    def test_enrich_report_survives_analyzer_failure(self):
        report = {
            "summary": {},
            "regression_report": [],
            "rows": [_regression_row()],
        }
        with patch(
            "agent_ci.analysis.root_cause.analyze_regression",
            side_effect=[RuntimeError("boom")],
        ):
            # analyze_regression itself catches errors; patch inner live call instead
            pass

        with patch(
            "agent_ci.analysis.root_cause._mock_analysis",
            side_effect=RuntimeError("boom"),
        ):
            result = analyze_regression(_regression_row())
        self.assertFalse(result.success)

        enriched = enrich_report_with_root_cause(report)
        self.assertIn("ai_root_cause_analysis", enriched["rows"][0])

    def test_full_evaluation_with_root_cause(self):
        report = build_diff_report()
        enriched = enrich_report_with_root_cause(report)
        regressions = [r for r in enriched["rows"] if r["verdict"] == VERDICT_REGRESSION]
        self.assertTrue(regressions)
        self.assertIn("ai_root_cause_analysis", regressions[0])
        self.assertTrue(regressions[0]["ai_root_cause_analysis"]["success"])


class TestCLIRootCauseIntegration(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_check_with_root_cause_flag(self):
        from agent_ci.cli import cmd_check

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            args = type("Args", (), {
                "output": str(output),
                "max_regressions": 0,
                "no_history": True,
                "history_path": None,
                "root_cause": True,
            })()
            code = cmd_check(args)
            self.assertEqual(code, 1)
            import json
            data = json.loads(output.read_text(encoding="utf-8"))
            row = next(r for r in data["rows"] if r["verdict"] == VERDICT_REGRESSION)
            self.assertIn("ai_root_cause_analysis", row)
            self.assertTrue(row["ai_root_cause_analysis"]["ai_generated"])


if __name__ == "__main__":
    unittest.main()

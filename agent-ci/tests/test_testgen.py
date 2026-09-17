"""Tests for optional AI-assisted test generation."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_ci.diff import build_diff_report
from agent_ci.regression.types import VERDICT_IMPROVEMENT, VERDICT_REGRESSION
from agent_ci.testgen.config import is_test_generation_enabled
from agent_ci.testgen.generator import generate_tests_for_regression, generate_tests_for_report
from agent_ci.testgen.store import GeneratedTestStore
from agent_ci.testgen.types import AI_TEST_DISCLAIMER
from agent_ci.testgen.validator import TestValidationError, validate_generated_test, validate_generated_tests


def _regression_row() -> dict:
    return {
        "id": "audit_logs_enterprise",
        "test_id": "audit_logs_enterprise",
        "category": "policy",
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
        "metric_regressions": ["correctness"],
        "explanation": "Overall score decreased.",
        "candidate_agent_response": {
            "retrieved_context": [{
                "section": "Enterprise features",
                "text": "Audit logs are Enterprise-only.",
                "document": "policy",
                "chunk_id": "enterprise_features",
            }]
        },
    }


class TestTestGenConfig(unittest.TestCase):
    def test_disabled_by_default(self):
        os.environ.pop("AGENT_CI_GENERATE_TESTS", None)
        self.assertFalse(is_test_generation_enabled())
        self.assertTrue(is_test_generation_enabled(explicit_flag=True))


class TestValidator(unittest.TestCase):
    def test_valid_test(self):
        raw = {
            "id": "ai_gen_audit_logs_pro",
            "category": "policy",
            "user_message": "Does Pro have audit logs?",
            "judge_rubric": "Audit logs are Enterprise-only.",
            "must_include": ["enterprise"],
            "must_not_include": [],
        }
        result = validate_generated_test(raw, source_test_id="audit_logs_enterprise")
        self.assertEqual(result["disclaimer"], AI_TEST_DISCLAIMER)
        self.assertFalse(result["trusted"])
        self.assertTrue(result["ai_generated"])
        self.assertEqual(result["review_status"], "pending")

    def test_missing_field_rejected(self):
        with self.assertRaises(TestValidationError):
            validate_generated_test({"id": "ai_gen_x", "category": "policy"})

    def test_invalid_id_rejected(self):
        with self.assertRaises(TestValidationError):
            validate_generated_test({
                "id": "Bad ID!",
                "category": "policy",
                "user_message": "Does Pro have audit logs?",
                "judge_rubric": "Enterprise only.",
            })

    def test_validate_list_collects_errors(self):
        valid, errors = validate_generated_tests([
            {
                "id": "ai_gen_ok",
                "category": "policy",
                "user_message": "Does Pro have audit logs?",
                "judge_rubric": "Enterprise only.",
            },
            {"id": "bad"},
        ])
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(errors), 1)


class TestGenerator(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_mock_generation_success(self):
        batch = generate_tests_for_regression(_regression_row())
        self.assertTrue(batch.success)
        self.assertEqual(batch.source, "mock")
        self.assertGreaterEqual(len(batch.tests), 3)
        messages = [t["user_message"] for t in batch.tests]
        self.assertTrue(any("Pro" in m for m in messages))
        self.assertTrue(any("Free" in m for m in messages))
        for test in batch.tests:
            self.assertEqual(test["disclaimer"], AI_TEST_DISCLAIMER)
            self.assertFalse(test["trusted"])

    def test_skips_non_regression(self):
        row = {**_regression_row(), "verdict": VERDICT_IMPROVEMENT}
        batch = generate_tests_for_regression(row)
        self.assertFalse(batch.success)

    def test_live_generation_success(self):
        os.environ["AGENT_CI_LIVE"] = "1"
        os.environ["OPENROUTER_API_KEY"] = "test-key"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "tests": [{
                "id": "ai_gen_live_example",
                "category": "policy",
                "user_message": "Does Pro have audit logs?",
                "judge_rubric": "Should say Enterprise only.",
                "must_include": [],
                "must_not_include": [],
            }]
        })

        with patch("openai.OpenAI") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response
            batch = generate_tests_for_regression(_regression_row())

        self.assertTrue(batch.success)
        self.assertEqual(batch.source, "llm")
        self.assertEqual(batch.tests[0]["id"], "ai_gen_live_example")
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ.pop("OPENROUTER_API_KEY", None)

    def test_live_generation_failure_does_not_raise(self):
        os.environ["AGENT_CI_LIVE"] = "1"
        os.environ["OPENROUTER_API_KEY"] = "test-key"

        with patch("openai.OpenAI", side_effect=RuntimeError("network down")):
            batch = generate_tests_for_regression(_regression_row())

        self.assertFalse(batch.success)
        self.assertIn("network down", batch.error or "")
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ.pop("OPENROUTER_API_KEY", None)

    def test_malformed_live_output_fails_gracefully(self):
        os.environ["AGENT_CI_LIVE"] = "1"
        os.environ["OPENROUTER_API_KEY"] = "test-key"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not json"

        with patch("openai.OpenAI") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response
            batch = generate_tests_for_regression(_regression_row())

        self.assertFalse(batch.success)
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ.pop("OPENROUTER_API_KEY", None)


class TestGeneratedTestStore(unittest.TestCase):
    def test_save_list_approve_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "pending.jsonl"
            approved = Path(tmp) / "approved.jsonl"
            rejected = Path(tmp) / "rejected.jsonl"
            store = GeneratedTestStore(
                pending_path=pending,
                approved_path=approved,
                rejected_path=rejected,
            )

            from agent_ci.testgen.types import GeneratedTestBatch

            batch = GeneratedTestBatch(
                generation_id="gen-123",
                timestamp="2026-01-01T00:00:00+00:00",
                source_test_id="audit_logs_enterprise",
                review_status="pending",
                source="mock",
                success=True,
                tests=[{
                    "id": "ai_gen_audit_logs_pro",
                    "category": "policy",
                    "user_message": "Does Pro have audit logs?",
                    "judge_rubric": "Enterprise only.",
                    "disclaimer": AI_TEST_DISCLAIMER,
                    "ai_generated": True,
                    "trusted": False,
                    "review_status": "pending",
                    "source_test_id": "audit_logs_enterprise",
                    "must_include": [],
                    "must_not_include": [],
                }],
            )
            store.save_batch(batch)
            self.assertEqual(len(store.list_pending()), 1)

            shown = store.get_batch("gen-123")
            self.assertIsNotNone(shown)

            approved_batch = store.approve("gen-123", reviewer_note="looks good")
            self.assertEqual(approved_batch["review_status"], "approved")
            self.assertEqual(len(store.list_pending()), 0)
            self.assertEqual(len(store.list_approved()), 1)

            store.save_batch(batch)
            store.reject("gen-123", reviewer_note="duplicate")
            self.assertEqual(len(store.list_pending()), 0)


class TestReportIntegration(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_generate_tests_for_report(self):
        report = build_diff_report()
        batches = generate_tests_for_report(report)
        self.assertTrue(batches)
        row = next(r for r in report["rows"] if r["id"] == "audit_logs_enterprise")
        self.assertIn("ai_generated_tests", row)
        self.assertTrue(row["ai_generated_tests"]["success"])


class TestCLIGenerateTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)

    def test_check_with_generate_tests(self):
        from agent_ci.cli import cmd_check

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            pending = Path(tmp) / "pending.jsonl"
            args = type("Args", (), {
                "output": str(output),
                "max_regressions": 0,
                "no_history": True,
                "history_path": None,
                "root_cause": False,
                "generate_tests": True,
                "generated_tests_path": str(pending),
            })()
            code = cmd_check(args)
            self.assertEqual(code, 1)
            self.assertTrue(pending.exists())
            lines = pending.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreaterEqual(len(lines), 1)
            batch = json.loads(lines[0])
            self.assertEqual(batch["disclaimer"], AI_TEST_DISCLAIMER)
            self.assertTrue(batch["tests"])


if __name__ == "__main__":
    unittest.main()

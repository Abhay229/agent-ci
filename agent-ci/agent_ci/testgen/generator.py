"""Optional AI-assisted test generation from regressions."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from agent_ci.analysis.root_cause import _build_analysis_input
from agent_ci.dataset import TEST_CASES
from agent_ci.evaluation.llm_judge import _extract_json_object
from agent_ci.regression.types import VERDICT_REGRESSION
from agent_ci.testgen.config import DEFAULT_JUDGE_MODEL, is_live_generation
from agent_ci.testgen.types import AI_TEST_DISCLAIMER, GeneratedTestBatch
from agent_ci.testgen.validator import validate_generated_tests

logger = logging.getLogger(__name__)

_TEST_CASE_INDEX = {tc["id"]: tc for tc in TEST_CASES}


def _build_generation_input(row: dict[str, Any]) -> dict[str, Any]:
    test_id = row.get("id") or row.get("test_id")
    metadata = _TEST_CASE_INDEX.get(test_id or {}, {})
    analysis = _build_analysis_input(row)

    return {
        "source_test_id": test_id,
        "original_test": {
            "id": test_id,
            "category": metadata.get("category", row.get("category", "policy")),
            "user_message": metadata.get("user_message") or row.get("user_message", ""),
            "judge_rubric": metadata.get("judge_rubric", ""),
            "must_include": metadata.get("must_include", []),
            "must_not_include": metadata.get("must_not_include", []),
        },
        "regression": {
            "verdict": row.get("verdict"),
            "delta": row.get("delta"),
            "baseline_score": row.get("baseline_score"),
            "candidate_score": row.get("candidate_score"),
            "metric_regressions": row.get("metric_regressions") or [],
            "explanation": row.get("explanation", ""),
        },
        "policy_context": analysis.get("retrieved_context", ""),
        "baseline_response": row.get("baseline_response", ""),
        "candidate_response": row.get("candidate_response", ""),
    }


def _mock_generated_tests(gen_input: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic related tests for mock mode — no API key required."""
    source_id = gen_input.get("source_test_id", "unknown")
    category = gen_input["original_test"].get("category", "policy")

    if source_id == "audit_logs_enterprise":
        return [
            {
                "id": "ai_gen_audit_logs_pro",
                "category": category,
                "user_message": "Does Pro have audit logs?",
                "judge_rubric": "Audit logs are Enterprise-only; Pro should not be told it has audit logs.",
                "must_include": ["enterprise"],
                "must_not_include": ["yes, pro includes audit logs"],
            },
            {
                "id": "ai_gen_audit_logs_free",
                "category": category,
                "user_message": "Does Free have audit logs?",
                "judge_rubric": "Audit logs are Enterprise-only; Free plan should not include audit logs.",
                "must_include": ["enterprise"],
                "must_not_include": ["yes, free includes audit logs"],
            },
            {
                "id": "ai_gen_audit_logs_export",
                "category": category,
                "user_message": "Can Enterprise export audit logs?",
                "judge_rubric": "Only answer if policy mentions export; otherwise say unsure rather than inventing.",
                "must_include": [],
                "must_not_include": [],
            },
            {
                "id": "ai_gen_audit_logs_included",
                "category": category,
                "user_message": "Are audit logs included in Enterprise?",
                "judge_rubric": "Should confidently confirm audit logs are an Enterprise feature when policy supports it.",
                "must_include": ["yes", "enterprise"],
                "must_not_include": ["not sure", "let me check"],
            },
        ]

    original_message = gen_input["original_test"].get("user_message", "support question")
    return [
        {
            "id": f"ai_gen_{source_id}_variant_a",
            "category": category,
            "user_message": f"Follow-up: {original_message}",
            "judge_rubric": "Related scenario to the original regression — verify policy-grounded answer.",
            "must_include": [],
            "must_not_include": [],
        },
        {
            "id": f"ai_gen_{source_id}_variant_b",
            "category": category,
            "user_message": f"Can you clarify: {original_message}",
            "judge_rubric": "Related scenario testing similar behavior under a rephrased question.",
            "must_include": [],
            "must_not_include": [],
        },
    ]


def _live_generated_tests(gen_input: dict[str, Any], model: str) -> list[dict[str, Any]]:
    from openai import OpenAI

    original = gen_input["original_test"]
    regression = gen_input["regression"]
    prompt = (
        "You are helping expand an LLM agent regression test suite.\n\n"
        "Original test case:\n"
        f"- id: {original.get('id')}\n"
        f"- question: {original.get('user_message')}\n"
        f"- expected behavior: {original.get('judge_rubric')}\n\n"
        "Regression information:\n"
        f"- score delta: {regression.get('delta')}\n"
        f"- failed metrics: {', '.join(regression.get('metric_regressions') or []) or 'none'}\n"
        f"- explanation: {regression.get('explanation')}\n\n"
        f"Policy/context:\n{gen_input.get('policy_context')}\n\n"
        f"Baseline response:\n{gen_input.get('baseline_response')}\n\n"
        f"Candidate response:\n{gen_input.get('candidate_response')}\n\n"
        "Generate 3-5 RELATED test cases that probe similar behavior (plan tiers, "
        "edge cases, rephrasings). These are suggestions for human review — not ground truth.\n\n"
        "Respond with ONLY valid JSON in this shape:\n"
        "{\n"
        '  "tests": [\n'
        "    {\n"
        '      "id": "ai_gen_example_id",\n'
        '      "category": "policy",\n'
        '      "user_message": "customer question",\n'
        '      "judge_rubric": "what good behavior looks like",\n'
        '      "must_include": [],\n'
        '      "must_not_include": []\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Every id must start with ai_gen_."
    )

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=800,
    )
    content = (resp.choices[0].message.content or "").strip()
    payload = _extract_json_object(content)
    if payload is None or not isinstance(payload.get("tests"), list):
        raise ValueError("LLM returned malformed test generation JSON.")
    return payload["tests"]


def generate_tests_for_regression(
    row: dict[str, Any],
    *,
    model: str = DEFAULT_JUDGE_MODEL,
) -> GeneratedTestBatch:
    """Generate related tests for one regression. Never raises."""
    generation_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    source_test_id = row.get("id") or row.get("test_id") or "unknown"

    if row.get("verdict") != VERDICT_REGRESSION:
        return GeneratedTestBatch(
            generation_id=generation_id,
            timestamp=timestamp,
            source_test_id=source_test_id,
            review_status="skipped",
            source="mock",
            success=False,
            error="Not a regression row.",
        )

    gen_input = _build_generation_input(row)
    source = "llm" if is_live_generation() else "mock"

    try:
        raw_tests = (
            _live_generated_tests(gen_input, model)
            if is_live_generation()
            else _mock_generated_tests(gen_input)
        )
        valid_tests, validation_errors = validate_generated_tests(
            raw_tests,
            source_test_id=source_test_id,
        )
        if not valid_tests:
            return GeneratedTestBatch(
                generation_id=generation_id,
                timestamp=timestamp,
                source_test_id=source_test_id,
                review_status="failed",
                source=source,
                success=False,
                regression_summary=gen_input["regression"],
                error="; ".join(validation_errors) or "No valid tests generated.",
            )

        return GeneratedTestBatch(
            generation_id=generation_id,
            timestamp=timestamp,
            source_test_id=source_test_id,
            review_status="pending",
            source=source,
            success=True,
            tests=valid_tests,
            regression_summary=gen_input["regression"],
            error="; ".join(validation_errors) if validation_errors else None,
        )
    except Exception as exc:
        logger.warning("Test generation failed for %s", source_test_id, exc_info=True)
        return GeneratedTestBatch(
            generation_id=generation_id,
            timestamp=timestamp,
            source_test_id=source_test_id,
            review_status="failed",
            source=source,
            success=False,
            regression_summary=gen_input.get("regression", {}),
            error=str(exc),
        )


def generate_tests_for_report(
    report: dict[str, Any],
    *,
    model: str = DEFAULT_JUDGE_MODEL,
) -> list[GeneratedTestBatch]:
    """Generate related tests for every regression in a diff report."""
    batches: list[GeneratedTestBatch] = []
    for row in report.get("rows", []):
        if row.get("verdict") != VERDICT_REGRESSION:
            continue
        batch = generate_tests_for_regression(row, model=model)
        batches.append(batch)
        row["ai_generated_tests"] = {
            "generation_id": batch.generation_id,
            "count": len(batch.tests),
            "review_status": batch.review_status,
            "disclaimer": AI_TEST_DISCLAIMER,
            "success": batch.success,
        }
    return batches

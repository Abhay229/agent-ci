"""Optional LLM-based regression root-cause analysis."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from agent_ci.analysis.config import DEFAULT_JUDGE_MODEL, is_live_analysis
from agent_ci.analysis.types import RootCauseAnalysis
from agent_ci.dataset import TEST_CASES
from agent_ci.evaluation.llm_judge import _extract_json_object
from agent_ci.regression.types import VERDICT_REGRESSION

logger = logging.getLogger(__name__)

_TEST_CASE_INDEX = {tc["id"]: tc for tc in TEST_CASES}


def _format_context(chunks: list[dict[str, Any]] | None) -> str:
    if not chunks:
        return "No retrieved policy context."
    parts = []
    for chunk in chunks:
        section = chunk.get("section", "Unknown")
        text = chunk.get("text", "")
        parts.append(f"[{section}]\n{text}")
    return "\n\n".join(parts)


def _format_metrics(metric_changes: dict[str, dict[str, Any]] | None) -> str:
    if not metric_changes:
        return "No per-metric breakdown available."
    lines = []
    for name, change in sorted(metric_changes.items()):
        lines.append(
            f"- {name}: baseline={change.get('baseline_score')} "
            f"candidate={change.get('candidate_score')} "
            f"delta={change.get('delta')} verdict={change.get('verdict')}"
        )
    return "\n".join(lines)


def _build_analysis_input(row: dict[str, Any]) -> dict[str, Any]:
    test_id = row.get("id") or row.get("test_id")
    metadata = _TEST_CASE_INDEX.get(test_id or {}, {})
    candidate_agent = row.get("candidate_agent_response") or {}

    return {
        "test_id": test_id,
        "question": row.get("user_message") or row.get("question") or metadata.get("user_message", ""),
        "expected_behavior": metadata.get("judge_rubric", ""),
        "retrieved_context": _format_context(candidate_agent.get("retrieved_context")),
        "baseline_response": row.get("baseline_response", ""),
        "candidate_response": row.get("candidate_response", ""),
        "baseline_score": row.get("baseline_score"),
        "candidate_score": row.get("candidate_score"),
        "delta": row.get("delta"),
        "baseline_metrics": _format_metrics(row.get("metric_changes")),
        "candidate_metrics": _format_metrics(row.get("metric_changes")),
        "failed_metrics": row.get("metric_regressions") or [],
    }


def _normalize_payload(payload: dict[str, Any]) -> RootCauseAnalysis:
    confidence_raw = payload.get("confidence", 0.5)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    return RootCauseAnalysis(
        root_cause=str(payload.get("root_cause") or "Unknown root cause."),
        explanation=str(payload.get("explanation") or "No explanation provided."),
        suggested_fix=str(payload.get("suggested_fix") or "Review prompt and policy grounding."),
        confidence=round(confidence, 3),
        source="llm" if is_live_analysis() else "mock",
        success=True,
    )


def _mock_analysis(row: dict[str, Any], analysis_input: dict[str, Any]) -> RootCauseAnalysis:
    """Deterministic mock analysis — no API key required."""
    test_id = analysis_input.get("test_id", "")
    failed = analysis_input.get("failed_metrics") or []
    delta = float(row.get("delta") or 0)

    if test_id == "audit_logs_enterprise":
        return RootCauseAnalysis(
            root_cause="Over-cautious policy grounding",
            explanation=(
                "The candidate agent hedged even though retrieved policy context mentions "
                "audit logs as an Enterprise feature. The stricter RAG-only prompt likely "
                "pushed the model to defer instead of confirming a supported capability."
            ),
            suggested_fix=(
                "Refine the candidate prompt to allow direct confirmation when retrieved "
                "context clearly answers the question. Add an example for Enterprise-only "
                "features that are explicitly present in context."
            ),
            confidence=0.78,
            source="mock",
        )

    return RootCauseAnalysis(
        root_cause="Candidate response quality decreased versus baseline",
        explanation=(
            f"Scores dropped by {abs(delta):.3f} on test '{test_id}'. "
            f"Regressed metrics: {', '.join(failed) if failed else 'overall score'}."
        ),
        suggested_fix=(
            "Compare baseline and candidate prompts, then inspect retrieved context and "
            "hard-check requirements for this scenario."
        ),
        confidence=0.55,
        source="mock",
    )


def _live_analysis(analysis_input: dict[str, Any], model: str) -> RootCauseAnalysis:
    from openai import OpenAI

    prompt = (
        "You are an expert at diagnosing LLM agent regressions.\n\n"
        f"Test question:\n{analysis_input['question']}\n\n"
        f"Expected behavior:\n{analysis_input['expected_behavior']}\n\n"
        f"Retrieved policy/context:\n{analysis_input['retrieved_context']}\n\n"
        f"Baseline response:\n{analysis_input['baseline_response']}\n\n"
        f"Candidate response:\n{analysis_input['candidate_response']}\n\n"
        f"Baseline score: {analysis_input['baseline_score']}\n"
        f"Candidate score: {analysis_input['candidate_score']}\n"
        f"Score delta: {analysis_input['delta']}\n\n"
        f"Metric breakdown:\n{analysis_input['baseline_metrics']}\n\n"
        f"Failed metrics: {', '.join(analysis_input['failed_metrics']) or 'none listed'}\n\n"
        "Explain why the candidate regressed. Respond with ONLY valid JSON in this shape:\n"
        "{\n"
        '  "root_cause": "short label",\n'
        '  "explanation": "detailed explanation",\n'
        '  "suggested_fix": "actionable fix",\n'
        '  "confidence": 0.0\n'
        "}\n"
        "confidence must be between 0 and 1."
    )

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=400,
    )
    content = (resp.choices[0].message.content or "").strip()
    payload = _extract_json_object(content)
    if payload is None:
        return RootCauseAnalysis.failed(source="llm", error="LLM returned malformed JSON.")
    result = _normalize_payload(payload)
    result.source = "llm"
    return result


def analyze_regression(
    row: dict[str, Any],
    *,
    model: str = DEFAULT_JUDGE_MODEL,
) -> RootCauseAnalysis:
    """Analyze one regression. Never raises — returns a failed result on error."""
    if row.get("verdict") != VERDICT_REGRESSION:
        return RootCauseAnalysis.failed(source="mock", error="Not a regression row.")

    analysis_input = _build_analysis_input(row)
    try:
        if is_live_analysis():
            return _live_analysis(analysis_input, model)
        return _mock_analysis(row, analysis_input)
    except Exception as exc:
        logger.warning("Root-cause analysis failed for %s", analysis_input.get("test_id"), exc_info=True)
        source = "llm" if is_live_analysis() else "mock"
        return RootCauseAnalysis.failed(source=source, error=str(exc))


def enrich_report_with_root_cause(
    report: dict[str, Any],
    *,
    model: str = DEFAULT_JUDGE_MODEL,
) -> dict[str, Any]:
    """Attach optional AI root-cause analysis to regression rows.

    Failures are captured per row and never interrupt report generation.
    """
    analysis_by_id: dict[str, dict[str, Any]] = {}

    for row in report.get("rows", []):
        if row.get("verdict") != VERDICT_REGRESSION:
            continue
        test_id = row.get("id") or row.get("test_id")
        if not test_id:
            continue
        result = analyze_regression(row, model=model)
        payload = result.to_dict()
        row["ai_root_cause_analysis"] = payload
        analysis_by_id[test_id] = payload

    for entry in report.get("regression_report", []):
        test_id = entry.get("test_id")
        if test_id in analysis_by_id:
            entry["ai_root_cause_analysis"] = analysis_by_id[test_id]

    summary = report.setdefault("summary", {})
    summary["root_cause_analysis"] = {
        "enabled": True,
        "count": len(analysis_by_id),
        "source": "llm" if is_live_analysis() else "mock",
    }

    return report

"""
The RUBRIC.

Backward-compatible entry points that delegate to the modular evaluation engine.
"""

from __future__ import annotations

from typing import Any

from agent_ci.conversation import get_test_type
from agent_ci.evaluation.engine import get_engine
from agent_ci.evaluation.hard_rules import HardRuleEvaluator


def hard_check(response: str, test_case: dict) -> dict:
    """Legacy hard-check API."""
    result = HardRuleEvaluator().evaluate(response, test_case)
    details = result.details or {}
    return {
        "score": result.score,
        "missing_required": details.get("missing_required", []),
        "violated_forbidden": details.get("violated_forbidden", []),
    }


def llm_judge(response: str, test_case: dict, model: str = "google/gemini-2.0-flash-001") -> dict:
    """Legacy LLM-judge view derived from modular LLM metric evaluators."""
    _ = model
    evaluation = get_engine().evaluate(response, test_case)
    return evaluation["llm_judge"]


def score_response(
    response: str,
    test_case: dict,
    weights: tuple[float, float] | None = None,
    retrieved_context: list[dict] | None = None,
    conversation_transcript: list[dict[str, str]] | None = None,
    tool_calls: list[dict] | None = None,
) -> dict[str, Any]:
    """Evaluate a response and return per-test metrics plus final score."""
    _ = weights  # legacy tuple ignored; weights come from metric_weights.json
    evaluation_context: dict = {"test_type": get_test_type(test_case)}
    if conversation_transcript:
        evaluation_context["conversation_transcript"] = conversation_transcript
    if retrieved_context:
        evaluation_context["retrieved_context"] = retrieved_context
    if tool_calls is not None:
        evaluation_context["tool_calls"] = tool_calls
    return get_engine().evaluate(response, test_case, evaluation_context)

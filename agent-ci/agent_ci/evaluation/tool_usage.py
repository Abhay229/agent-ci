"""Evaluator for agent tool selection, arguments, and phantom action claims."""

from __future__ import annotations

from typing import Any

from agent_ci.evaluation.base import BaseEvaluator
from agent_ci.evaluation.types import EvaluationResult
from agent_ci.tools.types import STATUS_SUCCESS, normalize_tool_calls

DEFAULT_COMPLETION_PHRASES = [
    "has been processed",
    "has been cancelled",
    "has been canceled",
    "i've cancelled",
    "i've canceled",
    "i have cancelled",
    "i have canceled",
    "refund processed",
    "subscription cancelled",
    "subscription canceled",
    "done for you",
    "completed your",
    "already processed",
]


def _arguments_match(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    for key, value in expected.items():
        if key not in actual:
            return False
        if actual[key] != value:
            return False
    return True


def _successful_tools(tool_calls: list) -> list:
    return [call for call in tool_calls if call.status == STATUS_SUCCESS]


def _detect_phantom_action(
    response: str,
    tool_calls: list,
    phrases: list[str],
) -> str | None:
    """Return an explanation when the agent claims completion without a successful tool."""
    if not phrases:
        return None

    text = response.lower()
    matched = [phrase for phrase in phrases if phrase.lower() in text]
    if not matched:
        return None

    if _successful_tools(tool_calls):
        return None

    return (
        "Agent claimed an action was completed "
        f"({', '.join(matched)}) but no tool was successfully executed."
    )


def evaluate_tool_usage(
    response: str,
    test_case: dict,
    tool_calls: list[dict[str, Any]] | None = None,
) -> EvaluationResult:
    """Evaluate tool usage for one test case."""
    expectations = test_case.get("tool_expectations")
    if not expectations:
        return EvaluationResult(
            metric="tool_usage",
            score=1.0,
            passed=True,
            reason="No tool expectations defined for this test case.",
        )

    calls = normalize_tool_calls(tool_calls)
    issues: list[str] = []
    checks = 0
    passed_checks = 0

    forbidden = expectations.get("forbidden_tools") or []
    if forbidden:
        checks += 1
        used_forbidden = [call.tool for call in calls if call.tool in forbidden]
        if used_forbidden:
            issues.append(f"Forbidden tool(s) used: {', '.join(used_forbidden)}")
        else:
            passed_checks += 1

    expected_tool = expectations.get("expected_tool")
    if expected_tool:
        checks += 1
        if any(call.tool == expected_tool for call in calls):
            passed_checks += 1
        else:
            used = ", ".join(call.tool for call in calls) or "none"
            issues.append(f"Expected tool {expected_tool!r}, but agent used: {used}")

    expected_arguments = expectations.get("expected_arguments")
    if expected_arguments and expected_tool:
        checks += 1
        matching = [
            call for call in calls
            if call.tool == expected_tool and _arguments_match(expected_arguments, call.arguments)
        ]
        if matching:
            passed_checks += 1
        else:
            actual_args = [
                call.arguments for call in calls if call.tool == expected_tool
            ]
            issues.append(
                f"Expected arguments {expected_arguments} for {expected_tool!r}, "
                f"got {actual_args or 'no matching tool call'}."
            )

    require_execution = expectations.get("require_execution", bool(expected_tool))
    if require_execution:
        checks += 1
        if _successful_tools(calls):
            passed_checks += 1
        elif calls:
            issues.append("Tool was invoked but did not complete successfully.")
        else:
            issues.append("Required tool execution missing.")

    should_detect_phantom = bool(
        expectations.get("detect_phantom_actions")
        or test_case.get("action_completion_phrases")
    )
    if should_detect_phantom:
        completion_phrases = (
            test_case.get("action_completion_phrases")
            or expectations.get("action_completion_phrases")
            or DEFAULT_COMPLETION_PHRASES
        )
        checks += 1
        phantom_issue = _detect_phantom_action(response, calls, completion_phrases)
        if phantom_issue:
            issues.append(phantom_issue)
        else:
            passed_checks += 1

    if checks == 0:
        score = 1.0
        passed = True
        reason = "Tool expectations present but no checks applied."
    else:
        score = round(passed_checks / checks, 3)
        passed = not issues

    reason = "; ".join(issues) if issues else "Tool usage matched expectations."

    return EvaluationResult(
        metric="tool_usage",
        score=score,
        passed=passed,
        reason=reason,
        details={
            "tool_calls": [call.to_dict() for call in calls],
            "issues": issues,
            "checks_run": checks,
            "checks_passed": passed_checks,
        },
    )


class ToolUsageEvaluator(BaseEvaluator):
    metric = "tool_usage"

    def evaluate(
        self,
        response: str,
        test_case: dict,
        context: dict | None = None,
    ) -> EvaluationResult:
        tool_calls = (context or {}).get("tool_calls")
        return evaluate_tool_usage(response, test_case, tool_calls=tool_calls)

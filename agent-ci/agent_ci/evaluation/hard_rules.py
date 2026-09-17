"""Deterministic hard-rule evaluator."""

from __future__ import annotations

from agent_ci.evaluation.base import BaseEvaluator
from agent_ci.evaluation.types import EvaluationResult


class HardRuleEvaluator(BaseEvaluator):
    metric = "hard_rules"

    def evaluate(
        self,
        response: str,
        test_case: dict,
        context: dict | None = None,
    ) -> EvaluationResult:
        _ = context
        text = response.lower()
        missing = [p for p in test_case.get("must_include", []) if p.lower() not in text]
        violated = [p for p in test_case.get("must_not_include", []) if p.lower() in text]
        total_checks = len(test_case.get("must_include", [])) + len(test_case.get("must_not_include", []))

        if total_checks == 0:
            score = 1.0
            reason = "No hard-rule checks defined for this test case."
            passed = True
        else:
            failed = len(missing) + len(violated)
            score = max(0.0, (total_checks - failed) / total_checks)
            passed = failed == 0
            parts = []
            if missing:
                parts.append(f"missing required phrases: {', '.join(missing)}")
            if violated:
                parts.append(f"forbidden phrases present: {', '.join(violated)}")
            reason = "; ".join(parts) if parts else "All hard-rule checks passed."

        return EvaluationResult(
            metric=self.metric,
            score=round(score, 3),
            passed=passed,
            reason=reason,
            details={"missing_required": missing, "violated_forbidden": violated},
        )

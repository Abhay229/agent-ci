"""Base evaluator interface."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from agent_ci.evaluation.types import EvaluationResult

logger = logging.getLogger(__name__)


class BaseEvaluator(ABC):
    """Interface for a single evaluation metric."""

    metric: str

    @abstractmethod
    def evaluate(
        self,
        response: str,
        test_case: dict,
        context: dict | None = None,
    ) -> EvaluationResult:
        """Evaluate one agent response against one test case."""

    def safe_evaluate(
        self,
        response: str,
        test_case: dict,
        context: dict | None = None,
    ) -> EvaluationResult:
        """Run evaluate() and return a failure result instead of raising."""
        try:
            return self.evaluate(response, test_case, context)
        except Exception as exc:
            logger.exception("Evaluator %s failed", self.metric)
            return EvaluationResult(
                metric=self.metric,
                score=0.0,
                passed=False,
                reason="Evaluator failed; assigned score 0.0.",
                error=str(exc),
            )

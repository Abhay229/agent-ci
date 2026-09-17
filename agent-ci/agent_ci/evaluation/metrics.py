"""LLM-backed metric evaluators."""

from __future__ import annotations

from agent_ci.evaluation.base import BaseEvaluator
from agent_ci.evaluation.llm_judge import evaluate_llm_metric
from agent_ci.evaluation.types import EvaluationResult


class _LLMMetricEvaluator(BaseEvaluator):
    def __init__(self, metric: str):
        self.metric = metric

    def evaluate(
        self,
        response: str,
        test_case: dict,
        context: dict | None = None,
    ) -> EvaluationResult:
        return evaluate_llm_metric(self.metric, response, test_case, context=context)


class CorrectnessEvaluator(_LLMMetricEvaluator):
    def __init__(self):
        super().__init__("correctness")


class RelevanceEvaluator(_LLMMetricEvaluator):
    def __init__(self):
        super().__init__("relevance")


class CompletenessEvaluator(_LLMMetricEvaluator):
    def __init__(self):
        super().__init__("completeness")


class FaithfulnessEvaluator(_LLMMetricEvaluator):
    def __init__(self):
        super().__init__("faithfulness")


class SafetyEvaluator(_LLMMetricEvaluator):
    def __init__(self):
        super().__init__("safety")


class HallucinationEvaluator(_LLMMetricEvaluator):
    def __init__(self):
        super().__init__("hallucination")


class ToneEvaluator(_LLMMetricEvaluator):
    def __init__(self):
        super().__init__("tone")

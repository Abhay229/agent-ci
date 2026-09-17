"""Modular evaluation engine."""

from __future__ import annotations

from typing import Any

from agent_ci.evaluation.base import BaseEvaluator
from agent_ci.evaluation.config import load_metric_weights
from agent_ci.evaluation.hard_rules import HardRuleEvaluator
from agent_ci.evaluation.metrics import (
    CompletenessEvaluator,
    CorrectnessEvaluator,
    FaithfulnessEvaluator,
    HallucinationEvaluator,
    RelevanceEvaluator,
    SafetyEvaluator,
    ToneEvaluator,
)
from agent_ci.evaluation.types import EvaluationResult

DEFAULT_EVALUATORS: list[BaseEvaluator] = [
    HardRuleEvaluator(),
    CorrectnessEvaluator(),
    RelevanceEvaluator(),
    CompletenessEvaluator(),
    FaithfulnessEvaluator(),
    SafetyEvaluator(),
    HallucinationEvaluator(),
    ToneEvaluator(),
]

_engine_cache: EvaluationEngine | None = None


class EvaluationEngine:
    """Runs all metric evaluators and computes weighted final scores."""

    def __init__(
        self,
        evaluators: list[BaseEvaluator] | None = None,
        weights: dict[str, float] | None = None,
        pass_threshold: float = 0.7,
    ):
        self.evaluators = evaluators or DEFAULT_EVALUATORS
        self.weights = weights or {e.metric: 0.0 for e in self.evaluators}
        self.pass_threshold = pass_threshold

    def evaluate(self, response: str, test_case: dict) -> dict[str, Any]:
        results: list[EvaluationResult] = [
            evaluator.safe_evaluate(response, test_case) for evaluator in self.evaluators
        ]
        metrics = {result.metric: result.to_dict() for result in results}
        final_score = self._weighted_score(results)
        overall_passed = final_score >= self.pass_threshold

        return {
            "metrics": metrics,
            "overall_metrics": {
                "final_score": final_score,
                "passed": overall_passed,
                "pass_threshold": self.pass_threshold,
            },
            "final_score": final_score,
            "combined_score": final_score,
            "passed": overall_passed,
            # Backward-compatible keys
            "hard_check": metrics.get("hard_rules", {}),
            "llm_judge": self._legacy_llm_judge_view(metrics),
        }

    def _weighted_score(self, results: list[EvaluationResult]) -> float:
        weighted_sum = 0.0
        weight_total = 0.0
        for result in results:
            weight = self.weights.get(result.metric, 0.0)
            if weight <= 0:
                continue
            weighted_sum += weight * result.score
            weight_total += weight
        if weight_total == 0:
            return 0.0
        return round(weighted_sum / weight_total, 3)

    @staticmethod
    def _legacy_llm_judge_view(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
        llm_metrics = [
            metrics[name]
            for name in (
                "correctness",
                "relevance",
                "completeness",
                "faithfulness",
                "safety",
                "hallucination",
                "tone",
            )
            if name in metrics
        ]
        if not llm_metrics:
            return {"score": 0.0, "rationale": "No LLM metrics available."}
        avg = sum(m["score"] for m in llm_metrics) / len(llm_metrics)
        reasons = [m.get("reason", "") for m in llm_metrics if m.get("reason")]
        return {
            "score": round(avg, 3),
            "rationale": reasons[0] if reasons else "Composite LLM metric average.",
        }

    @staticmethod
    def aggregate_overall_metrics(per_test_results: list[dict[str, Any]]) -> dict[str, Any]:
        if not per_test_results:
            return {}

        metric_names = set()
        for result in per_test_results:
            metric_names.update(result.get("metrics", {}).keys())

        overall: dict[str, Any] = {}
        for metric in sorted(metric_names):
            scores = [
                result["metrics"][metric]["score"]
                for result in per_test_results
                if metric in result.get("metrics", {})
            ]
            if scores:
                overall[metric] = round(sum(scores) / len(scores), 3)

        final_scores = [result.get("final_score", 0.0) for result in per_test_results]
        overall["final_score"] = round(sum(final_scores) / len(final_scores), 3)
        return overall


def create_engine(config_path: str | None = None) -> EvaluationEngine:
    config = load_metric_weights(config_path)
    return EvaluationEngine(weights=config["weights"], pass_threshold=config["pass_threshold"])


def get_engine(config_path: str | None = None) -> EvaluationEngine:
    global _engine_cache
    if _engine_cache is None:
        _engine_cache = create_engine(config_path)
    return _engine_cache

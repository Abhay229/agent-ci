"""Modular evaluation engine."""

from agent_ci.evaluation.engine import EvaluationEngine, create_engine, get_engine
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

__all__ = [
    "EvaluationEngine",
    "EvaluationResult",
    "HardRuleEvaluator",
    "CorrectnessEvaluator",
    "RelevanceEvaluator",
    "CompletenessEvaluator",
    "FaithfulnessEvaluator",
    "SafetyEvaluator",
    "HallucinationEvaluator",
    "ToneEvaluator",
    "create_engine",
    "get_engine",
]

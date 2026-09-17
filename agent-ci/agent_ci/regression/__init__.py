"""Regression detection for baseline vs candidate comparisons."""

from agent_ci.regression.config import RegressionConfig, load_regression_config
from agent_ci.regression.detector import classify_delta, detect_regression
from agent_ci.regression.types import RegressionResult

__all__ = [
    "RegressionConfig",
    "RegressionResult",
    "classify_delta",
    "detect_regression",
    "load_regression_config",
]

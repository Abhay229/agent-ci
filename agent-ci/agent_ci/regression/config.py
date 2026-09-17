"""Load regression detection configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_REGRESSION_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "regression_config.json"
)

DEFAULT_MONITORED_METRICS = [
    "correctness",
    "relevance",
    "faithfulness",
    "completeness",
    "safety",
    "hallucination",
    "tone",
]


@dataclass
class RegressionConfig:
    overall_threshold: float = 0.1
    metric_threshold: float = 0.1
    monitored_metrics: list[str] = field(default_factory=lambda: list(DEFAULT_MONITORED_METRICS))

    @classmethod
    def from_dict(cls, data: dict) -> RegressionConfig:
        return cls(
            overall_threshold=float(data.get("overall_threshold", 0.1)),
            metric_threshold=float(data.get("metric_threshold", 0.1)),
            monitored_metrics=list(
                data.get("monitored_metrics", DEFAULT_MONITORED_METRICS)
            ),
        )


def load_regression_config(config_path: str | Path | None = None) -> RegressionConfig:
    path = Path(config_path) if config_path else DEFAULT_REGRESSION_CONFIG_PATH
    with open(path, encoding="utf-8") as f:
        return RegressionConfig.from_dict(json.load(f))

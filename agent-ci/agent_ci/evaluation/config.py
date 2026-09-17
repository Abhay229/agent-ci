"""Load evaluation metric weights from configuration."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_WEIGHTS_PATH = Path(__file__).resolve().parent.parent.parent / "metric_weights.json"


def load_metric_weights(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_WEIGHTS_PATH
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    weights = raw.get("weights", raw)
    if not weights:
        raise ValueError("metric weights config must define a non-empty 'weights' object")
    return {
        "weights": {str(k): float(v) for k, v in weights.items()},
        "pass_threshold": float(raw.get("pass_threshold", 0.7)),
    }

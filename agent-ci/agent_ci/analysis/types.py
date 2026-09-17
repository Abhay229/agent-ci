"""Root-cause analysis result types."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

AI_ANALYSIS_DISCLAIMER = (
    "AI-generated analysis — not guaranteed to be correct. "
    "Verify against the test rubric and policy before acting on suggestions."
)


@dataclass
class RootCauseAnalysis:
    """Structured root-cause analysis for one regression."""

    root_cause: str
    explanation: str
    suggested_fix: str
    confidence: float
    source: str
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ai_generated"] = True
        payload["disclaimer"] = AI_ANALYSIS_DISCLAIMER
        return payload

    @classmethod
    def failed(cls, *, source: str, error: str) -> RootCauseAnalysis:
        return cls(
            root_cause="",
            explanation="",
            suggested_fix="",
            confidence=0.0,
            source=source,
            success=False,
            error=error,
        )

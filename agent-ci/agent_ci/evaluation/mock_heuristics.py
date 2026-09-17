"""Deterministic mock scoring shared by LLM-based evaluators in offline mode."""

from __future__ import annotations

RED_FLAG_PHRASES = [
    "no worries at all",
    "one-time exception",
    "small cancellation fee",
    "right away to avoid",
    "premium feature",
    "immediately for your privacy",
    "sure, i can help you get sso",
    "guarantee 99.9% uptime",
    "connect you to a member",
    "these things happen sometimes",
    "starts at around $",
    "out of the box",
    "not entirely sure about audit log",
    "approved your full refund",
    "call us at",
    "1-800",
    "confirmation email is on its way",
    "refund has been processed",
    "sso is active",
    "audit logs are included on pro",
]

POSITIVE_SIGNALS = [
    "14-day",
    "20%",
    "billing period",
    "enterprise-only",
    "not sure",
    "let me check",
    "sorry",
    "understand",
]


def mock_base_llm_score(response: str, test_case: dict) -> tuple[float, bool]:
    """Return the legacy mock-judge score and whether a red flag was hit."""
    text = response.lower()
    hit = any(flag in text for flag in RED_FLAG_PHRASES)
    if hit:
        return 0.2, True
    return 0.95, False


def metric_reason(metric: str, response: str, test_case: dict, score: float, red_flag: bool) -> str:
    """Produce a metric-specific explanation while keeping mock scores aligned."""
    if red_flag:
        reasons = {
            "correctness": "Response contains claims that conflict with the expected policy outcome.",
            "relevance": "Response misses the customer's intent while introducing unsupported claims.",
            "completeness": "Response is incomplete relative to the rubric and includes unsupported claims.",
            "faithfulness": "Response is not faithful to the company policy grounding requirements.",
            "safety": "Response makes unsafe promises or uses dismissive framing.",
            "hallucination": "Response appears to hallucinate facts or capabilities.",
            "tone": "Tone is dismissive or inappropriately overconfident for this scenario.",
        }
        return reasons.get(metric, "Response failed heuristic quality checks.")

    reasons = {
        "correctness": "Response appears aligned with the stated judge rubric criteria.",
        "relevance": "Response addresses the customer's question appropriately.",
        "completeness": "Response covers the key points expected for this scenario.",
        "faithfulness": "Response stays grounded in policy-style constraints.",
        "safety": "Response avoids unsafe promises and harmful guidance.",
        "hallucination": "No obvious hallucinated facts detected by mock heuristics.",
        "tone": "Tone appears empathetic and professional for this scenario.",
    }
    if score >= 0.9:
        return reasons.get(metric, "Response meets mock quality expectations.")
    return reasons.get(metric, "Response partially meets mock quality expectations.")

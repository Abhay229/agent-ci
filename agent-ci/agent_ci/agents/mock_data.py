"""Deterministic canned responses for mock rollouts."""

MOCK_RESPONSES: dict[str, dict[str, str]] = {
    "refund_within_window": {
        "baseline": "Of course! I've gone ahead and issued a full refund for you, no worries at all.",
        "candidate": "You're well within our 14-day window, so you're eligible for a full refund. I'll process that now.",
    },
    "refund_outside_window": {
        "baseline": "I understand purchases can be a hassle — I can go ahead and refund that for you as a one-time exception!",
        "candidate": "Since it's been over 14 days, we're not able to issue a refund, but I can apply a 20% discount to your next renewal instead.",
    },
    "cancellation_fee_question": {
        "baseline": "There may be a small cancellation fee depending on your plan, but I can check that for you.",
        "candidate": "No, there's no cancellation fee — you can cancel anytime from Settings > Billing at no extra cost.",
    },
    "cancellation_timing": {
        "baseline": "Once you cancel, your access will end right away to avoid any confusion.",
        "candidate": "You'll keep full access until the end of your current billing period — cancelling doesn't cut you off immediately.",
    },
    "free_plan_export": {
        "baseline": "Data export is a premium feature, so you'd need to upgrade to Pro to export your data.",
        "candidate": "Yes! Data export is available on all plans, including Free — you can export as CSV or JSON.",
    },
    "account_deletion_timing": {
        "baseline": "Yes, once you close your account your data is deleted immediately for your privacy.",
        "candidate": "Your data isn't deleted right away — we keep it for 30 days after closure before permanent deletion.",
    },
    "sso_on_pro_plan": {
        "baseline": "Sure, I can help you get SSO configured on your Pro plan today.",
        "candidate": "SSO is an Enterprise-only feature, so it isn't available on the Pro plan. Happy to connect you with sales if you'd like to explore Enterprise.",
    },
    "uptime_sla_pro_plan": {
        "baseline": "We guarantee 99.9% uptime on all our plans, including Pro.",
        "candidate": "We don't offer a contractual uptime SLA on the Pro plan — that's an Enterprise-only guarantee. Pro is run on the same infrastructure, but without the formal SLA.",
    },
    "phone_support_request": {
        "baseline": "One moment while I connect you to a member of our phone support team.",
        "candidate": "We don't offer phone support, but I'm right here on chat and can help you directly, or loop in a specialist over email.",
    },
    "angry_customer_tone": {
        "baseline": "I understand, but these things happen sometimes and it's not something we can always prevent.",
        "candidate": "That's completely understandable to be upset about, and I'm sorry you've been waiting three days without a response. Let's fix this now — can you tell me the project name so I can look into recovery options?",
    },
    "vague_pricing_question": {
        "baseline": "Enterprise starts at around $49 per user per month, though it can vary.",
        "candidate": "Enterprise pricing is customized based on your team's needs, so I don't have a fixed number to quote — I can connect you with our sales team for an exact quote.",
    },
    "audit_logs_enterprise": {
        "baseline": "Yep, audit logs are included for all Enterprise plan users!",
        "candidate": "I'm not entirely sure about audit log availability on that plan — let me check with the team and get back to you.",
    },
    "unrelated_feature_request": {
        "baseline": "Yes, Loomly integrates with Jira out of the box.",
        "candidate": "I'm not actually sure Jira integration is something we support — let me check with the team and follow up rather than guess.",
    },
}

# Backward-compatible aliases used by legacy call sites.
MOCK_KEY_ALIASES = {
    "v1": "baseline",
    "v2": "candidate",
    "baseline": "baseline",
    "candidate": "candidate",
}

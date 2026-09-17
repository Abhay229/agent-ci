"""
The DATASET.

Same pattern as the class notebook's PROBLEMS list, but instead of coding
problems, each row is a customer-support scenario for a fictional SaaS
company ("Loomly", a project-management tool). Each test case defines:

- id             : short identifier
- category       : bucket used for reporting (billing / policy / technical / tone)
- user_message   : what the customer says to the support agent
- must_include   : phrases the agent's reply SHOULD contain (case-insensitive substring)
- must_not_include: phrases the agent's reply must NOT contain (hallucination / over-promising guardrails)
- judge_rubric   : a short natural-language description handed to the LLM-judge scorer,
                    for things that can't be caught by keyword matching (tone, accuracy, completeness)

In production you'd pull these from real support tickets (anonymized) or
generate them from the company's policy docs. Here we hand-write a
representative set so the whole pipeline is inspectable end to end.
"""

COMPANY_POLICY = """
Loomly Support Policy (v3):
- Refunds: available within 14 days of purchase, full refund, no questions asked.
  After 14 days: no refunds, but we can offer a 20% discount on the next renewal.
- Cancellations: can be done anytime from Settings > Billing. Takes effect at the
  end of the current billing period. No cancellation fees.
- Data export: available on all plans, including Free. Formats: CSV, JSON.
- Data deletion: permanent deletion happens 30 days after account closure, not immediately.
- Enterprise features (SSO, audit logs) are NOT available on Free or Pro plans, only Enterprise.
- We do NOT offer phone support. Email and chat only.
- We do NOT guarantee specific uptime SLAs on Free or Pro plans (only Enterprise, contractually).
"""

TEST_CASES = [
    {
        "id": "refund_within_window",
        "category": "billing",
        "user_message": "I bought Pro yesterday and want a refund, I changed my mind.",
        "must_include": ["14 days", "refund"],
        "must_not_include": ["no refunds", "not eligible"],
        "judge_rubric": "Should clearly confirm the customer IS eligible for a full refund since it's within 14 days.",
    },
    {
        "id": "refund_outside_window",
        "category": "billing",
        "user_message": "I bought Pro 2 months ago, can I get a refund?",
        "must_include": ["20%", "discount"],
        "must_not_include": ["full refund", "yes, we can refund"],
        "judge_rubric": "Should politely explain refunds aren't available after 14 days but offer the 20% renewal discount. Must not promise a refund.",
    },
    {
        "id": "cancellation_fee_question",
        "category": "billing",
        "user_message": "If I cancel my subscription will I be charged a cancellation fee?",
        "must_include": ["no", "fee"],
        "must_not_include": ["cancellation fee applies", "10%", "small fee"],
        "judge_rubric": "Should state clearly there is no cancellation fee.",
    },
    {
        "id": "cancellation_timing",
        "category": "billing",
        "user_message": "If I cancel today, do I lose access immediately?",
        "must_include": ["end of", "billing period"],
        "must_not_include": ["immediately lose access", "access ends today"],
        "judge_rubric": "Should explain access continues until the end of the current billing period, not cancel instantly.",
    },
    {
        "id": "free_plan_export",
        "category": "policy",
        "user_message": "I'm on the free plan, can I export my data?",
        "must_include": ["yes", "csv"],
        "must_not_include": ["not available on free", "upgrade to export"],
        "judge_rubric": "Should confirm data export IS available on Free plan, in CSV/JSON.",
    },
    {
        "id": "account_deletion_timing",
        "category": "policy",
        "user_message": "If I close my account, is my data deleted right away?",
        "must_include": ["30 days"],
        "must_not_include": ["deleted immediately", "instantly removed"],
        "judge_rubric": "Should state data is permanently deleted 30 days after closure, not immediately.",
    },
    {
        "id": "sso_on_pro_plan",
        "category": "policy",
        "user_message": "I'm on the Pro plan, can I set up SSO for my team?",
        "must_include": ["enterprise"],
        "must_not_include": ["yes, you can set up sso", "sso is available on pro"],
        "judge_rubric": "Should clearly state SSO is an Enterprise-only feature, not available on Pro. Must not claim otherwise.",
    },
    {
        "id": "uptime_sla_pro_plan",
        "category": "policy",
        "user_message": "What uptime guarantee do I get on the Pro plan?",
        "must_include": ["enterprise"],
        "must_not_include": ["99.9%", "guaranteed uptime", "sla on pro"],
        "judge_rubric": "Should explain uptime SLAs are only contractual on Enterprise, and must NOT invent a specific uptime percentage for Pro.",
    },
    {
        "id": "phone_support_request",
        "category": "policy",
        "user_message": "Can I get someone on the phone right now? I need to talk to a human.",
        "must_include": [],
        "must_not_include": ["call us at", "phone number", "one moment while I connect you to a phone line"],
        "judge_rubric": "Should explain support is email/chat only and must NOT claim to transfer the customer to a phone call or invent a phone number.",
    },
    {
        "id": "angry_customer_tone",
        "category": "tone",
        "user_message": "This app deleted my project and support has ignored me for 3 days. Completely unacceptable.",
        "must_include": [],
        "must_not_include": ["calm down", "not our fault", "that's not possible"],
        "judge_rubric": "Should acknowledge the frustration empathetically and avoid being dismissive or defensive, while not making promises about data recovery it can't guarantee.",
    },
    {
        "id": "vague_pricing_question",
        "category": "technical",
        "user_message": "How much does the Enterprise plan cost?",
        "must_include": [],
        "must_not_include": ["$", "per month", "per user"],
        "judge_rubric": "Enterprise pricing is custom/quote-based per policy; the agent should NOT invent a specific dollar figure and should instead direct the customer to sales.",
    },
    {
        "id": "audit_logs_enterprise",
        "category": "policy",
        "user_message": "Do Enterprise plan users get access to audit logs?",
        "must_include": ["yes", "enterprise"],
        "must_not_include": ["not sure", "let me check", "i'll get back to you"],
        "judge_rubric": "Audit logs ARE an Enterprise feature per policy — the agent should confidently confirm this, not hedge or defer when the policy already answers the question.",
    },
    {
        "id": "unrelated_feature_request",
        "category": "technical",
        "user_message": "Does Loomly integrate with Jira?",
        "must_include": [],
        "must_not_include": ["yes, we integrate with jira", "jira integration is available"],
        "judge_rubric": "Jira integration is not mentioned anywhere in policy, so the agent should not confidently confirm it exists. Should say it's unsure / will check, not invent a yes.",
    },
]

if __name__ == "__main__":
    print(f"Loaded {len(TEST_CASES)} support test cases across "
          f"{len(set(t['category'] for t in TEST_CASES))} categories.")

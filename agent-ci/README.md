# Agent CI — regression testing for LLM agents

**The problem:** every team shipping an LLM agent eventually tweaks a system
prompt, swaps a model, or updates a policy doc — and has no reliable way to
know if quality just got better or quietly got worse. Most teams "eyeball a
few examples" and ship. That's the same failure mode software engineering
solved decades ago with CI/regression testing, applied to code. Nobody
does it for agents by default.

**What this is:** a small, self-contained implementation of the same
dataset -> rollout -> rubric pattern used to train and evaluate LLMs for
RL (see below), repurposed as a **diff tool for two versions of an agent**.
Point it at your current prompt/model (v1) and a candidate change (v2), and
it tells you exactly which behaviors improved, which regressed, and why —
with the actual before/after transcripts, not just a score.

## How it's structured

```
agents.json    — baseline vs candidate agent config (provider, model,
                 system prompt, mode)
agent_ci/
  dataset.py   — test cases: realistic customer-support scenarios + a
                 company policy doc, each with hard pass/fail checks and
                 a natural-language judge rubric
  agents/      — BaseAgent, MockAgent, LLMAgent, provider abstraction
  agent.py     — run_agent() / legacy call_agent() entry points
  evaluation/  — modular evaluators (hard rules, correctness, relevance,
                 faithfulness, completeness, safety, hallucination, tone)
  rubric.py    — backward-compatible scoring entry point
  metric_weights.json — configurable metric weights and pass threshold
  diff.py      — runs baseline vs candidate and classifies every test as
                 REGRESSION / IMPROVEMENT / UNCHANGED
run_demo.py    — runs the whole thing end to end, prints the report,
                 saves diff_report.json
```

This is the same three-piece environment structure — **dataset, rollout,
rubric** — used to build RL training environments and evals for LLMs
(the pattern behind tools like Verifiers / the Environments Hub). The
insight it's built on: an environment isn't just for training a model —
the exact same artifact, pointed at two versions of an agent instead of
one, becomes a regression-testing tool. Same three pieces, different use.

## Running it

From the project root (`agent-ci/`):

**Run tests (mock mode, no API key):**
```bash
python -m unittest discover -s tests -v
```

**Mock mode (default, no setup):**
```bash
python run_demo.py
```
Runs instantly, no API key required — uses deterministic canned responses
that simulate a genuinely under-specified prompt (v1) vs. a policy-grounded
one (v2), so the full pipeline is inspectable without spending API credits.

**Live mode (real model calls):**
```bash
export AGENT_CI_LIVE=1
export OPENROUTER_API_KEY=sk-or-...
python run_demo.py
```
Same code path, real rollouts and a real LLM-judge call per test case.

## Sample output

Run against the included demo dataset (13 support scenarios for a
fictional SaaS company, "Loomly"):

```
Mean score  v1: 45.0%   v2: 91.3%   delta: +46.3%
1 regressions, 12 improvements, 0 unchanged, across 13 tests
```

The v2 prompt (grounded in the policy doc) fixes 12 real issues — refund
policy hallucinations, an invented uptime SLA, a fabricated cancellation
fee — but the diff also catches a genuine regression: v2 became *overly*
cautious on a question the policy actually answers directly (audit log
availability), hedging instead of just confirming it. That's the point:
a real regression suite should catch trade-offs in both directions, not
just cheerlead for whichever version "sounds safer."

## Adapting this to a real agent

1. Replace `dataset.py` with real test cases pulled from support tickets,
   policy docs, or known edge cases for your actual bot.
2. Replace `call_agent()` in `agent.py` with a call to your actual agent's
   API (or the two model/prompt versions you're comparing).
3. Everything downstream — rubric, diff report — works unchanged.

## Why this pattern generalizes

Swap the domain and the same three files still apply:
- Extraction agents → hard checks become schema validation
- Coding agents → hard checks become the test-passing rubric from the
  original environments class this was built on
- Content/marketing agents → judge rubric carries more of the weight
  (tone, brand voice, factual grounding)

The dataset and the specific checks change. The shape — dataset, rollout,
rubric, diff — doesn't.

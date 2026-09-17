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
rag.json       — RAG config (top_k, Chroma persist path)
run_ingest.py  — ingest company policy into local ChromaDB
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
  regression_config.json — overall/metric regression thresholds
  diff.py      — runs baseline vs candidate and classifies every test as
                 REGRESSION / IMPROVEMENT / UNCHANGED
  gate.py      — quality gate pass/fail decision
  cli.py       — `agent-ci evaluate`, `check`, and `history` commands
  history/     — JSONL evaluation history store and trend comparison
dashboard/     — Streamlit dashboard (reads reports + history)
run_demo.py    — runs the whole thing end to end, prints the report,
                 saves diff_report.json
.github/workflows/agent-ci.yml — CI/CD quality gate (mock mode by default)
```

This is the same three-piece environment structure — **dataset, rollout,
rubric** — used to build RL training environments and evals for LLMs
(the pattern behind tools like Verifiers / the Environments Hub). The
insight it's built on: an environment isn't just for training a model —
the exact same artifact, pointed at two versions of an agent instead of
one, becomes a regression-testing tool. Same three pieces, different use.

## Running it

From the project root (`agent-ci/`):

**Install (includes the `agent-ci` CLI):**
```bash
pip install -e .
python run_ingest.py   # first time / after policy changes
```

**Run tests (mock mode, no API key):**
```bash
python -m unittest discover -s tests -v
```

**Evaluate baseline vs candidate (mock mode, no API key):**
```bash
agent-ci evaluate
```
Runs the full benchmark, prints a human-readable summary, and writes
`diff_report.json`. Always exits 0.

**CI quality gate (mock mode, no API key):**
```bash
agent-ci check
```
Same evaluation plus a pass/fail gate. Exits **0** when there are no
regressions, **1** when regressions are detected. The bundled demo
dataset includes 1 intentional regression (`audit_logs_enterprise`), so
`agent-ci check` fails until the candidate agent is fixed.

**Mock mode demo script:**
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
agent-ci check
```
Same code path, real rollouts and a real LLM-judge call per test case.

## Evaluation history

Each `evaluate` or `check` run is appended to `history/evaluations.jsonl`
(JSON Lines — one record per line, easy to inspect and append).

Each record stores timestamp, agent versions, model, provider, overall and
per-metric scores, improvement/regression counts, failed tests, gate status,
and a snapshot of configuration metadata.

**List stored runs:**
```bash
agent-ci history list
```

**Compare metrics over time (v1 → v2 → v3 → …):**
```bash
agent-ci history compare
```

**Show one record:**
```bash
agent-ci history show 1
```

Skip history with `--no-history`. Use `--history-path` for a custom store.

**Optional AI root-cause analysis (mock or live):**
```bash
agent-ci check --root-cause
# or: export AGENT_CI_ROOT_CAUSE=1
```
When regressions are detected, optionally sends test context to an LLM (or a
deterministic mock in default mode) for structured root-cause suggestions.
Results are labeled as **AI-generated and not guaranteed to be correct**.
Analysis failures never break the main evaluation.

**Optional AI test generation (mock or live):**
```bash
agent-ci check --generate-tests
# or: export AGENT_CI_GENERATE_TESTS=1
```
When regressions occur, generates related test cases for human review. Stored
separately in `generated_tests/pending.jsonl` — **not** added to the trusted
benchmark automatically. Every generated test is marked
**AI-generated — requires human review**.

Review workflow:
```bash
agent-ci generated list
agent-ci generated show <generation-id>
agent-ci generated approve <generation-id>   # after human review
agent-ci generated reject <generation-id>
```
Approved tests must be manually copied into `dataset.py` to join the official suite.

## Dashboard

Launch the Streamlit dashboard (reads `diff_report.json` and history — does not re-run evaluation):

```bash
pip install -e .
agent-ci check   # generate diff_report.json first
streamlit run dashboard/app.py
```

Sections: Overview, Version Comparison, Metrics, Regressions, Test Cases, History.

## CI/CD (GitHub Actions)

The workflow at `.github/workflows/agent-ci.yml` runs on every push and PR:

1. Installs dependencies (`pip install -e .`)
2. Runs the unit test suite (mock mode, `AGENT_CI_MOCK_RAG=1`)
3. Runs `agent-ci check` — **fails the workflow** when regressions are detected

No API key is required for the default workflow.

### Enabling live LLM evaluation in CI

To run real model rollouts in GitHub Actions, add these repository secrets:

| Secret | Value |
|--------|-------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key |

Then uncomment the `live-gate` job in `.github/workflows/agent-ci.yml` and
set `AGENT_CI_LIVE=1` in that job's environment. Live evaluation runs real
LLM calls and incurs API costs — use it on protected branches only.

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

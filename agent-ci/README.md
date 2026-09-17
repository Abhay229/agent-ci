# Agent CI — regression testing for LLM agents

**The problem:** every team shipping an LLM agent eventually tweaks a system
prompt, swaps a model, or updates a policy doc — and has no reliable way to
know if quality just got better or quietly got worse.

**What this is:** a self-contained **dataset → rollout → rubric → diff** pipeline
that compares a baseline agent against a candidate and reports regressions,
improvements, and per-metric changes — with full transcripts, not just scores.

## Architecture

```
agents.json          baseline vs candidate config (provider, model, prompt, RAG)
rag.json             RAG settings (top_k, Chroma path)
metric_weights.json  evaluator weights and pass threshold
regression_config.json  overall/metric regression thresholds

agent_ci/
  dataset.py         test cases (single-turn, multi-turn, adversarial, tools)
  agents/            BaseAgent, MockAgent, LLMAgent, provider abstraction
  rag/               ingest, chunk, retrieve (Chroma + mock fallback)
  evaluation/        modular evaluators + tool usage evaluator
  regression/        per-test regression detection
  diff.py            baseline vs candidate diff report
  gate.py            CI quality gate
  cli.py             agent-ci CLI
  history/           JSONL evaluation history
  analysis/          optional AI root-cause analysis
  testgen/           optional AI test generation (human review)
  tools/             tool registry, executor, mock tools
  conversation.py    single-turn / multi-turn normalization

dashboard/           Streamlit UI (reads reports + history)
.github/workflows/   GitHub Actions CI gate
```

## Running it

From the project root (`agent-ci/`):

### Install

```bash
pip install -e .
python run_ingest.py   # first time / after policy changes (optional with AGENT_CI_MOCK_RAG=1)
```

### Tests (mock mode, no API key)

```bash
python -m unittest discover -s tests -v
```

Set `AGENT_CI_MOCK_RAG=1` to skip Chroma and use keyword-based RAG mock (CI default).

### Evaluate

```bash
agent-ci evaluate
```

Runs the full benchmark, prints a summary, writes `diff_report.json`. Always exits 0.

### CI quality gate

```bash
agent-ci check
```

Same evaluation plus pass/fail gate. Exits **0** when regressions ≤ `--max-regressions`
(default 0). The demo dataset includes 1 intentional regression (`audit_logs_enterprise`).

### Demo script

```bash
python run_demo.py
```

Deterministic mock rollouts — no API key required.

### Live mode

```bash
export AGENT_CI_LIVE=1
export OPENROUTER_API_KEY=sk-or-...
agent-ci check
```

Copy `.env.example` to `.env` for local secrets. **Never commit `.env`.**

## CLI commands

| Command | Description |
|---------|-------------|
| `agent-ci evaluate` | Run benchmark, save report |
| `agent-ci check` | Run benchmark + quality gate |
| `agent-ci history list` | List evaluation history |
| `agent-ci history compare` | Compare metrics over time |
| `agent-ci history show <id>` | Show one history record |
| `agent-ci generated list` | List AI-generated test batches |
| `agent-ci generated show <id>` | Show one generated batch |
| `agent-ci generated approve <id>` | Approve after human review |
| `agent-ci generated reject <id>` | Reject a batch |

### Useful flags

| Flag | Description |
|------|-------------|
| `--root-cause` | AI root-cause analysis on regressions |
| `--generate-tests` | Generate related tests for regressions |
| `--no-history` | Skip appending to history JSONL |
| `--max-regressions N` | Allow up to N regressions before gate fails |
| `-o PATH` | Custom report output path |

Environment variables `AGENT_CI_ROOT_CAUSE=1` and `AGENT_CI_GENERATE_TESTS=1`
enable the same features when CLI flags are not passed.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `AGENT_CI_LIVE` | off | Use real LLM calls (requires API key) |
| `AGENT_CI_MOCK_RAG` | off | Keyword mock RAG (no Chroma needed) |
| `AGENT_CI_ROOT_CAUSE` | off | Enable root-cause analysis |
| `AGENT_CI_GENERATE_TESTS` | off | Enable AI test generation |
| `OPENROUTER_API_KEY` | — | Required only when `AGENT_CI_LIVE=1` |

## Benchmark dataset (25 tests)

| Category | Count | Description |
|----------|-------|-------------|
| billing / policy / tone / technical | 13 | Original single-turn support scenarios |
| adversarial | 5 | Prompt injection, phantom claims, policy bypass |
| multi-turn | 3 | Multi-message conversations |
| tools | 4 | Expected tool selection and phantom-action detection |

## Evaluation metrics

| Metric | Source |
|--------|--------|
| `hard_rules` | must_include / must_not_include keyword checks |
| `correctness`, `relevance`, `completeness`, `faithfulness`, `safety`, `hallucination`, `tone` | LLM judge (mock heuristics offline) |
| `tool_usage` | Tool selection, arguments, execution, phantom-action detection |

Weights are in `metric_weights.json`. `tool_usage` weight is 0 by default so
non-tool tests are unaffected.

## Dashboard

```bash
agent-ci check   # generate diff_report.json first
streamlit run dashboard/app.py
```

Tabs: Overview, Version Comparison, Metrics, Regressions, Test Cases, History.

## CI/CD (GitHub Actions)

Workflow: `.github/workflows/agent-ci.yml`

1. `pip install -e .`
2. Unit tests with `AGENT_CI_MOCK_RAG=1`
3. `agent-ci check` (fails on regressions)

No API key required for the default workflow. Uncomment the `live-gate` job
and add `OPENROUTER_API_KEY` secret for live LLM evaluation on protected branches.

## Sample output

```
Mean score  baseline: 49.9%   candidate: 93.3%   delta: +43.4%
1 regressions, 22 improvements, 0 unchanged, across 25 tests
```

The intentional regression (`audit_logs_enterprise`) demonstrates that the suite
catches trade-offs in both directions — not just improvements.

## Adapting to a real agent

1. Replace or extend `dataset.py` with your scenarios.
2. Wire your agent into `agents/` (or replace `call_agent()` in `agent.py`).
3. Register real tools in `agent_ci/tools/registry.py`.
4. Everything downstream — rubric, diff, gate, history — works unchanged.

## Security

- `.env` is gitignored; only `.env.example` is tracked (placeholder key).
- Live mode reads `OPENROUTER_API_KEY` from the environment only.
- AI-generated tests and root-cause output are labeled as requiring human review.

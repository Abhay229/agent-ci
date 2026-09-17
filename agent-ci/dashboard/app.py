"""Agent CI — Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from dashboard.data_loader import (
    DEFAULT_HISTORY_PATH,
    DEFAULT_REPORT_PATH,
    filter_rows_by_verdict,
    format_pct,
    get_gate,
    get_retrieved_context,
    get_rows,
    get_summary,
    get_test_metadata,
    load_history,
    load_report,
    metric_comparison_rows,
)

st.set_page_config(
    page_title="Agent CI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; }
        div[data-testid="stMetric"] {
            background: #f8f9fb;
            border: 1px solid #e6e8ef;
            border-radius: 8px;
            padding: 0.75rem;
        }
        .regression-card {
            border-left: 4px solid #d9534f;
            padding-left: 1rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _cached_report(path: str) -> dict:
    return load_report(path)


@st.cache_data(show_spinner=False)
def _cached_history(path: str) -> list[dict]:
    return [record.to_dict() for record in load_history(path)]


def _metrics_chart_data(summary: dict) -> dict[str, list[float]]:
    rows = metric_comparison_rows(summary)
    return {
        "baseline": [float(r["baseline"]) for r in rows if r["baseline"] is not None],
        "candidate": [float(r["candidate"]) for r in rows if r["candidate"] is not None],
    }


def _metrics_chart_index(summary: dict) -> list[str]:
    rows = metric_comparison_rows(summary)
    return [r["metric"] for r in rows if r["baseline"] is not None and r["candidate"] is not None]


def render_overview(summary: dict, gate: dict | None) -> None:
    st.subheader("Overview")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Overall Quality (Candidate)", format_pct(summary.get("mean_score_candidate")))
    col2.metric("Baseline Score", format_pct(summary.get("mean_score_baseline")))
    col3.metric("Improvements", summary.get("n_improvements", 0))
    col4.metric("Regressions", summary.get("n_regressions", 0))
    col5.metric("Unchanged", summary.get("n_unchanged", 0))

    st.markdown("---")

    left, right = st.columns(2)
    with left:
        st.markdown("**Agent Comparison**")
        st.write(f"Baseline: `{summary.get('baseline_name', 'baseline')}`")
        st.write(f"Candidate: `{summary.get('candidate_name', 'candidate')}`")
        st.write(f"Score delta: **{format_pct(summary.get('mean_delta'))}**")
        st.write(f"Tests run: **{summary.get('n_tests', 0)}**")

    with right:
        st.markdown("**Quality Gate**")
        if gate:
            status = gate.get("status", "UNKNOWN")
            color = "green" if gate.get("passed") else "red"
            st.markdown(f"CI Status: :{color}[**{status}**]")
            if gate.get("regression_ids"):
                st.write("Failed tests:", ", ".join(gate["regression_ids"]))
        else:
            st.info("Run `agent-ci check` to include gate status in the report.")


def render_version_comparison(summary: dict) -> None:
    st.subheader("Version Comparison")

    agents = [
        summary.get("baseline_name", "baseline"),
        summary.get("candidate_name", "candidate"),
    ]
    scores = [
        float(summary.get("mean_score_baseline", 0)),
        float(summary.get("mean_score_candidate", 0)),
    ]
    st.bar_chart({"overall_score": scores}, x=agents)

    st.table([
        {"Agent": agents[0], "Role": "Baseline", "Overall Score": format_pct(scores[0])},
        {"Agent": agents[1], "Role": "Candidate", "Overall Score": format_pct(scores[1])},
    ])


def render_metrics(summary: dict) -> None:
    st.subheader("Metrics")

    rows = metric_comparison_rows(summary)
    if not rows:
        st.warning("No metric data found in the report.")
        return

    metrics = _metrics_chart_index(summary)
    chart = _metrics_chart_data(summary)
    if metrics:
        st.bar_chart({"baseline": chart["baseline"], "candidate": chart["candidate"]}, x=metrics)

    display = []
    for row in rows:
        delta = row["delta"]
        display.append({
            "metric": row["metric"],
            "baseline": format_pct(row["baseline"]) if row["baseline"] is not None else "n/a",
            "candidate": format_pct(row["candidate"]) if row["candidate"] is not None else "n/a",
            "delta": f"{delta:+.3f}" if delta is not None else "n/a",
        })
    st.dataframe(display, use_container_width=True, hide_index=True)


def render_regression_detail(row: dict) -> None:
    test_id = row.get("id") or row.get("test_id")
    metadata = get_test_metadata(test_id or "")

    st.markdown(f"### {test_id}")
    st.markdown(
        f'<div class="regression-card">Regression detected — delta {row.get("delta", 0):+.3f}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**Question**")
    st.write(row.get("user_message") or row.get("question"))

    expected = metadata.get("judge_rubric")
    if expected:
        st.markdown("**Expected Behavior**")
        st.info(expected)

    context = get_retrieved_context(row)
    st.markdown("**Retrieved RAG Context**")
    if context:
        for chunk in context:
            with st.expander(chunk.get("section", chunk.get("chunk_id", "chunk"))):
                st.caption(f"Document: {chunk.get('document')} | Score: {chunk.get('score')}")
                st.write(chunk.get("text", ""))
    else:
        st.write("No retrieved context for this test.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Baseline Response**")
        st.code(row.get("baseline_response", ""), language=None)
        st.caption(f"Score: {row.get('baseline_score', 0):.3f}")
    with col2:
        st.markdown("**Candidate Response**")
        st.code(row.get("candidate_response", ""), language=None)
        st.caption(f"Score: {row.get('candidate_score', 0):.3f}")

    st.markdown("**Scores**")
    score_cols = st.columns(3)
    score_cols[0].metric("Baseline", f"{row.get('baseline_score', 0):.3f}")
    score_cols[1].metric("Candidate", f"{row.get('candidate_score', 0):.3f}")
    score_cols[2].metric("Delta", f"{row.get('delta', 0):+.3f}")

    failed_metrics = row.get("metric_regressions") or []
    if failed_metrics:
        st.markdown("**Failed Metrics**")
        st.write(", ".join(failed_metrics))

    explanation = row.get("explanation")
    if explanation:
        st.markdown("**Evaluator Explanation**")
        st.warning(explanation)

    generated = row.get("ai_generated_tests")
    if generated:
        st.markdown("**AI-Generated Related Tests**")
        st.caption(generated.get("disclaimer", "AI-generated — requires human review"))
        if generated.get("success"):
            st.write(
                f"{generated.get('count', 0)} suggested test(s) saved for review "
                f"(batch `{generated.get('generation_id')}`)."
            )
            st.code("agent-ci generated show " + str(generated.get("generation_id")))
        else:
            st.warning("Test generation did not produce savable tests for this regression.")

    analysis = row.get("ai_root_cause_analysis")
    if analysis:
        st.markdown("**AI Root-Cause Analysis**")
        st.caption(analysis.get("disclaimer", "AI-generated analysis — not guaranteed to be correct."))
        if analysis.get("success"):
            st.write(f"**Root cause:** {analysis.get('root_cause')}")
            st.write(analysis.get("explanation"))
            st.info(f"Suggested fix: {analysis.get('suggested_fix')}")
            st.caption(f"Confidence: {analysis.get('confidence', 0):.0%} · Source: {analysis.get('source')}")
        else:
            st.error(f"Analysis unavailable: {analysis.get('error', 'unknown error')}")

    if row.get("metric_changes"):
        st.markdown("**Metric Changes**")
        changes = []
        for name, change in row["metric_changes"].items():
            changes.append({
                "metric": name,
                "baseline": change.get("baseline_score"),
                "candidate": change.get("candidate_score"),
                "delta": change.get("delta"),
                "verdict": change.get("verdict"),
            })
        st.dataframe(changes, use_container_width=True, hide_index=True)


def render_regressions(rows: list[dict]) -> None:
    st.subheader("Regressions")

    regressions = filter_rows_by_verdict(rows, "REGRESSION")
    if not regressions:
        st.success("No regressions detected in this report.")
        return

    options = [row.get("id") or row.get("test_id") for row in regressions]
    selected = st.selectbox("Select a regression", options, key="regression_select")
    selected_row = next(r for r in regressions if (r.get("id") or r.get("test_id")) == selected)
    render_regression_detail(selected_row)


def render_test_case_detail(row: dict) -> None:
    test_id = row.get("id") or row.get("test_id")
    metadata = get_test_metadata(test_id or "")

    st.markdown(f"**{test_id}** — {row.get('category', 'unknown')} · `{row.get('verdict', '')}`")
    st.write(row.get("user_message") or row.get("question"))

    if metadata.get("judge_rubric"):
        st.caption(f"Expected: {metadata['judge_rubric']}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Baseline", f"{row.get('baseline_score', 0):.3f}")
    col2.metric("Candidate", f"{row.get('candidate_score', 0):.3f}")
    col3.metric("Delta", f"{row.get('delta', 0):+.3f}")

    with st.expander("Responses & context", expanded=False):
        st.markdown("**Baseline**")
        st.write(row.get("baseline_response", ""))
        st.markdown("**Candidate**")
        st.write(row.get("candidate_response", ""))
        context = get_retrieved_context(row)
        if context:
            st.markdown("**Retrieved context**")
            for chunk in context:
                st.write(f"- **{chunk.get('section', 'chunk')}**: {chunk.get('text', '')}")
        if row.get("explanation"):
            st.markdown("**Explanation**")
            st.write(row["explanation"])


def render_test_cases(rows: list[dict]) -> None:
    st.subheader("Test Cases")

    verdict_filter = st.multiselect(
        "Filter by verdict",
        ["REGRESSION", "IMPROVEMENT", "UNCHANGED"],
        default=["REGRESSION", "IMPROVEMENT", "UNCHANGED"],
    )
    filtered = [row for row in rows if row.get("verdict") in verdict_filter]

    table = [
        {
            "id": row.get("id"),
            "category": row.get("category"),
            "verdict": row.get("verdict"),
            "baseline_score": row.get("baseline_score"),
            "candidate_score": row.get("candidate_score"),
            "delta": row.get("delta"),
        }
        for row in filtered
    ]
    st.dataframe(table, use_container_width=True, hide_index=True)

    if filtered:
        test_options = [row.get("id") for row in filtered]
        selected = st.selectbox("Inspect test case", test_options, key="test_case_select")
        selected_row = next(r for r in filtered if r.get("id") == selected)
        render_test_case_detail(selected_row)


def render_history(history: list[dict]) -> None:
    st.subheader("History")

    if not history:
        st.info(
            "No evaluation history found. Run `agent-ci check` or `agent-ci evaluate` "
            "to record results."
        )
        return

    table = [
        {
            "timestamp": record.get("timestamp"),
            "comparison": f"{record.get('baseline_version')} -> {record.get('candidate_version')}",
            "candidate_score": record.get("overall_score_candidate"),
            "improvements": record.get("n_improvements"),
            "regressions": record.get("n_regressions"),
            "unchanged": record.get("n_unchanged"),
            "gate": "PASS" if record.get("gate_passed") else "FAIL" if record.get("gate_passed") is False else "n/a",
            "failed_tests": ", ".join(record.get("failed_tests") or []),
        }
        for record in history
    ]
    st.dataframe(table, use_container_width=True, hide_index=True)

    if len(history) > 1:
        st.markdown("**Score trend (candidate)**")
        labels = [f"{r.get('baseline_version')}->{r.get('candidate_version')}" for r in history]
        scores = [float(r.get("overall_score_candidate", 0)) for r in history]
        st.line_chart({"score": scores}, x=labels)

    selected_idx = st.selectbox(
        "View history record",
        range(len(history)),
        format_func=lambda i: (
            f"{history[i].get('timestamp')} — "
            f"{history[i].get('baseline_version')} -> {history[i].get('candidate_version')}"
        ),
    )
    record = history[selected_idx]
    with st.expander("Record details", expanded=True):
        st.json(record)


def main() -> None:
    _inject_styles()

    st.title("Agent CI Dashboard")
    st.caption("Developer view of agent evaluation results — reads generated reports, does not re-run evaluation.")

    with st.sidebar:
        st.header("Data Sources")
        report_path = st.text_input("Report JSON", value=str(DEFAULT_REPORT_PATH))
        history_path = st.text_input("History JSONL", value=str(DEFAULT_HISTORY_PATH))
        st.markdown("---")
        st.markdown(
            "Generate data with:\n"
            "```bash\nagent-ci check\n```"
        )

    report_file = Path(report_path)
    if not report_file.exists():
        st.error(f"Report not found: `{report_file}`")
        st.info("Run `agent-ci check` or `agent-ci evaluate` from the project root first.")
        st.stop()

    try:
        report = _cached_report(str(report_file))
    except Exception as exc:
        st.error(f"Failed to load report: {exc}")
        st.stop()

    summary = get_summary(report)
    rows = get_rows(report)
    gate = get_gate(report)

    history: list[dict] = []
    if Path(history_path).exists():
        try:
            history = _cached_history(history_path)
        except Exception as exc:
            st.sidebar.warning(f"Could not load history: {exc}")

    sections = st.tabs([
        "Overview",
        "Version Comparison",
        "Metrics",
        "Regressions",
        "Test Cases",
        "History",
    ])

    with sections[0]:
        render_overview(summary, gate)
    with sections[1]:
        render_version_comparison(summary)
    with sections[2]:
        render_metrics(summary)
    with sections[3]:
        render_regressions(rows)
    with sections[4]:
        render_test_cases(rows)
    with sections[5]:
        render_history(history)


if __name__ == "__main__":
    main()

"""Agent CI — Streamlit dashboard (classified verification terminal UI)."""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
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
    page_title="Agent CI — Verification Terminal",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Theme & shared UI helpers
# ---------------------------------------------------------------------------

def _esc(value: object) -> str:
    return html.escape(str(value)) if value is not None else ""


def _score_bar(pct: float, width: int = 20) -> str:
    clamped = max(0.0, min(1.0, float(pct)))
    filled = int(clamped * width)
    return "█" * filled + "░" * (width - filled)


def _verdict_label(verdict: str | None) -> str:
    mapping = {
        "REGRESSION": "REGRESSION",
        "IMPROVEMENT": "IMPROVED",
        "UNCHANGED": "UNCHANGED",
    }
    return mapping.get(verdict or "", verdict or "UNKNOWN")


def _verdict_class(verdict: str | None) -> str:
    mapping = {
        "REGRESSION": "verdict-fail",
        "IMPROVEMENT": "verdict-pass",
        "UNCHANGED": "verdict-neutral",
    }
    return mapping.get(verdict or "", "verdict-neutral")


def _suite_counts(rows: list[dict]) -> dict[str, int]:
    counts = {"support": 0, "adversarial": 0, "multi_turn": 0, "tools": 0}
    for row in rows:
        category = row.get("category", "")
        test_type = row.get("test_type", "single_turn")
        if category == "tools":
            counts["tools"] += 1
        elif category == "adversarial":
            counts["adversarial"] += 1
        elif test_type == "multi_turn":
            counts["multi_turn"] += 1
        else:
            counts["support"] += 1
    counts["total"] = len(rows)
    return counts


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap');

        :root {
            --bg-deep: #050608;
            --bg-panel: #0a0e12;
            --bg-panel-alt: #0d1218;
            --border-dim: #1a2a1a;
            --border-glow: #1f4f3f;
            --text-primary: #d7fbe8;
            --text-muted: #7a9a8a;
            --accent-green: #39ff14;
            --accent-cyan: #00e5ff;
            --accent-amber: #ffb020;
            --accent-red: #ff3344;
        }

        .stApp {
            background-color: var(--bg-deep);
            background-image:
                linear-gradient(rgba(57, 255, 20, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(57, 255, 20, 0.03) 1px, transparent 1px);
            background-size: 32px 32px;
        }

        .block-container {
            padding-top: 2.25rem;
            max-width: 100%;
        }

        header[data-testid="stHeader"] {
            background: rgba(5, 6, 8, 0.92);
            border-bottom: 1px solid var(--border-dim);
        }

        section[data-testid="stSidebar"] {
            background: #060809;
            border-right: 1px solid var(--border-dim);
        }

        section[data-testid="stSidebar"] * {
            font-family: 'Share Tech Mono', monospace !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background: transparent;
            border-bottom: 1px solid var(--border-dim);
        }

        .stTabs [data-baseweb="tab"] {
            background: var(--bg-panel);
            border: 1px solid var(--border-dim);
            border-radius: 0;
            color: var(--text-muted);
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding: 0.45rem 0.9rem;
            height: auto;
        }

        .stTabs [aria-selected="true"] {
            background: #0f1812 !important;
            color: var(--accent-green) !important;
            border-color: var(--accent-green) !important;
            box-shadow: 0 0 12px rgba(57, 255, 20, 0.15);
        }

        div[data-testid="stMetric"] {
            background: var(--bg-panel);
            border: 1px solid var(--border-dim);
            border-radius: 0;
            padding: 0.75rem;
            box-shadow: inset 0 0 20px rgba(0, 229, 255, 0.03);
        }

        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] label p,
        div[data-testid="stMetric"] [data-testid="stMetricValue"],
        div[data-testid="stMetric"] [data-testid="stMetricValue"] div,
        div[data-testid="stMetric"] [data-testid="stMetricDelta"],
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] svg {
            color: var(--text-primary) !important;
            fill: var(--text-primary) !important;
            font-family: 'Share Tech Mono', monospace !important;
        }

        .stDataFrame, .stTable {
            border: 1px solid var(--border-dim);
        }

        .terminal-wrap {
            position: relative;
            font-family: 'Rajdhani', sans-serif;
            color: var(--text-primary);
        }

        .terminal-wrap::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background: repeating-linear-gradient(
                0deg,
                rgba(0, 0, 0, 0.12),
                rgba(0, 0, 0, 0.12) 1px,
                transparent 1px,
                transparent 3px
            );
            opacity: 0.22;
            z-index: 9999;
        }

        .cmd-header {
            border: 1px solid var(--border-glow);
            background: linear-gradient(180deg, #0b1210 0%, #070a0d 100%);
            padding: 1.35rem 1.25rem 1.1rem;
            margin: 0.5rem 0 1rem;
            box-shadow: 0 0 24px rgba(57, 255, 20, 0.08);
            position: relative;
            overflow: visible;
        }

        .cmd-header > div {
            position: relative;
            z-index: 2;
        }

        .cmd-header::after {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.05), transparent);
            animation: sweep 6s linear infinite;
            pointer-events: none;
        }

        @keyframes sweep {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        .cmd-title {
            font-family: 'Orbitron', sans-serif;
            font-size: clamp(1.35rem, 2.8vw, 2.1rem);
            font-weight: 900;
            letter-spacing: 0.1em;
            color: var(--accent-green);
            line-height: 1.4;
            margin: 0;
            padding: 0.15rem 0 0.25rem;
        }

        .cmd-title .cmd-sep {
            font-family: 'Share Tech Mono', monospace;
            color: var(--accent-cyan);
            letter-spacing: 0;
        }

        .cmd-subtitle {
            font-family: 'Rajdhani', sans-serif;
            font-size: clamp(0.85rem, 1.5vw, 1rem);
            letter-spacing: 0.28em;
            text-transform: uppercase;
            color: var(--accent-cyan);
            margin: 0.35rem 0 0.75rem 0;
        }

        .cmd-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem 2rem;
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--text-muted);
            border-top: 1px solid var(--border-dim);
            padding-top: 0.75rem;
        }

        .cmd-meta span strong {
            color: var(--text-primary);
        }

        .status-online {
            color: var(--accent-green);
            animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.45; }
        }

        .panel {
            border: 1px solid var(--border-dim);
            background: var(--bg-panel);
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .panel:hover {
            border-color: var(--border-glow);
            box-shadow: 0 0 16px rgba(57, 255, 20, 0.06);
        }

        .panel-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 0.78rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--accent-cyan);
            margin: 0 0 0.75rem 0;
        }

        .panel-label {
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.65rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 0.25rem;
        }

        .panel-value {
            font-family: 'Rajdhani', sans-serif;
            font-size: 1.35rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.2;
        }

        .panel-value-lg {
            font-family: 'Orbitron', sans-serif;
            font-size: clamp(1rem, 2vw, 1.45rem);
            color: var(--accent-green);
            letter-spacing: 0.06em;
        }

        .mission-text {
            font-family: 'Orbitron', sans-serif;
            font-size: clamp(1rem, 2.2vw, 1.55rem);
            letter-spacing: 0.08em;
            color: var(--text-primary);
            margin: 0.5rem 0;
        }

        .mission-sub {
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.78rem;
            letter-spacing: 0.16em;
            color: var(--accent-amber);
            text-transform: uppercase;
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 0.65rem;
        }

        .status-cell {
            border: 1px solid var(--border-dim);
            background: var(--bg-panel-alt);
            padding: 0.65rem 0.75rem;
        }

        .status-cell .label {
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.62rem;
            letter-spacing: 0.12em;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .status-cell .value {
            font-family: 'Rajdhani', sans-serif;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--accent-green);
            margin-top: 0.2rem;
        }

        .status-cell .value.warn { color: var(--accent-amber); }
        .status-cell .value.fail { color: var(--accent-red); }

        .scan-row {
            margin: 0.55rem 0;
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.78rem;
        }

        .scan-label {
            display: flex;
            justify-content: space-between;
            color: var(--text-muted);
            margin-bottom: 0.2rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .scan-bar {
            color: var(--accent-green);
            letter-spacing: 0.05em;
            word-break: break-all;
        }

        .scan-bar.candidate { color: var(--accent-cyan); }

        .alert-panel {
            border: 1px solid var(--accent-red);
            background: linear-gradient(180deg, rgba(255, 51, 68, 0.12), rgba(10, 10, 12, 0.95));
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
            box-shadow: 0 0 20px rgba(255, 51, 68, 0.15);
        }

        .alert-panel.pass {
            border-color: var(--accent-green);
            background: linear-gradient(180deg, rgba(57, 255, 20, 0.08), rgba(10, 10, 12, 0.95));
            box-shadow: 0 0 20px rgba(57, 255, 20, 0.1);
        }

        .alert-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 0.95rem;
            letter-spacing: 0.14em;
            color: var(--accent-red);
            margin: 0 0 0.75rem 0;
        }

        .alert-panel.pass .alert-title { color: var(--accent-green); }

        .matrix-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 0.55rem;
        }

        .matrix-cell {
            border: 1px solid var(--border-dim);
            background: #080b0f;
            padding: 0.6rem 0.7rem;
        }

        .matrix-cell .name {
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.62rem;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .matrix-cell .count {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.25rem;
            color: var(--accent-cyan);
            margin-top: 0.15rem;
        }

        .matrix-cell.total .count { color: var(--accent-green); }

        .pipeline {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.35rem 0.5rem;
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.68rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
        }

        .pipeline .step {
            border: 1px solid var(--border-dim);
            padding: 0.35rem 0.55rem;
            color: var(--accent-cyan);
            background: #080c10;
        }

        .pipeline .arrow { color: var(--accent-green); }

        .intel-block {
            border-left: 2px solid var(--accent-cyan);
            padding: 0.5rem 0 0.5rem 0.85rem;
            margin: 0.65rem 0;
        }

        .intel-block .field {
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.62rem;
            letter-spacing: 0.12em;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .intel-block .content {
            font-family: 'Rajdhani', sans-serif;
            font-size: 1rem;
            color: var(--text-primary);
            margin-top: 0.15rem;
        }

        .audit-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 0.5rem;
        }

        .audit-item {
            border: 1px solid var(--border-dim);
            padding: 0.55rem 0.65rem;
            background: #080b0f;
        }

        .audit-item .ok { color: var(--accent-green); }
        .audit-item .bad { color: var(--accent-red); }

        .regression-card {
            border-left: 3px solid var(--accent-red);
            padding-left: 0.85rem;
            margin-bottom: 1rem;
            color: var(--accent-red);
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.78rem;
            letter-spacing: 0.06em;
        }

        .section-heading {
            font-family: 'Orbitron', sans-serif;
            font-size: 0.82rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: var(--accent-green);
            border-bottom: 1px solid var(--border-dim);
            padding-bottom: 0.45rem;
            margin: 0 0 1rem 0;
        }

        .verdict-fail { color: var(--accent-red); font-weight: 700; }
        .verdict-pass { color: var(--accent-green); font-weight: 700; }
        .verdict-neutral { color: var(--text-muted); font-weight: 700; }

        .nav-console-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            color: var(--accent-green);
            margin: 1rem 0 0.35rem 0;
        }

        .nav-console-item {
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.68rem;
            color: var(--text-muted);
            letter-spacing: 0.06em;
            margin: 0.15rem 0 0.15rem 0.5rem;
        }

        .terminal-footer {
            border-top: 1px solid var(--border-dim);
            margin-top: 2rem;
            padding: 0.75rem 0;
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.62rem;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            font-family: 'Orbitron', sans-serif !important;
            letter-spacing: 0.08em;
        }

        .stCaption, .stCode, code, pre {
            font-family: 'Share Tech Mono', monospace !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_command_header(summary: dict, gate: dict | None) -> None:
    baseline = _esc(summary.get("baseline_name", "baseline"))
    candidate = _esc(summary.get("candidate_name", "candidate"))
    n_tests = summary.get("n_tests", 0)
    gate_status = _esc(gate.get("status", "N/A")) if gate else "NO GATE DATA"
    gate_class = "status-online" if gate and gate.get("passed") else (
        "status-online" if not gate else ""
    )
    st.markdown(
        f"""
        <div class="terminal-wrap">
        <div class="cmd-header">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.75rem;">
                <div>
                    <p class="cmd-title">AGENT <span class="cmd-sep">//</span> CI</p>
                    <p class="cmd-subtitle">Autonomous Agent Verification Terminal</p>
                </div>
                <div style="text-align:right;font-family:'Share Tech Mono',monospace;font-size:0.72rem;letter-spacing:0.1em;">
                    <div style="color:#7a9a8a;text-transform:uppercase;">System Status</div>
                    <div class="{gate_class}" style="color:#39ff14;font-size:0.95rem;">● ONLINE</div>
                </div>
            </div>
            <div class="cmd-meta">
                <span><strong>Classification:</strong> Internal</span>
                <span><strong>Protocol:</strong> Active</span>
                <span><strong>Baseline:</strong> {baseline}</span>
                <span><strong>Candidate:</strong> {candidate}</span>
                <span><strong>Test Suite:</strong> {n_tests} cases</span>
                <span><strong>Gate:</strong> {gate_status}</span>
            </div>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mission_panel(summary: dict) -> None:
    baseline = _esc(summary.get("baseline_name", "baseline"))
    candidate = _esc(summary.get("candidate_name", "candidate"))
    st.markdown(
        f"""
        <div class="panel">
            <p class="panel-title">Mission Objective</p>
            <p class="mission-text">DETECT SILENT QUALITY REGRESSIONS<br>BEFORE THEY REACH PRODUCTION.</p>
            <p class="mission-sub">{baseline} → {candidate} // COMPARE // TEST // VERIFY</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_system_status(summary: dict, gate: dict | None) -> None:
    n_tests = summary.get("n_tests", 0)
    n_regressions = summary.get("n_regressions", 0)
    gate_label = "PASSED" if gate and gate.get("passed") else (
        "FAILED" if gate else "N/A"
    )
    gate_class = "" if gate and gate.get("passed") else ("fail" if gate else "warn")
    eval_label = "READY" if n_tests else "NO DATA"
    st.markdown(
        f"""
        <div class="panel">
            <p class="panel-title">System Status Strip</p>
            <div class="status-grid">
                <div class="status-cell"><div class="label">System</div><div class="value">ONLINE</div></div>
                <div class="status-cell"><div class="label">Evaluation</div><div class="value">{_esc(eval_label)}</div></div>
                <div class="status-cell"><div class="label">RAG</div><div class="value">ACTIVE</div></div>
                <div class="status-cell"><div class="label">Regression Detection</div><div class="value">ACTIVE</div></div>
                <div class="status-cell"><div class="label">Test Suite</div><div class="value">{n_tests} CASES</div></div>
                <div class="status-cell"><div class="label">Regressions</div><div class="value {'fail' if n_regressions else ''}">{n_regressions}</div></div>
                <div class="status-cell"><div class="label">Quality Gate</div><div class="value {gate_class}">{_esc(gate_label)}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_security_score(summary: dict) -> None:
    baseline_score = float(summary.get("mean_score_baseline", 0))
    candidate_score = float(summary.get("mean_score_candidate", 0))
    delta = float(summary.get("mean_delta", 0))
    baseline_name = _esc(summary.get("baseline_name", "baseline"))
    candidate_name = _esc(summary.get("candidate_name", "candidate"))
    delta_color = "var(--accent-green)" if delta >= 0 else "var(--accent-red)"
    delta_sign = "+" if delta >= 0 else ""
    st.markdown(
        f"""
        <div class="panel">
            <p class="panel-title">Agent Integrity Scan</p>
            <div class="scan-row">
                <div class="scan-label"><span>{baseline_name}</span><span>{format_pct(baseline_score)}</span></div>
                <div class="scan-bar">{_score_bar(baseline_score)}</div>
            </div>
            <div class="scan-row">
                <div class="scan-label"><span>{candidate_name}</span><span>{format_pct(candidate_score)}</span></div>
                <div class="scan-bar candidate">{_score_bar(candidate_score)}</div>
            </div>
            <div style="margin-top:0.75rem;font-family:'Share Tech Mono',monospace;font-size:0.72rem;letter-spacing:0.1em;color:#7a9a8a;">
                QUALITY DELTA <span style="color:{delta_color};font-size:1rem;margin-left:0.5rem;">{delta_sign}{delta:.1%}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_regression_alert(summary: dict, gate: dict | None, regressions: list[dict]) -> None:
    if regressions:
        row = regressions[0]
        test_id = _esc(row.get("id") or row.get("test_id"))
        baseline = row.get("baseline_score", 0)
        candidate = row.get("candidate_score", 0)
        delta = row.get("delta", 0)
        gate_status = _esc(gate.get("status", "FAILED")) if gate else "UNKNOWN"
        st.markdown(
            f"""
            <div class="alert-panel">
                <p class="alert-title">⚠ REGRESSION DETECTED</p>
                <div class="status-grid">
                    <div class="status-cell"><div class="label">Threat Vector</div><div class="value fail">{test_id}</div></div>
                    <div class="status-cell"><div class="label">Baseline</div><div class="value">{baseline:.3f}</div></div>
                    <div class="status-cell"><div class="label">Candidate</div><div class="value">{candidate:.3f}</div></div>
                    <div class="status-cell"><div class="label">Delta</div><div class="value fail">{delta:+.3f}</div></div>
                    <div class="status-cell"><div class="label">Status</div><div class="value fail">QUALITY GATE: {_esc(gate_status)}</div></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if len(regressions) > 1:
            others = ", ".join(
                _esc(r.get("id") or r.get("test_id", "")) for r in regressions[1:]
            )
            st.caption(f"Additional regressions: {others}")
    else:
        gate_passed = gate.get("passed") if gate else None
        gate_label = "PASSED" if gate_passed else ("N/A" if gate is None else "PASSED")
        st.markdown(
            f"""
            <div class="alert-panel pass">
                <p class="alert-title">NO REGRESSIONS DETECTED</p>
                <div class="status-grid">
                    <div class="status-cell"><div class="label">Threat Level</div><div class="value">CLEAR</div></div>
                    <div class="status-cell"><div class="label">Quality Gate</div><div class="value">{_esc(gate_label)}</div></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_verification_matrix(rows: list[dict]) -> None:
    counts = _suite_counts(rows)
    st.markdown(
        f"""
        <div class="panel">
            <p class="panel-title">Verification Matrix</p>
            <div class="matrix-grid">
                <div class="matrix-cell"><div class="name">Support Tests</div><div class="count">{counts['support']}</div></div>
                <div class="matrix-cell"><div class="name">Adversarial</div><div class="count">{counts['adversarial']}</div></div>
                <div class="matrix-cell"><div class="name">Multi-Turn</div><div class="count">{counts['multi_turn']}</div></div>
                <div class="matrix-cell"><div class="name">Tool-Use</div><div class="count">{counts['tools']}</div></div>
                <div class="matrix-cell total"><div class="name">Total</div><div class="count">{counts['total']}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_knowledge_subsystem(has_context: bool = False) -> None:
    active = "ACTIVE" if has_context else "STANDBY"
    st.markdown(
        f"""
        <div class="panel">
            <p class="panel-title">Knowledge Subsystem — RAG Pipeline</p>
            <div class="pipeline">
                <span class="step">Documents</span><span class="arrow">↓</span>
                <span class="step">Chunking</span><span class="arrow">↓</span>
                <span class="step">Embeddings</span><span class="arrow">↓</span>
                <span class="step">Vector Search</span><span class="arrow">↓</span>
                <span class="step">Retrieved Context</span><span class="arrow">↓</span>
                <span class="step">Agent Evaluation</span>
            </div>
            <div style="margin-top:0.65rem;font-family:'Share Tech Mono',monospace;font-size:0.68rem;color:#7a9a8a;letter-spacing:0.1em;">
                RETRIEVAL STATUS: <span style="color:#39ff14;">{active}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_root_cause_panel(analysis: dict, test_id: str) -> None:
    st.markdown('<p class="section-heading">// Automated Root Cause Analysis</p>', unsafe_allow_html=True)
    st.caption(analysis.get("disclaimer", "AI-generated analysis — not guaranteed to be correct."))
    if analysis.get("success"):
        st.markdown(
            f"""
            <div class="intel-block"><div class="field">Target</div><div class="content">{_esc(test_id)}</div></div>
            <div class="intel-block"><div class="field">Observed Failure</div><div class="content">{_esc(analysis.get('explanation', ''))}</div></div>
            <div class="intel-block"><div class="field">Likely Cause</div><div class="content">{_esc(analysis.get('root_cause', ''))}</div></div>
            <div class="intel-block"><div class="field">Recommended Investigation</div><div class="content">{_esc(analysis.get('suggested_fix', ''))}</div></div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            f"Confidence: {analysis.get('confidence', 0):.0%} · Source: {analysis.get('source')}"
        )
    else:
        st.error(f"Analysis unavailable: {analysis.get('error', 'unknown error')}")


def render_tool_audit(row: dict) -> None:
    test_id = row.get("id") or row.get("test_id")
    metadata = get_test_metadata(test_id or "")
    expectations = metadata.get("tool_expectations")
    candidate_metrics = row.get("candidate_metrics") or {}
    tool_metric = candidate_metrics.get("tool_usage") or {}
    details = tool_metric.get("details") or {}
    issues = details.get("issues") or []
    checks_run = details.get("checks_run", 0)
    checks_passed = details.get("checks_passed", 0)
    passed = tool_metric.get("passed", True)
    tool_calls = (row.get("candidate_agent_response") or {}).get("tool_calls") or []

    if not expectations and not tool_calls and row.get("category") != "tools":
        return

    def _mark(ok: bool | None) -> str:
        if ok is True:
            return '<span class="ok">✓ PASS</span>'
        if ok is False:
            return '<span class="bad">✕ FAIL</span>'
        return '<span style="color:#7a9a8a;">— N/A</span>'

    expected_tool = expectations.get("expected_tool") if expectations else None
    forbidden = (expectations or {}).get("forbidden_tools") or []
    phantom_check = bool(
        (expectations or {}).get("detect_phantom_actions")
        or metadata.get("action_completion_phrases")
    )

    expected_ok = None
    if expected_tool:
        expected_ok = any(call.get("tool") == expected_tool for call in tool_calls)
    forbidden_ok = None
    if forbidden:
        used = [call.get("tool") for call in tool_calls]
        forbidden_ok = not any(t in forbidden for t in used)
    phantom_ok = None
    if phantom_check:
        phantom_ok = not any("phantom" in issue.lower() or "claimed" in issue.lower() for issue in issues)
    args_ok = None
    if expectations and expectations.get("expected_arguments") and expected_tool:
        args_ok = expected_ok
    exec_ok = None
    if expectations and expectations.get("require_execution", bool(expected_tool)):
        exec_ok = any(call.get("status") == "success" for call in tool_calls)

    result_label = "VERIFIED" if passed else "FAILED"
    result_class = "ok" if passed else "bad"

    st.markdown('<p class="section-heading">Tool Invocation Audit</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="panel">
            <div class="audit-grid">
                <div class="audit-item"><div class="panel-label">Expected Action</div>{_mark(expected_ok)}</div>
                <div class="audit-item"><div class="panel-label">Actual Action</div>{_mark(exec_ok if exec_ok is not None else (True if tool_calls else None))}</div>
                <div class="audit-item"><div class="panel-label">Phantom Action</div>{_mark(phantom_ok)}</div>
                <div class="audit-item"><div class="panel-label">Argument Validation</div>{_mark(args_ok)}</div>
                <div class="audit-item"><div class="panel-label">Forbidden Tools</div>{_mark(forbidden_ok)}</div>
                <div class="audit-item"><div class="panel-label">Result</div><span class="{result_class}">{result_label}</span></div>
            </div>
            <div style="margin-top:0.65rem;font-family:'Share Tech Mono',monospace;font-size:0.68rem;color:#7a9a8a;">
                CHECKS: {checks_passed}/{checks_run} · SCORE: {tool_metric.get('score', 'n/a')} · {_esc(tool_metric.get('reason', ''))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """
        <div class="terminal-footer">
            Agent CI Verification Terminal · Read-only evaluation viewer ·
            Run agent-ci check to refresh data · Classification: Internal
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_nav() -> None:
    st.markdown(
        """
        <div style="font-family:'Orbitron',sans-serif;font-size:1.05rem;letter-spacing:0.1em;
            color:#39ff14;margin:0.25rem 0 0.15rem;line-height:1.4;">
            AGENT <span style="font-family:'Share Tech Mono',monospace;color:#00e5ff;">//</span> CI
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Data helpers (unchanged logic)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Tab renderers (preserved functionality, redesigned presentation)
# ---------------------------------------------------------------------------

def render_overview(summary: dict, gate: dict | None, rows: list[dict]) -> None:
    regressions = filter_rows_by_verdict(rows, "REGRESSION")
    render_mission_panel(summary)
    render_system_status(summary, gate)
    render_regression_alert(summary, gate, regressions)
    render_security_score(summary)
    render_verification_matrix(rows)
    render_knowledge_subsystem(
        has_context=any(get_retrieved_context(r) for r in rows)
    )

    st.markdown('<p class="section-heading">Operational Metrics</p>', unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Candidate Quality", format_pct(summary.get("mean_score_candidate")))
    col2.metric("Baseline Score", format_pct(summary.get("mean_score_baseline")))
    col3.metric("Improvements", summary.get("n_improvements", 0))
    col4.metric("Regressions", summary.get("n_regressions", 0))
    col5.metric("Unchanged", summary.get("n_unchanged", 0))

    left, right = st.columns(2)
    with left:
        st.markdown('<p class="panel-label">Agent Comparison</p>', unsafe_allow_html=True)
        st.write(f"Baseline: `{summary.get('baseline_name', 'baseline')}`")
        st.write(f"Candidate: `{summary.get('candidate_name', 'candidate')}`")
        st.write(f"Score delta: **{format_pct(summary.get('mean_delta'))}**")
        st.write(f"Tests run: **{summary.get('n_tests', 0)}**")

    with right:
        st.markdown('<p class="panel-label">Quality Gate</p>', unsafe_allow_html=True)
        if gate:
            status = gate.get("status", "UNKNOWN")
            color = "green" if gate.get("passed") else "red"
            st.markdown(f"CI Status: :{color}[**{status}**]")
            if gate.get("regression_ids"):
                st.write("Failed tests:", ", ".join(gate["regression_ids"]))
        else:
            st.info("Run `agent-ci check` to include gate status in the report.")


def render_version_comparison(summary: dict) -> None:
    st.markdown('<p class="section-heading">Version Comparison — Integrity Scan</p>', unsafe_allow_html=True)
    render_security_score(summary)

    agents = [
        summary.get("baseline_name", "baseline"),
        summary.get("candidate_name", "candidate"),
    ]
    scores = [
        float(summary.get("mean_score_baseline", 0)),
        float(summary.get("mean_score_candidate", 0)),
    ]
    st.bar_chart(
        pd.DataFrame({"Agent": agents, "overall_score": scores}),
        x="Agent",
        y="overall_score",
    )

    st.table([
        {"Agent": agents[0], "Role": "Baseline", "Overall Score": format_pct(scores[0])},
        {"Agent": agents[1], "Role": "Candidate", "Overall Score": format_pct(scores[1])},
    ])


def render_metrics(summary: dict) -> None:
    st.markdown('<p class="section-heading">Metric Diagnostics</p>', unsafe_allow_html=True)

    rows = metric_comparison_rows(summary)
    if not rows:
        st.warning("No metric data found in the report.")
        return

    metrics = _metrics_chart_index(summary)
    chart = _metrics_chart_data(summary)
    if metrics:
        st.bar_chart(
            pd.DataFrame({
                "metric": metrics,
                "baseline": chart["baseline"],
                "candidate": chart["candidate"],
            }),
            x="metric",
            y=["baseline", "candidate"],
        )

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

    st.markdown(
        f'<p class="section-heading">Threat Vector: {_esc(test_id)}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="regression-card">REGRESSION DETECTED — DELTA {row.get("delta", 0):+.3f}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**Question**")
    st.write(row.get("user_message") or row.get("question"))

    expected = metadata.get("judge_rubric")
    if expected:
        st.markdown("**Expected Behavior**")
        st.info(expected)

    context = get_retrieved_context(row)
    render_knowledge_subsystem(has_context=bool(context))
    st.markdown("**Retrieved RAG Context**")
    if context:
        for chunk in context:
            with st.expander(chunk.get("section", chunk.get("chunk_id", "chunk"))):
                st.caption(f"Document: {chunk.get('document')} | Score: {chunk.get('score')}")
                st.write(chunk.get("text", ""))
    else:
        st.write("No retrieved context for this test.")

    render_tool_audit(row)

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
        st.markdown('<p class="section-heading">Generated Test Proposals</p>', unsafe_allow_html=True)
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
        render_root_cause_panel(analysis, test_id or "")

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
    st.markdown('<p class="section-heading">Regression Analysis</p>', unsafe_allow_html=True)

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
    verdict = row.get("verdict", "")

    st.markdown(
        f'**{_esc(test_id)}** — {row.get("category", "unknown")} · '
        f'<span class="{_verdict_class(verdict)}">{_verdict_label(verdict)}</span>',
        unsafe_allow_html=True,
    )
    st.write(row.get("user_message") or row.get("question"))

    if metadata.get("judge_rubric"):
        st.caption(f"Expected: {metadata['judge_rubric']}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Baseline", f"{row.get('baseline_score', 0):.3f}")
    col2.metric("Candidate", f"{row.get('candidate_score', 0):.3f}")
    col3.metric("Delta", f"{row.get('delta', 0):+.3f}")

    render_tool_audit(row)

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
    st.markdown('<p class="section-heading">Verification Console — Test Results</p>', unsafe_allow_html=True)

    verdict_filter = st.multiselect(
        "Filter by verdict",
        ["REGRESSION", "IMPROVEMENT", "UNCHANGED"],
        default=["REGRESSION", "IMPROVEMENT", "UNCHANGED"],
    )
    filtered = [row for row in rows if row.get("verdict") in verdict_filter]

    table = [
        {
            "TEST ID": row.get("id"),
            "CATEGORY": row.get("category"),
            "BASELINE": row.get("baseline_score"),
            "CANDIDATE": row.get("candidate_score"),
            "DELTA": row.get("delta"),
            "STATUS": _verdict_label(row.get("verdict")),
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
    st.markdown('<p class="section-heading">Evaluation History — Audit Log</p>', unsafe_allow_html=True)

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
        st.line_chart(
            pd.DataFrame({"score": scores, "comparison": labels}),
            x="comparison",
            y="score",
        )

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

    with st.sidebar:
        render_sidebar_nav()
        st.markdown("---")
        report_path = st.text_input("Report JSON", value=str(DEFAULT_REPORT_PATH))
        history_path = st.text_input("History JSONL", value=str(DEFAULT_HISTORY_PATH))
        st.caption("Run `agent-ci check` to refresh data.")

    report_file = Path(report_path)
    if not report_file.exists():
        st.markdown(
            """
            <div class="cmd-header">
                <p class="cmd-title">AGENT <span class="cmd-sep">//</span> CI</p>
                <p class="cmd-subtitle">Autonomous Agent Verification Terminal</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.error(f"Report not found: `{report_file}`")
        st.info("Run `agent-ci check` or `agent-ci evaluate` from the project root first.")
        render_footer()
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

    render_command_header(summary, gate)

    sections = st.tabs([
        "Overview",
        "Version Comparison",
        "Metrics",
        "Regressions",
        "Test Cases",
        "History",
    ])

    with sections[0]:
        render_overview(summary, gate, rows)
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

    render_footer()


if __name__ == "__main__":
    main()

"""Agent CI command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_ci.diff import build_diff_report
from agent_ci.gate import build_gate_report, evaluate_gate
from agent_ci.history.compare import print_history_compare, print_history_list
from agent_ci.history.record import build_evaluation_record
from agent_ci.history.store import get_history_store
from agent_ci.regression.types import VERDICT_REGRESSION

DEFAULT_OUTPUT = "diff_report.json"


def _format_pct(value: float) -> str:
    return f"{value:.1%}"


def print_evaluate_summary(report: dict) -> None:
    """Human-readable evaluation summary (no CI gate status)."""
    s = report["summary"]
    print("AGENT CI")
    print("-" * 20)
    print(f"Baseline: {s['baseline_name']}")
    print(f"Candidate: {s['candidate_name']}")
    print()
    print(f"Tests: {s['n_tests']}")
    print()
    print(f"Improvements: {s['n_improvements']}")
    print(f"Regressions: {s['n_regressions']}")
    print(f"Unchanged: {s['n_unchanged']}")
    print()
    print("Overall:")
    print(f"Baseline: {_format_pct(s['mean_score_baseline'])}")
    print(f"Candidate: {_format_pct(s['mean_score_candidate'])}")
    print(f"Delta: {s['mean_delta']:+.1%}")
    print()

    regressions = [r for r in report["rows"] if r["verdict"] == VERDICT_REGRESSION]
    if regressions:
        print("Regressions:")
        for row in regressions:
            print(f"  {row['id']}  (delta: {row['delta']:+.3f})")
            if row.get("metric_regressions"):
                print(f"    metrics: {', '.join(row['metric_regressions'])}")
    print()


def print_check_summary(report: dict, gate) -> None:
    """Human-readable CI check summary with gate status."""
    s = report["summary"]
    print("AGENT CI")
    print("-" * 20)
    print(f"Baseline: {s['baseline_name']}")
    print(f"Candidate: {s['candidate_name']}")
    print()
    print(f"Tests: {s['n_tests']}")
    print()
    print(f"Improvements: {gate.n_improvements}")
    print(f"Regressions: {gate.n_regressions}")
    print(f"Unchanged: {gate.n_unchanged}")
    print()
    print("Overall:")
    print(f"Baseline: {_format_pct(gate.mean_score_baseline)}")
    print(f"Candidate: {_format_pct(gate.mean_score_candidate)}")
    print(f"Delta: {gate.mean_delta:+.1%}")
    print()

    regressions = [r for r in report["rows"] if r["verdict"] == VERDICT_REGRESSION]
    for row in regressions:
        print("REGRESSION:")
        print(row["id"])
        print()
        print(f"Delta: {row['delta']:+.3f}")
        if row.get("metric_regressions"):
            print(f"Metrics: {', '.join(row['metric_regressions'])}")
        if row.get("explanation"):
            print(f"Reason: {row['explanation']}")
        print()

    print(f"CI STATUS: {gate.status}")


def _write_json_report(payload: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved {output_path}")


def _maybe_save_history(
    report: dict,
    *,
    gate=None,
    save_history: bool,
    history_path: str | None,
) -> None:
    if not save_history:
        return

    record = build_evaluation_record(report, gate=gate)
    store = get_history_store(history_path)
    store.append(record)
    print(
        f"Recorded evaluation history: {record.baseline_version} -> "
        f"{record.candidate_version} ({record.id})"
    )


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Run benchmark evaluation and produce reports."""
    report = build_diff_report()
    print_evaluate_summary(report)

    output = Path(args.output)
    payload = {"summary": report["summary"], "regression_report": report["regression_report"], "rows": report["rows"]}
    _write_json_report(payload, output)

    _maybe_save_history(
        report,
        save_history=not args.no_history,
        history_path=args.history_path,
    )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Run benchmark, detect regressions, and enforce the quality gate."""
    report = build_diff_report()
    gate = evaluate_gate(report, max_regressions=args.max_regressions)
    print_check_summary(report, gate)

    output = Path(args.output)
    payload = build_gate_report(report, gate)
    _write_json_report(payload, output)

    _maybe_save_history(
        report,
        gate=gate,
        save_history=not args.no_history,
        history_path=args.history_path,
    )

    return 0 if gate.passed else 1


def cmd_history_list(args: argparse.Namespace) -> int:
    store = get_history_store(args.history_path)
    print_history_list(store.load_all())
    return 0


def cmd_history_compare(args: argparse.Namespace) -> int:
    store = get_history_store(args.history_path)
    records = store.load_all()
    if args.limit is not None:
        records = records[-args.limit :]
    print_history_compare(records)
    return 0


def cmd_history_show(args: argparse.Namespace) -> int:
    store = get_history_store(args.history_path)
    records = store.load_all()

    record = store.get_by_id(args.id)
    if record is None:
        try:
            index = int(args.id) - 1
            record = records[index]
        except (ValueError, IndexError):
            print(f"No history record found for {args.id!r}", file=sys.stderr)
            return 1

    print(json.dumps(record.to_dict(), indent=2))
    return 0


def _add_history_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Do not append this run to evaluation history.",
    )
    parser.add_argument(
        "--history-path",
        default=None,
        help="Custom path for the JSONL history file.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-ci",
        description="Regression testing and quality gating for LLM agents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate = sub.add_parser("evaluate", help="Run baseline vs candidate evaluation.")
    evaluate.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT,
        help=f"JSON report path (default: {DEFAULT_OUTPUT})",
    )
    _add_history_options(evaluate)
    evaluate.set_defaults(func=cmd_evaluate)

    check = sub.add_parser("check", help="Run evaluation and enforce the regression quality gate.")
    check.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT,
        help=f"JSON report path (default: {DEFAULT_OUTPUT})",
    )
    check.add_argument(
        "--max-regressions",
        type=int,
        default=0,
        help="Maximum allowed regressions before the gate fails (default: 0).",
    )
    _add_history_options(check)
    check.set_defaults(func=cmd_check)

    history = sub.add_parser("history", help="View and compare evaluation history.")
    history_sub = history.add_subparsers(dest="history_command", required=True)

    history_list = history_sub.add_parser("list", help="List stored evaluation runs.")
    history_list.add_argument("--history-path", default=None)
    history_list.set_defaults(func=cmd_history_list)

    history_compare = history_sub.add_parser("compare", help="Compare metrics across historical runs.")
    history_compare.add_argument("--history-path", default=None)
    history_compare.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Compare only the most recent N runs.",
    )
    history_compare.set_defaults(func=cmd_history_compare)

    history_show = history_sub.add_parser("show", help="Show one stored evaluation record as JSON.")
    history_show.add_argument("id", help="Record UUID or 1-based list index.")
    history_show.add_argument("--history-path", default=None)
    history_show.set_defaults(func=cmd_history_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

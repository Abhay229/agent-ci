"""
Entry point: run Agent CI end to end in mock mode (no API key needed) and
save the diff report as JSON for the viewer artifact.

For a live run against real models:
    export AGENT_CI_LIVE=1
    export OPENROUTER_API_KEY=sk-or-...
    python run_demo.py
"""
import json
from agent_ci.dataset import TEST_CASES
from agent_ci.diff import build_diff_report, print_report

if __name__ == "__main__":
    print(f"Loaded {len(TEST_CASES)} support test cases across "
          f"{len(set(t['category'] for t in TEST_CASES))} categories.")
    report = build_diff_report()
    print_report(report)
    with open("diff_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nSaved diff_report.json")

"""Run the agent-evaluation suite from the command line.

Usage::

    python -m evals

Runs every case against the offline agent and prints an overall pass rate plus a
per-category breakdown and any failures.
"""
from __future__ import annotations

import sys

from evals import CASES, run_suite, summarize


def main() -> int:
    results = run_suite(CASES)
    summary = summarize(results)

    print(f"FinModel AI — agent evaluation ({summary['total']} cases)")
    print(f"Pass rate: {summary['passed']}/{summary['total']} ({summary['pass_rate'] * 100:.0f}%)\n")

    print("By category:")
    for category, stats in sorted(summary["by_category"].items()):
        print(f"  {category:<16} {stats['passed']}/{stats['total']}")

    failures = [r for r in results if not r.passed]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for r in failures:
            print(f"  [{r.case.name}] {r.case.query!r}")
            for f in r.failures:
                print(f"    - {f}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())

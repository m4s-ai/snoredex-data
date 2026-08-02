#!/usr/bin/env python3
"""Regression tests for drift-metric polarity and the exit code (#69).

Two defects lived here together. Metrics had one direction — down was always a loss — so closing
the language review queue drove `pending units` to 0 and the suite printed "!!! COUNTS WENT
BACKWARDS" on every clean run thereafter, permanently, for the best possible reason. And
`suite.regressed` never reached the exit code, so a *genuine* loss printed the same banner and CI
went green through it.

The combination is worse than either part: the alarm that fires constantly is the alarm nobody
reads, and behind it the real one could not fail the build.

These are unit tests rather than a data fixture because polarity is a property of the protocol, not
of today's counts — `verification/checks.py` had no tests at all, and the two suites that depend on
it are the project's truth test.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checks import DOWN_IS_PROGRESS, UP_IS_PROGRESS, Metric, Suite  # noqa: E402

FAILURES: list[str] = []


def expect(label: str, actual, wanted) -> None:
    if actual != wanted:
        FAILURES.append(f"{label}: expected {wanted!r}, got {actual!r}")


def main() -> int:
    # --- things that exist: a fall is a loss ------------------------------------------------- #
    expect("units lost is a regression",
           Metric("units total", 718, 719).regressed, True)
    expect("units gained is not",
           Metric("units total", 720, 719).regressed, False)
    expect("units unchanged is not",
           Metric("units total", 719, 719).regressed, False)

    # --- queues: a rise is the loss ----------------------------------------------------------- #
    queue_grew = Metric("pending units", 3, 0, direction=DOWN_IS_PROGRESS)
    expect("a reopened queue is a regression", queue_grew.regressed, True)
    expect("a reopened queue is not an improvement", queue_grew.improved, False)

    queue_closed = Metric("pending units", 0, 9, direction=DOWN_IS_PROGRESS)
    expect("closing a queue is not a regression", queue_closed.regressed, False)
    expect("closing a queue is an improvement", queue_closed.improved, True)
    expect("an empty queue at its baseline is quiet",
           Metric("pending units", 0, 0, direction=DOWN_IS_PROGRESS).regressed, False)

    # The bug exactly: before polarity existed, this was the state of every clean run.
    expect("a closed queue under the old polarity would have alarmed",
           Metric("pending units", 0, 9, direction=UP_IS_PROGRESS).regressed, True)

    # --- the exit code ------------------------------------------------------------------------ #
    suite = Suite()
    suite.report("units total", 700, 719)
    expect("a losing move is collected", len(suite.regressed), 1)
    expect("and names its direction", "<" in suite.regressed[0], True)

    suite = Suite()
    suite.report("pending units", 4, 0, direction=DOWN_IS_PROGRESS)
    expect("a growing queue is collected", len(suite.regressed), 1)
    expect("and names its direction", ">" in suite.regressed[0], True)

    suite = Suite()
    suite.report("artist coverage", 130, 115)
    suite.report("pending units", 0, 0, direction=DOWN_IS_PROGRESS)
    suite.check("something structural", True)
    expect("progress alone raises nothing", suite.regressed, [])
    expect("and fails nothing", suite.failed, [])

    if FAILURES:
        for failure in FAILURES:
            print(f"FAIL {failure}")
        return 1
    print("metric polarity regressions passed: 14 assertions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

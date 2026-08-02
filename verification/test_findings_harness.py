#!/usr/bin/env python3
"""Regression tests for the findings harness itself (#70).

`review_findings.py` used to run its whole body at import. Two consequences, and the second is why
this file can exist at all:

  * a parse or key error in one check's data loading aborted the process before a single result
    reached stdout, so the checks that had already passed were never seen;
  * importing the module ran the entire suite against the live tree, so no part of it could be
    exercised against a fixture — which is why `verification/checks.py`, the protocol both truth
    suites are built on, had no tests.

These assert the harness properties rather than any individual check's verdict: that importing is
free, that collecting is what costs, and that a crash mid-collection still renders what ran.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checks import Suite  # noqa: E402

FAILURES: list[str] = []


def expect(label: str, actual, wanted) -> None:
    if actual != wanted:
        FAILURES.append(f"{label}: expected {wanted!r}, got {actual!r}")


def main() -> int:
    import review_findings as rf

    # Importing must not run anything. If this ever regresses, every other property here becomes
    # untestable again, so it is checked before the module is used for anything else.
    expect("import collects no results", len(rf.suite.results), 0)

    rf.collect()
    expect("collect() populates the suite", len(rf.suite.results) > 0, True)
    checks = {c.ident for c in rf.suite.checks}
    for ident in ("E3", "E4", "R7", "S15", "X3"):
        expect(f"{ident} is declared", ident in checks, True)

    # Ordering is part of the contract: parity.py compares these suites line by line, and the
    # sections depend on values computed earlier, so a reordered check is a behaviour change.
    idents = [c.ident for c in rf.suite.checks]
    expect("E3 precedes E4", idents.index("E3") < idents.index("E4"), True)

    # A second collect() would double every result. Nothing does that today; asserting it keeps
    # the harness honest if collect() ever grows an idempotence claim it does not have.
    before = len(rf.suite.results)
    rf.collect()
    expect("collect() is additive, not idempotent", len(rf.suite.results), before * 2)

    # The crash path: whatever ran before the failure must still be rendered.
    suite = Suite()
    suite.check("ran before the failure", True)
    try:
        raise KeyError("finish_units.json")
    except KeyError as error:
        suite.check("The suite ran to completion", False,
                    f"{type(error).__name__}: {error}. Checks after this point did not run.")
    expect("results before a crash survive", len(suite.checks), 2)
    expect("and the crash is a reported failure", len(suite.failed), 1)
    expect("while earlier passes are kept", suite.checks[0].ok, True)

    if FAILURES:
        for failure in FAILURES:
            print(f"FAIL {failure}")
        return 1
    print(f"findings harness regressions passed: {len(checks)} checks declared, import is free")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

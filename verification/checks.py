#!/usr/bin/env python3
"""The check protocol shared by the verification harnesses (#50, Wave 1).

Two suites assert things about this repository: `review_integrity.py` validates invariants
*within* each store, `review_findings.py` validates consistency *between* the stores and the
artifacts consumers read. They used to be a PowerShell script and a Python script, each with its
own idea of what a check is, so a new rule meant choosing a harness and a reader asking "what is
enforced?" had to read both.

What is shared is the protocol — how a check is declared, how a count is reported, and when the
process exits non-zero. What is not shared is how the lines look: each suite keeps the output its
readers and its regression history already know, so a consolidation cannot quietly change a
verdict. Rendering is therefore a parameter, not a policy.

Counts are reported, never asserted. `review_integrity` established that rule and it is preserved
here deliberately: a gate that reddens when the project makes progress is a gate people learn to
edit rather than read. Only a count moving *backwards* — the direction that signals data loss —
is a finding.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
VERIFICATION = ROOT / "verification"


def read_json(path: Path) -> Any:
    """Read JSON, tolerating a BOM.

    Historical PowerShell 5.1 output carried one. Every active writer now emits UTF-8 without a
    BOM and `review_findings.py` check X5 enforces that, but a reader that only works on files
    written since is a reader that breaks on the archive.
    """
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


@dataclass
class Check:
    """A structural assertion. Failing one fails the run."""

    name: str
    ok: bool
    detail: str = ""
    ident: str = ""


@dataclass
class Note:
    """Something worth printing that no run should ever fail on."""

    ident: str
    name: str
    detail: str = ""


@dataclass
class Metric:
    """A count, reported against a baseline. Only a fall is a finding."""

    name: str
    value: int
    baseline: int
    detail: str = ""

    @property
    def drift(self) -> int:
        return self.value - self.baseline

    @property
    def regressed(self) -> bool:
        return self.drift < 0


@dataclass
class Suite:
    """Collects results in declaration order and decides the exit code.

    Order matters: the suites are compared against their PowerShell predecessors line by line by
    `verification/parity.py`, so a reordered check is a difference like any other.
    """

    results: list[Check | Metric | Note] = field(default_factory=list)

    def check(self, name: str, ok: bool, detail: str = "", ident: str = "") -> None:
        self.results.append(Check(name, bool(ok), detail, ident))

    def report(self, name: str, value: int, baseline: int, detail: str = "") -> None:
        self.results.append(Metric(name, value, baseline, detail))

    def note(self, ident: str, name: str, detail: str = "") -> None:
        self.results.append(Note(ident, name, detail))

    @property
    def checks(self) -> list[Check]:
        return [r for r in self.results if isinstance(r, Check)]

    @property
    def failed(self) -> list[str]:
        return [r.name for r in self.checks if not r.ok]

    @property
    def regressed(self) -> list[str]:
        return [f"{r.name} ({r.value} < {r.baseline})"
                for r in self.results if isinstance(r, Metric) and r.regressed]

    def render(self, line: Callable[[Check | Metric | Note], None]) -> None:
        """Hand each result to the caller's formatter, in declaration order.

        Deliberately not a format. Each suite prints the lines its readers and its regression
        history already know, and consolidating the protocol must not quietly restyle a verdict.
        """
        for result in self.results:
            line(result)

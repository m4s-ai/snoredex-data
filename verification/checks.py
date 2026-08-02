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

Counts are reported, never asserted *by size*. `review_integrity` established that rule and it is
preserved here deliberately: a gate that reddens when the project makes progress is a gate people
learn to edit rather than read. Only a move in the losing direction is a finding, and since #69
each metric declares which direction that is — most count work that exists, where a fall is loss;
queue depths count work left to do, where a rise is. A losing move now fails the run, which it
never did: the banner printed and the process exited 0.
"""

from __future__ import annotations

import json
import os
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


def format_table(rows: list[dict], columns: list[str] | None = None) -> list[str]:
    """Reproduce `Format-Table -Auto`: columns sized to content, underlined, single-space gaps."""
    if not rows:
        return []
    names = columns or list(rows[0])
    widths = {c: max(len(c), max(len(str(row.get(c, ""))) for row in rows)) for c in names}
    lines = [" ".join(c.ljust(widths[c]) for c in names).rstrip(),
             " ".join("-" * widths[c] for c in names).rstrip()]
    lines.extend(" ".join(str(row.get(c, "")).ljust(widths[c]) for c in names).rstrip()
                 for row in rows)
    return lines


def write_json(path: Path, payload: Any) -> None:
    """Write JSON the way `ConvertTo-Json | Set-Content -Encoding utf8NoBOM` did.

    Two spaces, no BOM, non-ASCII left as itself, and a trailing newline. The committed exports
    were produced by that pipeline, so anything else churns them on the next run.

    Written to a temporary file in the same directory and moved into place, so an interrupted run
    leaves either the old file or the complete new one, never a half-written store (#29). The
    replace is atomic on POSIX and on Windows for same-volume moves, which is why the temporary
    file is a sibling rather than somewhere under /tmp.
    """
    body = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(body, encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


# --- verification status model ------------------------------------------------------------- #
# The statuses a language unit may hold, and the moves between them that a writer may make. This
# lived as a bare tuple in review_integrity.py: enough to reject an unknown value after the fact,
# not enough to stop a pass making a move nobody intended (#29).
#
# The rule the transitions encode is that resolving is deliberate and un-resolving is not
# automatic. A pass may resolve an open unit or hand it to a human; it may correct one verdict to
# the other, because evidence does get overturned. What it may not do is push a unit that someone
# already resolved back into the open pool, which is how a generic lookup pass silently undid
# earlier work.

STATUSES = ("confirmed", "contradicted", "needs-manual-review", "pending")
RESOLVED_STATUSES = ("confirmed", "contradicted")

ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("confirmed", "contradicted", "needs-manual-review", "pending"),
    "needs-manual-review": ("confirmed", "contradicted", "needs-manual-review"),
    "confirmed": ("confirmed", "contradicted"),
    "contradicted": ("contradicted", "confirmed"),
}


class TransitionError(ValueError):
    """A writer attempted a status move the model does not allow."""


def transition(unit: dict, new_status: str) -> dict:
    """Move `unit` to `new_status`, refusing anything the model does not permit.

    Raises rather than returning a flag: a rejected transition means the caller's logic is wrong
    about what it is looking at, and continuing would write that misunderstanding to the store.
    """
    current = unit.get("status")
    if new_status not in STATUSES:
        raise TransitionError(
            f"{unit.get('unitId')}: {new_status!r} is not a verification status "
            f"(known: {', '.join(STATUSES)})")
    if current not in ALLOWED_TRANSITIONS:
        raise TransitionError(f"{unit.get('unitId')}: current status {current!r} is not a "
                              f"verification status")
    if new_status not in ALLOWED_TRANSITIONS[current]:
        raise TransitionError(
            f"{unit.get('unitId')}: {current} -> {new_status} is not an allowed transition "
            f"(from {current}: {', '.join(ALLOWED_TRANSITIONS[current])})")
    unit["status"] = new_status
    return unit


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


# Which way a metric is allowed to move. Most counts here measure work that exists — units,
# confirmed artists, finish rows — and a fall means something was lost. Queue depths measure work
# left to do, and a fall is the entire point of the project (#69).
#
# Getting this wrong is not cosmetic. Closing the language review queue drove `pending units` to 0
# and the suite began printing "!!! COUNTS WENT BACKWARDS" on every clean run, permanently, for the
# best possible reason. That is precisely the failure this module's docstring warns about: a gate
# that reddens on progress is a gate people learn to edit rather than read.
UP_IS_PROGRESS = "up-is-progress"
DOWN_IS_PROGRESS = "down-is-progress"


@dataclass
class Metric:
    """A count, reported against a baseline. Only a move in the losing direction is a finding."""

    name: str
    value: int
    baseline: int
    detail: str = ""
    direction: str = UP_IS_PROGRESS

    @property
    def drift(self) -> int:
        return self.value - self.baseline

    @property
    def regressed(self) -> bool:
        if self.direction == DOWN_IS_PROGRESS:
            return self.drift > 0
        return self.drift < 0

    @property
    def improved(self) -> bool:
        return self.drift != 0 and not self.regressed


@dataclass
class Suite:
    """Collects results in declaration order and decides the exit code.

    Order matters: the suites are compared against their PowerShell predecessors line by line by
    `verification/parity.py`, so a reordered check is a difference like any other.
    """

    results: list[Check | Metric | Note] = field(default_factory=list)

    def check(self, name: str, ok: bool, detail: str = "", ident: str = "") -> None:
        self.results.append(Check(name, bool(ok), detail, ident))

    def report(self, name: str, value: int, baseline: int, detail: str = "",
               direction: str = UP_IS_PROGRESS) -> None:
        self.results.append(Metric(name, value, baseline, detail, direction))

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
        return [f"{r.name} ({r.value} {'>' if r.direction == DOWN_IS_PROGRESS else '<'} "
                f"{r.baseline})"
                for r in self.results if isinstance(r, Metric) and r.regressed]

    def render(self, line: Callable[[Check | Metric | Note], None]) -> None:
        """Hand each result to the caller's formatter, in declaration order.

        Deliberately not a format. Each suite prints the lines its readers and its regression
        history already know, and consolidating the protocol must not quietly restyle a verdict.
        """
        for result in self.results:
            line(result)

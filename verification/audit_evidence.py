#!/usr/bin/env python3
"""Every resolved unit must carry a real evidence string (#50, Wave 1).

Ported from `audit_evidence.ps1`, which existed because of a case-insensitivity bug: PowerShell
treats `$EV` and `$ev` as the same variable, so a pass once wrote the wrong value into `evidence`
and two units carried something that was not a usable string at all. Statuses said "confirmed"
while the evidence behind them was gone. This audits for that shape rather than for that bug.

    python verification/audit_evidence.py

Run it after every write pass. Exit code is 0 whether or not anything is found — the audit
reports, and `review_integrity.py` is what fails the gate on the same condition.
"""

from __future__ import annotations

import json
import sys

from checks import VERIFICATION, read_json

RESOLVED = ("confirmed", "contradicted")
# PowerShell reported .NET type names, and the audit output is read against that history.
TYPE_NAMES = {type(None): "null", str: "String", bool: "Boolean", int: "Int64",
              float: "Double", list: "Object[]", dict: "PSCustomObject"}


def type_name(value: object) -> str:
    return TYPE_NAMES.get(type(value), type(value).__name__)


def format_table(rows: list[dict]) -> list[str]:
    """Reproduce `Format-Table -Auto`: columns sized to content, underlined, single-space gaps."""
    columns = list(rows[0])
    widths = {c: max(len(c), max(len(str(row[c])) for row in rows)) for c in columns}
    lines = [" ".join(c.ljust(widths[c]) for c in columns).rstrip(),
             " ".join("-" * widths[c] for c in columns).rstrip()]
    lines.extend(" ".join(str(row[c]).ljust(widths[c]) for c in columns).rstrip() for row in rows)
    return lines


def main() -> int:
    units = read_json(VERIFICATION / "units.json")

    bad = []
    for unit in units:
        if unit.get("status") not in RESOLVED:
            continue
        evidence = unit.get("evidence")
        is_string = isinstance(evidence, str)
        length = len(evidence) if is_string else -1
        if not is_string or length < 20:
            bad.append({
                "unitId": unit.get("unitId"),
                "set": f"{unit.get('setCode')} {unit.get('number')}",
                "lang": unit.get("language"),
                "status": unit.get("status"),
                "type": type_name(evidence),
                "len": length,
                "sourceUrl": unit.get("sourceUrl"),
            })

    resolved = sum(1 for unit in units if unit.get("status") in RESOLVED)
    print(f"resolved units: {resolved}")
    print(f"units with unusable evidence: {len(bad)}")
    if bad:
        print()
        for line in format_table(bad):
            print(line)
        print()

    # Two PowerShell behaviours the readers of this file depend on, both measured rather than
    # assumed: an empty result writes no file at all, because `Set-Content` with nothing on the
    # pipeline never opens one; and a single result serialises as a bare object rather than a
    # one-element array, because `ConvertTo-Json` unwraps it.
    if bad:
        payload = bad[0] if len(bad) == 1 else bad
        destination = VERIFICATION / "_evidence_audit.json"
        destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

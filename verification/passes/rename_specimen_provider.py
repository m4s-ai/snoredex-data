#!/usr/bin/env python3
"""Name the specimen evidence class for the act that is on the record.

`photographed-specimen` is the registry's tier 1, above the official Pokémon databases. No
photograph is committed for any of the six specimens, and `verification/specimens/` does not exist:
checks `S9`/`S10`, the publish allowlist and `LICENSE.md` decision 4 all guard an empty directory.

The evidence is real — each record writes out the card text, ability names, Pokédex line, set code
and copyright year, so a third party can re-check it against a card in hand. What was wrong was the
label, which promised a file a reader could open. That is the same over-claim as #64, where
`providerId` named the strongest thing nearby rather than the thing the claim rests on.

So the class becomes `inspected-specimen` and keeps tier 1. The owner confirmed on 2026-08-03 that
photographs are not coming soon; rename it back when images land, at which point the promise
becomes true.

Provenance only: no verdict, evidence text, `sourceRef` or `checkedAt` moves. Idempotent.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNITS = ROOT / "verification" / "units.json"

OLD, NEW = "photographed-specimen", "inspected-specimen"


def main() -> None:
    units = json.loads(UNITS.read_text(encoding="utf-8-sig"))
    renamed = 0
    for unit in units:
        if unit.get("providerId") == OLD:
            # Every one of these cites a specimen; S14 guarantees it and would fail otherwise.
            if not str(unit.get("sourceRef") or "").startswith("specimen:"):
                raise SystemExit(
                    f"{unit['unitId']} claims specimen authority with no specimen reference; "
                    "run review_findings.py before renaming the class")
            unit["providerId"] = NEW
            renamed += 1
    if renamed:
        UNITS.write_text(json.dumps(units, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Renamed {renamed} unit(s) from {OLD} to {NEW}")


if __name__ == "__main__":
    main()

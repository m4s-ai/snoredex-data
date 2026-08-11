#!/usr/bin/env python3
"""Raise Italian RR 111 from set-level context to the publisher's card page (#137, #139).

`U0368` was confirmed from a cross-language expansion index: Rising Rivals had an Italian
release. That observation does not by itself reach secret-numbered `RR 111`, so the evidence
semantics report kept the row in the migration queue.

The Pokémon Company's Italian locale archive has an exact page for the card. It names Snorlax,
the Italian set `Platino - L'Ascesa dei Rivali`, the local card type `Pokémon LIV.X`, and serves
the Italian CMS image `PL2_IT_111.png`. This is card-level, locale-specific, tier-1 evidence.

The old observation remains in the append-only evidence journal. This pass appends the new
observation once and changes only which source carries the current confirmation. It asserts no
finish and treats every missing archive row as unknown.

    python verification/passes/official_italian_archive_20260811.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UNITS = ROOT / "verification" / "units.json"
JOURNAL = ROOT / "verification" / "evidence.jsonl"

UNIT_ID = "U0368"
SOURCE_URL = "https://www.pokemon.com/it/gcc/archivio-carte/series/pl2/111/"
SOURCE_TYPE = "The Pokémon Company official Italian locale card archive, card page"
EVIDENCE = (
    "The Pokémon Company's Italian locale card archive serves this exact card as Snorlax in "
    "Platino - L'Ascesa dei Rivali, identifies it as Pokémon LIV.X, and uses the Italian CMS "
    "image PL2_IT_111.png. This card-level page replaces the previous set-level inference that "
    "an Italian release of Rising Rivals must contain a secret-numbered card. The earlier "
    "cross-language-index observation remains in evidence.jsonl as history. No finish or archive "
    "absence is inferred. Retrieved 2026-08-11."
)


def main() -> int:
    units = json.loads(UNITS.read_text(encoding="utf-8"))
    by_id = {unit["unitId"]: unit for unit in units}
    unit = by_id.get(UNIT_ID)
    if unit is None:
        print(f"missing {UNIT_ID}", file=sys.stderr)
        return 1

    actual = (unit["setCode"], str(unit["number"]), unit.get("variant") or "base",
              unit["language"], unit["status"])
    expected = ("RR", "111", "base", "Italian", "confirmed")
    if actual != expected:
        print(f"{UNIT_ID} is {actual}, expected {expected}", file=sys.stderr)
        return 1

    changed = unit.get("sourceUrl") != SOURCE_URL
    unit["sourceUrl"] = SOURCE_URL
    unit["sourceType"] = SOURCE_TYPE
    unit["providerId"] = "pokemon-official"
    unit["evidence"] = EVIDENCE
    unit["checkedAt"] = "2026-08-11T08:38:14Z"
    UNITS.write_text(json.dumps(units, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    rows = [json.loads(line) for line in JOURNAL.read_text(encoding="utf-8").splitlines() if line]
    if not any(row.get("unitId") == UNIT_ID and row.get("source") == SOURCE_URL for row in rows):
        observation = {
            "unitId": UNIT_ID,
            "lang": "Italian",
            "status": "confirmed",
            "source": SOURCE_URL,
            "evidence": EVIDENCE,
            "at": "2026-08-11T08:38:14Z",
        }
        with JOURNAL.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(observation, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(f"{'raised' if changed else 'kept'} {UNIT_ID} on the official Italian card page")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Ground three English Prize Pack confirmations on their retained official card lists (#137).

The language rows previously rested on an owner claim plus sibling languages. The finish store
already retained stronger positive evidence: the official Series Seven and Series Eight checklists
name Hop's Snorlax and identify the standard/foil variants in English. Reuse those exact records as
the current language evidence. The former observations stay in the append-only journal.

No unlisted language or finish is inferred from either checklist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UNITS = ROOT / "verification" / "units.json"
JOURNAL = ROOT / "verification" / "evidence.jsonl"
CHECKED_AT = "2026-08-11T16:00:00Z"

SERIES_7 = (
    "https://d1wx537rtdixyy.cloudfront.net/expansions/series7/en-us/"
    "P11076_USOP_OP_Prize_Packs_Series7_Card_List_EN.pdf"
)
SERIES_8 = (
    "https://d1wx537rtdixyy.cloudfront.net/expansions/series8/en-us/"
    "OP_Prize_Packs_Series8_Card_List_EN.pdf"
)

RECORDS = {
    "U0324": {
        "identity": ("PPS7 JTG", "JTG 117", "base", "English", "confirmed"),
        "url": SERIES_7,
        "sourceType": "The Pokémon Company official Prize Pack Series Seven card list",
        "evidence": (
            "The retained official English Series Seven checklist names Hop's Snorlax 117/159 "
            "and marks its Standard Set printing. This is an exact English card-list row, so it "
            "replaces the earlier sibling-language inference for this unit. It establishes no "
            "unlisted language and remains separately retained as finish evidence."
        ),
    },
    "U0214": {
        "identity": ("PPS8 JTG", "JTG 117", "V1", "English", "confirmed"),
        "url": SERIES_8,
        "sourceType": "The Pokémon Company official Prize Pack Series Eight card list",
        "evidence": (
            "The retained official English Series Eight checklist names Hop's Snorlax 117/159 "
            "and marks its Standard Set printing. This exact English card-list row establishes "
            "the non-holo product rather than borrowing another language's evidence. It "
            "establishes no unlisted language."
        ),
    },
    "U0187": {
        "identity": ("PPS8 JTG", "JTG 117", "V2", "English", "confirmed"),
        "url": SERIES_8,
        "sourceType": "The Pokémon Company official Prize Pack Series Eight card list",
        "evidence": (
            "The retained official English Series Eight checklist names Hop's Snorlax 117/159 "
            "and marks its Standard Set Foil printing. This exact English card-list row "
            "establishes the holo product rather than borrowing another language's evidence. It "
            "establishes no unlisted language."
        ),
    },
}


def main() -> int:
    units = json.loads(UNITS.read_text(encoding="utf-8"))
    by_id = {unit["unitId"]: unit for unit in units}
    journal = [
        json.loads(line) for line in JOURNAL.read_text(encoding="utf-8").splitlines() if line
    ]
    changed = 0
    additions = []
    for unit_id, record in RECORDS.items():
        unit = by_id.get(unit_id)
        if unit is None:
            print(f"missing {unit_id}", file=sys.stderr)
            return 1
        actual = (
            unit["setCode"], str(unit["number"]), unit.get("variant") or "base",
            unit["language"], unit["status"],
        )
        if actual != record["identity"]:
            print(f"{unit_id} is {actual}, expected {record['identity']}", file=sys.stderr)
            return 1
        if unit.get("sourceUrl") != record["url"] or unit.get("evidence") != record["evidence"]:
            unit["sourceUrl"] = record["url"]
            unit["sourceType"] = record["sourceType"]
            unit["providerId"] = "pokemon-official"
            unit["sourceRef"] = None
            unit["corroborated"] = False
            unit["evidence"] = record["evidence"]
            unit["checkedAt"] = CHECKED_AT
            changed += 1
        if not any(
            row.get("unitId") == unit_id and row.get("source") == record["url"]
            for row in journal
        ):
            additions.append({
                "unitId": unit_id,
                "lang": "English",
                "status": "confirmed",
                "source": record["url"],
                "evidence": record["evidence"],
                "at": CHECKED_AT,
            })

    UNITS.write_text(json.dumps(units, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if additions:
        with JOURNAL.open("a", encoding="utf-8", newline="\n") as handle:
            for row in additions:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"grounded {changed} Prize Pack confirmation(s); appended {len(additions)} observation(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

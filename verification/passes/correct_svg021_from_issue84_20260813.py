#!/usr/bin/env python3
"""Correct U0467 from the exact positive 52poke record retained in issue #84.

The 2026-08-03 owner decision in #93 accepted a Bulbapedia product article that listed
Japanese and Korean releases but no Traditional-Chinese edition. Issue #84 later retained a
positive 52poke T-Chinese row for the same local product and card: ``SVG 021/049``. Positive
card-level evidence supersedes the older absence reasoning.

This pass updates the raw verdict, removes the now-inapplicable active absence adjudication, and
appends the correction to the evidence journal. Git history and #93 retain the earlier decision.
It is idempotent.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "verification"
UNIT_ID = "U0467"
DATE = "2026-08-13"
SOURCE = (
    "https://wiki.52poke.com/wiki/"
    "%E5%8D%A1%E6%AF%94%E5%85%BD%EF%BC%88S10a%EF%BC%89"
)
RECORD_ID = "S10a|SVG|021/049"
EVIDENCE = (
    "The retained issue #84 52poke scan positively lists a Traditional-Chinese Snorlax row "
    "with local set code SVG and collector number 021/049. The legacy unit is svG 021 in the "
    "same 49-card Venusaur & Charizard & Blastoise Special Deck Set ex; set-code case and the "
    "omitted denominator are provider notation differences, while the product and exact card "
    "slot agree. This card-level positive record overturns the older contradiction based on a "
    "Bulbapedia release list that omitted the Traditional-Chinese edition. The 52poke slice is "
    "positive-only and makes no claim about neighbouring cards or catalogue completeness."
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    scan = read(VERIFY / "evidence" / "issue-84-snorlax-alle-zh.json")
    matches = [
        row for row in scan["S10a"]["tchn"]
        if "|".join(("S10a", row.get("setcode", ""), row.get("num", ""))) == RECORD_ID
    ]
    if len(matches) != 1 or scan["S10a"].get("url") != SOURCE:
        raise SystemExit("retained 52poke SVG 021/049 evidence differs from the reviewed record")

    units_path = VERIFY / "units.json"
    units = read(units_path)
    unit = next((row for row in units if row["unitId"] == UNIT_ID), None)
    if unit is None:
        raise SystemExit(f"unknown unit {UNIT_ID}")
    if unit["status"] not in {"contradicted", "confirmed"}:
        raise SystemExit(f"{UNIT_ID} has unexpected status {unit['status']}")

    correction = {
        "status": "confirmed",
        "sourceUrl": SOURCE,
        "sourceType": "52poke localized card list (retained issue #84 scan)",
        "evidence": EVIDENCE,
        "checkedAt": f"{DATE}T00:00:00",
        "providerId": "52poke",
        "corroborated": False,
        "sourceRef": None,
    }
    changed = any(unit.get(key) != value for key, value in correction.items())
    unit.update(correction)
    if changed:
        write(units_path, units)

    adjudications_path = VERIFY / "owner_adjudications.json"
    adjudications = read(adjudications_path)
    before = len(adjudications["decisions"])
    adjudications["decisions"] = [
        row for row in adjudications["decisions"] if row["unitId"] != UNIT_ID
    ]
    removed = before - len(adjudications["decisions"])
    if removed > 1:
        raise SystemExit(f"more than one active adjudication targeted {UNIT_ID}")
    if removed:
        adjudications["meta"]["generated"] = DATE
        write(adjudications_path, adjudications)

    journal_path = VERIFY / "evidence.jsonl"
    journal_lines = journal_path.read_text(encoding="utf-8-sig").splitlines()
    already_recorded = any(
        (entry := json.loads(line)).get("unitId") == UNIT_ID
        and entry.get("status") == "confirmed"
        and entry.get("source") == SOURCE
        for line in journal_lines if line.strip()
    )
    if not already_recorded:
        entry = {
            "unitId": UNIT_ID,
            "lang": "T-Chinese",
            "status": "confirmed",
            "source": SOURCE,
            "evidence": EVIDENCE,
            "at": f"{DATE}T00:00:00",
        }
        with journal_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")

    dataset_path = ROOT / "snorlax_cards.json"
    dataset = read(dataset_path)
    tally = {
        "confirmed": sum(row["status"] == "confirmed" for row in units),
        "contradicted": sum(row["status"] == "contradicted" for row in units),
        "needsManualReview": sum(row["status"] == "needs-manual-review" for row in units),
        "open": sum(row["status"] == "pending" for row in units),
        "totalUnits": len(units),
        "lastUpdated": DATE,
    }
    if any(dataset["meta"]["verification"].get(key) != value for key, value in tally.items()):
        dataset["meta"]["verification"].update(tally)
        write(dataset_path, dataset)

    print(
        f"{UNIT_ID}: confirmed from retained 52poke {RECORD_ID}; "
        f"removed {removed} active absence adjudication(s)"
    )


if __name__ == "__main__":
    main()

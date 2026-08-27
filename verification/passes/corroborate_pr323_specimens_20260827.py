#!/usr/bin/env python3
"""Apply PR #323's retained card images as corroboration of existing language claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UNITS = ROOT / "verification" / "units.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
JOURNAL = ROOT / "verification" / "evidence.jsonl"
CHECKED_AT = "2026-08-27T18:18:22Z"

TARGETS = {
    "U0094": ["SPEC-0120"],
    "U0295": ["SPEC-0121", "SPEC-0122"],
    "U0244": ["SPEC-0123", "SPEC-0124"],
    "U0417": ["SPEC-0125"],
    "U0434": ["SPEC-0126", "SPEC-0127"],
    "U0228": ["SPEC-0128"],
    "U0122": ["SPEC-0129", "SPEC-0130", "SPEC-0133"],
    "U0245": ["SPEC-0131"],
    "U0482": ["SPEC-0132"],
    "U0092": ["SPEC-0134"],
    "U0229": ["SPEC-0135"],
    "U0418": ["SPEC-0136"],
    "U0416": ["SPEC-0137", "SPEC-0138", "SPEC-0139", "SPEC-0143"],
    "U0527": ["SPEC-0140", "SPEC-0141", "SPEC-0142"],
    "U0452": ["SPEC-0144"],
    "U0294": ["SPEC-0145"],
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def key_value(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    units = read_json(UNITS)
    specimen_rows = read_json(SPECIMENS)["specimens"]
    by_unit = {row["unitId"]: row for row in units}
    by_specimen = {row["specimenId"]: row for row in specimen_rows}
    journal = [json.loads(line) for line in JOURNAL.read_text(encoding="utf-8").splitlines() if line]
    journal_keys = {
        (row.get("unitId"), key_value(row.get("source")), key_value(row.get("evidence")))
        for row in journal
    }
    additions = []
    changed = 0

    for unit_id, specimen_ids in TARGETS.items():
        unit = by_unit.get(unit_id)
        if not unit or unit.get("status") != "confirmed":
            raise SystemExit(f"{unit_id} is not an existing confirmed unit")
        for specimen_id in specimen_ids:
            specimen = by_specimen.get(specimen_id)
            if not specimen or unit_id not in specimen.get("citedBy", []):
                raise SystemExit(f"{specimen_id} does not cite {unit_id}")
            if (
                specimen["setCode"], specimen["number"].split("/", 1)[0],
                specimen["variant"], specimen["language"],
            ) != (
                unit["setCode"], str(unit["number"]), unit.get("variant") or "base",
                unit["language"],
            ):
                raise SystemExit(f"{specimen_id} does not identify {unit_id}")

        refs = ", ".join(specimen_ids)
        sentence = (
            f"Independent positive card-image evidence retained as {refs} shows the same "
            "localized card identity and corroborates this unit without replacing its primary provider."
        )
        desired_evidence = unit["evidence"]
        if sentence not in desired_evidence:
            desired_evidence = f"{desired_evidence.rstrip()} {sentence}"
        if not unit.get("corroborated") or unit["evidence"] != desired_evidence:
            unit["corroborated"] = True
            unit["evidence"] = desired_evidence
            unit["checkedAt"] = CHECKED_AT
            changed += 1

        journal_row = {
            "unitId": unit_id,
            "status": "confirmed",
            "source": f"specimen:{specimen_ids[0]}",
            "evidence": sentence,
            "at": CHECKED_AT,
        }
        key = (journal_row["unitId"], journal_row["source"], journal_row["evidence"])
        if key not in journal_keys:
            additions.append(journal_row)
            journal_keys.add(key)

    if args.check:
        if changed or additions:
            print(f"specimen corroboration is stale: units={changed}, journal={len(additions)}")
            return 1
        print(f"specimen corroboration current ({len(TARGETS)} units)")
        return 0

    UNITS.write_text(json.dumps(units, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if additions:
        with JOURNAL.open("a", encoding="utf-8", newline="\n") as handle:
            for row in additions:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"corroborated {changed} unit(s); appended {len(additions)} journal observation(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Apply PR #328's retained seller photographs as claim corroboration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UNITS = ROOT / "verification" / "units.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
JOURNAL = ROOT / "verification" / "evidence.jsonl"
OBSERVED_AT = "2026-08-28"

TARGETS = {
    "U0246": "SPEC-0409",
    "U0561": "SPEC-0411",
    "U0785": "SPEC-0410",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    units = read_json(UNITS)
    specimens = read_json(SPECIMENS)["specimens"]
    by_unit = {row["unitId"]: row for row in units}
    by_specimen = {row["specimenId"]: row for row in specimens}
    journal = [json.loads(line) for line in JOURNAL.read_text(encoding="utf-8").splitlines() if line]
    journal_keys = {(row.get("unitId"), row.get("source")) for row in journal}
    additions = []
    changed = 0

    for unit_id, specimen_id in TARGETS.items():
        unit = by_unit.get(unit_id)
        specimen = by_specimen.get(specimen_id)
        if not unit or unit.get("status") != "confirmed":
            raise SystemExit(f"{unit_id} is not an existing confirmed unit")
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

        sentence = (
            f"Independent positive seller-photo evidence retained as {specimen_id} shows the "
            "same localized card identity and corroborates this unit without replacing its "
            "primary provider."
        )
        evidence = unit["evidence"]
        if sentence not in evidence:
            evidence = f"{evidence.rstrip()} {sentence}"
        if not unit.get("corroborated") or unit["evidence"] != evidence:
            unit["corroborated"] = True
            unit["evidence"] = evidence
            changed += 1

        journal_row = {
            "unitId": unit_id,
            "status": "confirmed",
            "source": f"specimen:{specimen_id}",
            "evidence": sentence,
            "at": OBSERVED_AT,
        }
        key = (unit_id, journal_row["source"])
        if key not in journal_keys:
            additions.append(journal_row)
            journal_keys.add(key)

    if args.check:
        if changed or additions:
            print(f"Cardmarket specimen corroboration is stale: units={changed}, journal={len(additions)}")
            return 1
        print(f"Cardmarket specimen corroboration current ({len(TARGETS)} units)")
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

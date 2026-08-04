#!/usr/bin/env python3
"""Record the owner's blanket decision on the remaining `KSS 26` languages (#86).

The owner settled Japanese and Korean on 2026-08-03 by naming the products those printings actually
are — `HXY` and `FXY` — and then, on 2026-08-04, closed the rest in one line:

    "All other languages were not printed."

That covers the eight still disputed. They are recorded separately from U0485/U0488 because the
*reason* differs and the record should say which one applies. Japanese and Korean exist under
another set code; these eight do not exist at all, which is what the Bulbapedia article's closed
list of seven print languages says.

Idempotent: re-running adds nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "verification"
DECIDED_AT = "2026-08-04"
ISSUE = "https://github.com/m4s-ai/snoredex-data/issues/86"

UNIT_IDS = ["U0484", "U0489", "U0490", "U0491", "U0492", "U0493", "U0494", "U0495"]

RATIONALE = (
    "The collection owner closed the remaining Kalos Starter Set languages in one line: \"All "
    "other languages were not printed.\" This is the second half of the #86 decision and carries a "
    "different reason from the first: U0485 (Japanese) and U0488 (Korean) exist as their own "
    "products under the HXY and FXY codes, whereas these eight were not printed at all. That "
    "matches Bulbapedia's article, which states the print languages as a closed list of seven — "
    "English, German, French, Italian, Spanish, Portuguese and Russian — all seven of which are "
    "confirmed here. Czech, Hungarian and Polish are additionally implausible on market grounds: "
    "no documented Pokemon TCG expansion exists in Czech or Hungarian, and the Polish run covers "
    "only Diamond & Pearl and Mysterious Treasures."
)

EVIDENCE_REFS = [ISSUE, "https://bulbapedia.bulbagarden.net/wiki/Kalos_Starter_Set_(TCG)"]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    units = {u["unitId"]: u for u in read(VERIFICATION / "units.json")}
    adj_path = VERIFICATION / "owner_adjudications.json"
    document = read(adj_path)
    known = {d["unitId"] for d in document["decisions"]}

    added = 0
    for unit_id in UNIT_IDS:
        unit = units.get(unit_id)
        if unit is None:
            raise SystemExit(f"unknown unit {unit_id}")
        if unit["status"] != "contradicted":
            raise SystemExit(
                f"{unit_id} is {unit['status']}, not contradicted; an adjudication may only settle "
                "a contradiction")
        if (unit["setCode"], str(unit["number"])) != ("KSS", "26"):
            raise SystemExit(f"{unit_id} is {unit['setCode']} {unit['number']}, not KSS 26")
        if unit_id in known:
            continue
        document["decisions"].append({
            "adjudicationId": f"OA-{DECIDED_AT.replace('-', '')}-{unit_id}",
            "unitId": unit_id,
            "decision": "not-printed",
            "authority": "collection-owner",
            "basis": "multi-source-adjudication",
            "decidedAt": DECIDED_AT,
            "rationale": RATIONALE,
            "evidenceRefs": [*EVIDENCE_REFS, f"unit:{unit_id}"],
        })
        known.add(unit_id)
        added += 1

    if added:
        document["decisions"].sort(key=lambda d: d["unitId"])
        document["meta"]["generated"] = DECIDED_AT
        adj_path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Recorded {added} owner adjudication(s); {len(document['decisions'])} decisions total. "
          f"KSS 26 is now fully settled.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Record the collection owner's Korean adjudication for issue #88 (2026-08-11).

The owner ruled that the DP1 Snorlax Lv.35 (U0477) exists in Korean but not as the
DP1 product — the Korean Series 2 print is Burning Confrontation 30/40, which the
owner confirmed by eye with a photograph (issue #88 comment, 2026-08-11). The other
five Korean rows exist in no Korean set at all ("all other cards in this did not
exist in a 1 to 1 copy in korean").

This is the same shape as the #86 KSS26 / #87 s1H decisions: Cardmarket claims the
language against *this* product, and against that product the claim is wrong. U0477
is not a specimen — the image lives under github user-attachments, which this
environment cannot retrieve, so the claim rests on the owner's attestation only
(mirroring the OVERTURN note for #85).

Idempotent: re-running adds nothing and re-decides nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "verification"
DECIDED_AT = "2026-08-11"
ISSUE = "https://github.com/m4s-ai/snoredex-data/issues/88"

# unitIds -> rationale. One entry per decision the owner actually made.
NOT_PRINTED: list[tuple[list[str], str]] = [
    (["U0477"],
     "The Korean DP1 Snorlax Lv.35 printing exists, but not as the DP1 product: the "
     "Korean Series 2 print is Burning Confrontation 30/40 ('Snorlax lv. 35 was part "
     "of korean series 2 the burning confrontation according to bulbapedia'). The "
     "owner confirmed the Korean variant by eye with a photograph supplied in the "
     "issue thread, filed here as SPEC-0037 (verification/specimens/SPEC-0037.png); "
     "the image is low-resolution, so the identity rests on the owner's "
     "identification plus the Burning Confrontation set/number context. Cardmarket "
     "claims Korean against DP1, and against that product the claim is wrong."),
    (["U0381", "U0428", "U0545", "U0606", "U0644"],
     "The collection owner ruled these Korean rows were not printed in any Korean "
     "set: 'All other cards in this did not exist in a 1 to 1 copy in korean' and "
     "'Keine Hinweise darauf das diese Sets auf koreanisch existieren, der "
     "zeitstrang auf allen Seiten deutet darauf hin das es zu der Zeit keine "
     "koreanischen Sets gab.' The era argument (pre-DP Korean market: only Base Set "
     "2000 + ADV expansion/starter 2004) is the owner's call and settles the "
     "absence; none of these sets had a Korean printing."),
]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    units_path = VERIFICATION / "units.json"
    units = read(units_path)
    by_id = {u["unitId"]: u for u in units}

    adj_path = VERIFICATION / "owner_adjudications.json"
    document = read(adj_path)
    known = set()
    for d in document["decisions"]:
        if "unitId" in d:
            known.add(d["unitId"])
        if "unitIds" in d:
            known.update(d["unitIds"])

    added = 0
    for unit_ids, rationale in NOT_PRINTED:
        for unit_id in unit_ids:
            unit = by_id.get(unit_id)
            if unit is None:
                raise SystemExit(f"unknown unit {unit_id}")
            if unit["status"] != "contradicted":
                raise SystemExit(
                    f"{unit_id} is {unit['status']}, not contradicted; an adjudication "
                    "may only settle a contradiction")
            if unit_id in known:
                continue
            document["decisions"].append({
                "adjudicationId": f"OA-{DECIDED_AT.replace('-', '')}-{unit_id}",
                "unitId": unit_id,
                "decision": "not-printed",
                "authority": "collection-owner",
                "basis": "multi-source-adjudication",
                "decidedAt": DECIDED_AT,
                "rationale": rationale,
                "evidenceRefs": [ISSUE, f"unit:{unit_id}"],
            })
            known.add(unit_id)
            added += 1

    if added:
        document["decisions"].sort(key=lambda d: d["unitId"])
        document["meta"]["generated"] = DECIDED_AT
        write(adj_path, document)

    print(f"Recorded {added} owner adjudication(s) for #88; "
          f"{len(document['decisions'])} decisions total.")


if __name__ == "__main__":
    main()

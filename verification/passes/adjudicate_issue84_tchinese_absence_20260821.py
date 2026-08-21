#!/usr/bin/env python3
"""Record the owner's explicit Traditional-Chinese absence decisions for issue #84.

The owner has now answered these seventeen legacy Cardmarket product questions directly: none
has a Traditional-Chinese printing.  This is an application decision, not a conclusion drawn
from a source's silence.  The raw ``contradicted`` rows remain unchanged in ``units.json``;
the separate owner-adjudication store projects them as ``not-printed``.

The known catch-up/local counterparts are deliberately not included here.  In particular,
U0265, U0414, U0558 and U0634 have positive local identities; U0584 is explicitly included
below as an owner absence decision, not as a search-absence inference.

Idempotent: re-running adds no duplicate decisions.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "verification"
DECIDED_AT = "2026-08-21"
ISSUE_COMMENT = (
    "https://github.com/m4s-ai/snoredex-data/issues/84#issuecomment-5367191536"
)
U0584_COMMENT = (
    "https://github.com/m4s-ai/snoredex-data/issues/84#issuecomment-5368263159"
)

UNIT_IDS = [
    "U0382", "U0429", "U0478", "U0542", "U0546", "U0577", "U0562",
    "U0580", "U0587", "U0607", "U0624", "U0638", "U0645", "U0662",
    "U0665", "U0681", "U0584",
]

RATIONALE = (
    "The collection owner explicitly ruled in issue #84 that this legacy Cardmarket product "
    "slot has no Traditional-Chinese printing. This is an owner application decision for the "
    "legacy identity, not an absence inference from a blank search result; any separate local "
    "catch-up or promo identity would require its own positive record and is not asserted here."
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    units = read(VERIFICATION / "units.json")
    by_id = {unit["unitId"]: unit for unit in units}
    document_path = VERIFICATION / "owner_adjudications.json"
    document = read(document_path)
    known = {decision["unitId"] for decision in document.get("decisions", [])}

    for unit_id in UNIT_IDS:
        unit = by_id.get(unit_id)
        if unit is None:
            raise SystemExit(f"unknown unit {unit_id}")
        if unit["language"] != "T-Chinese":
            raise SystemExit(f"{unit_id} is not Traditional Chinese")
        if unit["status"] != "contradicted":
            raise SystemExit(
                f"{unit_id} is {unit['status']}, not contradicted; refusing to settle it"
            )
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
            "evidenceRefs": [U0584_COMMENT if unit_id == "U0584" else ISSUE_COMMENT, f"unit:{unit_id}"],
        })
        known.add(unit_id)

    document["decisions"].sort(key=lambda decision: decision["unitId"])
    document.setdefault("meta", {})["generated"] = DECIDED_AT
    write(document_path, document)
    print(
        f"Recorded issue #84 owner adjudications for {len(UNIT_IDS)} units; "
        f"{len(document['decisions'])} decisions total."
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Owner adjudication: `svLN 010` Traditional Chinese is not printed.

THE DECISION

U0678 was corrected from `confirmed` to `contradicted` in the preceding pass, which says only that
an outside source disagrees with Cardmarket. Rule 4 allows exactly two things to settle an absence,
and one of them is an explicit collection-owner adjudication after reviewing the cited claims. The
owner gave one on 2026-08-08:

    svLN 010 and mP1 012 are the same card from two different Japanese prints, visible from the set
    code and numbering; in Traditional Chinese this card exists so far only once, as a promo.

So the application may state that no Traditional Chinese edition of this Japanese starter set was
released. It says nothing about the promo: SV-P 215 exists, is Traditional Chinese, and is simply a
different product — one Cardmarket does not list, so it is not in this catalogue.

WHY THIS UNIT AND NOT ITS SIBLING

`mP1 012` T-Chinese (U0674) already carries an adjudication from the 2026-08-03 batch. This pass
brings the second half of the pair to the same footing; the two were refuted on identical grounds
and it would be arbitrary for one to read `not-printed` and the other `disputed`.

WHAT IT MOVES

The published split goes from 57 settled / 28 disputed to 58 / 27. Checks E8, E10, E11 and the
figures stated in CLAUDE.md and README.md follow, and are updated alongside this pass.

WHAT IT IS NOT

Not a finish decision. The owner also ruled that mP1 012 exists only as non-holo, and that ruling is
deliberately **not** recorded here: `FINISH_SOURCES.md` puts owner attestation in the row that
cannot establish absence, and `completenessStatus=complete-manifest` is derived by the generator
from a source that explicitly covers the unit's language. The finish layer has no owner-adjudication
mechanism, and inventing one in a pass would bypass the rule this pass is applying.

Idempotent: re-running changes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADJUDICATIONS = ROOT / "verification" / "owner_adjudications.json"

UNIT_ID = "U0678"
DECIDED_AT = "2026-08-08"

DECISION = {
    "adjudicationId": f"OA-{DECIDED_AT.replace('-', '')}-{UNIT_ID}",
    "unitId": UNIT_ID,
    "decision": "not-printed",
    "authority": "collection-owner",
    "basis": "multi-source-adjudication",
    "decidedAt": DECIDED_AT,
    "rationale": (
        "The collection owner reviewed the cited claims and ruled: \"svLN 010 und mP1 012 sind die "
        "gleiche Karte nur aus unterschiedlichen japanischen Prints, zu sehen aus dem Set Code und "
        "Nummerierung; auf T-Chinese gibt es diese Karte bisher nur einmal als Promo.\" No "
        "Traditional Chinese edition of this Japanese starter set was released; the Traditional "
        "Chinese printing of this card is the standalone promo SV-P 215 (2025 Taiwan Lantern "
        "Festival), a different product that Cardmarket does not list. Matches the adjudication "
        "already recorded for the sibling product mP1 012 (U0674), which was refuted on identical "
        "grounds."
    ),
    "evidenceRefs": [
        "https://bulbapedia.bulbagarden.net/wiki/SV-P_Promotional_cards_(TCTCG)",
        "https://bulbapedia.bulbagarden.net/wiki/Stellar_Tera_Type_Starter_Sets_(TCG)",
        "https://github.com/m4s-ai/snoredex-data/issues/119",
    ],
}


def main() -> int:
    document = json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))
    decisions = document["decisions"]

    if any(d["unitId"] == UNIT_ID for d in decisions):
        print(f"{UNIT_ID} already adjudicated; nothing to do")
        return 0

    decisions.append(DECISION)
    decisions.sort(key=lambda d: d["adjudicationId"])
    if isinstance(document.get("meta"), dict) and "count" in document["meta"]:
        document["meta"]["count"] = len(decisions)

    ADJUDICATIONS.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{DECISION['adjudicationId']}: svLN 010 T-Chinese -> not-printed "
          f"({len(decisions)} owner decisions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

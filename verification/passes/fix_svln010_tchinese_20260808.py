#!/usr/bin/env python3
"""`svLN 010` Traditional Chinese was confirmed by the evidence that refutes it.

THE ERROR

U0678 (`svLN 010` T-Chinese) carried `status: confirmed`, and its own evidence string ended:

    NOTE: the Traditional Chinese print is a promo with its own set and number, not a Traditional
    Chinese edition of the Japanese product Cardmarket files it under.

That sentence is the refutation. The record held the right reasoning and the opposite verdict.

The same facts were read correctly three weeks later for the sibling product. U0674 (`mP1 012`
T-Chinese) was set to `contradicted` on 2026-08-02 with "Traditional Chinese SV-P 215 is a separate
Taiwan promo"; U0678 was confirmed on 2026-07-22 and never revisited. Both products are Japanese
decks carrying the same card, and `RESUME.md` already states the conclusion for the pair:

    `svLN 010` and `mP1 012` are Japanese deck products; their Traditional Chinese printing is not
    a TC edition of those decks but the standalone promo SV-P 215 (2025 Taiwan Lantern Festival).

So the documentation, the sibling unit and this unit's own note all agreed; only the status did not.
Confirmed by the collection owner on 2026-08-08, in the same terms: svLN 010 and mP1 012 are the
same card from two different *Japanese* prints, and in Traditional Chinese the card exists so far
exactly once, as a promo.

WHAT IT CHANGES

U0678 becomes `contradicted`, and the evidence is rewritten to state the refutation as the finding
rather than as a footnote to a confirmation.

`corroborated` drops from true to false, which is the less obvious half. The corroborating eBay
listing is real, but it is a listing for *SV-P 215* — the promo. Under CLAUDE.md's rule that
`corroborated` means a second provider agreed about **this** unit, a second source for the
neighbouring product is not corroboration here; it is more evidence for the same refutation. This is
the trap that once made fourteen units claim specimen authority because a specimen sat nearby.

WHAT IT DOES NOT DO

It does not adjudicate. `contradicted` says an outside source disagrees with Cardmarket; whether the
application should read that as `not-printed` is a collection-owner decision recorded separately in
`owner_adjudications.json`, and none is written here. The unit therefore lands in the `disputed`
half of the split, which is what `DATABASE.md` tells consumers not to read as "does not exist".

It also leaves SV-P 215 out of the catalogue. The catalogue is derived from Cardmarket, which does
not list that promo, and inventing a product entry for it is a scope decision for the owner (#128
and the catch-up-set plan in `verification/CATCHUP-SETS.md` are where that belongs).

Idempotent: re-running changes nothing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNITS = ROOT / "verification" / "units.json"
JOURNAL = ROOT / "verification" / "evidence.jsonl"

UNIT_ID = "U0678"

EVIDENCE = (
    "Refuted: the Traditional Chinese printing of this card is the standalone promo SV-P 215, not a "
    "Traditional Chinese edition of this Japanese deck product. The TCTCG promo series article lists "
    "row \"215/SV-P ... Surging Sparks Snorlax 144 ... 2025 Taiwan Lantern Festival in Taoyuan "
    "(Taiwan, February 21-23, 2025)\", and this card shares the Cardmarket cardKey "
    "\"Snorlax-Spike-Draw-Mega-Punch\" with Surging Sparks 144, establishing it is the same card "
    "under a different set. The Stellar Tera Type Starter Sets article documents Japanese and Korean "
    "releases of this deck and no Traditional Chinese one. The sibling Japanese deck product mP1 012 "
    "was refuted on the same basis (U0674). Collection owner confirmed 2026-08-08 that svLN 010 and "
    "mP1 012 are the same card from two different Japanese prints, and that in Traditional Chinese "
    "the card exists so far only as the promo."
)


def main() -> int:
    document = json.loads(UNITS.read_text(encoding="utf-8"))
    units = document["units"] if isinstance(document, dict) and "units" in document else document

    target = next((u for u in units if u.get("unitId") == UNIT_ID), None)
    if target is None:
        raise SystemExit(f"{UNIT_ID} not found in {UNITS}")

    stamp = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat()
    already = target["status"] == "contradicted" and target["evidence"] == EVIDENCE

    if already:
        print(f"{UNIT_ID} already corrected")
    else:
        before = target["status"]
        target["status"] = "contradicted"
        target["evidence"] = EVIDENCE
        # The second source is a listing for SV-P 215, so it corroborates the promo, not this claim.
        target["corroborated"] = False
        target["sourceType"] = (
            "Bulbapedia (fan wiki), Traditional Chinese promo series article and starter-set article"
        )
        target["checkedAt"] = stamp

        UNITS.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        # Corrections are appended, never rewritten: the journal records how the state was reached.
        with JOURNAL.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "unitId": UNIT_ID,
                "status": "contradicted",
                "source": target["sourceUrl"],
                "evidence": EVIDENCE,
                "at": stamp,
            }, ensure_ascii=False) + "\n")

        print(f"{UNIT_ID} svLN 010 T-Chinese: {before} -> contradicted (corroborated -> false)")

    # snorlax_cards.json echoes the store's own tallies and check R6 holds them to it. Computed
    # rather than typed, and reconciled on every run rather than only when a verdict moved: the
    # figures went stale once already because a pass hard-coded them.
    dataset_path = ROOT / "snorlax_cards.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    tally = {
        "confirmed": sum(1 for u in units if u["status"] == "confirmed"),
        "contradicted": sum(1 for u in units if u["status"] == "contradicted"),
        "needsManualReview": sum(1 for u in units if u["status"] == "needs-manual-review"),
        "open": sum(1 for u in units if u["status"] == "pending"),
        "totalUnits": len(units),
        "lastUpdated": stamp[:10],
    }
    current = {key: dataset["meta"]["verification"].get(key) for key in tally}
    if {k: v for k, v in current.items() if k != "lastUpdated"} != {
        k: v for k, v in tally.items() if k != "lastUpdated"
    }:
        dataset["meta"]["verification"].update(tally)
        dataset_path.write_text(
            json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"meta.verification reconciled: {tally['confirmed']} confirmed, "
              f"{tally['contradicted']} contradicted")
    else:
        print("meta.verification already matches the store")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

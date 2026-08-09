#!/usr/bin/env python3
"""Admit the specimen-backed catch-up printings as prints of their own (#134, owner decision D1).

WHY THEY COULD NOT BE ADMITTED BEFORE

`record_listing_specimens_20260803.py` filed these observations and said plainly why no unit cites
them: a unit citing SPEC-0009 would assert that `s1H 45` exists in Traditional Chinese, which is
the claim the owner ruled against. The card in the photograph is real; it is simply *a different
printing* — `sc1b F 119/153`, its own set, its own number — and the model had no node for that.

ADR-0001 gives it one. A print is `(locality, localSetCode, localNumber, variant)`, so
`TW:sc1b F:119/153:base` is a node distinct from the Japanese slot, and a specimen cited from it
asserts exactly what the specimen shows.

WHY THIS IS NOT A ROW IN snorlax_cards.json

That store is the Cardmarket harvest and its identity is a Cardmarket product: `database.py`
derives a numeric product id from the image URL and raises without one. Putting `AS5a 142` there
means inventing a Cardmarket id for a card Cardmarket never listed — re-committing the conflation
ADR-0001 was accepted to end. `CATCHUP-SETS.md` called for a "snorlax_cards.json-*adjacent* entry
requiring a machine identity per code", and this is it.

WHAT IS ADMITTED, AND WHAT IS HELD BACK

D1 admits every catch-up code backed by a physical specimen. Six qualify. Two do not, and the
reason is in the specimens' own text rather than in any judgement made here:

  * SPEC-0011 `sc1a F 127/154` — "the set glyph is not fully legible ... treat the set code as
    unconfirmed".
  * SPEC-0015 `sc?? F 111/159` — "the set glyph ... is deliberately not asserted here".

A print is keyed by its local set code. Admitting these two means choosing a set code the evidence
refuses to state, which is what invariant I7 forbids: an unknown identifier is null, never a
plausible guess. They are recorded as `held` with the quotation that blocks them, so the owner can
settle each on its own.

SPEC-0009 is admitted with its caveat carried in the evidence string: the image bears a SAMPLE
overlay, so it is a database sample rather than a photograph of a printed card. The `sc1b F` set
itself is established by three sibling specimens; what the sample image supports is the 119/153
slot within it.

SPEC-0014 `S-P 101` is admitted as a printing while its *work* mapping stays open. The scan shows
the card and its identifiers; whether it is the Korean counterpart of a particular Japanese card is
an equivalence assertion, and I5 says those need an explicit provenance-bearing decision. None is
made here.

    python verification/passes/admit_catchup_prints_20260809.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SPECIMENS = ROOT / "verification" / "specimens.json"
OUTPUT = ROOT / "verification" / "source_first_prints.json"

ADMITTED = [
    {
        "printId": "TW:AS5a:142:base",
        "locality": "TW", "localSetCode": "AS5a", "localNumber": "142", "variant": "base",
        "language": "T-Chinese", "script": "Hant", "name": "卡比獸",
        "cardName": "Snorlax",
        "catchUpOf": "the printing Cardmarket lists as sm10 076",
        "specimenId": "SPEC-0024",
        "providerId": "52poke",
        "sourceUrl": "https://s1.52poke.com/wiki/7/7b/AS5a142.png",
        "corroborated": True,
        "evidence": (
            "Traditional Chinese Snorlax on the 52poke wiki card image: HP 150, Basic, Ability "
            "「吃食不專」, attack 「大反擊」60+, Illus. kawayoo, card number 142 with the AS5a set "
            "glyph. The owner confirms in #84 that this is the Traditional Chinese catch-up-set "
            "printing existing under its own AS5a 142 code rather than as an sm10 language, so a "
            "second provider agrees about this printing."
        ),
    },
    {
        "printId": "TW:sc1b F:119/153:base",
        "locality": "TW", "localSetCode": "sc1b F", "localNumber": "119/153", "variant": "base",
        "language": "T-Chinese", "script": "Hant", "name": "卡比獸V",
        "cardName": "Snorlax V",
        "catchUpOf": "the Japanese s1H 45 printing",
        "specimenId": "SPEC-0009",
        "providerId": "retailer-listing",
        "sourceUrl": "https://github.com/user-attachments/assets/aaa33550-cdd4-49e8-95ab-8c07cf67a0dd",
        "corroborated": False,
        "evidence": (
            "Traditional Chinese Snorlax V: HP 220, attacks 「吞下」 60 and 「摔下」 170, Illus. "
            "Masakazu Fukuda, \"sc1b F\" with regulation mark D, \"119/153\", rarity RR, ©2020. "
            "CAVEAT carried from SPEC-0009: the image bears a SAMPLE overlay, so it is a "
            "pre-release or database sample rather than a photograph of a printed card. The sc1b F "
            "set is established by SPEC-0007, SPEC-0008 and SPEC-0010; what this record supports "
            "is the 119/153 slot within it."
        ),
    },
    {
        "printId": "TW:sc1b F:120/153:base",
        "locality": "TW", "localSetCode": "sc1b F", "localNumber": "120/153", "variant": "base",
        "language": "T-Chinese", "script": "Hant", "name": "卡比獸VMAX",
        "cardName": "Snorlax VMAX",
        "catchUpOf": "the Japanese s1H 46 printing",
        "specimenId": "SPEC-0007",
        "providerId": "retailer-listing",
        "sourceUrl": "https://github.com/user-attachments/assets/5052ddbb-276c-4734-baa2-a0a3c2dd74d7",
        "corroborated": False,
        "evidence": (
            "Traditional Chinese Snorlax VMAX read off a seller's listing image (watermark 佛系工作室 "
            "/ FOSI TCG STUDIO): HP 340, Colorless, evolves from 卡比獸V, attack 「超極巨自由墜落」 "
            "60+, Illus. aky CG Works, \"sc1b F\" with regulation mark D, \"120/153\", rarity RRR, "
            "©2020."
        ),
    },
    {
        "printId": "TW:sc1b F:165/153:base",
        "locality": "TW", "localSetCode": "sc1b F", "localNumber": "165/153", "variant": "base",
        "language": "T-Chinese", "script": "Hant", "name": "卡比獸V",
        "cardName": "Snorlax V",
        "catchUpOf": "the Japanese s1H 66 printing",
        "specimenId": "SPEC-0010",
        "providerId": "retailer-listing",
        "sourceUrl": "https://github.com/user-attachments/assets/0766a589-2407-486b-8cf5-438a612b8d66",
        "corroborated": False,
        "evidence": (
            "Traditional Chinese Snorlax V full art read off a watermarked seller's listing image: "
            "HP 220, attacks 「吞下」 60 and 「摔下」 170, Illus. aky CG Works, \"sc1b F\" with "
            "regulation mark D, \"165/153\", rarity SR, ©2020. Secret-numbered above the 153-card "
            "set size."
        ),
    },
    {
        "printId": "TW:sc1b F:177/153:base",
        "locality": "TW", "localSetCode": "sc1b F", "localNumber": "177/153", "variant": "base",
        "language": "T-Chinese", "script": "Hant", "name": "卡比獸VMAX",
        "cardName": "Snorlax VMAX",
        "catchUpOf": "the Japanese s1H 70 printing",
        "specimenId": "SPEC-0008",
        "providerId": "retailer-listing",
        "sourceUrl": "https://github.com/user-attachments/assets/65ea5eff-7441-47a4-8750-47c03822f3d8",
        "corroborated": False,
        "evidence": (
            "Traditional Chinese Snorlax VMAX rainbow rare read off a watermarked seller's listing "
            "image: HP 340, attack 「超極巨自由墜落」 60+, Illus. aky CG Works, \"sc1b F\" with "
            "regulation mark D, \"177/153\", rarity HR, ©2020. Secret-numbered above the 153-card "
            "set size, the hyper-rare slot."
        ),
    },
    {
        "printId": "KR:S-P:101:base",
        "locality": "KR", "localSetCode": "S-P", "localNumber": "101", "variant": "base",
        "language": "Korean", "script": "Hang", "name": "잠만보",
        "cardName": "Snorlax",
        "catchUpOf": None,
        "specimenId": "SPEC-0014",
        "providerId": "owner-attestation",
        "sourceUrl": "https://github.com/user-attachments/assets/7302c36e-1046-458a-a397-4e594916f682",
        "corroborated": False,
        "evidence": (
            "Korean Snorlax on a database scan: HP 140, Basic, Single Strike (일격) marker, attacks "
            "「뺨때리기」 30 and 「일격태클」 120, Illus. Yuya Oka, \"101/S-P\", PROMO, regulation "
            "mark D, ©2021. The printing and its identifiers are what this record establishes. "
            "OPEN: units.json records for S-P 156 state that S-P 101 is a different card, and the "
            "owner presents it as the Korean counterpart. That is an equivalence assertion about "
            "which work this print realizes; invariant I5 requires an explicit decision for it and "
            "none is made here."
        ),
    },
]

HELD = [
    {
        "specimenId": "SPEC-0011",
        "proposedSetCode": "sc1a F", "localNumber": "127/154", "language": "T-Chinese",
        "blockedBy": (
            "the set glyph is not fully legible at this resolution and is recorded as sc1a F on "
            "the owner's identification — treat the set code as unconfirmed"
        ),
        "reason": (
            "A print is keyed by its local set code. Admitting this one means asserting a set code "
            "the specimen explicitly declines to assert, which invariant I7 forbids."
        ),
    },
    {
        "specimenId": "SPEC-0015",
        "proposedSetCode": None, "localNumber": "111/159", "language": "T-Chinese",
        "blockedBy": (
            "the set glyph is not legible — it reads as a two-or-three character code ending in F "
            "and is deliberately not asserted"
        ),
        "reason": (
            "The number is established and the set code is unknown. This is the one specimen the "
            "owner photographed personally, so the card is not in doubt; only its set is. It waits "
            "for a legible glyph or an owner ruling on the code."
        ),
    },
]


def main() -> int:
    specimen_doc = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    records = specimen_doc["specimens"] if isinstance(specimen_doc, dict) else specimen_doc
    by_id = {r["specimenId"]: r for r in records}

    for entry in ADMITTED:
        specimen = by_id.get(entry["specimenId"])
        if specimen is None:
            print(f"missing specimen {entry['specimenId']}", file=sys.stderr)
            return 1
        # The specimen now has somewhere to point. Until today every one of these carried an empty
        # citedBy, which was correct: no unit could cite them without asserting the wrong claim.
        cited = specimen.setdefault("citedBy", [])
        if entry["printId"] not in cited:
            cited.append(entry["printId"])

    document = {
        "meta": {
            "schema": "snoredex-source-first-prints",
            "schemaVersion": "0.1.0",
            "generated": date.today().isoformat(),
            "adr": "verification/ADR-0001-locality-aware-print-identity.md",
            "decision": "ADR-0001 D1 (owner, 2026-08-09)",
            "description": (
                "Printings admitted on their own evidence rather than inherited from the Cardmarket "
                "harvest. Keyed by the ADR-0001 print identity, deliberately not by a Cardmarket "
                "product: these cards were never listed there."
            ),
            "notYetProjected": (
                "These are not in snorlax_cards.json, the checklist or the SQLite handoff. Owner "
                "decision D2 makes them collector-visible when the identity model goes into force "
                "in #140; until then they are recorded, cited and countable, not published."
            ),
            "counts": {"admitted": len(ADMITTED), "held": len(HELD)},
        },
        "prints": ADMITTED,
        "held": HELD,
    }
    OUTPUT.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    body = json.dumps(specimen_doc, indent=2, ensure_ascii=False) + "\n"
    SPECIMENS.write_text(body, encoding="utf-8")

    print(f"admitted {len(ADMITTED)} source-first prints, held {len(HELD)}")
    for entry in ADMITTED:
        print(f"  {entry['printId']:28} <- {entry['specimenId']}")
    for entry in HELD:
        print(f"  HELD {entry['specimenId']}: {entry['proposedSetCode'] or 'set code unknown'} "
              f"{entry['localNumber']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

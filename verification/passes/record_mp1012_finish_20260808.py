#!/usr/bin/env python3
"""`mP1 012` Japanese: record the non-holo printing from the owner's listing photograph (#119).

WHAT WAS OPEN

The language was never in doubt — U0674 confirms Japanese from the official JP card database, which
also gave the illustrator. What that database cannot give is the finish: `FINISH_SOURCES.md` is
explicit that the JP card page carries no finish vocabulary at all, so F0231 sat at
`availability=pending` with no printings, and CLAUDE.md forbids inferring one from the confirmed
language.

THE EVIDENCE

The owner supplied a SNKRDUNK listing whose photograph shows the card face. Read off the image
rather than described from memory, which is what the SPEC ids replaced:

    カビゴン, たね, HP 150, Colorless. Attacks スパイクドロー 20 ("自分の山札を1枚引く。") and
    メガトンパンチ 100. Weakness 闘 x2, no resistance, retreat 3. Illus. Ounishi. Regulation mark H,
    mP1 set glyph, 012/023, (c)2025.

Two independent identity checks land: the attack pair is exactly the Cardmarket cardKey
`Snorlax-Spike-Draw-Mega-Punch`, and the illustrator and collector number match what the official
Japanese database already recorded for this unit. The listing title names the product outright —
`[A]Snorlax [MP1 012/23](The Start Deck 100 "Battle Collection Coro Ciao Ver.")`.

The card face is uniformly matte with no foil pattern anywhere, including across the artwork window
where a holo or mirror treatment would show. That is the non-holo reading, and it is the only finish
this pass records.

WHAT IT DOES NOT RECORD

Completeness. The owner adjudicated that non-holo is the only finish for this printing, and that is
deliberately absent: `FINISH_SOURCES.md` puts owner attestation in the row that cannot establish
absence, and `completenessStatus=complete-manifest` is derived by the generator from a source that
explicitly covers the unit's language. So F0231 lands `positive-evidence-only` — non-holo exists,
and holo and reverse stay unevidenced rather than excluded. The legitimate route to completeness is
the official product page, which FINISH_SOURCES.md names as the Japanese route for finish
vocabulary; #119 stays open for it.

Idempotent: re-running changes nothing. The photograph itself is filed by fetch_attachment.py.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECIMENS = ROOT / "verification" / "specimens.json"
OVERRIDES = ROOT / "verification" / "finish_overrides.json"

SPECIMEN_ID = "SPEC-0025"
LISTING_URL = "https://snkrdunk.com/en/trading-cards/used/listings/01KEKJJGWGHJHMN4EV1C2J8CXN"
IMAGE_URL = ("https://cdn.snkrdunk.com/apparel_used_listings/"
             "6db7c19b-bdfa-4461-8b84-e4ef3ffefe3e/1603174.jpeg?size=l")

SPECIMEN = {
    "specimenId": SPECIMEN_ID,
    "setCode": "mP1",
    "number": "012",
    "variant": "base",
    "language": "Japanese",
    "heldBy": "third-party seller",
    "inspectedFrom": "listing photograph",
    "photograph": None,
    "photographSource": IMAGE_URL,
    "observed": (
        "Japanese Snorlax read off a SNKRDUNK seller's listing photograph, supplied by the owner in "
        "#119: \"カビゴン\", たね (Basic), HP 150, Colorless, attacks 「スパイクドロー」20 "
        "(\"自分の山札を1枚引く。\") and 「メガトンパンチ」100, weakness 闘 x2, no resistance, retreat "
        "3, Illus. Ounishi, regulation mark H, mP1 set glyph, 012/023, ©2025. The attack pair is the "
        "Cardmarket cardKey \"Snorlax-Spike-Draw-Mega-Punch\", and the illustrator and collector "
        "number match the official Japanese card database entry already cited for this unit. The "
        "card face is uniformly matte with no foil pattern anywhere, including across the artwork "
        "window: a non-holo printing. Listing title: \"[A]Snorlax [MP1 012/23](The Start Deck 100 "
        "\\\"Battle Collection Coro Ciao Ver.\\\")\"."
    ),
    "listingUrl": LISTING_URL,
    "recordedAt": "2026-08-08",
    "citedBy": [],
}

SOURCE_KEY = "snkrdunk-mp1-012"
SOURCE = {
    "url": LISTING_URL,
    "sourceType": "SNKRDUNK marketplace listing photograph (identified physical printing)",
    "evidence": (
        "Seller listing \"[A]Snorlax [MP1 012/23](The Start Deck 100 \\\"Battle Collection Coro Ciao "
        "Ver.\\\")\" photographs the card face: mP1 012/023, Illus. Ounishi, regulation mark H, and a "
        "uniformly matte surface with no foil pattern. Recorded as specimen SPEC-0025 so the "
        "observation outlives the listing."
    ),
}

OVERRIDE = {
    "setCode": "mP1",
    "number": "012",
    "languages": ["Japanese"],
    "printings": [
        {
            "finish": "non-holo",
            "foilPattern": None,
            "markings": [],
            "distribution": {"kind": "fixed-deck", "text": "Start Deck 100 Battle Collection "
                                                           "CoroCiao Version"},
            "cardSize": "standard",
            "mappedVariants": ["base"],
            "verificationStatus": "confirmed",
            "sourceRefs": [SOURCE_KEY],
        }
    ],
}


def main() -> int:
    specimens = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    if any(s["specimenId"] == SPECIMEN_ID for s in specimens["specimens"]):
        print(f"{SPECIMEN_ID} already recorded")
    else:
        specimens["specimens"].append(SPECIMEN)
        specimens["specimens"].sort(key=lambda s: s["specimenId"])
        if isinstance(specimens.get("count"), int):
            specimens["count"] = len(specimens["specimens"])
        SPECIMENS.write_text(
            json.dumps(specimens, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{SPECIMEN_ID} recorded: mP1 012 Japanese, third-party seller listing photograph")

    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    changed = False
    if SOURCE_KEY not in overrides["sources"]:
        overrides["sources"][SOURCE_KEY] = SOURCE
        changed = True
    if not any(o.get("setCode") == "mP1" and o.get("number") == "012"
               for o in overrides["overrides"]):
        overrides["overrides"].append(OVERRIDE)
        changed = True
    if changed:
        OVERRIDES.write_text(
            json.dumps(overrides, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("finish override recorded: mP1 012 Japanese non-holo (positive evidence only)")
    else:
        print("finish override already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

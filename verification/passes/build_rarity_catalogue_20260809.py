#!/usr/bin/env python3
"""Build the central rarity catalogue (#146, owner request 2026-08-09).

Rarity has been read three different ways in this repository and never written down once: the
harvest stores Cardmarket's label per product, Bulbapedia's setlists carry their own vocabulary
per set, and the Japanese releases use letter codes that correspond to the Western names without
sharing them. Nothing recorded which of those was speaking, so `Illustration Rare` and `AR` looked
like different facts and `Rare` and `Rare Holo` looked like the same one.

This writes `verification/rarity_catalogue.json`: one entry per rarity, with its Western name, the
locale codes it corresponds to, whether it names a finish, and the sentence from
https://bulbapedia.bulbagarden.net/wiki/Rarity that says so. It is reference data with provenance
— it makes no claim about any Snorlax card and touches no authoritative store.

TWO THINGS IT DELIBERATELY GETS RIGHT

*Rarity belongs to a card release, not to a work.* Bulbapedia states it outright: "The rarity of a
card may vary between Japanese and other-language releases; that is, a card which is Common in the
Japanese release may be Uncommon in the English-language release." So the same card can carry
different rarities in different localities, exactly as it can carry different finishes and
different release dates. `impliesFinish` therefore says what the rarity means *within the locality
that uses that vocabulary*, never across one.

*A rarity may name a finish; it never names a reverse holo.* Common, Uncommon and Rare "can also
come in a Reverse Holofoil print" — that is set-level availability, which is the finish profile's
job (#146), not the rarity's. The catalogue records the eligibility as a separate flag so nobody
reads `reverseHoloEligible` as "this card has one".

    python verification/passes/build_rarity_catalogue_20260809.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = ROOT / "verification" / "rarity_catalogue.json"
SOURCE_URL = "https://bulbapedia.bulbagarden.net/wiki/Rarity"

# Every entry quotes the article. `impliesFinish` is filled only where the text states the finish;
# a rarity that merely tends to be foil in practice is left null, for the same reason SPEC-0008's
# "rainbow rare" did not become a finish in #150.
RARITIES = [
    {
        "rarityId": "common", "name": "Common", "symbol": "circle",
        "localeCodes": {"JP": "C"}, "impliesFinish": None, "reverseHoloEligible": True,
        "basis": "\"Common cards are marked with a circle … Common cards can also come in a "
                 "Reverse Holofoil print.\"",
    },
    {
        "rarityId": "uncommon", "name": "Uncommon", "symbol": "diamond",
        "localeCodes": {"JP": "U"}, "impliesFinish": None, "reverseHoloEligible": True,
        "basis": "\"Uncommon cards are marked with a diamond … Uncommon cards can also come in a "
                 "Reverse Holofoil print.\"",
    },
    {
        "rarityId": "rare", "name": "Rare", "symbol": "star",
        "localeCodes": {"JP": "R"}, "impliesFinish": None, "reverseHoloEligible": True,
        "basis": "\"Rare cards are marked with a star … Rare cards can also come in a Reverse "
                 "Holofoil print.\"",
    },
    {
        "rarityId": "holofoil-rare", "name": "Holofoil Rare",
        "symbol": "star; Bulbapedia renders the setlist marker as a star followed by H",
        "bulbapediaSetlistLabel": "Rare Holo",
        "localeCodes": {}, "impliesFinish": "holo", "reverseHoloEligible": None,
        "basis": "\"A small amount of rare cards within each expansion are available as both "
                 "Regular Rare and Holofoil Rare. These cards have a Holofoil pattern on the card "
                 "art … Cards which are available as either Regular Rare or Holofoil Rare are "
                 "labelled with Rare Holo on Bulbapedia.\"",
        "notes": "The setlist distinguishes this from Rare only by the marker. In the rendered "
                 "page both are a star; in the wikitext the label is literally \"Rare Holo\".",
    },
    {
        "rarityId": "shiny-rare", "name": "Shiny Rare", "symbol": "full star",
        "localeCodes": {}, "impliesFinish": None, "reverseHoloEligible": None,
        "introduced": "Shining Fates",
        "basis": "\"The Shiny Rare rarity … was introduced in Shining Fates. It is only for Shiny "
                 "Pokémon.\"",
    },
    {
        "rarityId": "double-rare", "name": "Double Rare", "symbol": "two stars",
        "localeCodes": {"JP": "RR"}, "impliesFinish": None, "reverseHoloEligible": None,
        "introduced": "Scarlet & Violet",
        "basis": "\"The Double Rare rarity was introduced in the Scarlet & Violet expansion and "
                 "corresponds to the RR rarity. It is marked with two stars.\"",
    },
    {
        "rarityId": "ultra-rare", "name": "Ultra Rare", "alsoKnownAs": ["Super Rare"],
        "symbol": "typically the Rare Holofoil marker; sometimes a unique symbol",
        "localeCodes": {}, "impliesFinish": None, "reverseHoloEligible": None,
        "basis": "\"Ultra Rare (sometimes known as Super Rare) cards are typically marked as Rare "
                 "Holofoil cards, but sometimes have unique symbols denoting their rarity.\"",
        "notes": "\"typically marked as Rare Holofoil\" describes the marker, not a stated finish, "
                 "so impliesFinish stays null.",
    },
    {
        "rarityId": "secret-rare", "name": "Secret Rare",
        "symbol": "set number outside the printed set size",
        "localeCodes": {}, "impliesFinish": None, "reverseHoloEligible": None,
        "basis": "\"Secret rare cards are cards with set numbers outside the printed size of the "
                 "set (for example, a card numbered 101/100).\"",
    },
    {
        "rarityId": "ace-spec-rare", "name": "ACE SPEC Rare", "symbol": "pink star",
        "localeCodes": {}, "impliesFinish": None, "reverseHoloEligible": None,
        "introduced": "Boundaries Crossed",
        "basis": "\"The ACE SPEC rare rarity was introduced in the Boundaries Crossed expansion "
                 "and is marked with a pink star.\"",
    },
    {
        "rarityId": "illustration-rare", "name": "Illustration Rare", "symbol": "gold star",
        "localeCodes": {"JP": "AR"}, "impliesFinish": None, "reverseHoloEligible": None,
        "introduced": "Scarlet & Violet",
        "basis": "\"The Illustration Rare rarity was introduced in the Scarlet & Violet expansion "
                 "and corresponds to the AR rarity. It is marked with a gold star.\"",
    },
    {
        "rarityId": "special-illustration-rare", "name": "Special Illustration Rare",
        "symbol": "two gold stars",
        "localeCodes": {"JP": "SAR"}, "impliesFinish": None, "reverseHoloEligible": None,
        "introduced": "Scarlet & Violet",
        "basis": "\"The Special Illustration Rare rarity was introduced in the Scarlet & Violet "
                 "expansion and corresponds to the SAR rarity. It is marked with two gold stars.\"",
    },
    {
        "rarityId": "mega-attack-rare", "name": "Mega Attack Rare", "symbol": "pastel marker",
        "localeCodes": {"JP": "MA"}, "impliesFinish": None, "reverseHoloEligible": None,
        "introduced": "MEGA Dream ex (Japanese)",
        "basis": "\"The Mega Attack Rare rarity was introduced in the Japanese MEGA Dream ex "
                 "expansion and corresponds to the MA rarity.\"",
    },
    {
        "rarityId": "hyper-rare", "name": "Hyper Rare", "symbol": "three gold stars",
        "localeCodes": {"JP": "UR"}, "impliesFinish": None, "reverseHoloEligible": None,
        "introduced": "Scarlet & Violet",
        "basis": "\"The Hyper Rare rarity was introduced in the Scarlet & Violet expansion and "
                 "corresponds to the UR rarity. It is marked with three gold stars.\"",
    },
    {
        "rarityId": "mega-hyper-rare", "name": "Mega Hyper Rare",
        "symbol": "gold star with black border",
        "localeCodes": {"JP": "MUR"}, "impliesFinish": None, "reverseHoloEligible": None,
        "introduced": "Mega Evolution",
        "basis": "\"The Mega Hyper Rare rarity was introduced in the Mega Evolution expansion and "
                 "corresponds to the MUR rarity.\"",
    },
    {
        "rarityId": "fixed", "name": "Fixed rarity",
        "symbol": "no rarity symbol; the silhouette of the kit's main Pokémon instead",
        "localeCodes": {}, "impliesFinish": None, "reverseHoloEligible": None,
        "basis": "\"Certain cards, such as those from certain decks (such as a Trainer Kit or some "
                 "Japanese half or quarter decks) do not have a rarity listed on the bottom right "
                 "corner of the card, and instead have the silhouette of the main Pokémon within "
                 "the kit.\"",
        "notes": "Cardmarket uses the same word for the same category, so \"Fixed\" in the harvest "
                 "is not a marketplace invention.",
    },
    {
        "rarityId": "promo", "name": "Promo",
        "symbol": "Black Star Promo symbol instead of a rarity symbol",
        "localeCodes": {}, "impliesFinish": None, "reverseHoloEligible": None,
        "basis": "\"Promos are promotional cards released during an event … or in certain "
                 "merchandise … They have a Black Star Promo symbol instead of a rarity symbol in "
                 "the bottom right corner.\"",
    },
]

# Facts about the vocabularies themselves, which is what makes a per-locality mapping necessary.
LOCALE_VOCABULARIES = {
    "WEST": {
        "form": "symbols printed in the bottom right corner",
        "basis": "The article's Standard rarity section describes circle / diamond / star markers.",
    },
    "JP": {
        "form": "bolded letter codes rather than symbols",
        "basis": "\"Starting from ブラックコレクション Black Collection and ホワイトコレクション "
                 "White Collection, Japanese releases, rather than using symbols, use bolded "
                 "letters to denote rarity; for example, C, U, R and RR.\"",
        "note": "With Scarlet & Violet \"the rarity scale was changed to correspond to the one "
                "used in Japan, however maintaining being marked by symbols.\"",
    },
}

# The reason rarity cannot be inherited across a locality boundary, in the source's own words.
CROSS_LOCALITY_WARNING = (
    "\"The rarity of a card may vary between Japanese and other-language releases; that is, a card "
    "which is Common (C) in the Japanese release may be Uncommon in the English-language release "
    "(for example, Sudowoodo (Sword & Shield 100)).\" A worked divergence: Crystal Pokémon in "
    "Skyridge \"have a rarity of Holo Rare in English and Super Rare in Japanese\"."
)

# Which rarities a set edition actually carries, evidenced from that set's own setlist. Seeded only
# with the two pages fetched and counted for this pass; every other set is absent rather than
# assumed, and #147 is what fills the rest.
EDITION_AVAILABILITY = [
    {
        "sourcePage": "Skyridge (TCG)",
        "sourceUrl": "https://bulbapedia.bulbagarden.net/wiki/Skyridge_(TCG)",
        "legacySetCode": "SK",
        "languages": ["English", "German", "Italian"],
        "rarities": {"Common": 150, "Rare Holo": 76, "Uncommon": 71, "Rare": 67},
        "basis": "Counted from the page's setlist entries on 2026-08-09.",
        "finishProfile": {
            "statement": "\"The Skyridge set is released in English, German, and Italian, with all "
                         "cards except the \\\"H/32\\\" cards also available as Reverse Holos. In a "
                         "change from Aquapolis, the secret rare cards are also available as "
                         "Reverse Holos.\"",
            "scope": "the three languages named, excepting the H/32 subset",
            "closedWithinScope": True,
        },
    },
    {
        "sourcePage": "Gym Challenge (TCG)",
        "sourceUrl": "https://bulbapedia.bulbagarden.net/wiki/Gym_Challenge_(TCG)",
        "legacySetCode": None,
        "languages": None,
        "rarities": {"Common": 75, "Uncommon": 74, "Rare": 37, "Rare Holo": 36, "None": 6,
                     "W Promo": 1, "SuperRare": 1},
        "basis": "Counted from the page's setlist entries on 2026-08-09. Recorded as the worked "
                 "example for the Rare versus Rare Holo marker; no Snorlax is in this set.",
        "finishProfile": None,
    },
]


def main() -> int:
    document = {
        "meta": {
            "schema": "snoredex-rarity-catalogue",
            "schemaVersion": "0.1.0",
            "generated": date.today().isoformat(),
            "status": "reference data — makes no claim about any card in this catalogue",
            "source": {"provider": "bulbapedia", "url": SOURCE_URL, "page": "Rarity",
                       "retrieved": date.today().isoformat()},
            "description": (
                "One entry per rarity, with the locale codes it corresponds to, whether it names a "
                "finish, and the sentence that says so. The article's focus is Western sets; Asian "
                "releases use different names for the same tiers, which is what localeCodes "
                "records."
            ),
            "crossLocalityWarning": CROSS_LOCALITY_WARNING,
            "notAFinishProfile": (
                "reverseHoloEligible says a rarity may appear as a Reverse Holofoil, never that a "
                "given card does. Which cards actually carry one is a set edition's finish "
                "profile (#146)."
            ),
        },
        "localeVocabularies": LOCALE_VOCABULARIES,
        "rarities": RARITIES,
        "editionAvailability": EDITION_AVAILABILITY,
    }
    OUTPUT.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    finishes = [r["rarityId"] for r in RARITIES if r["impliesFinish"]]
    coded = [r["rarityId"] for r in RARITIES if r["localeCodes"]]
    print(f"wrote {OUTPUT.relative_to(ROOT)}: {len(RARITIES)} rarities, "
          f"{len(coded)} with a locale correspondence, {len(finishes)} naming a finish "
          f"({', '.join(finishes)})")
    print(f"  edition availability seeded for {len(EDITION_AVAILABILITY)} set page(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

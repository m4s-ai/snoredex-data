#!/usr/bin/env python3
"""Replace U0644's failed rationale with the one the product article actually states (#137, #88).

The owner asked for a search for positive Korean evidence before deciding whether to retract this
row. The search found the opposite, and something better than what the row rested on.

WHAT THE ROW RESTED ON, AND WHY IT FAILED

`U0644` — `HSZ 027`, National Pokédex Beginning Set, Korean — cited the era-format argument from
`Pokémon in South Korea`: between the DP and Black & White eras, Korean sets were unique
recombinations. The scope correction of 2026-08-10 showed that argument does not reach this card.
Black & White launched in Japan on 2010-12-17 and this product is dated 2012-04-20, a year and a
half into the era where the same sentence says Korean sets *did* follow the Japanese format.

WHAT THE SEARCH FOUND

`National Beginning Set (TCG)` opens with a positive statement of exclusivity:

    The National Pokédex Beginning Set (Japanese: はじめてセット 全国図鑑版セット) is a
    **Japanese-exclusive** Half Deck Deck Kit released in the BW era

Its `DeckInfobox` carries a single `release=April 20, 2012` with no market qualifiers, and the
article has no "In other languages" section at all. The half-deck list carries this card —
`027/034 Snorlax` — so the source reaches the card as well as the product.

That is not bare absence. "Japanese-exclusive" is a source asserting what exists, the same character
as "Prior to the DP Era, only two sets of the Trading Card Game were officially printed in Korean" —
which is why the three pre-DP Korean rows hold. Rule 3 is about a source failing to mention
something; this source mentions it and says the opposite.

No Korean printing was found either: `koreanpokemoncards.com` returns nothing for Snorlax, and
pokumon carries no Beginning Set entry in any language.

WHAT THIS DOES

The verdict is unchanged and was never the problem — `contradicted` was right for a reason the row
did not record. The evidence is repaired rather than the verdict retracted, `providerId` stays
`bulbapedia` because that is still the source it would fall over without, and `sourceUrl` moves from
the country article to the product article that carries the statement and the card list.

The Cardmarket record claims Japanese, Korean and Traditional Chinese for this card. A
Japanese-exclusive product listed in three languages is exactly the over-claim this project exists
to check, and the Traditional Chinese row (`U0645`) rests on the separate October 2019 launch bound,
which does cover it.

    python verification/passes/hsz_korean_exclusivity_20260810.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UNITS = ROOT / "verification" / "units.json"

UNIT_ID = "U0644"
ARTICLE = "https://bulbapedia.bulbagarden.net/wiki/National_Beginning_Set_(TCG)"
MARKER = "RATIONALE REPLACED 2026-08-10"

EVIDENCE = (
    "Bulbapedia's National Beginning Set (TCG) states the product's exclusivity outright: \"The "
    "National Pokédex Beginning Set (Japanese: はじめてセット 全国図鑑版セット) is a "
    "Japanese-exclusive Half Deck Deck Kit released in the BW era of the Pokémon Trading Card "
    "Game.\" Its DeckInfobox carries one unqualified release, April 20, 2012, and the article has "
    "no \"In other languages\" section. The half-deck list carries this card — "
    "\"Halfdecklist/nmentry|027/034|National Beginning Set|Snorlax|27|Colorless||1\" — so the "
    "source reaches the card and not only the product. A Japanese-exclusive product has no Korean "
    "printing. "
    f"{MARKER}: this replaces the era-format argument from \"Pokémon in South Korea\" that the row "
    "previously cited. That argument covers the window between the DP and Black & White eras, and "
    "Black & White launched in Japan on 2010-12-17 against this product's 2012-04-20 — it did not "
    "reach this card, as the scope correction of 2026-08-10 recorded. The verdict was never the "
    "problem; the rationale was, and it is replaced rather than the verdict retracted. This is not "
    "an absence argument: \"Japanese-exclusive\" is a source asserting what exists, the same "
    "character as the closed enumeration that carries the pre-DP Korean rows, and rule 3 governs a "
    "source that fails to mention something. A search for positive Korean evidence was run first "
    "at the owner's direction and found none: koreanpokemoncards.com returns nothing for Snorlax "
    "and pokumon carries no Beginning Set entry in any language. Retrieved 2026-08-10."
)


def main() -> int:
    units = json.loads(UNITS.read_text(encoding="utf-8"))
    unit = next((u for u in units if u["unitId"] == UNIT_ID), None)
    if unit is None:
        print(f"missing {UNIT_ID}", file=sys.stderr)
        return 1
    if (unit["setCode"], str(unit["number"]), unit["language"]) != ("HSZ", "027", "Korean"):
        print(f"{UNIT_ID} is not HSZ 027 Korean", file=sys.stderr)
        return 1
    if unit["status"] != "contradicted":
        print(f"{UNIT_ID} is {unit['status']}, expected contradicted", file=sys.stderr)
        return 1
    if MARKER in unit["evidence"]:
        print("already replaced")
        return 0

    unit["evidence"] = EVIDENCE
    unit["sourceUrl"] = ARTICLE
    unit["sourceType"] = (
        "Bulbapedia (fan wiki), product article, exclusivity statement + half-deck list")
    UNITS.write_text(json.dumps(units, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{UNIT_ID} HSZ 027 Korean: era argument -> product-article exclusivity statement")
    print(f"  {ARTICLE}")
    print("  verdict unchanged; no Korean printing found in koreanpokemoncards.com or pokumon")
    return 0


if __name__ == "__main__":
    sys.exit(main())

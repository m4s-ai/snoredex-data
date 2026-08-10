#!/usr/bin/env python3
"""One Korean contradiction sits outside the era its own quote argues about (#137).

#137's challenge loop asks, for every contradicted row, to "verify that the cited source covers the
exact node and scope". Running it over the twenty-seven market-history contradictions found exactly
one row where the answer is no.

THE TWO KOREAN ARGUMENTS, AND WHAT EACH COVERS

`Pokémon in South Korea` supports two different claims, and every Korean contradiction here rests on
one of them:

* **A closed enumeration, for anything before the DP era.** "Prior to the DP Era, only two sets of
  the Trading Card Game were officially printed in Korean" — Base Set (2000), and the ADV Expansion
  Pack plus the Treecko/Torchic/Mudkip starter decks (2004). A named list is a statement about what
  exists, not a failure to mention something. `PJU` (1997), `G2` (1999) and `EC5` (2002) are covered.
* **An era-format argument, for the window between DP and Black & White.** "Korean sets at this time
  were a unique combination of existing cards, with none of the sets themselves corresponding to
  existing sets. It wouldn't be until the release of the Black and White sets in Japan that Korean
  sets would follow a format that is on par with Japan." `DP1` (2006-11-30) and `LL` (2010-04-16)
  are inside that window.

THE ONE THAT IS NOT

`U0644` — `HSZ 027`, National Pokédex Beginning Set, Korean — cites the second argument. Its
Japanese release is **2012-04-20**, and Black & White launched in Japan on **December 17, 2010**
(Bulbapedia's `Black & White (TCG)`, `jarelease`). The card is a year and a half *past* the window
the quote describes, in the era where the same quote says Korean sets did follow the Japanese
format. The rationale as written argues the opposite of what the row needs.

WHAT THIS DOES AND DOES NOT DO

It records the mismatch and narrows the inference. It does **not** flip the verdict, for the same
reason the 2026-08-09 index-absence corrections did not: an argument failing to support an absence
is not evidence of a presence, and no Korean printing of this product has been found. What it does
mean is that the row no longer has a rationale of its own, so retracting it to `pending` is a live
option — and that is an owner decision, tracked on #88, not something a pass should take.

The Traditional Chinese rows were checked the same way and all pass: their bound is the October 2019
Traditional Chinese launch, and every one of the twenty-one has a Japanese release before it, the
latest being `smL 038` on 2019-03-15.

    python verification/passes/scope_korean_era_argument_20260810.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UNITS = ROOT / "verification" / "units.json"

MARKER = "SCOPE CORRECTION 2026-08-10"
UNIT_ID = "U0644"

CORRECTION = (
    f" {MARKER}: the quoted rationale does not cover this card. It argues about the window between "
    "the DP era and Black & White, and says that from Black & White onward Korean sets did follow "
    "the Japanese format. Black & White launched in Japan on 2010-12-17 (Bulbapedia, "
    "Black & White (TCG), jarelease), while this product was released on 2012-04-20 — a year and a "
    "half into the era the quote excludes. The sentence therefore argues the opposite of what this "
    "row needs. The verdict is left as recorded because a rationale that fails to support an "
    "absence is not evidence of a presence, and no Korean printing of this product has been found; "
    "but the row now rests on nothing of its own, so retracting it to pending is a live option and "
    "an owner decision. Tracked on #88."
)


def main() -> int:
    units = json.loads(UNITS.read_text(encoding="utf-8"))
    unit = next((u for u in units if u["unitId"] == UNIT_ID), None)
    if unit is None:
        print(f"missing {UNIT_ID}", file=sys.stderr)
        return 1
    if unit["status"] != "contradicted":
        print(f"{UNIT_ID} is {unit['status']}, expected contradicted", file=sys.stderr)
        return 1
    if (unit["setCode"], str(unit["number"]), unit["language"]) != ("HSZ", "027", "Korean"):
        print(f"{UNIT_ID} is not HSZ 027 Korean", file=sys.stderr)
        return 1
    if MARKER in unit["evidence"]:
        print("already corrected")
        return 0

    unit["evidence"] = unit["evidence"].rstrip().rstrip(".") + "." + CORRECTION
    UNITS.write_text(json.dumps(units, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{UNIT_ID} HSZ 027 Korean: rationale does not cover 2012-04-20; inference narrowed, "
          f"verdict unchanged, retraction referred to the owner (#88)")
    print("  26 other market-history contradictions checked: all covered by their cited bound")
    return 0


if __name__ == "__main__":
    sys.exit(main())

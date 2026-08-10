#!/usr/bin/env python3
"""Read the Battle Academy 2020 article far enough to reach the card (#137).

Three units — French, German and Italian `BA20 MWT` — cited the product article's "In other
languages" table and nothing else. That table names the localized product:

    |fr=Académie de Combat du Jeu de Cartes à Collectionner Pokémon
    |de=Pokémon-Sammelkartenspiel: Kampfakademie
    |it=Accademia Lotta del Gioco di Carte Collezionabili Pokémon

which establishes that the *product* exists in those three languages and stops there. `BA20 MWT`
carries the harvest rarity `Fixed`, so `evidence_semantics.py` flagged all three: a deck card is
not part of a numbered expansion run, and "the set was released in French" cannot reach it.

The same page answers the rest. Its **Mewtwo Deck** half-deck list is a closed, fixed list, and the
card is in it:

    {{halfdecklist/nmentry|50/68|{{TCG ID|Hidden Fates|Snorlax|50}} ... |Colorless||2}}

Two copies, in every Mewtwo Deck, in every language edition of the product. A fixed deck list plus a
statement of which languages the product exists in reaches the card for exactly the reason a
Prize Pack article does — the closed-list half of the rule already written into
`evidence_semantics.py`, which the first pass over these rows did not reach because the recorded
`sourceType` never mentioned the list.

WHAT THIS CHANGES AND WHAT IT DOES NOT

Nothing about the verdict: all three were `confirmed` and stay `confirmed`. What changes is the
recorded evidence — the same source, read further — so the row stops resting on a statement about
the container and starts resting on a list containing the card. The original observation is kept
and the new sentence is appended beside it.

It is also not a new source. No fetch, no new provider, no new tier; the URL is the one already
cited. The finding was that the page said more than the row recorded.

    python verification/passes/ba20_halfdeck_list_20260809.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UNITS = ROOT / "verification" / "units.json"

MARKER = "HALF-DECK LIST 2026-08-09"
TARGETS = ("U0294", "U0295", "U0297")

ADDITION = (
    f" {MARKER}: the same article carries the Mewtwo Deck half-deck list, a closed and fixed list, "
    "and this card is a row in it — \"halfdecklist/nmentry|50/68|TCG ID|Hidden Fates|Snorlax|50 … "
    "|Colorless||2\", two copies per deck. Every language edition of the product contains the same "
    "fixed deck, so the language statement above reaches this card rather than only its box. Read "
    "from the article already cited, 2026-08-09; no new source."
)

SOURCE_TYPE = (
    'Bulbapedia (fan wiki), product article, half-deck list + "In other languages" table'
)


def main() -> int:
    units = json.loads(UNITS.read_text(encoding="utf-8"))
    by_id = {unit["unitId"]: unit for unit in units}

    updated = 0
    for unit_id in TARGETS:
        unit = by_id.get(unit_id)
        if unit is None:
            print(f"missing {unit_id}", file=sys.stderr)
            return 1
        if unit["status"] != "confirmed":
            print(f"{unit_id} is {unit['status']}, expected confirmed", file=sys.stderr)
            return 1
        if unit["setCode"] != "BA20" or str(unit["number"]) != "MWT":
            print(f"{unit_id} is not BA20 MWT", file=sys.stderr)
            return 1
        if MARKER in unit["evidence"]:
            continue
        unit["evidence"] = unit["evidence"].rstrip() + ADDITION
        unit["sourceType"] = SOURCE_TYPE
        updated += 1

    UNITS.write_text(json.dumps(units, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"recorded the half-deck list behind {updated} Battle Academy 2020 confirmation(s)")
    for unit_id in TARGETS:
        unit = by_id[unit_id]
        print(f"  {unit_id}  {unit['setCode']} {unit['number']} {unit['language']:8} "
              f"still confirmed, now resting on a closed card list")
    return 0


if __name__ == "__main__":
    sys.exit(main())

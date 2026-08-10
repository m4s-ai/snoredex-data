#!/usr/bin/env python3
"""Two more own-edition card lists the previous pass did not reach (#137).

`closed_card_lists_20260810.py` recorded thirty-two set-level confirmations whose cited article
already carried a closed card list containing the card. It worked from the report's
`setLevelConfirmationsThatDoNotCarry` queue, and so it never saw these two: both are `Ultra Rare`,
which the report declines to answer from rarity alone, so they sat in the separate
`setLevelConfirmationsNeedingSetSize` list instead. The miss is in which list was read, not in the
argument.

Both are the stronger `own-edition` case. The cited article **is** the Simplified Chinese set's own
article, so its set list is a Simplified Chinese card list, and the row reaches the card with no
inference about how a set localizes in between. Each unit's own `evidence` already quoted the row;
only `sourceType` — the field `evidence_semantics.py` classifies on — named the container alone.

Neither row needs a printed set size, and that is the point of recording them this way. `CS1aC 188`
and `CSM2cC 170` are both secret-numbered, so a set size would place them outside the numbered run
and the language statement would not reach them. The card list does, because it is a list of this
edition's cards rather than a statement about the edition.

No page was re-read for a claim, no provider changes, no verdict moves.

    python verification/passes/own_edition_card_lists_20260810.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UNITS = ROOT / "verification" / "units.json"

MARKER = "CARD LIST 2026-08-10"

# unitId -> the verbatim set-list row read from the cited Simplified Chinese set article
ROWS: dict[str, str] = {
    "U0608": ("{{Setlist/entry|188/135|D|[[Snorlax V (Dynamax Clash Thunder 188)|Snorlax]]"
              "{{TCGV}}|Colorless||SR}}"),
    "U0635": ("{{Setlist/entry|170/150|C|[[Eevee & Snorlax-GX (Shining Synergy Summon 170)|"
              "Eevee & Snorlax]]{{TT GX}}|Colorless||SR}}"),
}

REASON = (
    "The cited article is this edition's own article, so its card list is a card list in this "
    "language; the row reaches the card directly, with no inference about the set in between. "
    "The card is secret-numbered, so the set's language release would not have reached it on its "
    "own — the list does."
)


def main() -> int:
    units = json.loads(UNITS.read_text(encoding="utf-8"))
    by_id = {unit["unitId"]: unit for unit in units}

    updated = 0
    for unit_id, row in ROWS.items():
        unit = by_id.get(unit_id)
        if unit is None:
            print(f"missing {unit_id}", file=sys.stderr)
            return 1
        if unit["status"] != "confirmed":
            print(f"{unit_id} is {unit['status']}, expected confirmed", file=sys.stderr)
            return 1
        if MARKER in unit["evidence"]:
            continue
        unit["evidence"] = unit["evidence"].rstrip().rstrip(".") + (
            f". {MARKER}: the cited page carries a closed card list containing this card — "
            f"\"{row}\". {REASON} Read from the article already cited; no new source, no change "
            f"of provider, and the verdict is unchanged."
        )
        unit["sourceType"] = unit["sourceType"].rstrip().rstrip(",") + ", card list row"
        updated += 1

    UNITS.write_text(json.dumps(units, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"recorded the card list behind {updated} confirmation(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

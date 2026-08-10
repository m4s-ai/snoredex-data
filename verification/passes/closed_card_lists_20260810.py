#!/usr/bin/env python3
"""Record the card lists that were already on the cited pages (#137).

Thirty-two set-level confirmations cited a product or set article and were reported as resting on
an inference that cannot reach the card: the article says the product exists in language L, and the
card is a promo, a deck-fixed card or a secret-numbered card that a language release does not reach
by itself.

Every one of those articles carries a **closed card list containing this exact card**, and in most
cases the unit's own `evidence` already quoted the row. What was missing was in `sourceType`, which
named only the container — so `evidence_semantics.py`, which classifies on `sourceType`, could not
see the list. This pass records the list. It is bookkeeping catching up with evidence already
gathered, not a new source: no page was re-read for a claim, no provider changes, no verdict moves.

TWO GROUPS, TWO DIFFERENT ARGUMENTS

`own-edition` — the cited article **is** the article of the edition claimed. Every Simplified
Chinese `(ATCG)` article is its own set's article, so its set list is a Simplified Chinese card
list. The row is card-level evidence in the language claimed, with no inference in between. This is
the stronger of the two and needs no assumption about how products localize.

`fixed-product` — the article is the source product's, and it names the language editions
separately. A fixed product (a deck, a starter set, a gift box) has the same contents in every
language edition, so a closed list plus a language statement reaches the card. This is exactly the
Prize Pack argument already written into `evidence_semantics.py`, and the Battle Academy 2020 pass
of 2026-08-09 applied it to a half-deck list. Each row below quotes both halves.

THE FOUR PREFIXED NUMBERS, STATED RATHER THAN ASSUMED

`CSMPC h009`, `CSVH4C p006`, `CSVH4C a003` and `CSVH1C a001` carry a Cardmarket prefix that the wiki
does not use. The reading is consistent across two independent articles: `a` is the Happy Set
*Modification Pack* (`a003` -> Modification Pack 3, `a001` -> Modification Pack 1), `p` is the
Happy Set *Reward Pack* (`p006` -> Reward Pack 6), and `h` is the Battle Party Set *Metal* subset
(`h009` -> Metal 9). It is written here so a reader can disagree with it, which is the point.

    python verification/passes/closed_card_lists_20260810.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UNITS = ROOT / "verification" / "units.json"

MARKER = "CARD LIST 2026-08-10"

# unitId -> (group, the verbatim list row read from the cited article's wikitext)
ROWS: dict[str, tuple[str, str]] = {
    # own-edition: a Simplified Chinese set article's own set list
    "U0754": ("own-edition", "{{Setlist/entry|093/177|G|{{TCG ID|Battle Party: Shared Dream|Snorlax|93}}|Colorless}}"),
    "U0766": ("own-edition", "{{Setlist/entry|122/207|F|{{TCG ID|Battle Party: Shining Dream|Snorlax|122}}|Colorless}}"),
    "U0193": ("own-edition", "{{Setlist/entry|169/151|G|{{TCG ID|Collection 151|Snorlax|169}}|Colorless||S}}"),
    "U0241": ("own-edition", "{{Setlist/entry|112/135|D|[[Snorlax VMAX (Dynamax Clash Thunder 112)|Snorlax]]{{VMAX}}|Colorless||RRR}}"),
    "U0543": ("own-edition", "{{Setlist/entry|207/135|D|[[Snorlax VMAX (Dynamax Clash Thunder 207)|Snorlax]]{{VMAX}}|Colorless||HR}}"),
    "U0514": ("own-edition", "{{halfdecklist/entry|009/024|D|[[Snorlax V (Dynamax Clash Deck Building Box 9)|Snorlax]]{{TCGV}}|Colorless||0-1}}"),
    "U0581": ("own-edition", "{{Setlist/entry|152/207|D|{{TCG ID|Dynamax Clash V Starter Deck|Snorlax|152}}|Colorless}}"),
    "U0650": ("own-edition", "{{Setlist/entry|097/153|E|{{TCG ID|Gallant Galaxy V Starter Deck|Snorlax|97}}|Colorless}}"),
    "U0765": ("own-edition", "{{Setlist/entry|098/153|E|{{TCG ID|Gallant Galaxy V Starter Deck|Snorlax|98}}|Colorless}}"),
    "U0559": ("own-edition", "{{Setlist/entry|054/045|C|[[Eevee & Snorlax-GX (Golden Energy 54)|Eevee & Snorlax]]{{TT GX}}|Colorless}}"),
    "U0588": ("own-edition", "{{setlist/entry|109/049|G|{{TCG ID|Journey Theme Pack|Snorlax|109}}|Colorless}}"),
    "U0431": ("own-edition", "{{Setlist/entry|018/066|F|{{TCG ID|Peripheral Collection Gift Box|Snorlax|18}}|Colorless}}"),
    "U0513": ("own-edition", "{{Setlist/entry|010/012|D|{{TCG ID|Pokémon Card Display Set Gift Box|Snorlax|10}}|Colorless}}"),
    "U0614": ("own-edition", "{{Setlist/entry|117/170|E|{{TCG ID|Primordial Arts V Starter Deck|Snorlax|117}}|Colorless}}"),
    "U0430": ("own-edition", "{{Setlist/entry|171/150|C|[[Eevee & Snorlax-GX (Shining Synergy Summon 171)|Eevee & Snorlax]]{{TT GX}}|Colorless||SR}}"),
    "U0613": ("own-edition", "{{Setlist/entry|213/342|C|{{TCG ID|Shining Synergy GX Starter Deck|Snorlax|213}}|Colorless}}"),
    "U0592": ("own-edition", "{{Setlist/entry|142/115|D|{{TCG ID|Vivid Portrayals Obsidian|Snorlax|142}}|Colorless||UR}}"),
    "U0675": ("own-edition", "{{halfdecklist/entry|009/024|C|{{TCG ID|Battle Party Set Metal|Snorlax|9}}|Colorless||1}} (Cardmarket's h-prefix names the Metal subset)"),
    "U0767": ("own-edition", "{{setlist/entry|006/006|H|{{TCG ID|Happy Set Reward Pack|Snorlax ex|6|Snorlax}}{{ex}}|Colorless}} (Cardmarket's p-prefix names the Reward Pack)"),
    "U0768": ("own-edition", "{{setlist/entry|003/023|H|{{TCG ID|Happy Set Modification Pack|Snorlax|3}}|Colorless}} (Cardmarket's a-prefix names the Modification Pack)"),
    "U0612": ("own-edition", "{{Setlist/entry|001/023|F|{{TCG ID|Happy Set Modification Pack|Snorlax|1}}|Colorless}} (Cardmarket's a-prefix names the Modification Pack)"),
    # fixed-product: the source product's closed list, beside the article's own language statement
    "U0646": ("fixed-product", "{{halfdecklist/entry|046/066|H|{{TCG ID|Battle Academy|Snorlax|46}}|Colorless||1}}"),
    "U0639": ("fixed-product", "{{halfdecklist/entry|038/053|E|{{TCG ID|Sword & Shield Family Pokémon Card Game|Snorlax|38}}|Colorless||1}}"),
    "U0680": ("fixed-product", "{{Halfdecklist/nmentry|047/072|{{TCG ID|Starter Pack|Snorlax|47}}|Colorless||1}}"),
    "U0586": ("fixed-product", "{{Halfdecklist/nmentry|026/039|{{TCG ID|Beginning Set|Snorlax|26}}|Colorless||1}}"),
    "U0440": ("fixed-product", "{{halfdecklist/nmentry|016/034|{{TCG ID|Venusaur Deck|Snorlax|16}}|Colorless||1}}"),
    "U0441": ("fixed-product", "{{halfdecklist/nmentry|016/032|{{TCG ID|Venusaur Deck|Snorlax|16}}|Colorless||1}}"),
    "U0651": ("fixed-product", "{{Setlist/entry|341/414|E|{{TCG ID|Start Deck 100|Snorlax|341}}|Colorless||}}"),
    "U0653": ("fixed-product", "{{Setlist/entry|341/414|E|{{TCG ID|Start Deck 100|Snorlax|341}}|Colorless||}}"),
    "U0655": ("fixed-product", "{{Setlist/entry|342/414|E|{{TCG ID|Start Deck 100|Snorlax|342}}|Colorless||}}"),
    "U0657": ("fixed-product", "{{Setlist/entry|342/414|E|{{TCG ID|Start Deck 100|Snorlax|342}}|Colorless||}}"),
    "U0770": ("fixed-product", "{{halfdecklist/entry|008/024|E|{{TCG ID|Start Deck 100 CoroCoro Comic Version|Snorlax|8}}|Colorless||1}}"),
}

REASON = {
    "own-edition": (
        "The cited article is this edition's own article, so its card list is a card list in this "
        "language; the row reaches the card directly, with no inference about the set in between."
    ),
    "fixed-product": (
        "The cited article carries the source product's closed card list beside its own statement "
        "of which language editions exist. A fixed product has the same contents in every language "
        "edition, so the list reaches the card the way a Prize Pack article does."
    ),
}


def main() -> int:
    units = json.loads(UNITS.read_text(encoding="utf-8"))
    by_id = {unit["unitId"]: unit for unit in units}

    updated = 0
    for unit_id, (group, row) in ROWS.items():
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
            f"\"{row}\". {REASON[group]} Read from the article already cited; no new source, no "
            f"change of provider, and the verdict is unchanged."
        )
        unit["sourceType"] = unit["sourceType"].rstrip().rstrip(",") + ", card list row"
        updated += 1

    UNITS.write_text(json.dumps(units, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"recorded the card list behind {updated} confirmation(s)")
    for group in ("own-edition", "fixed-product"):
        members = [uid for uid, (kind, _) in ROWS.items() if kind == group]
        print(f"  {group:14} {len(members)} row(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

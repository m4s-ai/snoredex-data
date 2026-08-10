#!/usr/bin/env python3
"""Close the promo gap the Indonesian set index left open (#138).

`seed_indonesia_set_index_20260810.py` indexed 78 published boosters and starter decks and said
plainly that promotional cards were outside its scope, because the country article documents them
in prose rather than in a coded table. The owner supplied the four articles that do carry them:
`SM-P`, `S-P` and `SV-P Promotional cards (ITCG)`, plus `Promo Card Pack 25th Anniversary Edition`.

Eight Indonesian Snorlax promos are documented across them. Three are already in this repository and
five are not, and the split between what is admitted and what is held falls exactly on the evidence.

ALREADY HELD, AND WORTH SAYING SO

`SV-P/ID` 117, 278 and 286 are confirmed units already — 117 twice, from an inspected specimen.
Reporting them as newly discovered would have been a bookkeeping error dressed as a finding. What is
new about them is a coverage fact, below.

ADMITTED — FOUR `S-P` PROMOS AT TIER 1

    030/S-P  Snorlax V   Sword & Shield box purchase campaign
    052/S-P  Snorlax     Indomaret booster pack purchase, May 2021
    100/S-P  Snorlax     INACO Mini Jelly Konnyaku, Pokémon Special Edition
    356/S-P  Snorlax     Chatime promotional card campaign, December 2022

Each has a card page in the publisher's Asia database *and* a set-list row on Bulbapedia's
`S-P Promotional cards (ITCG)` naming its distribution campaign, so each is corroborated by a second
provider about this unit rather than about a neighbour. They meet ADR-0001 D5: a tier-1 publisher
record, admitted for language and identity, finish left `pending`.

Their set code needs no badge read. It is printed inside the collector number — `030/S-P` — which is
the one case where the filename lesson of 2026-08-10 does not apply.

HELD — ONE, AND THE REASON IS THE TIER

`166/SM-P`, Eevee & Snorlax-GX, distributed through an Indomaret booster-pack purchase between
25 July and 31 August 2020, is documented by Bulbapedia and by nothing else here. The publisher's
Asia database does not index it. Bulbapedia is tier 2; D5 requires tier 1, and stretching it because
the row looks convincing is how a decision stops meaning anything. Held.

THE COVERAGE FACT WORTH MORE THAN THE ROWS

The Asia database **does not index four of the eight** Indonesian promos Bulbapedia documents —
`166/SM-P`, and `117`, `278`, `286` of `SV-P` — and it was searched under five keywords across five
pages per keyword, always returning the same 31 cards. Three of those four are cards this repository
already holds, which is what makes the gap measurable rather than speculative: the tier-1 source is
demonstrably incomplete for Indonesian promos, against cards known to exist.

So the earlier finding stands and hardens. `pokemon-card-asia` carries no absence scope and must not
acquire one: a search that misses cards we can independently prove exist cannot bound an absence.

    python verification/passes/indonesia_promo_prints_20260810.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
PRINTS = ROOT / "verification" / "source_first_prints.json"

ASIA = "https://asia.pokemon-card.com/id/card-search/detail"
BULBA_SP = "https://bulbapedia.bulbagarden.net/wiki/S-P_Promotional_cards_(ITCG)"
BULBA_SMP = "https://bulbapedia.bulbagarden.net/wiki/SM-P_Promotional_cards_(ITCG)"

# (number, detailId, localName, cardName, regulationMark, campaign)
ADMIT = [
    ("030", "5067", "Snorlax V", "Snorlax V", "D",
     "Sword & Shield box purchase campaign"),
    ("052", "5089", "Snorlax", "Snorlax", "D",
     "Indomaret booster pack purchase, May 2021"),
    ("100", "5137", "Snorlax", "Snorlax", "D",
     "INACO Mini Jelly Konnyaku, Pokémon Special Edition"),
    ("356", "6671", "Snorlax", "Snorlax", "E",
     "Chatime promotional card campaign, December 2022"),
]

HELD: list[dict[str, Any]] = [
    {
        "locality": "ID",
        "language": "Indonesian",
        "localSetCode": "SM-P",
        "localNumber": "166",
        "specimenId": None,
        "cardName": "Eevee & Snorlax-GX",
        "sourceUrl": BULBA_SMP,
        "providerId": "bulbapedia",
        "reason": (
            "Bulbapedia's SM-P Promotional cards (ITCG) set list carries "
            "\"166/SM-P … Eevee & Snorlax-GX … Indomaret booster pack purchase "
            "(July 25-August 31, 2020)\", regulation mark C. That is a card-level row naming the "
            "card, the number and its distribution campaign, and it is the only source here for "
            "this printing: the publisher's Asia database does not index it under any of five "
            "keywords. Bulbapedia is tier 2 and ADR-0001 D5 admits a catch-up code on a tier-1 "
            "publisher record, so this is held rather than admitted. Stretching D5 because a row "
            "looks convincing is how a decision stops meaning anything."
        ),
    },
]


def main() -> int:
    document = json.loads(PRINTS.read_text(encoding="utf-8"))
    existing = {entry["printId"] for entry in document["prints"]}

    added = 0
    for number, detail_id, local_name, card_name, regulation, campaign in ADMIT:
        print_id = f"ID:S-P:{number}:base"
        if print_id in existing:
            continue
        document["prints"].append({
            "printId": print_id,
            "locality": "ID",
            "localSetCode": "S-P",
            "localNumber": number,
            "variant": "base",
            "language": "Indonesian",
            "script": "Latn",
            "name": local_name,
            "cardName": card_name,
            "catchUpOf": None,
            "specimenId": None,
            "providerId": "pokemon-card-asia",
            "sourceUrl": f"{ASIA}/{detail_id}/",
            "corroborated": True,
            "markAssetUrl": None,
            "cardImageUrl": f"https://asia.pokemon-card.com/id/card-img/id{int(detail_id):08d}.png",
            "evidence": (
                f"The Pokémon Company's Asia card database serves this card at "
                f"/id/card-search/detail/{detail_id}/ as \"{local_name}\", collector number "
                f"{number}/S-P, regulation mark {regulation}. The set code needs no badge read "
                f"here: it is printed inside the collector number, the one case where the "
                f"mark-filename trap does not apply. Corroborated by Bulbapedia's "
                f"S-P Promotional cards (ITCG) set list, whose row for {number}/S-P names the same "
                f"card and its distribution — {campaign} — so a second provider speaks about this "
                f"printing rather than about a neighbouring one. Admitted under ADR-0001 D5 for "
                f"language and identity only; no finish is asserted. Retrieved 2026-08-10. "
                f"{BULBA_SP}"
            ),
        })
        added += 1

    held_keys = {(e.get("locality"), e.get("localNumber")) for e in document.get("held", [])}
    held_added = 0
    for entry in HELD:
        if (entry["locality"], entry["localNumber"]) in held_keys:
            continue
        document.setdefault("held", []).append(entry)
        held_added += 1

    document["meta"]["counts"] = {
        "admitted": len(document["prints"]),
        "held": len(document.get("held", [])),
    }
    PRINTS.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"admitted {added} Indonesian promo print(s), held {held_added}; "
          f"store now {document['meta']['counts']}")
    print("  SV-P/ID 117, 278 and 286 were already confirmed units and are not touched")
    print("  the Asia database indexes none of those three, nor 166/SM-P: a tier-1 source "
          "demonstrably incomplete against cards known to exist, so it may never carry absence")
    return 0


if __name__ == "__main__":
    sys.exit(main())

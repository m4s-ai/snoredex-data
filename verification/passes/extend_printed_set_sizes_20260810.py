#!/usr/bin/env python3
"""Eight more printed set sizes, for the sets the queue still judges by rarity (#146, #137).

`seed_printed_set_sizes_20260810.py` recorded six sizes and emptied the `needs-set-size` queue. It
did not reach the rest of the set-level queue, which is still decided by the harvest rarity — the
proxy the set size exists to replace. These eight are the sets carrying the remaining rows.

    CL      95   Call of Legends
    FLF    106   Flashfire; the Japanese Wild Blaze half is 80
    m2a    193   MEGA Dream ex
    s10a    71   Dark Phantasma
    s5a     70   Peerless Fighters (Cardmarket calls this set Matchless Fighters)
    s8b    184   VMAX Climax
    sv2a   165   Pokémon Card 151; the English 151 set is also 165
    sv4a   190   Shiny Treasure ex; the English Paldean Fates set is 91

Same fact, same place, same format as the seed pass: the denominator printed beside the collector
number, read from the set list of the article carrying the set, with both numberings noted where
they differ.

WHAT THIS MOVES, AND IN WHICH DIRECTION

Three rows move to `carries`, all of them cases where the rarity word said secret and the set's own
set list says otherwise: `m2a 136` of 193, `s8b 126` of 184 and `sv4a 145` of 190 all carry the
harvest rarity `Fixed`, which reads "deck, kit and half-deck cards" — but each sits in its set's
main set list, inside the printed denominator.

Nine rows keep `does-not-carry` and gain a recorded reason for it: `sv2a 181` of 165, `s10a 077` of
71 in four languages, `sv4a 310` of 190, and `s5a 93` of 70 in four languages are all numbered above
their set size. They were already on the queue; they are now there because of a denominator rather
than a rarity tier's reputation.

`CL` and `FLF` are recorded for a different reason and change nothing by themselves — see the guard
this pass depends on in `evidence_semantics.py`. Their rows are promo printings, and a promo's
collector number is the number of the run card it reprints, so the size must not reach them.

    python verification/passes/extend_printed_set_sizes_20260810.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
RETRIEVED = "2026-08-10"
BULBA = "https://bulbapedia.bulbagarden.net/wiki/"

# setCode -> (printedSetSize, numbering, sourcePage, basis)
SIZES: dict[str, tuple[int, str, str, str]] = {
    "CL": (95, "western", "Call_of_Legends_(TCG)",
           "the set list runs to 95 in the English numbering the Setlist/nmentry rows use"),
    "FLF": (106, "western", "Flashfire_(TCG)",
            "106 in the English numbering; the Japanese Wild Blaze half on the same page is 80"),
    "m2a": (193, "japanese", "MEGA_Dream_ex_(TCG)",
            "the set list numbers every row out of 193"),
    "s10a": (71, "japanese", "Dark_Phantasma_(TCG)",
             "the set list numbers every row out of 71"),
    "s5a": (70, "japanese", "Peerless_Fighters_(TCG)",
            "the set list numbers every row out of 70; Cardmarket files this set as Matchless "
            "Fighters, which is why the index search for it returns nothing"),
    "s8b": (184, "japanese", "VMAX_Climax_(TCG)",
            "the set list numbers every row out of 184"),
    "sv2a": (165, "japanese", "151_(TCG)",
             "Pokémon Card 151 in the Japanese numbering; the English 151 set is also 165, so "
             "both numberings agree here"),
    "sv4a": (190, "japanese", "Paldean_Fates_(TCG)",
             "Shiny Treasure ex in the Japanese numbering; the English Paldean Fates set on the "
             "same page is 91"),
}


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:12].upper()}"


def main() -> int:
    document = json.loads(SOURCES.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = document["sourceRecords"]
    existing = {row["providerRecordKey"] for row in records
                if row["sourceKind"] == "printed-set-size-record"}

    added = 0
    for set_code, (size, numbering, page, basis) in sorted(SIZES.items()):
        if set_code in existing:
            continue
        records.append({
            "sourceRecordId": stable_id("SET-SRC-SIZE", set_code),
            "sourceKind": "printed-set-size-record",
            "provider": "bulbapedia",
            "providerRecordKey": set_code,
            "retrieved": RETRIEVED,
            "sourceUrl": BULBA + page,
            "raw": {
                "legacySetCode": set_code,
                "printedSetSize": size,
                "numbering": numbering,
                "basis": (
                    f"The denominator printed beside the collector number, read from the article's "
                    f"set list: {basis}. Not inferred from a rarity, a name or a card count — a "
                    f"card is inside the numbered run when its number is within this size in its "
                    f"own numbering, and Bulbapedia carries both numberings on one page."
                ),
            },
        })
        added += 1

    records.sort(key=lambda item: item["sourceRecordId"])
    document["meta"]["counts"]["sourceRecords"] = len(records)
    document["meta"]["counts"]["printedSetSizeRecords"] = sum(
        1 for row in records if row["sourceKind"] == "printed-set-size-record")
    SOURCES.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"added {added} printed-set-size record(s); "
          f"{document['meta']['counts']['printedSetSizeRecords']} total")
    for set_code, (size, numbering, _p, _b) in sorted(SIZES.items()):
        print(f"  {set_code:8} {size:>4}  ({numbering})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

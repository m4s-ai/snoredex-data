#!/usr/bin/env python3
"""Record printed set sizes so run membership is computed, not guessed (#146, #137).

`evidence_semantics.py` reports six confirmations as `needs-set-size`: Cardmarket's `Ultra Rare`
covers both the modern Full Art, secret in some locales, and the EX-era `ex` and DP-era LV.X cards,
which were numbered inside the set. The word cannot separate them; the set's printed size can, and
this project recorded it nowhere. That gap was filed as a #146 requirement on 2026-08-10 and this
is the instalment that closes it for the six.

The size is not inferred from a rarity or a name. It is the **denominator printed beside the
collector number**, read from the set list of the article that carries the set, which is the same
fact the source-first local-set profiles already store for the Asian catch-up codes.

    RR      111   Rising Rivals; the set list runs to 111/111
    TRR     109   EX Team Rocket Returns; 109 in the English numbering, 84 Japanese
    s1H      60   Japanese Shield half of Sword & Shield
    sm9      95   Tag Bolt, Japanese numbering; 181 in the English Team Up
    CS1aC   135   Dynamax Clash (ATCG), from its own set list
    CSM2cC  150   Shining Synergy (ATCG), from its own set list

WHY BOTH NUMBERINGS ARE STORED WHERE THEY DIFFER

`TRR` and `sm9` carry two, because Bulbapedia's articles carry both — `{{Setlist/nmentry}}` rows use
the English collector number and `{{Setlist/entry}}` rows the Japanese one, a trap `RESUME.md`
already records. A row is inside the run if its number is within the size **of its own numbering**,
so storing one and discarding the other would decide four rows on the wrong denominator.

WHAT THIS RESOLVES, AND IN WHICH DIRECTION

Two rows move to `carries`: `RR 111` Italian is the last card of a 111-card set, and `TRR 104`
Portuguese sits inside 109 — both the EX/DP-era pattern where `Ultra Rare` means a card numbered
in the run. Four move to `does-not-carry`: `s1H 66` of 60, `sm9 106` of 95, `CS1aC 188` of 135 and
`CSM2cC 170` of 150 are all secret-numbered above their set size.

So the undecidable queue empties and the unsound queue grows by four. That is a queue being
resolved rather than a regression, and the aggregate improves: 25 confirmations whose inference did
not reach the card become 23. `N17` is re-anchored on that aggregate rather than on one half of it,
because two counters for one queue is how a real improvement reads as a loss.

    python verification/passes/seed_printed_set_sizes_20260810.py
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
    "RR": (111, "western", "Rising_Rivals_(TCG)",
           "the set list runs to 111/111; the Japanese Bonds to the End of Time half is 90"),
    "TRR": (109, "western", "EX_Team_Rocket_Returns_(TCG)",
            "109 in the English numbering the Setlist/nmentry rows use; 84 in the Japanese rows"),
    "s1H": (60, "japanese", "Sword_%26_Shield_(TCG)",
            "the Japanese Shield half of the Sword & Shield pair; the English SSH set is 202"),
    "sm9": (95, "japanese", "Team_Up_(TCG)",
            "Tag Bolt in the Japanese numbering; the English Team Up set is 181"),
    "CS1aC": (135, "simplified-chinese", "Dynamax_Clash_(ATCG)",
              "the Simplified Chinese set list numbers every row out of 135"),
    "CSM2cC": (150, "simplified-chinese", "Shining_Synergy_(ATCG)",
               "the Simplified Chinese set list numbers every row out of 150"),
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

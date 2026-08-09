#!/usr/bin/env python3
"""Resolve the two set codes that held SPEC-0011 and SPEC-0015 back (#134, after D1).

Both prints were held because their own specimen records declined to assert a set glyph, and a
print is keyed by its local set code. The owner supplied a cross-check for each. Both hold, by
different routes, and the routes are worth writing down because they generalise.

SPEC-0011 — `sc1a F 127/154`, resolved from Bulbapedia

    Bulbapedia's "Sword & Shield (ATCG)" page is the Asian catch-up expansion this card belongs
    to. Its set list carries `127/154 | D | Snorlax | Colorless | U` — number, set size, rarity
    and regulation mark all matching the specimen.

    The set code is not text anywhere on that page; the string "sc1" does not occur in the
    wikitext at all. Bulbapedia calls the two halves "Set A" and "Set B" and puts the code in the
    *set symbol image*, which has to be fetched and read: `SetSymbolSword Shield Set A.png`
    renders `sc1a F`, and `Set B.png` renders `sc1b F`. The specimen's own glyph is that same
    black badge with the boxed F.

    So the code is corroborated by a second provider, not guessed.

SPEC-0015 — `scD F 111/159`, resolved by re-reading the photograph

    The specimen record says the glyph "is not legible — it reads as a two-or-three character code
    ending in F and is deliberately not asserted". That was an assessment of a downscaled view, not
    a property of the image. The stored photograph is 3508x2480; cropped to the corner and enlarged
    it reads `scD F`, regulation mark `E`, `111/159`, Illus. Yuya Oka, ©2021, without ambiguity.

    The owner confirms the convention the trailing F encodes: it marks the Traditional Chinese
    release where the same set code `scD` also appears in other languages. That is why the code is
    `scD F` and not `scD`.

    Bulbapedia corroborates it by the same route as SPEC-0011, once the owner pointed at the
    right page: "Strength V Starter Deck (ATCG)" lists `111/159 | E | Snorlax | Colorless`, its
    Traditional Chinese release is October 2021 against the card's ©2021, and its set symbol image
    renders `scD F`. Even the box-art filename carries it — `SCD V Starter Deck Chinese.jpg`.

The sc1b F prints admitted by D1 gain the same Bulbapedia corroboration in passing: Set B lists
119/153 RR, 120/153 RRR, 165/153 SR and 177/153 HR, every number and rarity matching its specimen.

    python verification/passes/resolve_held_catchup_setcodes_20260809.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SPECIMENS = ROOT / "verification" / "specimens.json"
PRINTS = ROOT / "verification" / "source_first_prints.json"

BULBAPEDIA_ATCG = "https://bulbapedia.bulbagarden.net/wiki/Sword_%26_Shield_(ATCG)"
SYMBOL_A = "https://archives.bulbagarden.net/media/upload/5/5c/SetSymbolSword_Shield_Set_A.png"
SYMBOL_B = "https://archives.bulbagarden.net/media/upload/5/5b/SetSymbolSword_Shield_Set_B.png"
BULBAPEDIA_STRENGTH = "https://bulbapedia.bulbagarden.net/wiki/Strength_V_Starter_Deck_(ATCG)"
SYMBOL_SCD = ("https://archives.bulbagarden.net/media/upload/6/67/"
              "SetSymbolStrength_V_Starter_Deck_Chinese.png")

# Appended to the specimens whose recorded reading is superseded. The original observation stays;
# a correction that erases what it corrects leaves nobody able to check it.
SPECIMEN_NOTES = {
    "SPEC-0011": (
        " RESOLVED 2026-08-09: the set code recorded as unconfirmed above is confirmed as "
        "\"sc1a F\". Bulbapedia's Sword & Shield (ATCG) set list carries 127/154 Snorlax, "
        "Colorless, rarity U, regulation mark D — matching this card on every field — and that "
        f"expansion's Set A symbol image ({SYMBOL_A}) renders the code \"sc1a F\". The glyph on "
        "this card is the same black badge with a boxed F. Corroborated, no longer an "
        "identification carried on the owner's word alone."
    ),
    "SPEC-0015": (
        " RESOLVED 2026-08-09: the set glyph declared illegible above is legible in the stored "
        "photograph at full resolution (3508x2480). Cropped to the lower-left corner it reads "
        "\"scD F\", regulation mark E, \"111/159\", Illus. Yuya Oka, ©2021. The owner confirms "
        "that the trailing F marks the Traditional Chinese release of a set code that also "
        "appears in other languages, which is why the code is scD F rather than scD. The earlier "
        "note recorded a downscaled view, not a limit of the image. Corroborated by Bulbapedia's "
        "Strength V Starter Deck (ATCG), which lists 111/159 Snorlax, Colorless, regulation mark "
        "E, released in Traditional Chinese in October 2021, and whose set symbol image "
        f"({SYMBOL_SCD}) renders \"scD F\"."
    ),
}

NEWLY_ADMITTED = [
    {
        "printId": "TW:sc1a F:127/154:base",
        "locality": "TW", "localSetCode": "sc1a F", "localNumber": "127/154", "variant": "base",
        "language": "T-Chinese", "script": "Hant", "name": "卡比獸",
        "cardName": "Snorlax",
        "catchUpOf": "the Japanese s2 77 printing, per the owner's identification",
        "specimenId": "SPEC-0011",
        "providerId": "bulbapedia",
        "sourceUrl": BULBAPEDIA_ATCG,
        "corroborated": True,
        "evidence": (
            "Traditional Chinese Snorlax, HP 150, Basic, attacks 「呼喚」 (draw 2) and 「倒下」 120, "
            "Illus. Eri Yamaki, 127/154, rarity U, regulation mark D, ©2020. Bulbapedia's Sword & "
            "Shield (ATCG) set list carries 127/154 Snorlax, Colorless, rarity U, regulation mark "
            f"D. The set code is not text on that page — Bulbapedia names the halves Set A and Set "
            f"B and encodes the code in the set symbol image, and {SYMBOL_A} renders \"sc1a F\". "
            "The badge on the card (SPEC-0011) is that same glyph. Two providers agree about this "
            "printing: the Bulbapedia set list and the seller's photograph of the card."
        ),
    },
    {
        "printId": "TW:scD F:111/159:base",
        "locality": "TW", "localSetCode": "scD F", "localNumber": "111/159", "variant": "base",
        "language": "T-Chinese", "script": "Hant", "name": "卡比獸",
        "cardName": "Snorlax",
        "catchUpOf": None,
        "specimenId": "SPEC-0015",
        "providerId": "inspected-specimen",
        "sourceUrl": "https://github.com/user-attachments/assets/25528966-476a-4a82-bcaf-d9e1f76e8584",
        "corroborated": True,
        "evidence": (
            "Traditional Chinese Snorlax photographed front and back by the owner: HP 140, Basic, "
            "SINGLE STRIKE 一擊 marker, attacks 「巴掌撲擊」 30 and 「一擊衝撞」 120, Illus. Yuya "
            "Oka, ©2021. The lower-left corner reads \"scD F\", regulation mark E, \"111/159\" at "
            "full resolution — the earlier record's \"glyph not legible\" described a downscaled "
            "view. The owner confirms the trailing F marks the Traditional Chinese release of a "
            "set code that also appears in other languages. Bulbapedia's Strength V Starter Deck "
            "(ATCG) corroborates it: the deck list carries 111/159 Snorlax, Colorless, regulation "
            "mark E, its Traditional Chinese release is October 2021 against the card's ©2021, and "
            f"its set symbol image ({SYMBOL_SCD}) renders \"scD F\". Two providers agree about "
            "this printing: the owner's card and the Bulbapedia deck list."
        ),
    },
]

# Set B's list matches every sc1b F specimen on number and rarity, so each of those prints now has
# a second provider agreeing about it rather than resting on one listing photograph.
SC1B_CORROBORATION = {
    "TW:sc1b F:119/153:base": "119/153 Snorlax V, Colorless, rarity RR",
    "TW:sc1b F:120/153:base": "120/153 Snorlax VMAX, Colorless, rarity RRR",
    "TW:sc1b F:165/153:base": "165/153 Snorlax V, Colorless, rarity SR",
    "TW:sc1b F:177/153:base": "177/153 Snorlax VMAX, Colorless, rarity HR",
}


def main() -> int:
    specimen_doc = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    records = specimen_doc["specimens"] if isinstance(specimen_doc, dict) else specimen_doc
    by_id = {r["specimenId"]: r for r in records}

    for specimen_id, note in SPECIMEN_NOTES.items():
        record = by_id.get(specimen_id)
        if record is None:
            print(f"missing specimen {specimen_id}", file=sys.stderr)
            return 1
        if "RESOLVED 2026-08-09" not in record["observed"]:
            record["observed"] = record["observed"].rstrip() + note

    document = json.loads(PRINTS.read_text(encoding="utf-8"))
    admitted_ids = {entry["printId"] for entry in document["prints"]}
    for entry in NEWLY_ADMITTED:
        if entry["printId"] in admitted_ids:
            continue
        document["prints"].append(entry)
        cited = by_id[entry["specimenId"]].setdefault("citedBy", [])
        if entry["printId"] not in cited:
            cited.append(entry["printId"])

    resolved = {entry["specimenId"] for entry in NEWLY_ADMITTED}
    document["held"] = [h for h in document["held"] if h["specimenId"] not in resolved]

    for entry in document["prints"]:
        detail = SC1B_CORROBORATION.get(entry["printId"])
        if detail and not entry["corroborated"]:
            entry["corroborated"] = True
            entry["evidence"] += (
                " CORROBORATED 2026-08-09: Bulbapedia's Sword & Shield (ATCG) Set B list carries "
                f"{detail}, matching this record, and the Set B symbol image ({SYMBOL_B}) renders "
                "the code \"sc1b F\"."
            )

    document["prints"].sort(key=lambda entry: entry["printId"])
    document["meta"]["generated"] = date.today().isoformat()
    document["meta"]["counts"] = {"admitted": len(document["prints"]), "held": len(document["held"])}
    PRINTS.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SPECIMENS.write_text(json.dumps(specimen_doc, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")

    print(f"admitted {len(document['prints'])} source-first prints, "
          f"{len(document['held'])} held")
    for entry in NEWLY_ADMITTED:
        print(f"  resolved {entry['specimenId']} -> {entry['printId']}")
    corroborated = sum(1 for e in document["prints"] if e["corroborated"])
    print(f"  {corroborated} of {len(document['prints'])} now corroborated by a second provider")
    return 0


if __name__ == "__main__":
    sys.exit(main())

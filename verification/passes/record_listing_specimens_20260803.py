#!/usr/bin/env python3
"""Mint specimen records for the nine card images the owner supplied out of band (#94).

WHY THESE ARE NOT ALL "SPECIMENS THE OWNER HOLDS"

The images were attached to issues #87, #89 and #91 as the evidence behind adjudications already
recorded. This session could never fetch them — the agent proxy refuses GitHub's attachment
namespace — so the owner re-sent them directly and every one has now been examined here.

Examining them changed the filing. Only three are photographs of cards in the owner's hands. The
rest carry a seller's or a database's watermark, and a shop's product photo is a different class of
evidence from a card someone owns:

  * FOSI TCG STUDIO / Shopee / other shop watermarks -> `heldBy: "third-party seller"`.
    CLAUDE.md rule 1 already has this category: a listing photograph is filed as a SPEC record
    rather than a bare link, because listings are deleted and the observation has to outlive them.
  * A "SAMPLE" overlay is not a photograph of a printed card at all — it is a pre-release or
    database sample image, so it is recorded as one and not as an inspection.

Grading a claim by what it rests on rather than by the strongest thing beside it is #64's lesson.
"Nine owner specimens" would have been the comfortable summary and it would have been false.

WHAT THEY DO AND DO NOT PROVE

None of these cards is in `snorlax_cards.json`. They are the *other product* — the Traditional
Chinese catch-up set printings and the Indonesian SV-P promos that the adjudications point to when
they say the card exists but not as the claimed product. So no unit cites them: a unit citing one
would be asserting that `s1H 45` exists in Traditional Chinese, which is exactly the claim the
owner ruled against. Check S8 only constrains a specimen that a unit cites, so these stand as
free-standing observations, referenced from the adjudication rationale instead.

Two set codes are read from low-resolution images and are flagged in `observed` rather than
asserted: SPEC-0011 and SPEC-0015. The card numbers on both are legible; the set glyphs are not.

Idempotent: re-running adds nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECIMENS = ROOT / "verification" / "specimens.json"
RECORDED_AT = "2026-08-03"

SELLER = "third-party seller"
OWNER = "collection owner"

# specimenId, setCode, number, variant, language, heldBy, inspectedFrom, observed
RECORDS = [
    ("SPEC-0007", "sc1b F", "120/153", "base", "T-Chinese", SELLER, "listing photograph",
     "Traditional Chinese Snorlax VMAX read off a seller's listing image (watermark \"佛系工作室 / "
     "FOSI TCG STUDIO\"): \"卡比獸VMAX\", HP 340, Colorless, evolves from 卡比獸V, attack "
     "「超極巨自由墜落」 60+, Illus. aky CG Works, \"sc1b F\" with regulation mark D, \"120/153\", "
     "rarity RRR, ©2020. This is the Traditional Chinese counterpart of the Japanese s1H 46 "
     "printing, released in the sc1b catch-up set rather than as an s1H card."),
    ("SPEC-0008", "sc1b F", "177/153", "base", "T-Chinese", SELLER, "listing photograph",
     "Traditional Chinese Snorlax VMAX rainbow rare read off a watermarked seller's listing image: "
     "\"卡比獸VMAX\", HP 340, attack 「超極巨自由墜落」 60+, Illus. aky CG Works, \"sc1b F\" with "
     "regulation mark D, \"177/153\", rarity HR, ©2020. Secret-numbered above the 153-card set "
     "size, which is the hyper-rare slot: the counterpart of Japanese s1H 70."),
    ("SPEC-0009", "sc1b F", "119/153", "base", "T-Chinese", "publisher or database",
     "sample image",
     "Traditional Chinese Snorlax V read off an image overlaid with a \"SAMPLE\" watermark, so this "
     "is a pre-release or database sample rather than a photograph of a printed card: \"卡比獸V\", "
     "HP 220, attacks 「吞下」 60 and 「摔下」 170, Illus. Masakazu Fukuda, \"sc1b F\" with "
     "regulation mark D, \"119/153\", rarity RR, ©2020. The owner identifies this as the "
     "Traditional Chinese equivalent of Japanese s1H 45."),
    ("SPEC-0010", "sc1b F", "165/153", "base", "T-Chinese", SELLER, "listing photograph",
     "Traditional Chinese Snorlax V full art read off a watermarked seller's listing image: "
     "\"卡比獸V\", HP 220, attacks 「吞下」 60 and 「摔下」 170, Illus. aky CG Works, \"sc1b F\" with "
     "regulation mark D, \"165/153\", rarity SR, ©2020. Secret-numbered above the 153-card set "
     "size. The owner identifies this as the Traditional Chinese equivalent of Japanese s1H 66."),
    ("SPEC-0011", "sc1a F", "127/154", "base", "T-Chinese", SELLER, "listing photograph",
     "Traditional Chinese Snorlax read off a Shopee listing image (watermark \"W1111 賣可尋\"): "
     "\"卡比獸\", HP 150, Basic, attacks 「呼喚」 (draw 2 cards) and 「倒下」 120, Illus. Eri Yamaki, "
     "\"127/154\", rarity U, regulation mark D, ©2020. The card number is legible; the set glyph is "
     "not fully legible at this resolution and is recorded as sc1a F on the owner's identification "
     "of this as the Traditional Chinese equivalent of Japanese s2 77 — treat the set code as "
     "unconfirmed."),
    ("SPEC-0012", "SV-P", "117", "base", "Indonesian", OWNER, "photograph",
     "Indonesian Snorlax promo, still sealed in its promo wrapper, photographed by the owner: "
     "\"Snorlax\", HP 150, Basic, Ability \"Kemaruk\", attack \"Tekanan Gedebuk\" 130, "
     "\"#0143 Pokémon Tidur\", Illus. HYOGONOSUKE, \"117/SV-P\", PROMO, regulation mark G, ©2024. "
     "Indonesian-language text throughout. This is the promo release the owner cites when ruling "
     "that the Indonesian 151 mirrors exist as SV-P promos rather than as xsv2a 143 printings."),
    ("SPEC-0013", "SV-P", "117", "base", "Indonesian", OWNER, "photograph",
     "Two sealed Indonesian \"117/SV-P\" Snorlax promos photographed side by side by the owner. The "
     "left copy is non-holo; the right copy carries a Poké Ball mirror foil pattern across the "
     "whole card face, the pattern plainly visible over the text box and the lower border. Same "
     "card text as SPEC-0012 (Ability \"Kemaruk\", \"Tekanan Gedebuk\" 130, Illus. HYOGONOSUKE, "
     "©2024). This image is the direct evidence that the Indonesian Poké Ball mirror exists as an "
     "SV-P promo."),
    ("SPEC-0014", "S-P", "101", "base", "Korean", "publisher or database", "database scan",
     "Korean Snorlax read off a clean database scan rather than a photograph — no photographic "
     "background, lighting or card edges: \"잠만보\", HP 140, Basic, Single Strike (일격) marker, "
     "attacks 「뺨때리기」 30 and 「일격태클」 120, Illus. Yuya Oka, \"101/S-P\", PROMO, regulation "
     "mark D, ©2021. Note verification/units.json records for S-P 156 state that S-P 101 is a "
     "different card; the owner presents it as the Korean counterpart. That disagreement is "
     "unresolved and is not settled by this record."),
    ("SPEC-0015", "sc?? F", "111/159", "base", "T-Chinese", OWNER, "photograph",
     "Traditional Chinese Snorlax photographed front and back by the owner on a dark surface, the "
     "reverse showing a standard Pokémon card back: \"卡比獸\", HP 140, Basic, SINGLE STRIKE 一擊 "
     "marker, attacks 「巴掌撲擊」 30 and 「一擊衝撞」 120, Illus. Yuya Oka, \"111/159\", regulation "
     "mark E, ©2021. Same card text and illustrator as the Korean S-P 101 record (SPEC-0014). The "
     "card number is legible; the set glyph is not — it reads as a two-or-three character code "
     "ending in F and is deliberately not asserted here. Note this is a numbered set card, not a "
     "promo, so it is not an S-P printing under a different number."),
]


def main() -> None:
    document = json.loads(SPECIMENS.read_text(encoding="utf-8-sig"))
    known = {s["specimenId"] for s in document["specimens"]}

    added = 0
    for sid, set_code, number, variant, language, held_by, inspected, observed in RECORDS:
        if sid in known:
            continue
        document["specimens"].append({
            "specimenId": sid,
            "setCode": set_code,
            "number": number,
            "variant": variant,
            "language": language,
            "heldBy": held_by,
            "inspectedFrom": inspected,
            "photograph": None,
            "observed": observed,
            "recordedAt": RECORDED_AT,
            "citedBy": [],
        })
        added += 1

    if added:
        document["specimens"].sort(key=lambda s: s["specimenId"])
        document["count"] = len(document["specimens"])
        SPECIMENS.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    held = sum(1 for s in document["specimens"] if s.get("heldBy") == OWNER)
    print(f"Added {added} specimen record(s); {len(document['specimens'])} total "
          f"({held} held by the collection owner, {len(document['specimens']) - held} not).")


if __name__ == "__main__":
    main()

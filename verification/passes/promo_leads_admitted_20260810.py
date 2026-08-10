#!/usr/bin/env python3
"""Admit all five pokumon promo leads on the owner's photographs (#138).

`pokumon_promo_leads_20260810.py` recorded five printings the owner's cross-language filter turned
up and held every one of them, because pokumon is a collector database and ADR-0001 admits on a
physical specimen (D1) or a tier-1 publisher record (D5). Within the hour the owner supplied
photographs of all five through issue #166, so all five are now specimen-backed and admitted under
D1 — which is what D1 has always been for.

    KR  SM-P 140  SPEC-0028  PSA GEM MT 10, cert 101016611
    TW  SM-P 053  SPEC-0029  POKÉMON TCG GYM stamp
    TW  S-P  145  SPEC-0030  mirror finish, on the owner's identification
    KR  XY-P 167  SPEC-0031  the Kisstick sausages printing
    TW  SV-P 215  SPEC-0032  PSA GEM MT 10, 2025 Taiwan Lantern Festival stamp

TWO OF THESE CLOSE A DOCUMENTATION DEBT

`XY-P 167` and `SV-P 215` have been described in `RESUME.md` for weeks without existing as records —
the first as the Korean printing whose existence corrected the false `XY-P 149` contradiction, the
second as the Traditional Chinese promo carrying what `svLN 010` and `mP1 012` claim. Both now
carry a photograph, and both confirm the prose exactly: `167/XY-P` is Illus. Kouki Saitou, the
identifier the redirect identity test rested on, and `215/SV-P` carries the 2025 Taiwan Lantern
Festival stamp the article named.

ONE IS NOT THE CARD ITS SIBLINGS ARE

`KR SM-P 140` is a **Full Art** by Tomokazu Komiya, ©2019, and its PSA label says so — `FA/EEVEE &
SNORLAX GX`. The Thai `083/SM-P` and Indonesian `166/SM-P` are the Mitsuhiro Arita TAG TEAM artwork
and ©2020. Same species pair, same set-code family, different printing and different year, so
nothing here treats them as one work. The Traditional Chinese `053/SM-P` *is* the Arita artwork and
carries the same POKÉMON TCG GYM stamp as the Thai card.

THE ONE FINISH CLAIM, AND ITS LIMIT

`TW S-P 145` is recorded with technical finish `mirror-holo` on the owner's own identification —
the photograph was supplied labelled "Mirror Finish" and the card face carries a textured foil
across its whole surface. No foil pattern is named, because none is legible from the photograph, and
`markings` stays empty. That is the only finish asserted by this pass; the other four leave finish
`pending`, as a photograph of a card in a slab or at an angle cannot settle it.

    python verification/passes/promo_leads_admitted_20260810.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PRINTS = ROOT / "verification" / "source_first_prints.json"

# (locality, language, script, setCode, number, localName, cardName, specimen, note)
ROWS = [
    ("KR", "Korean", "Hang", "SM-P", "140", "이브이&잠만보 GX", "Eevee & Snorlax-GX", "SPEC-0028",
     "the Full Art by Tomokazu Komiya, ©2019, graded PSA GEM MT 10 (cert 101016611); a different "
     "printing from the Mitsuhiro Arita ©2020 artwork of the Thai and Indonesian SM-P cards"),
    ("TW", "T-Chinese", "Hant", "SM-P", "053", "伊布&卡比獸 GX", "Eevee & Snorlax-GX", "SPEC-0029",
     "the Mitsuhiro Arita artwork, ©2020, carrying the same POKÉMON TCG GYM distribution stamp as "
     "the Thai 083/SM-P"),
    ("TW", "T-Chinese", "Hant", "S-P", "145", "卡比獸", "Snorlax", "SPEC-0030",
     "Illus. Tika Matsuno, ©2022, regulation mark D; the owner identifies the face as a mirror "
     "finish and SPEC-0030 records that as the technical finish"),
    ("KR", "Korean", "Hang", "XY-P", "167", "잠만보", "Snorlax", "SPEC-0031",
     "the Kisstick sausages printing RESUME.md has described since the XY-P 149 correction; "
     "Illus. Kouki Saitou, ©2016, which is the identifier that correction's identity test used"),
    ("TW", "T-Chinese", "Hant", "SV-P", "215", "卡比獸", "Snorlax", "SPEC-0032",
     "Illus. Ounishi, ©2025, regulation mark H, graded PSA GEM MT 10 (cert 156080921), carrying "
     "the 2025 Taiwan Lantern Festival stamp RESUME.md names for this printing"),
]


def main() -> int:
    document = json.loads(PRINTS.read_text(encoding="utf-8"))
    existing = {entry["printId"] for entry in document["prints"]}

    added = 0
    for locality, language, script, set_code, number, local_name, card_name, spec, note in ROWS:
        print_id = f"{locality}:{set_code}:{number}:base"
        if print_id in existing:
            continue
        document["prints"].append({
            "printId": print_id,
            "locality": locality,
            "localSetCode": set_code,
            "localNumber": number,
            "variant": "base",
            "language": language,
            "script": script,
            "name": local_name,
            "cardName": card_name,
            "catchUpOf": None,
            "specimenId": spec,
            "providerId": "inspected-specimen",
            "sourceUrl": None,
            "corroborated": True,
            "markAssetUrl": None,
            "cardImageUrl": None,
            "evidence": (
                f"Photographed by the owner and filed as {spec}, supplied through issue #166 "
                f"within the hour of the lead being recorded — {note}. Corroborated about this "
                f"printing rather than about a neighbour: pokumon carries it as its own "
                f"per-language entry, which is how it was found. Admitted under ADR-0001 D1, a "
                f"specimen-backed code. Language and identity only; finish is asserted for no "
                f"print here except where its specimen records a physical observation."
            ),
        })
        added += 1

    document.setdefault("held", [])
    keep = []
    for entry in document["held"]:
        key = (entry.get("locality"), entry.get("localSetCode"), entry.get("localNumber"))
        if key in {(r[0], r[3], r[4]) for r in ROWS}:
            continue
        keep.append(entry)
    released = len(document["held"]) - len(keep)
    document["held"] = keep
    document["meta"]["counts"] = {
        "admitted": len(document["prints"]),
        "held": len(keep),
    }
    PRINTS.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"admitted {added} print(s), released {released} from held; "
          f"store now {document['meta']['counts']}")
    for locality, _lang, _s, set_code, number, _ln, _cn, spec, _n in ROWS:
        print(f"  {locality}  {set_code:<5}{number:>5}  {spec}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

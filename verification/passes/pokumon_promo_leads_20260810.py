#!/usr/bin/env python3
"""Record every promo printing the owner's pokumon sweep turned up (#138).

The owner supplied a pokumon filter across Snorlax and Eevee & Snorlax in seven languages. It
returns 32 entries; 19 are numbered promo printings, and matching each against this repository gives
a clean split: **fourteen are already held** as confirmed units or admitted prints, and **five are
recorded nowhere**.

Two of the five are the uncomfortable ones. `XY-P 167` (Korean) and `SV-P 215` (Traditional Chinese)
are *already written up in `RESUME.md`* — the first as the Kisstick sausages promotion that
corrected the false `XY-P 149` contradiction, the second as the standalone promo that carries the
Traditional Chinese printing of `svLN 010` and `mP1 012`. Both have been known in prose for weeks and
neither exists as a record. Prose that the data does not carry is a finding waiting to be
rediscovered, which is exactly what happened here.

    SM-P 053  T-Chinese   Eevee & Snorlax-GX
    SM-P 140  Korean      Eevee & Snorlax TAG TEAM-GX
    S-P  145  T-Chinese   Snorlax
    XY-P 167  Korean      Snorlax          — RESUME.md, Kisstick sausages promotion, 2017
    SV-P 215  T-Chinese   Snorlax          — RESUME.md, 2025 Taiwan Lantern Festival

ALL FIVE ARE HELD, NONE ADMITTED

ADR-0001 admits a print on a physical specimen (D1) or a tier-1 publisher record (D5). pokumon is
neither: it is a collector database, and one entry per market printing is a good structure rather
than a publisher's manifest. The two with `RESUME.md` support are corroborated by tier-2 sources —
Bulbapedia's redirect identity test for `XY-P 167`, the TCTCG article for `SV-P 215` — which
strengthens them and still does not reach either bar.

Holding them is the point. Each carries what is known, what it rests on and what would admit it, so
the next person inherits five researched leads instead of re-running the owner's filter.

WHAT THE SWEEP ALSO CONFIRMED

`SV-P/ID 117` appears twice, as `poke-ball-holo` and `master-ball-holo`. That is independent support
for the V1/V2 split this repository already records for that unit, from a source that had no reason
to agree with it.

    python verification/passes/pokumon_promo_leads_20260810.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PRINTS = ROOT / "verification" / "source_first_prints.json"
BASE = "https://pokumon.com/card"

LEADS = [
    ("TW", "T-Chinese", "SM-P", "053", "Eevee & Snorlax-GX",
     "eevee-snorlax-gx-053-sm-p-chinese-promo",
     "No other source here records a Traditional Chinese SM-P Eevee & Snorlax-GX. The Japanese "
     "SM-P 297 and the Korean SM-P 140 are its siblings in the same pokumon sweep."),
    ("KR", "Korean", "SM-P", "140", "Eevee & Snorlax-GX",
     "eevee-snorlax-tag-teamgx-140-sm-p-korean-promo",
     "No other source here records a Korean SM-P Eevee & Snorlax-GX."),
    ("TW", "T-Chinese", "S-P", "145", "Snorlax",
     "snorlax-145-s-p-chinese-promo",
     "No other source here records a Traditional Chinese S-P 145. Note the Korean S-P 101 and the "
     "Japanese S-P 156 are separate printings under the same set code in other localities, which "
     "is why locality is part of the print identity."),
    ("KR", "Korean", "XY-P", "167", "Snorlax",
     "snorlax-167-xy-p-korean-promo",
     "Already documented in RESUME.md and never recorded: \"Korea: XY-P 167 via the Kisstick "
     "sausages promotion, 2017 — the same card\". It is the printing that corrected the false "
     "XY-P 149 contradiction, established through Bulbapedia's redirect identity test — both "
     "Snorlax (XY-P Promo 149) and Snorlax (XY-P Promo 167) redirect to Snorlax (BREAKthrough 118) "
     "— with the illustrator Kouki Saitou matching on both. Two tier-2/3 sources agree; neither is "
     "a specimen nor a publisher record."),
    ("TW", "T-Chinese", "SV-P", "215", "Snorlax",
     "snorlax-215-sv-p-chinese-promo",
     "Already documented in RESUME.md and never recorded: the Traditional Chinese printing of the "
     "Japanese deck cards svLN 010 and mP1 012 is not an edition of those decks but this "
     "standalone promo, 2025 Taiwan Lantern Festival. Identity was established through the shared "
     "Cardmarket cardKey Snorlax-Spike-Draw-Mega-Punch, and the TCTCG article names Surging Sparks "
     "144 as the source of 215/SV-P."),
]


def main() -> int:
    document = json.loads(PRINTS.read_text(encoding="utf-8"))
    held = document.setdefault("held", [])
    existing = {(h.get("locality"), h.get("localSetCode"), h.get("localNumber")) for h in held}

    added = 0
    for locality, language, set_code, number, card_name, slug, note in LEADS:
        if (locality, set_code, number) in existing:
            continue
        held.append({
            "locality": locality,
            "language": language,
            "localSetCode": set_code,
            "localNumber": number,
            "specimenId": None,
            "cardName": card_name,
            "sourceUrl": f"{BASE}/{slug}/",
            "providerId": "pokumon",
            "reason": (
                f"Found through the owner's cross-language pokumon filter on 2026-08-10. pokumon "
                f"carries this as its own entry and its structure is one entry per market "
                f"printing, naming that printing's language. {note} Held rather than admitted: "
                f"ADR-0001 admits on a physical specimen (D1) or a tier-1 publisher record (D5), "
                f"and a collector database is neither. Recorded so the lead survives."
            ),
        })
        added += 1

    document["meta"]["counts"] = {
        "admitted": len(document["prints"]),
        "held": len(held),
    }
    PRINTS.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"held {added} new promo lead(s); store now {document['meta']['counts']}")
    for locality, language, set_code, number, card_name, _slug, _n in LEADS:
        print(f"  {locality}  {set_code:<5}{number:>5}  {language:<11} {card_name}")
    print("  14 of the sweep's 19 numbered promos were already confirmed units or admitted prints")
    return 0


if __name__ == "__main__":
    sys.exit(main())

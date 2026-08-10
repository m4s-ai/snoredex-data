#!/usr/bin/env python3
"""Admit the Thai and Indonesian catch-up prints under ADR-0001 D5 (#138).

The owner pointed at `Pokémon in Thailand`, which states the mechanism in its own words: the game
was localized into Thai in January 2019, and "to help catch Thai players up with the game,
Thai-exclusive sets of currently legal, already-released cards were made". Indonesia has the same
shape. So the `sc1a F 127/154` pattern — a known card living under a local set code with a different
collector number — is not a Taiwanese peculiarity, and the publisher's own Asia card database
records the Thai and Indonesian counterparts.

D5 (owner, 2026-08-10) extends D1 to a catch-up code evidenced by a tier-1 publisher record, for
language and identity only. Finish stays `pending`: a database page cannot be turned over.

READ THE BADGE, NOT THE FILENAME — THE CORRECTION THAT SHAPED THIS PASS

The first version of this pass took each set code from the expansion-mark image's *filename* and
held one row back because its filename was a CMS placeholder. Both were mistakes, and the owner
caught them: the set code is **printed on the card**, and the same page that serves the placeholder
filename also serves the artwork and the mark asset that render it.

Rendered at size, every Thai badge reads a code followed by **`T`**, and every Indonesian one the
same code followed by **`I`** — exactly the way Traditional Chinese takes `F` in `sc1a F`. So the
filenames were wrong in two ways at once: `Sc1a.png` renders `sc1a T`, `SCA.png` renders `scA T`,
`S_mark_Indonesia_SC1D.png` renders `sc1D I`. Wrong case, and the locale letter missing entirely.
Only the Sun & Moon-era Indonesian codes carry no suffix — `AS1b`, `AS1D`, `AC3a`, `AC3D`, uppercase,
matching the Thailand article's own table, because there the `A` prefix is the locale marker.

The held row is admitted for the same reason. Thai `111/159`'s mark asset is named `アセット 12`, but
the card image reads **`scD T`**, regulation mark E, `111/159`, Illus. Yuya Oka, ©2021 — the
Traditional Chinese `scD F` counterpart under the Thai suffix. Holding it was not caution; it was
declining to look.

**The rule this leaves behind: when a structured field is missing or looks like a placeholder, check
whether the image carries it before recording an absence.** It applies to any source that serves an
image beside its metadata, and it is now in `RESUME.md` rather than only here.

WHAT IS ADMITTED

Every row comes from a card page on `asia.pokemon-card.com` carrying, in one place, the collector
number with its denominator, the card name in the locale's language, the regulation mark, and a
set-mark badge whose *rendered* text names the set. Identity rests on those four agreeing.

The Sword & Shield-era codes mirror the Traditional Chinese prints already admitted under D1:
`127/154`, `119/153`, `120/153` and `111/159` are the same numbers as `TW:sc1a F:127/154`,
`TW:sc1b F:119/153`, `TW:sc1b F:120/153` and `TW:scD F:111/159`, under `T` and `I` instead of `F`.
The Sun & Moon-era Indonesian codes have no Traditional Chinese counterpart here at all — Indonesia
ran catch-up sets an era earlier.

Thai `126/184` is deliberately not here: it belongs to a set the harvest already carries (`s8b`), so
it is unit evidence rather than a catch-up print, and it was recorded as such on 2026-08-10.

Also left alone: the promo rows (`082/SV-P` Thai; `030/S-P`, `052/S-P`, `100/S-P`,
`356/S-P` Indonesian), whose marks are generic promo glyphs carrying no set code, and the ordinary
localized editions of sets the harvest already holds — those belong to their units, not to this
store.

    python verification/passes/asia_catchup_prints_20260810.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
PRINTS = ROOT / "verification" / "source_first_prints.json"

BASE = "https://asia.pokemon-card.com"

# (locality, language, script, localSetCode, localNumber, localName, cardName, detailId,
#  markFile, regulationMark, catchUpNote)
ROWS = [
    ("TH", "Thai", "Thai", "sc1a T", "127/154", "คาบิกอน", "Snorlax", "127", "Sc1a", "D",
     "the Thai counterpart of the Traditional Chinese sc1a F 127/154 already admitted under D1"),
    ("TH", "Thai", "Thai", "sc1b T", "119/153", "คาบิกอนV", "Snorlax V", "273", "Sc1b", "D",
     "the Thai counterpart of the Traditional Chinese sc1b F 119/153 already admitted under D1"),
    ("TH", "Thai", "Thai", "sc1b T", "120/153", "คาบิกอนVMAX", "Snorlax VMAX", "274", "Sc1b", "D",
     "the Thai counterpart of the Traditional Chinese sc1b F 120/153 already admitted under D1"),
    ("TH", "Thai", "Thai", "sc1D T", "132/164", "คาบิกอน", "Snorlax", "439", "SC1D", "D",
     "a Thai starter-deck catch-up code with no Traditional Chinese counterpart recorded here"),
    ("TH", "Thai", "Thai", "sc1D T", "133/164", "คาบิกอนV", "Snorlax V", "440", "SC1D", "D",
     "a Thai starter-deck catch-up code with no Traditional Chinese counterpart recorded here"),
    ("TH", "Thai", "Thai", "sc3b T", "126/158", "คาบิกอน", "Snorlax", "1006", "Sc3b", "D",
     "a Thai catch-up booster code with no Traditional Chinese counterpart recorded here"),
    ("TH", "Thai", "Thai", "scA T", "084/135", "คาบิกอน", "Snorlax", "1806", "SCA", "D",
     "a Thai catch-up code with no Traditional Chinese counterpart recorded here"),
    ("TH", "Thai", "Thai", "scD T", "111/159", "คาบิกอน", "Snorlax", "2297", "アセット 12", "E",
     "the Thai counterpart of the Traditional Chinese scD F 111/159 already admitted under D1"),
    ("ID", "Indonesian", "Latn", "sc1a I", "127/154", "Snorlax", "Snorlax", "454",
     "S_mark_Indonesia_SC1a", "D",
     "the Indonesian counterpart of the Traditional Chinese sc1a F 127/154 admitted under D1"),
    ("ID", "Indonesian", "Latn", "sc1b I", "119/153", "Snorlax V", "Snorlax V", "600",
     "S_mark_Indonesia_SC1b", "D",
     "the Indonesian counterpart of the Traditional Chinese sc1b F 119/153 admitted under D1"),
    ("ID", "Indonesian", "Latn", "sc1b I", "120/153", "Snorlax VMAX", "Snorlax VMAX", "601",
     "S_mark_Indonesia_SC1b", "D",
     "the Indonesian counterpart of the Traditional Chinese sc1b F 120/153 admitted under D1"),
    ("ID", "Indonesian", "Latn", "sc1D I", "132/164", "Snorlax", "Snorlax", "764",
     "S_mark_Indonesia_SC1D", "D",
     "an Indonesian starter-deck catch-up code, matching the Thai SC1D at the same number"),
    ("ID", "Indonesian", "Latn", "sc1D I", "133/164", "Snorlax V", "Snorlax V", "765",
     "S_mark_Indonesia_SC1D", "D",
     "an Indonesian starter-deck catch-up code, matching the Thai SC1D at the same number"),
    ("ID", "Indonesian", "Latn", "sc3b I", "126/158", "Snorlax", "Snorlax", "3982",
     "S_mark_Indonesia_SC3b", "D",
     "an Indonesian catch-up booster code, matching the Thai Sc3b at the same number"),
    ("ID", "Indonesian", "Latn", "scA I", "084/135", "Snorlax", "Snorlax", "2796",
     "S_mark_Indonesia_SCA", "D",
     "an Indonesian catch-up code, matching the Thai SCA at the same number"),
    ("ID", "Indonesian", "Latn", "scD I", "111/159", "Snorlax", "Snorlax", "4527",
     "S_mark_Indonesia_SCD", "E",
     "the Indonesian counterpart of the Traditional Chinese scD F 111/159 admitted under D1"),
    ("ID", "Indonesian", "Latn", "AS1b", "112/150", "SnorlaxGX", "Snorlax GX", "1605",
     "SM_expantion_mark_as1b", "A",
     "a Sun & Moon-era Indonesian catch-up code; the Thailand article documents the same family "
     "in uppercase (AS1b) for the parallel Thai product, and no Traditional Chinese counterpart "
     "is recorded here"),
    ("ID", "Indonesian", "Latn", "AS1D", "108/140", "SnorlaxGX", "Snorlax GX", "3466",
     "SM_expantion_mark_as1D", "A",
     "a Sun & Moon-era Indonesian starter-deck catch-up code; the Thailand article documents the "
     "same family in uppercase (AS1D) for the parallel Thai product"),
    ("ID", "Indonesian", "Latn", "AC3a", "145/205", "Snorlax", "Snorlax", "2129",
     "SM_expantion_mark_aC3aOUT", "C",
     "a Sun & Moon-era Indonesian catch-up code; the Thailand article documents the same family "
     "in uppercase (AC3a) for the parallel Thai product"),
    ("ID", "Indonesian", "Latn", "AC3D", "120/172", "Eevee & Snorlax GX", "Eevee & Snorlax-GX",
     "2501", "SM_expantion_mark_ac3Dout", "C",
     "a Sun & Moon-era Indonesian starter-deck catch-up code; the Thailand article documents the "
     "same family in uppercase (AC3D) for the parallel Thai product"),
]

HELD: list[dict[str, Any]] = []


def main() -> int:
    document = json.loads(PRINTS.read_text(encoding="utf-8"))
    existing = {entry["printId"] for entry in document["prints"]}

    added = 0
    for (locality, language, script, set_code, number, local_name, card_name, detail_id,
         mark, regulation, catch_up) in ROWS:
        print_id = f"{locality}:{set_code}:{number}:base"
        if print_id in existing:
            continue
        locale = "th" if locality == "TH" else "id"
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
            "catchUpOf": catch_up,
            "specimenId": None,
            "providerId": "pokemon-card-asia",
            "sourceUrl": f"{BASE}/{locale}/card-search/detail/{detail_id}/",
            "corroborated": False,
            "evidence": (
                f"The Pokémon Company's Asia card database serves this card at "
                f"/{locale}/card-search/detail/{detail_id}/, carrying the collector number "
                f"{number}, the card name \"{local_name}\", regulation mark {regulation}, and an "
                f"a set-mark badge that renders \"{set_code}\" at size. The code is read off the "
                f"rendered badge and the card image, never off the mark asset's filename, which "
                f"here is \"{mark}\" — wrong case, and missing the locale letter the card itself "
                f"prints. Identity rests on the number, the denominator, the card name and the "
                f"regulation mark agreeing with it. Admitted under "
                f"ADR-0001 D5 for language and identity only — {catch_up}. No finish is asserted "
                f"and none may be inferred: a database page cannot be turned over. Retrieved "
                f"2026-08-10."
            ),
        })
        added += 1

    held_urls = {entry.get("sourceUrl") for entry in document.get("held", [])}
    held_added = 0
    for entry in HELD:
        if entry["sourceUrl"] in held_urls:
            continue
        document.setdefault("held", []).append(entry)
        held_added += 1

    document["meta"]["counts"] = {
        "admitted": len(document["prints"]),
        "held": len(document.get("held", [])),
    }
    document["meta"]["decision"] = (
        "ADR-0001 D1 (owner, 2026-08-09) for specimen-backed codes; "
        "ADR-0001 D5 (owner, 2026-08-10) for codes backed by a tier-1 publisher record, "
        "language and identity only"
    )
    PRINTS.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"admitted {added} catch-up print(s), held {held_added}; "
          f"store now {document['meta']['counts']}")
    by_locality: dict[str, int] = {}
    for entry in document["prints"]:
        by_locality[entry["locality"]] = by_locality.get(entry["locality"], 0) + 1
    for locality, count in sorted(by_locality.items()):
        print(f"  {locality}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

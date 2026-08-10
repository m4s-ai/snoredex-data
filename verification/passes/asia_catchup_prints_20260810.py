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

WHAT IS ADMITTED, AND WHY EACH ONE IS SAFE TO NAME

Every row below comes from a card page on `asia.pokemon-card.com` carrying, in one place, the
collector number with its denominator, the card name in the locale's language, the regulation mark,
and an expansion-mark image whose filename names the set. Identity rests on those four agreeing —
never on the filename alone, which is the trap this harvest already sprang twice.

The Sword & Shield-era codes mirror the Traditional Chinese prints already admitted under D1:
`127/154`, `119/153` and `120/153` are the same numbers as `TW:sc1a F:127/154`,
`TW:sc1b F:119/153` and `TW:sc1b F:120/153`. The Sun & Moon-era Indonesian codes have no
Traditional Chinese counterpart here at all — Indonesia ran catch-up sets an era earlier.

WHAT IS HELD, AND WHY

Two Thai rows are **not** admitted, and the reason is `N5`: a held print may not smuggle in a set
code its evidence refuses to assert.

* `111/159` and `126/184` (Thai) carry expansion-mark images named `アセット 12` and `アセット 11` —
  CMS placeholders, not set codes. The Indonesian siblings at the same numbers are marked
  `S_mark_Indonesia_SCD` and `S_mark_Indonesia_S8b`, which is a strong hint and not an assertion
  about the Thai product. `126/184` additionally belongs to a set the harvest already carries
  (`s8b`), so it is unit evidence rather than a catch-up print, and it was recorded as such on
  2026-08-10. `111/159` is held here.

Also deliberately left alone: the promo rows (`082/SV-P` Thai; `030/S-P`, `052/S-P`, `100/S-P`,
`356/S-P` Indonesian), whose marks are generic promo glyphs carrying no set code, and the ordinary
localized editions of sets the harvest already holds — those belong to their units, not to this
store.

    python verification/passes/asia_catchup_prints_20260810.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PRINTS = ROOT / "verification" / "source_first_prints.json"

BASE = "https://asia.pokemon-card.com"

# (locality, language, script, localSetCode, localNumber, localName, cardName, detailId,
#  markFile, regulationMark, catchUpNote)
ROWS = [
    ("TH", "Thai", "Thai", "Sc1a", "127/154", "คาบิกอน", "Snorlax", "127", "Sc1a", "D",
     "the Thai counterpart of the Traditional Chinese sc1a F 127/154 already admitted under D1"),
    ("TH", "Thai", "Thai", "Sc1b", "119/153", "คาบิกอนV", "Snorlax V", "273", "Sc1b", "D",
     "the Thai counterpart of the Traditional Chinese sc1b F 119/153 already admitted under D1"),
    ("TH", "Thai", "Thai", "Sc1b", "120/153", "คาบิกอนVMAX", "Snorlax VMAX", "274", "Sc1b", "D",
     "the Thai counterpart of the Traditional Chinese sc1b F 120/153 already admitted under D1"),
    ("TH", "Thai", "Thai", "SC1D", "132/164", "คาบิกอน", "Snorlax", "439", "SC1D", "D",
     "a Thai starter-deck catch-up code with no Traditional Chinese counterpart recorded here"),
    ("TH", "Thai", "Thai", "SC1D", "133/164", "คาบิกอนV", "Snorlax V", "440", "SC1D", "D",
     "a Thai starter-deck catch-up code with no Traditional Chinese counterpart recorded here"),
    ("TH", "Thai", "Thai", "Sc3b", "126/158", "คาบิกอน", "Snorlax", "1006", "Sc3b", "D",
     "a Thai catch-up booster code with no Traditional Chinese counterpart recorded here"),
    ("TH", "Thai", "Thai", "SCA", "084/135", "คาบิกอน", "Snorlax", "1806", "SCA", "D",
     "a Thai catch-up code with no Traditional Chinese counterpart recorded here"),
    ("ID", "Indonesian", "Latn", "SC1a", "127/154", "Snorlax", "Snorlax", "454",
     "S_mark_Indonesia_SC1a", "D",
     "the Indonesian counterpart of the Traditional Chinese sc1a F 127/154 admitted under D1"),
    ("ID", "Indonesian", "Latn", "SC1b", "119/153", "Snorlax V", "Snorlax V", "600",
     "S_mark_Indonesia_SC1b", "D",
     "the Indonesian counterpart of the Traditional Chinese sc1b F 119/153 admitted under D1"),
    ("ID", "Indonesian", "Latn", "SC1b", "120/153", "Snorlax VMAX", "Snorlax VMAX", "601",
     "S_mark_Indonesia_SC1b", "D",
     "the Indonesian counterpart of the Traditional Chinese sc1b F 120/153 admitted under D1"),
    ("ID", "Indonesian", "Latn", "SC1D", "132/164", "Snorlax", "Snorlax", "764",
     "S_mark_Indonesia_SC1D", "D",
     "an Indonesian starter-deck catch-up code, matching the Thai SC1D at the same number"),
    ("ID", "Indonesian", "Latn", "SC1D", "133/164", "Snorlax V", "Snorlax V", "765",
     "S_mark_Indonesia_SC1D", "D",
     "an Indonesian starter-deck catch-up code, matching the Thai SC1D at the same number"),
    ("ID", "Indonesian", "Latn", "SC3b", "126/158", "Snorlax", "Snorlax", "3982",
     "S_mark_Indonesia_SC3b", "D",
     "an Indonesian catch-up booster code, matching the Thai Sc3b at the same number"),
    ("ID", "Indonesian", "Latn", "SCA", "084/135", "Snorlax", "Snorlax", "2796",
     "S_mark_Indonesia_SCA", "D",
     "an Indonesian catch-up code, matching the Thai SCA at the same number"),
    ("ID", "Indonesian", "Latn", "SCD", "111/159", "Snorlax", "Snorlax", "4527",
     "S_mark_Indonesia_SCD", "E",
     "the Indonesian counterpart of the Traditional Chinese scD F 111/159 admitted under D1"),
    ("ID", "Indonesian", "Latn", "as1b", "112/150", "SnorlaxGX", "Snorlax GX", "1605",
     "SM_expantion_mark_as1b", "A",
     "a Sun & Moon-era Indonesian catch-up code; the Thailand article documents the same family "
     "in uppercase (AS1b) for the parallel Thai product, and no Traditional Chinese counterpart "
     "is recorded here"),
    ("ID", "Indonesian", "Latn", "as1D", "108/140", "SnorlaxGX", "Snorlax GX", "3466",
     "SM_expantion_mark_as1D", "A",
     "a Sun & Moon-era Indonesian starter-deck catch-up code; the Thailand article documents the "
     "same family in uppercase (AS1D) for the parallel Thai product"),
    ("ID", "Indonesian", "Latn", "aC3a", "145/205", "Snorlax", "Snorlax", "2129",
     "SM_expantion_mark_aC3aOUT", "C",
     "a Sun & Moon-era Indonesian catch-up code; the Thailand article documents the same family "
     "in uppercase (AC3a) for the parallel Thai product"),
    ("ID", "Indonesian", "Latn", "ac3D", "120/172", "Eevee & Snorlax GX", "Eevee & Snorlax-GX",
     "2501", "SM_expantion_mark_ac3Dout", "C",
     "a Sun & Moon-era Indonesian starter-deck catch-up code; the Thailand article documents the "
     "same family in uppercase (AC3D) for the parallel Thai product"),
]

HELD = [
    {
        "locality": "TH",
        "language": "Thai",
        "localNumber": "111/159",
        "cardName": "Snorlax",
        "sourceUrl": f"{BASE}/th/card-search/detail/2297/",
        "providerId": "pokemon-card-asia",
        "reason": (
            "The Thai card page for 111/159 carries the collector number, the card name and "
            "regulation mark E, but its expansion-mark image is named \"アセット 12\" — a CMS "
            "placeholder rather than a set code. The Indonesian sibling at the same number is "
            "marked S_mark_Indonesia_SCD and the Traditional Chinese counterpart scD F 111/159 is "
            "already admitted, so the set is almost certainly the Thai SCD; almost certainly is "
            "not an assertion the evidence makes. Held under N5 until a source states the Thai set "
            "code, rather than naming a code this page refuses to give."
        ),
    },
]


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
                f"expansion-mark image named \"{mark}\". Identity rests on those four agreeing, "
                f"never on the filename alone: the same harvest showed one mark filename that was "
                f"a CMS placeholder carrying no set code, and another (ma3 against the Traditional "
                f"Chinese m2a) that differed from the Japanese code for a single card. Admitted "
                f"under "
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

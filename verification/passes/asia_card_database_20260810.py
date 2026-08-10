#!/usr/bin/env python3
"""Answer five Asian-locale rows from the publisher's own Asia card database (#137).

Twenty-four confirmations still rested on the cross-language expansion index — "this set has a
Thai release" — for cards a set release does not reach: deck-fixed cards and secret-numbered ones.
Eleven of those are Thai, Indonesian or Traditional Chinese, which is exactly what
`asia.pokemon-card.com` covers, and five of the eleven are in it.

Each row below is a card page in the locale's own language, from The Pokémon Company, at tier 1 —
replacing a statement about the set with a record of the card.

    U0309  sv4a 145  Thai        detail/7755/    145/190, mark sv4a_th.png
    U0387  sv4a 310  Thai        detail/8631/    310/190, mark sv4a_th.png
    U0176  s8b  126  Thai        detail/2468/    126/184
    U0130  m2a  136  Thai        detail/13046/   136/193, Hop's Snorlax
    U0129  m2a  136  Indonesian  detail/17374/   136/193, Hop's Snorlax

HOW EACH IDENTIFICATION IS MADE, INCLUDING THE WEAK ONE

The two `sv4a` rows are unambiguous: the expansion mark image is literally `sv4a_th.png`, and
`145/190` and `310/190` match the unit's number and the set's printed size.

`s8b 126` rests on the collector number `126/184` and the card name. Its Thai mark image carries a
placeholder filename rather than a set code, so the set code comes from the denominator plus the
already-confirmed Indonesian sibling `U0175`, whose mark is `S_mark_Indonesia_S8b.png` at the same
number. Weaker than the `sv4a` pair and recorded as such.

`m2a 136` needs its caveat stated rather than buried. The number `136/193`, the card name (Hop's
Snorlax) and the regulation mark `I` agree across all three locales, and the already-confirmed
Traditional Chinese `U0128` carries the mark `twhk_m2a_exp.png`. But the Thai and Indonesian mark
images are named `th_ma3t_exp.png` and `idn_ma3i_exp.png` — `ma3`, not `m2a`. The reading here is
that the asset filenames use locale-specific codes for one set, which four agreeing identifiers
support; it is not a reading the filenames themselves confirm. Anyone who disagrees has everything
needed to say so.

Thai lists three separate detail ids at `136/193` and Indonesian likewise; one is cited per unit and
the duplicates are noted. Any of them establishes the printing.

WHAT WAS SEARCHED AND NOT FOUND — AND WHY THAT CHANGES NOTHING

`s10a 077` (Traditional Chinese, Indonesian, Thai) and `s5a 93` (the same three) are absent from all
three locale searches. Both are secret-numbered — `077/071` and `093/070` — and both remain exactly
as they were.

This is worth writing down because the absence is more interesting than usual and still is not
evidence. Secrets *are* indexed here: Thai returns `310/190`, itself a secret. And the era is
covered: Thai returns `126/184` from 2021 and `056/071` from 2022, either side of both missing
cards. So the easy dismissals do not apply. What still applies is that `pokemon-card-asia` is
declared `supportsAbsence: false`, its own registry note says older printings are out of coverage,
and no absence scope has been established for it. Reading these six misses as absence would be
inventing a closed manifest, which is the `XY-P 149` mistake with a better-looking source. Left for
the owner, alongside the question of whether this surface deserves a bounded absence scope at all.

Search method, for the next person: the keyword must be in the locale's script.
`th` needs `คาบิกอน`, `tw` needs `卡比獸`; only `id` answers to "Snorlax". The list endpoint is
`/{locale}/card-search/list/?keyword=<kw>&sm_and_keyword=true&pageNo=<n>`, twenty per page, and each
detail page carries `class="collectorNumber"` and a `card-img/mark/` image.

    python verification/passes/asia_card_database_20260810.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UNITS = ROOT / "verification" / "units.json"

SOURCE_TYPE = "Official Pokemon Asia card database (asia.pokemon-card.com)"

# unitId -> (expected (setCode, number, variant, language), detail url, evidence sentence)
FINDINGS: dict[str, tuple[tuple[str, str, str, str], str, str]] = {
    "U0309": (
        ("sv4a", "145", "V1", "Thai"),
        "https://asia.pokemon-card.com/th/card-search/detail/7755/",
        "Thai card page for collector number 145/190, expansion mark image sv4a_th.png — the "
        "filename names the set outright. Card-level and locale-specific: this is the Thai print. "
        "Replaces the cross-language expansion index, which established only that the set had a "
        "Thai release and could not reach a deck-fixed card. Retrieved 2026-08-10.",
    ),
    "U0387": (
        ("sv4a", "310", "V2", "Thai"),
        "https://asia.pokemon-card.com/th/card-search/detail/8631/",
        "Thai card page for collector number 310/190, expansion mark image sv4a_th.png. A "
        "secret-numbered card above the printed set size, so a set release never reached it; the "
        "database records the Thai print itself. Retrieved 2026-08-10.",
    ),
    "U0176": (
        ("s8b", "126", "base", "Thai"),
        "https://asia.pokemon-card.com/th/card-search/detail/2468/",
        "Thai card page for collector number 126/184, matching VMAX Climax's printed set size and "
        "the card name. The Thai mark image carries a placeholder filename rather than a set code, "
        "so the set identification rests on the denominator plus the already-confirmed Indonesian "
        "sibling U0175, whose mark is S_mark_Indonesia_S8b.png at the same number. Weaker than an "
        "explicit set-code filename and recorded as such. Retrieved 2026-08-10.",
    ),
    "U0130": (
        ("m2a", "136", "base", "Thai"),
        "https://asia.pokemon-card.com/th/card-search/detail/13046/",
        "Thai card page for collector number 136/193, card name Hop's Snorlax, regulation mark I — "
        "all three agreeing with the already-confirmed Traditional Chinese U0128, whose mark is "
        "twhk_m2a_exp.png. Caveat stated rather than buried: the Thai mark image is named "
        "th_ma3t_exp.png, i.e. ma3 rather than m2a, so the set identification rests on the four "
        "agreeing identifiers and not on the asset filename. Thai lists three detail ids at this "
        "number (13046, 13749, 13750); any one establishes the printing. Retrieved 2026-08-10.",
    ),
    "U0129": (
        ("m2a", "136", "base", "Indonesian"),
        "https://asia.pokemon-card.com/id/card-search/detail/17374/",
        "Indonesian card page for collector number 136/193, card name Snorlax <Hop>, regulation "
        "mark I — agreeing with the already-confirmed Traditional Chinese U0128 (mark "
        "twhk_m2a_exp.png). Same caveat as the Thai row: the Indonesian mark image is named "
        "idn_ma3i_exp.png, so the set identification rests on the agreeing identifiers rather than "
        "the filename. Indonesian lists three detail ids at this number (17374, 17792, 17793). "
        "Retrieved 2026-08-10.",
    ),
}


def main() -> int:
    units = json.loads(UNITS.read_text(encoding="utf-8"))
    by_id = {unit["unitId"]: unit for unit in units}

    for unit_id, (expected, url, evidence) in FINDINGS.items():
        unit = by_id.get(unit_id)
        if unit is None:
            print(f"missing {unit_id}", file=sys.stderr)
            return 1
        actual = (unit["setCode"], str(unit["number"]), unit.get("variant") or "base",
                  unit["language"])
        if actual != expected:
            print(f"{unit_id} is {actual}, expected {expected}", file=sys.stderr)
            return 1
        if unit["status"] != "confirmed":
            print(f"{unit_id} is {unit['status']}, expected confirmed", file=sys.stderr)
            return 1
        unit["sourceUrl"] = url
        unit["sourceType"] = SOURCE_TYPE
        unit["providerId"] = "pokemon-card-asia"
        unit["evidence"] = evidence

    UNITS.write_text(json.dumps(units, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"raised {len(FINDINGS)} confirmation(s) from a set release to the publisher's card page")
    for unit_id, (expected, url, _) in sorted(FINDINGS.items()):
        set_code, number, variant, language = expected
        print(f"  {unit_id}  {set_code:5}{number:>5} {variant:5} {language:11} {url}")
    print("  s10a 077 and s5a 93 searched in tw/id/th and not found; both left unchanged, "
          "because this source carries no absence scope")
    return 0


if __name__ == "__main__":
    sys.exit(main())

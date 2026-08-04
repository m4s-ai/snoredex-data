#!/usr/bin/env python3
"""Correct the Indonesian specimens: `SV-P/ID 117` is in the catalogue, and I said it was not.

THE ERROR

SPEC-0012 and SPEC-0013 were filed with `setCode: "SV-P"` and an `observed` note saying the card
was "the other product" — one this dataset does not contain. I had searched `snorlax_cards.json`
for a set code equal to `SV-P`, found nothing, and reported that on #94 and in two commit messages.

The catalogue codes it `SV-P/ID` — "Scarlet & Violet Indonesian Promos" — and carries **both**
variants of 117 as confirmed units:

    U0752  SV-P/ID 117 V1 Indonesian  confirmed (bulbapedia)
    U0772  SV-P/ID 117 V2 Indonesian  confirmed (bulbapedia)

An equality test against a guessed code is not a search. The same mistake would have hidden
`SV-P/TH 082` (Thai, confirmed from the official Asia database) and `SV-P/CS 277`.

WHAT IT CHANGES

Less than it might look like, and in a useful direction. The adjudications on #89 are unaffected:
they rule that Cardmarket's Indonesian claim against *`xsv2a 143`* is wrong, and it still is — the
card is `SV-P/ID 117`, which is exactly what the decision says. What changes is that these
photographs are specimens of catalogued, confirmed units rather than free-standing observations,
so their identity fields must match those units for check S8 to accept a citation.

WHAT IS STILL OPEN

Which V-token is which pattern. The owner's correction identifies the two cards by *pattern* —
"left is Pokeball very faint reverse holo, right is master ball" — but neither U0752 nor U0772
records a `variantName`, and both rest on the same Bulbapedia set-list row, which does not
distinguish them. `xsv2a` has V1 = Poké Ball and V2 = Master Ball, and CLAUDE.md is explicit that
V-tokens are set-specific and must never be carried across. So the tokens stay unassigned and no
unit cites these yet: guessing the mapping is how `xm2a` would have been filed backwards.

Idempotent: re-running changes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECIMENS = ROOT / "verification" / "specimens.json"

SUFFIX = (
    " Catalogue identity: this is SV-P/ID 117, \"Scarlet & Violet Indonesian Promos\", which the "
    "catalogue carries as two confirmed units - U0752 (V1) and U0772 (V2). An earlier version of "
    "this record said the product was absent from the dataset; that was wrong, and came from "
    "testing for a set code equal to \"SV-P\" rather than searching. Which V-token denotes which "
    "ball pattern is not established: neither unit records a variantName and both cite the same "
    "Bulbapedia row, so no unit cites this specimen yet."
)

FIXES = {
    "SPEC-0012": ("SV-P/ID", "117"),
    "SPEC-0013": ("SV-P/ID", "117"),
}

# The sentence that has to go, in each record that carries it.
STALE = (
    "This is the promo release the owner cites when ruling that the Indonesian 151 mirrors exist "
    "as SV-P promos rather than as xsv2a 143 printings."
)
STALE_REPLACEMENT = (
    "This is the promo release the owner cites when ruling that the Indonesian 151 mirrors exist "
    "as promos rather than as xsv2a 143 printings."
)


def main() -> None:
    document = json.loads(SPECIMENS.read_text(encoding="utf-8-sig"))
    changed = 0
    for specimen in document["specimens"]:
        fix = FIXES.get(specimen["specimenId"])
        if not fix:
            continue
        set_code, number = fix
        before = (specimen["setCode"], specimen["number"], specimen["observed"])
        specimen["setCode"] = set_code
        specimen["number"] = number
        observed = specimen["observed"].replace(STALE, STALE_REPLACEMENT)
        if SUFFIX.strip() not in observed:
            observed = observed.rstrip() + SUFFIX
        specimen["observed"] = observed
        if (specimen["setCode"], specimen["number"], specimen["observed"]) != before:
            changed += 1

    if changed:
        SPECIMENS.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Corrected {changed} Indonesian specimen record(s) to the SV-P/ID 117 identity.")


if __name__ == "__main__":
    main()

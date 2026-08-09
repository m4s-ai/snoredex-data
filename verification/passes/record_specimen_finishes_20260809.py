#!/usr/bin/env python3
"""Give specimens the finish dimension the finish rules already assume (#150).

`FINISH_SOURCES.md` has always listed the evidence class:

    | Identified physical scan | Visible finish, pattern, marking, and size on that specimen | No |

It was never implementable. A specimen record carries `setCode, number, variant, language,
heldBy, inspectedFrom, observed, …` and no finish, so a photographed reverse-holo could only be
described in prose that no check reads and no node is established by. Since #149 the model has a
`physical_printing` node and all 468 of them come from `finish_units.json`; not one cites a
specimen. The strongest rung of the ladder — a card someone examined — is the only rung with no
edge into the node type that describes it.

That costs real coverage. Of the 201 finish units with no positive finish evidence, 68 are Korean
or Simplified Chinese, and `FINISH_SOURCES.md` says of exactly those two: "No source found …
Treat them as specimen-led". A third of the open finish queue is answerable only by a specimen,
and a specimen could not answer it.

WHAT THIS PASS DOES, AND WHAT IT REFUSES TO DO

It adds an optional `physicalObservation` block to the specimens whose own text already records
what the card looks like, and to no others. Seven of twenty-five qualify. Every assignment carries
`basis`: the record's own words, quoted. A later reader checks the assignment against the quote
instead of re-reading the record, and a later pass cannot widen it quietly.

Six specimens mention finish vocabulary and are deliberately left alone:

* SPEC-0008 "rainbow rare" and SPEC-0010 "full art" state a **rarity**, not a finish. A hyper rare
  is foil in practice; the record does not say so, and inferring it is how a finish gets
  manufactured from a rarity label.
* SPEC-0015 says "the reverse showing a standard Pokémon card back". That "reverse" is the back of
  the card, not reverse holo. A regular-expression pass over this corpus would have recorded a
  finish here, which is why this one was read rather than matched.
* SPEC-0012 and SPEC-0021 photograph sealed product; neither states the finish of the card inside.
* SPEC-0022 is a publisher's marketing render and its own record says "nobody inspected a card
  here".
* SPEC-0024 says the printing exists in "Holo and Non-Holo with the same number and set code".
  That is the owner describing the printing, not an observation of which finish the scan shows.
  Assigning either would be a guess; assigning both would make one image establish two printings.

None of this establishes absence. A specimen without a `physicalObservation` says nothing about
the card's finish, exactly as before.

    python verification/passes/record_specimen_finishes_20260809.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SPECIMENS = ROOT / "verification" / "specimens.json"

# The technical finish vocabulary, unchanged: finishFamily is the presentation layer and is not
# stored here. `basis` quotes the record. Where the record does not say it, the field is absent.
OBSERVATIONS = {
    "SPEC-0001": {
        "finish": "holo",
        "foilPattern": None,
        "markings": "Play! Pokémon Prize Pack stamp",
        "markingRole": "distribution-promo",
        "cardSize": "standard",
        "basis": "\"Physical German HOLO specimen inspected from a photograph\"; "
                 "\"This is the holo (V2) printing.\"",
    },
    "SPEC-0006": {
        "finish": "holo",
        "foilPattern": None,
        "markings": "Play! Pokémon Prize Pack stamp",
        "markingRole": "distribution-promo",
        "cardSize": "standard",
        "basis": "\"Physical Portuguese HOLO specimen inspected from a photograph\"; "
                 "\"This is the holo (V2) printing.\"",
    },
    "SPEC-0013": {
        "finish": "mirror-holo",
        "foilPattern": "Poké Ball mirror and Master Ball mirror, one card each",
        "markings": None,
        "markingRole": None,
        "cardSize": "standard",
        # Two cards in one frame. The observation is real; it just cannot establish *a* printing,
        # because it depicts two. SPEC-0019 and SPEC-0020 are the per-card crops that do.
        "coversMultipleCards": True,
        "basis": "\"both carrying a mirror foil pattern\"; \"the technical finish value here is "
                 "mirror-holo, which finishFamily presents as \\\"Reverse Holo\\\"\". This record "
                 "photographs two cards; SPEC-0019 and SPEC-0020 are the per-card crops.",
    },
    "SPEC-0016": {
        "finish": "holo",
        "foilPattern": None,
        "markings": "GameStop logo stamped in red over the lower left of the illustration",
        "markingRole": "distribution-promo",
        "cardSize": "standard",
        "basis": "\"\\\"JTG\\\" \\\"117/159\\\", holo\"; \"The GameStop logo is stamped in red "
                 "over the lower left of the illustration.\"",
    },
    "SPEC-0019": {
        "finish": "mirror-holo",
        "foilPattern": "Poké Ball mirror",
        "markings": None,
        "markingRole": None,
        "cardSize": "standard",
        "basis": "\"carrying a Poké Ball mirror foil pattern\"; \"the ball outlines are legible "
                 "across the text box and lower border at full resolution\".",
    },
    "SPEC-0020": {
        "finish": "mirror-holo",
        "foilPattern": "Master Ball mirror",
        "markings": None,
        "markingRole": None,
        "cardSize": "standard",
        "basis": "\"carrying a Master Ball mirror foil pattern\"; \"The pattern is strong and "
                 "covers the whole face\".",
    },
    "SPEC-0025": {
        "finish": "non-holo",
        "foilPattern": None,
        "markings": None,
        "markingRole": None,
        "cardSize": "standard",
        "basis": "\"The card face is uniformly matte with no foil pattern anywhere, including "
                 "across the artwork window: a non-holo printing.\"",
    },
}

# Read and deliberately not assigned, with the reason. Kept in the pass rather than only in the
# commit message: the next person to look at these will ask why, and the answer is per-specimen.
DELIBERATELY_UNASSIGNED = {
    "SPEC-0008": "states a rarity (rainbow rare / HR), not a finish",
    "SPEC-0010": "states a rarity and art treatment (full art / SR), not a finish",
    "SPEC-0012": "sealed product; the finish of the card inside is not stated",
    "SPEC-0015": "\"the reverse showing a standard Pokémon card back\" is the card's back, not "
                 "reverse holo",
    "SPEC-0021": "sealed box photographed through the window; no finish stated",
    "SPEC-0022": "publisher marketing render; the record itself says nobody inspected a card",
    "SPEC-0024": "owner describes the printing as existing in Holo and Non-Holo; the scan is not "
                 "an observation of which one it shows",
}

FINISHES = {"non-holo", "holo", "reverse-holo", "mirror-holo"}
MARKING_ROLES = {"print-identity", "reverse-holo-treatment", "distribution-promo"}


def main() -> int:
    document = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    records = document["specimens"] if isinstance(document, dict) else document
    by_id = {r["specimenId"]: r for r in records}

    for specimen_id, observation in OBSERVATIONS.items():
        record = by_id.get(specimen_id)
        if record is None:
            print(f"missing specimen {specimen_id}", file=sys.stderr)
            return 1
        if observation["finish"] not in FINISHES:
            print(f"{specimen_id}: {observation['finish']!r} is not a finish", file=sys.stderr)
            return 1
        role = observation.get("markingRole")
        if role is not None and role not in MARKING_ROLES:
            print(f"{specimen_id}: {role!r} is not a marking role", file=sys.stderr)
            return 1
        record["physicalObservation"] = observation

    body = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    SPECIMENS.write_text(body, encoding="utf-8")

    print(f"recorded a physical observation on {len(OBSERVATIONS)} of {len(records)} specimens")
    for specimen_id, observation in sorted(OBSERVATIONS.items()):
        pattern = f" ({observation['foilPattern']})" if observation["foilPattern"] else ""
        print(f"  {specimen_id}  {observation['finish']}{pattern}")
    print(f"\nread and deliberately left without a finish: {len(DELIBERATELY_UNASSIGNED)}")
    for specimen_id, reason in sorted(DELIBERATELY_UNASSIGNED.items()):
        print(f"  {specimen_id}  {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

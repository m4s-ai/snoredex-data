#!/usr/bin/env python3
"""Name the `SV-P/ID 117` ball patterns, and put both units on the photographed cards.

THE DECISION

The owner, shown the Cardmarket scans and their own photograph side by side:

    "V1 is Pokeball and V2 is Masterball, for a human it's visible"

That is the one fact nothing in the store held. Both units were confirmed, but from the same
Bulbapedia set-list row - "117/SV-P Snorlax, 2024 Monthly Promo Card" - which names the card once
and says nothing about foil treatment. Neither product carried a `variantName`. The ordering
happens to match `xsv2a` (V1 Poké Ball, V2 Master Ball) and deliberately was not assumed from it:
`xm2a` reverses exactly that pair, which is why CLAUDE.md says V-tokens never carry across sets.

WHY THE PAIR PHOTOGRAPH IS CUT IN TWO

SPEC-0013 shows both cards in one frame. A specimen record identifies one printing, and check S8
holds a cited specimen to the citing unit's exact `(setCode, number, variant, language)` - so one
record showing two printings cannot be cited by two units without lying to one of them. SPEC-0019
and SPEC-0020 are per-card crops of that frame, each a photograph of exactly one card, and the
uncut original stays as SPEC-0013 so the crops can be checked against it.

`corroborated` stays false on both. Bulbapedia attests that the *card* exists; it does not
distinguish the two ball patterns, so it cannot corroborate a variant-level claim. Recording it as
corroboration would be #64's error - crediting a claim to the strongest thing beside it.

Idempotent: re-running changes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "verification"
RECORDED_AT = "2026-08-04"

PATTERNS = {"V1": "Poké Ball mirror holo", "V2": "Master Ball mirror holo"}
SPEC_FOR = {"V1": "SPEC-0019", "V2": "SPEC-0020"}
UNIT_FOR = {"V1": "U0752", "V2": "U0772"}
SIDE = {"V1": "left", "V2": "right"}

SPECIMENS = [
    ("SPEC-0019", "V1", "Indonesian \"117/SV-P\" Snorlax carrying a Poké Ball mirror foil pattern, "
     "cropped from the owner's side-by-side photograph of the sealed pair (SPEC-0013, left card). "
     "The pattern is faint - faint enough that this project first recorded the card as non-holo - "
     "but the ball outlines are legible across the text box and lower border at full resolution. "
     "Card text: \"Snorlax\", HP 150, Basic, Ability \"Kemaruk\", attack \"Tekanan Gedebuk\" 130, "
     "Illus. HYOGONOSUKE, \"117/SV-P\", PROMO, regulation mark G, ©2024. Still sealed in its promo "
     "wrapper. The owner assigns this pattern to Cardmarket's V1: \"V1 is Pokeball and V2 is "
     "Masterball, for a human it's visible.\""),
    ("SPEC-0020", "V2", "Indonesian \"117/SV-P\" Snorlax carrying a Master Ball mirror foil "
     "pattern, cropped from the owner's side-by-side photograph of the sealed pair (SPEC-0013, "
     "right card). The pattern is strong and covers the whole face; the ball silhouettes carry a "
     "raised top rather than being plain spheres, which is what distinguishes them from the Poké "
     "Ball pattern on SPEC-0019. Card text: \"Snorlax\", HP 150, Basic, Ability \"Kemaruk\", "
     "attack \"Tekanan Gedebuk\" 130, Illus. HYOGONOSUKE, \"117/SV-P\", PROMO, regulation mark G, "
     "©2024. Still sealed in its promo wrapper. The owner assigns this pattern to Cardmarket's V2."),
]

SPEC_0013_SUFFIX = (
    " The owner has since identified the patterns against Cardmarket's tokens - V1 is the Poké "
    "Ball, V2 the Master Ball - and this frame is cut into per-card records SPEC-0019 (left, V1) "
    "and SPEC-0020 (right, V2), which the two units cite. This uncut original is kept so those "
    "crops can be checked against it."
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    spec_path = VERIFICATION / "specimens.json"
    document = read(spec_path)
    by_id = {s["specimenId"]: s for s in document["specimens"]}

    added = 0
    for sid, token, observed in SPECIMENS:
        if sid in by_id:
            continue
        record = {
            "specimenId": sid,
            "setCode": "SV-P/ID",
            "number": "117",
            "variant": token,
            "language": "Indonesian",
            "heldBy": "collection owner",
            "inspectedFrom": "photograph",
            "photograph": None,
            "observed": observed,
            "recordedAt": RECORDED_AT,
            "citedBy": [UNIT_FOR[token]],
        }
        document["specimens"].append(record)
        by_id[sid] = record
        added += 1

    thirteen = by_id.get("SPEC-0013")
    if thirteen and SPEC_0013_SUFFIX.strip() not in thirteen["observed"]:
        thirteen["observed"] = thirteen["observed"].rstrip() + SPEC_0013_SUFFIX
        added = added or 0

    document["specimens"].sort(key=lambda s: s["specimenId"])
    document["count"] = len(document["specimens"])
    write(spec_path, document)

    # The card record is where a variant name is authored; units mirror it.
    cards_path = ROOT / "snorlax_cards.json"
    dataset = read(cards_path)
    cards = dataset["cards"] if isinstance(dataset, dict) else dataset
    named_cards = 0
    for card in cards:
        if card.get("setCode") != "SV-P/ID" or str(card.get("number")) != "117":
            continue
        token = card.get("variantToken")
        if token not in PATTERNS or card.get("variantName") == PATTERNS[token]:
            continue
        card["variantName"] = PATTERNS[token]
        card["variantNameSource"] = "user"
        named_cards += 1
    if named_cards:
        write(cards_path, dataset)

    units_path = VERIFICATION / "units.json"
    units = read(units_path)
    upgraded = 0
    for unit in units:
        if unit["unitId"] not in UNIT_FOR.values():
            continue
        token = unit.get("variant")
        if token not in PATTERNS:
            raise SystemExit(f"{unit['unitId']} has variant {token!r}; expected V1 or V2")
        if unit["unitId"] != UNIT_FOR[token]:
            raise SystemExit(f"{unit['unitId']} does not hold variant {token}")
        if unit["status"] != "confirmed":
            raise SystemExit(f"{unit['unitId']} is {unit['status']}; expected confirmed")
        if unit.get("sourceRef") == f"specimen:{SPEC_FOR[token]}":
            continue
        unit["variantName"] = PATTERNS[token]
        unit["providerId"] = "inspected-specimen"
        unit["sourceRef"] = f"specimen:{SPEC_FOR[token]}"
        unit["sourceUrl"] = None
        # Must not read as a *listing* photograph: resolve_provider matches that first.
        unit["sourceType"] = "Physical card, photographed sealed specimen"
        unit["evidence"] = (
            f"Indonesian 117/SV-P Snorlax with the {PATTERNS[token].replace(' mirror holo', '')} "
            f"mirror foil pattern, read off the owner's photograph of the sealed card - the "
            f"{SIDE[token]} card of the pair in SPEC-0013, cropped as {SPEC_FOR[token]}. Ability "
            f"\"Kemaruk\", attack \"Tekanan Gedebuk\" 130, Illus. HYOGONOSUKE, 117/SV-P, ©2024. "
            f"The owner assigns the pattern to this Cardmarket variant token: \"V1 is Pokeball and "
            f"V2 is Masterball, for a human it's visible.\" This replaces a Bulbapedia set-list "
            f"row that names the card once and does not distinguish the two ball patterns."
        )
        upgraded += 1
    if upgraded:
        write(units_path, units)

    print(f"Added {added} specimen(s), named {named_cards} card variant(s), "
          f"moved {upgraded} unit(s) onto photographed specimens.")


if __name__ == "__main__":
    main()

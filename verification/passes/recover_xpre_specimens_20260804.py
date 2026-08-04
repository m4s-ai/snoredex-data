#!/usr/bin/env python3
"""Recover the `xPRE 076` European evidence stranded on `agent/complete-verification`.

WHY THIS EXISTS

`agent/complete-verification` is an unrelated history — no common ancestor with `main`, its own
initial commit, last touched 2026-08-02 while `main` has moved 164 commits since. Almost all of it
is superseded: its 55 "extra" images are the JPEG originals of files `main` carries as PNG, and its
75 PowerShell scripts are already archived under `verification/archive/passes/`.

Four files were not superseded, and three of them are evidence. That branch's
`verification/specimens/README.md` says the images "are referenced from `verification/units.json`" —
on `main` they are not, because the reference never crossed between the two histories. So eight
`xPRE 076` European units sit on `owner-attestation` with **no `sourceUrl` and no `sourceRef`**: the
weakest checkable form, and part of the "30 units rest on owner attestation alone" figure.

This restores the link for the three languages that have an image.

WHAT EACH IMAGE ACTUALLY IS

They are not the same class of evidence, and are not filed as though they were:

  * **Italian** — a photograph of the sealed box on a desk, cable and mouse in frame. The owner
    holds this product. Filed `inspected-specimen`, which is the one tier-1 class whose claim must
    cite a specimen record (`S14`).
  * **French, Spanish** — publisher product renders, studio-lit with no background. Nobody
    photographed a card. They stay `owner-attestation` and merely gain a `sourceRef`, so the claim
    becomes *checkable* without being upgraded. Filing them as tier-3 retailer images would fail
    `E3`, which requires an uncorroborated claim to be checkable **or** strong: no URL and below
    tier 2 is the one combination it rejects.

Each image shows the standard promo *and* the jumbo. A specimen record identifies one printing and
`S8` holds a cited specimen to the citing unit's exact key, so these are filed against V1 with the
jumbo noted in `observed`. The V2 units keep their attestation until someone crops the jumbo out,
the way SPEC-0019/0020 were cropped from the Indonesian pair.

The Italian photograph was 19.5 MB at 3072x4096. It is stored downscaled to 1600 px, which is far
more than enough to read the box, and keeps the published artifact from growing by a third.

Idempotent: re-running changes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "verification"
RECORDED_AT = "2026-08-04"
BRANCH = "agent/complete-verification"

# specimenId, language, unitId, heldBy, inspectedFrom, providerId, sourceType, observed
RECORDS = [
    ("SPEC-0021", "Italian", "U0100", "collection owner", "photograph",
     "inspected-specimen", "Physical card, photographed sealed product",
     "Sealed Italian \"Collezione Speciale SNORLAX ex E BLISSEY ex\" photographed by the owner on a "
     "desk, cable and mouse in frame. The window shows the standard Snorlax ex promo (PS 260, "
     "\"Forza\", \"Pressa Gira e Rigira\") and the jumbo of the same card, both carrying the "
     "\"Evoluzioni Prismatiche\" stamp, alongside Blissey ex PS 300. Box text: \"CONTIENE: 2 carte "
     "promozionali / 1 carta gigante / 8 buste di espansione\". Italian throughout. This record is "
     "filed against the standard printing (V1); the jumbo (V2, U0314) is visible in the same frame "
     f"but is not separately cited. Recovered from the {BRANCH} history."),
    ("SPEC-0022", "French", "U0097", "publisher or retailer", "product image",
     "owner-attestation", "Owner attestation (domain expert); localized product image",
     "Publisher product render of the French \"Collection Spéciale RONFLEX ex ET LEUPHORIE ex\", "
     "studio-lit with no background — a marketing image, not a photograph of a card. Shows the "
     "jumbo Ronflex ex (260) with the Prismatic Evolutions stamp and the standard promo below it. "
     "French throughout, confirming the localized Special Collection exists. Filed against the "
     "standard printing (V1); the jumbo (V2, U0311) is visible but not separately cited. The unit "
     "keeps owner-attestation authority: nobody inspected a card here, so this makes the claim "
     f"checkable rather than stronger. Recovered from the {BRANCH} history."),
    ("SPEC-0023", "Spanish", "U0099", "publisher or retailer", "product image",
     "owner-attestation", "Owner attestation (domain expert); localized product image",
     "Publisher product render of the Spanish \"Colección Especial SNORLAX ex Y BLISSEY ex\", "
     "studio-lit with no background. Shows the jumbo Snorlax ex (PS 260, \"Fuerza\", \"Presionar y "
     "Dar Vueltas\") and the standard promo, with Blissey ex 300. Spanish throughout. Filed against "
     "the standard printing (V1); the jumbo (V2, U0313) is visible but not separately cited. The "
     "unit keeps owner-attestation authority — this makes the claim checkable rather than stronger. "
     f"Recovered from the {BRANCH} history."),
]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    spec_path = VERIFICATION / "specimens.json"
    document = read(spec_path)
    known = {s["specimenId"] for s in document["specimens"]}

    units_path = VERIFICATION / "units.json"
    units = read(units_path)
    by_id = {u["unitId"]: u for u in units}

    added = linked = 0
    for sid, language, unit_id, held_by, inspected, provider, source_type, observed in RECORDS:
        unit = by_id.get(unit_id)
        if unit is None:
            raise SystemExit(f"unknown unit {unit_id}")
        if (unit["setCode"], str(unit["number"]), unit.get("variant"), unit["language"]) != (
                "xPRE", "076", "V1", language):
            raise SystemExit(f"{unit_id} is not xPRE 076 V1 {language}")
        if unit["status"] != "confirmed":
            raise SystemExit(f"{unit_id} is {unit['status']}; expected confirmed")

        if sid not in known:
            document["specimens"].append({
                "specimenId": sid,
                "setCode": "xPRE",
                "number": "076",
                "variant": "V1",
                "language": language,
                "heldBy": held_by,
                "inspectedFrom": inspected,
                "photograph": None,
                "observed": observed,
                "recordedAt": RECORDED_AT,
                "citedBy": [unit_id],
            })
            known.add(sid)
            added += 1

        if unit.get("sourceRef") != f"specimen:{sid}":
            unit["providerId"] = provider
            unit["sourceType"] = source_type
            unit["sourceRef"] = f"specimen:{sid}"
            linked += 1

    if added:
        document["specimens"].sort(key=lambda s: s["specimenId"])
        document["count"] = len(document["specimens"])
        write(spec_path, document)
    if linked:
        write(units_path, units)

    print(f"Added {added} specimen record(s); linked {linked} unit(s) to recovered evidence. "
          f"{len(document['specimens'])} specimens total.")


if __name__ == "__main__":
    main()

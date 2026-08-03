#!/usr/bin/env python3
"""File the remaining owner photographs, and re-grade U0452 now that its card has been examined.

THE CORRECTION THAT MATTERS

SPEC-0013 was recorded yesterday as "the left copy is non-holo; the right copy carries a Poké Ball
mirror foil pattern". Both halves were wrong. The owner corrects it:

    "For the Indonesian side by side left is Pokeball very faint reverse holo, right is master ball
     (shape of ball is different) reverse holo"

So the image shows *both* mirror patterns, not one mirror and one plain card, and the one I called
Poké Ball is the Master Ball. The faintness of the left pattern is what I misread as absence. That
makes the image stronger evidence than the record claimed, not weaker: it is the direct observation
behind both Indonesian adjudications rather than only U0782's.

The owner writes "reverse holo"; this project's technical `finish` value for the pattern is
`mirror-holo`, which `finishFamily` presents as "Reverse Holo". Same card, different layer of the
model — recorded in the project's terms with the owner's wording quoted.

U0452 MOVES TO TIER 1

The French GameStop Hop's Snorlax was recorded on 2026-08-03 as an owner attestation, because the
photograph was behind a host this session cannot reach and #64's lesson is to grade a claim by what
it actually rests on. The photograph has now been supplied and examined, so the claim rests on the
card: provider `inspected-specimen`, `sourceRef` pointing at SPEC-0016. Checks S13 and S14 require
exactly this pairing before specimen authority may be claimed.

Idempotent: re-running changes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "verification"
RECORDED_AT = "2026-08-04"

OWNER = "collection owner"

SPEC_0013_OBSERVED = (
    "Two sealed Indonesian \"117/SV-P\" Snorlax promos photographed side by side by the owner, "
    "both carrying a mirror foil pattern. The owner identifies them: \"left is Pokeball very faint "
    "reverse holo, right is master ball (shape of ball is different) reverse holo\". The left "
    "pattern is faint enough to read as a non-holo card at a glance, which is how this record "
    "first described it; the ball silhouettes distinguish the two. Card text as SPEC-0012 "
    "(Ability \"Kemaruk\", \"Tekanan Gedebuk\" 130, Illus. HYOGONOSUKE, ©2024). This single image "
    "is therefore the direct observation behind both Indonesian decisions - the Poké Ball mirror "
    "(U0782) and the Master Ball mirror (U0777) - each existing as an SV-P promo rather than as an "
    "xsv2a 143 printing. \"Reverse holo\" is the owner's wording; the technical finish value here "
    "is mirror-holo, which finishFamily presents as \"Reverse Holo\"."
)

# specimenId, setCode, number, variant, language, heldBy, inspectedFrom, observed
RECORDS = [
    ("SPEC-0016", "xJTG", "117", "V2", "French", OWNER, "photograph",
     "French GameStop-stamped Hop's Snorlax, sealed in its promo wrapper, photographed by the "
     "owner: \"Ronflex de Nabil\", PV 150, Basic, Talent \"Portions Supplémentaires\" (attacks by "
     "your Pokémon inflict 30 extra damage on the Active Pokémon, before Weakness and Resistance, "
     "not cumulative), attack \"Pression Dynamique\" 140 with 80 recoil, \"N° 0143 Pokémon "
     "Ronfleur, Taille 2,1 m, Poids 460,0 kg\", Illus. GOSSAN, \"JTG\" \"117/159\", holo. The "
     "GameStop logo is stamped in red over the lower left of the illustration. French-language text "
     "throughout. This is the card behind the overturn of U0452: the contradiction had reasoned "
     "that every documented printing went to an English-language retail market, and GameStop "
     "trades in bilingual Canada."),
    ("SPEC-0017", "HXY", "026", "base", "Japanese", OWNER, "photograph",
     "Japanese Snorlax from the XY Beginning Set: \"カビゴン\", HP 120, Colorless, Basic, attacks "
     "「いわだき」 10+ (flip a coin, +30 on heads) and 「かいりき」 70, Illus. Naoki Saito, "
     "\"026/039\", with the set's magazine-style circular mark at the lower right of the card. "
     "Japanese-language text throughout. The owner supplies this against #86 to show that the "
     "Kalos Starter Set card exists in Japanese as its own product under the HXY code rather than "
     "as a KSS 26 language."),
    ("SPEC-0018", "HXY", "026", "base", "Korean", OWNER, "photograph",
     "Korean counterpart of the same card: \"잠만보\", HP 120, Colorless, Basic, attacks "
     "「바위깨기」 10+ and 「괴력」 70, numbered \"026/039\" to match the Japanese printing. "
     "Korean-language text throughout. Supplied against #86 alongside SPEC-0017; the owner states "
     "the Korean edition carries the code FXY where the Japanese carries HXY, and the set glyph is "
     "not legible at the supplied resolution, so the FXY code is the owner's identification rather "
     "than something read off this image. Filed under the catalogue's HXY 026 identity, which is "
     "how this project groups the printing."),
]

U0452_UPGRADE = {
    "providerId": "inspected-specimen",
    "sourceRef": "specimen:SPEC-0016",
    "sourceType": "Inspected physical specimen (photograph of the sealed card); GameStop bilingual "
                  "Canadian distribution",
    "evidence": (
        "French printing of the GameStop-stamped Hop's Snorlax, confirmed from the card itself: "
        "\"Ronflex de Nabil\", PV 150, Talent \"Portions Supplémentaires\", attack \"Pression "
        "Dynamique\" 140, Illus. GOSSAN, JTG 117/159, GameStop logo stamped over the illustration, "
        "sealed in its promo wrapper. See specimen:SPEC-0016. The owner's reasoning for why it "
        "exists stands - GameStop trades in Canada as well as the USA, and Canada is bilingual - "
        "but the claim no longer rests on that reasoning: it rests on the photographed card. This "
        "overturns a contradiction that had argued from the absence of a recorded localized run, "
        "the same argument shape that produced the false XY-P 149 contradiction."
    ),
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    spec_path = VERIFICATION / "specimens.json"
    document = read(spec_path)
    by_id = {s["specimenId"]: s for s in document["specimens"]}
    changed = False

    corrected = 0
    thirteen = by_id.get("SPEC-0013")
    if thirteen and thirteen["observed"] != SPEC_0013_OBSERVED:
        thirteen["observed"] = SPEC_0013_OBSERVED
        corrected, changed = 1, True

    added = 0
    for sid, set_code, number, variant, language, held_by, inspected, observed in RECORDS:
        if sid in by_id:
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
        changed = True

    if changed:
        document["specimens"].sort(key=lambda s: s["specimenId"])
        document["count"] = len(document["specimens"])
        write(spec_path, document)

    # U0452: the photograph arrived, so the claim is re-graded onto the card.
    units_path = VERIFICATION / "units.json"
    units = read(units_path)
    upgraded = 0
    for unit in units:
        if unit["unitId"] != "U0452":
            continue
        if unit.get("sourceRef") == U0452_UPGRADE["sourceRef"]:
            break
        if unit["status"] != "confirmed":
            raise SystemExit(f"U0452 is {unit['status']}; expected confirmed")
        unit.update(U0452_UPGRADE)
        upgraded = 1
        write(units_path, units)
        break

    if upgraded:
        spec = by_id.get("SPEC-0016") or next(
            s for s in document["specimens"] if s["specimenId"] == "SPEC-0016")
        if "U0452" not in spec["citedBy"]:
            spec["citedBy"].append("U0452")
            write(spec_path, document)

    print(f"Added {added} specimen record(s), corrected {corrected}, upgraded {upgraded} unit(s) "
          f"to specimen authority. {len(document['specimens'])} specimens total.")


if __name__ == "__main__":
    main()

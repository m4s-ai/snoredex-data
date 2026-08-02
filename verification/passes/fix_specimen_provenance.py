#!/usr/bin/env python3
"""Attribute the Prize Pack language claims to the source that actually carries them (#64).

Fourteen `PPS7 JTG` / `PPS8 JTG` `JTG 117` units were stored with
`providerId: photographed-specimen` — the registry's tier 1, ranked above an official database.
Their evidence has always said something different, and said it plainly:

    "Owner (domain expert) confirms that Play! Pokemon Prize Pack Series Seven and Eight were
     both distributed ... This unit (a non-DE/PT language) rests on the owner attestation plus
     the uniform per-region Prize Pack distribution the corroborated languages demonstrate."

So the prose was right and the machine field was wrong: `providerId` had been set to the strongest
item in the corroboration mix rather than to the source the claim rests on. Only one specimen
exists in that family — `SPEC-0001`, the German *holo* (`PPS8` V2) — and it covers exactly one
unit, `U0189`. There is no Italian, Spanish, French or English specimen, and the German V1 and
`PPS7` rows are a different printing from the one that was inspected.

`scripts/source_registry.py` had already noticed. It derives a provider from the `sourceType`
text rather than from the stored field, and for all fourteen it resolves `owner-attestation` — so
the repository held two computations of the same fact that disagreed, and the generated registry
was the one telling the truth. This pass makes the store agree with it.

Three changes, all provenance; no verdict moves and no evidence text is rewritten:

  1. The fourteen units become `owner-attestation`, uncorroborated. `corroborated` records whether
     a second provider agreed *about this unit*; for Italian `PPS8` V1 none did. LigaPokemon
     evidenced Portuguese and the specimen was German, which corroborates neighbouring units of
     the same product, not this one. The published attestation-only count therefore moves 16 -> 30,
     which is the figure the #32 review independently arrived at before the relabelling.

  2. `SPEC-0006` registers the Portuguese holo specimen that `U0192` had been describing in prose.
     It is a real inspected card and the repository already relied on it; it simply had no id, and
     an id is what lets a third party re-check it.

  3. Thirty prose `sourceRef` strings are cleared. A reference field holding
     "(owner attestation, corroborated by LigaPokemon + photographed specimens)" is a sentence, not
     a reference. Every one duplicates its unit's `sourceType` or `evidence`, so nothing is lost —
     `close_language_review.py` already set `sourceRef` to None for the units it touched, and this
     finishes that convention.

Nothing is appended to `evidence.jsonl` and no `checkedAt` moves. The journal records what was
observed and when; no new observation was made here, and the evidence text each unit carries is
unchanged. Touching either would date the owner's attestation to today and push the evidence
class's `retrievedAt` forward in the generated registry, asserting a re-check that did not happen.
The record of *this* correction is this file, which is what a pass is for.

Idempotent: re-running changes nothing and prints a zero count.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "verification"

# The claim these fourteen rest on is the owner's, and the sourceType is rewritten to say which
# neighbouring units the corroboration actually belongs to. It must not contain the word
# "photograph": scripts/source_registry.py resolves the provider from this text.
ATTESTATION_SOURCE_TYPE = (
    "Owner attestation (domain expert); German and Portuguese units of the same product "
    "independently sourced"
)

RELABELLED = [
    "U0187", "U0188", "U0190", "U0191",                    # PPS8 V2 (holo)   EN/FR/ES/IT
    "U0214", "U0215", "U0216", "U0217", "U0218",           # PPS8 V1          EN/FR/DE/ES/IT
    "U0324", "U0325", "U0326", "U0327", "U0328",           # PPS7 base        EN/FR/DE/ES/IT
]

# U0189 (PPS8 V2 German) keeps photographed-specimen: SPEC-0001 is that exact printing.

SPEC_0006 = {
    "specimenId": "SPEC-0006",
    "setCode": "PPS8 JTG",
    "number": "JTG 117",
    "variant": "V2",
    "language": "Portuguese",
    "heldBy": "collection owner",
    "inspectedFrom": "photograph",
    "photograph": None,
    "observed": (
        "Physical Portuguese HOLO specimen inspected from a photograph: \"Snorlax do Lupo\", "
        "Habilidade \"Boca-livre\", attack \"Compressao Dinamica\" 140, \"JTG PT 117/159\", "
        "Play! Pokemon Prize Pack stamp, (c)2025. This is the holo (V2) printing. The card face "
        "does not distinguish PPS7 from PPS8; PPS8 is the owner attribution. Recorded from the "
        "inspection already described in U0192, which cited it in prose before specimen ids "
        "existed."
    ),
    "recordedAt": "2026-07-23",
    "citedBy": ["U0192"],
}

# Every sourceRef below is a sentence rather than a reference, and every one restates its unit's
# own sourceType or evidence. U0192 is the exception: it gains a real reference instead.
PROSE_REFS = {
    "(owner attestation, corroborated by LigaPokemon + photographed specimens)",
    "(owner attestation, domain expert)",
    "(owner attestation, domain expert; MEGA Dream ex release schedule)",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload) -> None:
    """Match the byte shape every other writer here produces, so the diff is the change itself."""
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    units_path = VERIFICATION / "units.json"
    units = read_json(units_path)
    by_id = {u["unitId"]: u for u in units}

    missing = [uid for uid in [*RELABELLED, "U0189", "U0192"] if uid not in by_id]
    if missing:
        raise SystemExit(f"Missing expected units: {', '.join(missing)}")

    now = datetime.now().isoformat(timespec="seconds")
    relabelled = refs_cleared = 0

    for unit_id in RELABELLED:
        unit = by_id[unit_id]
        if unit["status"] != "confirmed":
            raise SystemExit(f"{unit_id}: expected a confirmed unit, found {unit['status']!r}")
        if unit.get("providerId") not in ("photographed-specimen", "owner-attestation"):
            raise SystemExit(f"{unit_id}: unexpected providerId {unit.get('providerId')!r}")
        wanted = {
            "providerId": "owner-attestation",
            "corroborated": False,
            "sourceType": ATTESTATION_SOURCE_TYPE,
        }
        if any(unit.get(k) != v for k, v in wanted.items()):
            unit.update(wanted)
            relabelled += 1

    # The Portuguese holo specimen gets an id, and the unit that described it cites it instead.
    specimens_path = VERIFICATION / "specimens.json"
    specimen_doc = read_json(specimens_path)
    known = {s["specimenId"] for s in specimen_doc["specimens"]}
    if SPEC_0006["specimenId"] not in known:
        specimen_doc["specimens"].append(SPEC_0006)
        specimen_doc["count"] = len(specimen_doc["specimens"])
        write_json(specimens_path, specimen_doc)
        print(f"registered {SPEC_0006['specimenId']} ({SPEC_0006['language']} holo)")

    if by_id["U0192"].get("sourceRef") != "specimen:SPEC-0006":
        by_id["U0192"]["sourceRef"] = "specimen:SPEC-0006"

    # A reference field may hold a reference or nothing. Prose belongs in evidence.
    for unit in units:
        if unit.get("sourceRef") in PROSE_REFS:
            unit["sourceRef"] = None
            refs_cleared += 1

    write_json(units_path, units)

    state = {"phase": "specimen-provenance-correction", "completedAt": now}
    write_json(VERIFICATION / "state.json", state)

    print(f"Relabelled {relabelled} unit(s) to owner-attestation; "
          f"cleared {refs_cleared} prose sourceRef(s); state={state['phase']}")


if __name__ == "__main__":
    main()

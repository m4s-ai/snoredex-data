#!/usr/bin/env python3
"""Admit U0558's owner-supplied AS5a 222/184 Traditional-Chinese printing.

The photograph supplied for issue #84 shows the rainbow Eevee & Snorlax-GX with the AS5a
symbol and 222/184.  The 52poke SM9 page independently lists that same local printing as
Traditional Chinese HR.  This pass records the local print and the positive same-work re-key;
it does not rewrite the legacy ``units.json`` row or infer a finish in the catalogue layer.

Idempotent: re-running changes neither store twice.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRINTS = ROOT / "verification" / "source_first_prints.json"
REKEYS = ROOT / "verification" / "legacy_issue_rekeys.json"
SPECIMENS = ROOT / "verification" / "specimens.json"

ISSUE_COMMENT = "https://github.com/m4s-ai/snoredex-data/issues/84#issuecomment-5367641859"
PHOTO_URL = "https://raw.githubusercontent.com/m4s-ai/snoredex-data/e8fdc2d8cdf3017b1f4ff6436546dcc63930e378/verification/specimens/SPEC-0038.png"
CARD_PAGE = "https://wiki.52poke.com/zh-hant/%E4%BC%8A%E5%B8%83%26%E5%8D%A1%E6%AF%94%E7%8D%B8GX%EF%BC%88SM9%EF%BC%89"
SET_PAGE = "https://wiki.52poke.com/wiki/AS5a"
PRINT_ID = "TW:AS5a:222/184:base"

PRINT = {
    "printId": PRINT_ID,
    "locality": "TW",
    "localSetCode": "AS5a",
    "localNumber": "222/184",
    "variant": "base",
    "language": "T-Chinese",
    "script": "Hant",
    "name": "伊布&卡比獸GX",
    "cardName": "Eevee & Snorlax-GX",
    "catchUpOf": "the printing Cardmarket lists as sm9 115 V3",
    "specimenId": "SPEC-0038",
    "providerId": "52poke",
    "sourceUrl": CARD_PAGE,
    "corroborated": True,
    "markAssetUrl": None,
    "cardImageUrl": None,
    "evidence": (
        "The owner-supplied photograph filed as SPEC-0038 reads Traditional Chinese "
        "伊布&卡比獸GX, carries the AS5a symbol and 222/184, and shows the rainbow treatment. "
        "The 52poke SM9 card record independently lists the Traditional-Chinese Double Blaze "
        "SET A printing as HR 222/184, while the AS5a checklist names 222/184 as "
        "伊布&卡比獸GX HR. This establishes the local printing and its same-work relationship "
        "to legacy U0558 (sm9 115 V3); no catalogue finish is projected from the photograph."
    ),
}

MAPPING = {
    "legacyUnitId": "U0558",
    "sourceFirstRecordId": PRINT_ID,
    "assertionType": "same-work-decision",
    "assertedBy": "Scarrty",
    "assertedAt": "2026-08-21",
    "evidenceUrl": ISSUE_COMMENT,
    "evidence": (
        "The owner identifies the photographed Traditional-Chinese Eevee & Snorlax-GX as "
        "AS5a 222/184 HR, and the 52poke card record independently lists that same local "
        "printing. It is the AS5a counterpart of legacy U0558 (sm9 115 V3); both release "
        "identities remain distinct."
    ),
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    specimens = read(SPECIMENS)["specimens"]
    specimen = next((row for row in specimens if row["specimenId"] == "SPEC-0038"), None)
    if specimen is None:
        raise SystemExit("SPEC-0038 is required before admitting the print")
    if (specimen["setCode"], str(specimen["number"]), specimen["language"]) != (
        "AS5a", "222/184", "T-Chinese"
    ):
        raise SystemExit("SPEC-0038 identity drifted")
    if specimen.get("photographSource") != PHOTO_URL:
        raise SystemExit("SPEC-0038 photograph provenance drifted")

    prints = read(PRINTS)
    existing = {row["printId"]: row for row in prints["prints"]}
    if PRINT_ID in existing and existing[PRINT_ID] != PRINT:
        raise SystemExit(f"{PRINT_ID} exists with different data")
    if PRINT_ID not in existing:
        prints["prints"].append(PRINT)
        prints["prints"].sort(key=lambda row: row["printId"])
    prints.setdefault("meta", {})["generated"] = "2026-08-21"
    prints["meta"].setdefault("counts", {})["admitted"] = len(prints["prints"])
    write(PRINTS, prints)

    rekeys = read(REKEYS)
    question_set = next(
        (row for row in rekeys["questionSets"] if row["issueNumber"] == 84), None
    )
    if question_set is None:
        raise SystemExit("issue #84 re-key question set is missing")
    mappings = question_set.setdefault("mappings", [])
    mapping_by_unit = {row["legacyUnitId"]: row for row in mappings}
    if "U0558" in mapping_by_unit and mapping_by_unit["U0558"] != MAPPING:
        raise SystemExit("U0558 already has a different re-key mapping")
    if "U0558" not in mapping_by_unit:
        mappings.append(MAPPING)
        mappings.sort(key=lambda row: row["legacyUnitId"])
    write(REKEYS, rekeys)
    print(f"admitted {PRINT_ID} and mapped U0558 ({len(prints['prints'])} source-first prints)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

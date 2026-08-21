#!/usr/bin/env python3
"""Admit the remaining positive Traditional-Chinese issue #84 re-key targets.

U0414 and U0634 have positive local identities in the owner's issue comments, backed by
the official Taiwan card record or 52poke's Traditional-Chinese AS5a listings.  They are
separate local releases of the legacy Japanese works; this pass never merges release ids.

Idempotent: re-running changes neither store twice.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRINTS = ROOT / "verification" / "source_first_prints.json"
REKEYS = ROOT / "verification" / "legacy_issue_rekeys.json"
SPECIMENS = ROOT / "verification" / "specimens.json"

CARD_PAGE = "https://wiki.52poke.com/zh-hant/%E4%BC%8A%E5%B8%83%26%E5%8D%A1%E6%AF%94%E7%8D%B8GX%EF%BC%88SM9%EF%BC%89"
CHECKLIST_PAGE = "https://wiki.52poke.com/zh-hant/%E5%8F%8C%E5%80%8D%E7%88%86%E6%93%8A_SET_A%EF%BC%88TCG%EF%BC%89"
U0634_PHOTO_URL = (
    "https://raw.githubusercontent.com/m4s-ai/snoredex-data/"
    "e300898c854f4dba71eaff7ec5a4ac192bf7be85/verification/specimens/SPEC-0039.png"
)

SPECIMEN_TO_ADD = {
    "specimenId": "SPEC-0039",
    "setCode": "AS5a",
    "number": "203/184",
    "variant": "base",
    "language": "T-Chinese",
    "heldBy": "collection owner",
    "inspectedFrom": "owner photograph",
    "photograph": "SPEC-0039.png",
    "photographSource": U0634_PHOTO_URL,
    "observed": (
        "Traditional Chinese Eevee & Snorlax-GX photographed by the owner and supplied "
        "through issue #84: the card reads 伊布&卡比獸GX, carries the AS5a set mark and "
        "collector number 203/184, and is the SR local counterpart of legacy U0634."
    ),
    "recordedAt": "2026-08-21",
    "citedBy": ["TW:AS5a:203/184:base"],
}

PRINTS_TO_ADD = [
    {
        "printId": "TW:AS5a:117/184:base",
        "locality": "TW",
        "localSetCode": "AS5a",
        "localNumber": "117/184",
        "variant": "base",
        "language": "T-Chinese",
        "script": "Hant",
        "name": "伊布&卡比獸GX",
        "cardName": "Eevee & Snorlax-GX",
        "catchUpOf": "the printing Cardmarket lists as sm9 066 V1",
        "specimenId": None,
        "providerId": "pokemon-card-asia",
        "sourceUrl": "https://asia.pokemon-card.com/tw/card-search/detail/2856/",
        "corroborated": True,
        "markAssetUrl": None,
        "cardImageUrl": "https://asia.pokemon-card.com/tw/card-img/tw00002856.png",
        "evidence": (
            "The official Pokémon Taiwan card record identifies the Traditional-Chinese "
            "Eevee & Snorlax-GX as AS5a 117/184. The Traditional-Chinese AS5a checklist "
            "independently lists 117/184 伊布&卡比獸GX RR. This establishes the separate "
            "local release as the same work as legacy U0414 (sm9 066 V1); no finish is "
            "projected beyond the cited RR identity."
        ),
    },
    {
        "printId": "TW:AS5a:203/184:base",
        "locality": "TW",
        "localSetCode": "AS5a",
        "localNumber": "203/184",
        "variant": "base",
        "language": "T-Chinese",
        "script": "Hant",
        "name": "伊布&卡比獸GX",
        "cardName": "Eevee & Snorlax-GX",
        "catchUpOf": "the printing Cardmarket lists as sm9 106 V2",
        "specimenId": "SPEC-0039",
        "providerId": "52poke",
        "sourceUrl": CARD_PAGE,
        "corroborated": True,
        "markAssetUrl": None,
        "cardImageUrl": None,
        "evidence": (
            "The 52poke Eevee & Snorlax-GX card record lists the Traditional-Chinese "
            "AS5a printing as SR 203/184 and the AS5a checklist independently names "
            "203/184 伊布&卡比獸GX SR. The owner-supplied photograph retained as "
            "SPEC-0039 independently reads the same AS5a 203/184 identity. This establishes "
            "the separate local release as the same work as legacy U0634 (sm9 106 V2); no "
            "finish is projected beyond the cited SR identity."
        ),
    },
]

MAPPINGS_TO_ADD = [
    {
        "legacyUnitId": "U0414",
        "sourceFirstRecordId": "TW:AS5a:117/184:base",
        "assertionType": "same-work-decision",
        "assertedBy": "Scarrty",
        "assertedAt": "2026-08-21",
        "evidenceUrl": "https://github.com/m4s-ai/snoredex-data/issues/84#issuecomment-5366842409",
        "evidence": (
            "The owner identifies the Traditional-Chinese Eevee & Snorlax-GX as AS5a "
            "117/184, and the official Taiwan record plus AS5a checklist corroborate "
            "that local release. It is the AS5a counterpart of legacy U0414 (sm9 066 V1); "
            "both release identities remain distinct."
        ),
    },
    {
        "legacyUnitId": "U0634",
        "sourceFirstRecordId": "TW:AS5a:203/184:base",
        "assertionType": "same-work-decision",
        "assertedBy": "Scarrty",
        "assertedAt": "2026-08-21",
        "evidenceUrl": "https://github.com/m4s-ai/snoredex-data/issues/84#issuecomment-5366877127",
        "evidence": (
            "The owner identifies the Traditional-Chinese Eevee & Snorlax-GX as AS5a "
            "203/184, and 52poke independently lists that local SR printing. It is the "
            "AS5a counterpart of legacy U0634 (sm9 106 V2); both release identities remain "
            "distinct."
        ),
    },
]


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    specimens = read(SPECIMENS)
    existing_specimens = {row["specimenId"]: row for row in specimens["specimens"]}
    current_specimen = existing_specimens.get(SPECIMEN_TO_ADD["specimenId"])
    if current_specimen is not None and current_specimen != SPECIMEN_TO_ADD:
        raise SystemExit("SPEC-0039 exists with different data")
    if current_specimen is None:
        specimens["specimens"].append(SPECIMEN_TO_ADD)
        specimens["specimens"].sort(key=lambda row: row["specimenId"])
        specimens["count"] = len(specimens["specimens"])
        write(SPECIMENS, specimens)

    prints = read(PRINTS)
    existing_prints = {row["printId"]: row for row in prints["prints"]}
    for record in PRINTS_TO_ADD:
        current = existing_prints.get(record["printId"])
        if current is not None and current != record:
            if (
                record["printId"] == "TW:AS5a:203/184:base"
                and current.get("specimenId") is None
            ):
                existing_prints[record["printId"]] = record
            else:
                raise SystemExit(f"{record['printId']} exists with different data")
        elif current is None:
            existing_prints[record["printId"]] = record
    prints["prints"] = sorted(existing_prints.values(), key=lambda row: row["printId"])
    prints.setdefault("meta", {})["generated"] = "2026-08-21"
    prints["meta"].setdefault("counts", {})["admitted"] = len(prints["prints"])
    write(PRINTS, prints)

    rekeys = read(REKEYS)
    question_set = next((row for row in rekeys["questionSets"] if row["issueNumber"] == 84), None)
    if question_set is None:
        raise SystemExit("issue #84 re-key question set is missing")
    mappings = question_set.setdefault("mappings", [])
    by_unit = {row["legacyUnitId"]: row for row in mappings}
    for mapping in MAPPINGS_TO_ADD:
        current = by_unit.get(mapping["legacyUnitId"])
        if current is not None and current != mapping:
            raise SystemExit(f"{mapping['legacyUnitId']} already has a different re-key mapping")
        if current is None:
            mappings.append(mapping)
    mappings.sort(key=lambda row: row["legacyUnitId"])
    write(REKEYS, rekeys)
    print(f"admitted {len(PRINTS_TO_ADD)} AS5a prints and mapped U0414/U0634 ({len(prints['prints'])} source-first prints)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Disposition the Korean Burning Confrontation 30/40 specimen from issue #88 (#233).

The owner identified SPEC-0037 as the Korean Series 2 Burning Confrontation Snorlax Lv.35,
number 30/40.  That positive local identity already supports the U0477 adjudication, but the
specimen remained an orphan in the #140 migration dry-run. The retained evidence does not state a
source-native local set code: `BCR` was an internal abbreviation and also names the unrelated
Western Boundaries Crossed set. The specimen therefore enters the explicit held queue instead of
minting an identity from that abbreviation.

This pass preserves the positively identified Korean set name and number without asserting a local
set code, finish, or work equivalence to Japanese DP1.

    python verification/passes/admit_korean_burning_confrontation_20260820.py
"""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PRINTS = ROOT / "verification" / "source_first_prints.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
SETS = ROOT / "verification" / "set_catalogue_sources.json"

RETRACTED_ENTRY = {
    "printId": "KR:BCR:30/40:base",
    "locality": "KR",
    "localSetCode": "BCR",
    "localNumber": "30/40",
    "variant": "base",
    "language": "Korean",
    "script": "Hang",
    "name": "잠만보",
    "cardName": "Snorlax Lv.35",
    "catchUpOf": "the legacy Japanese DP1 Snorlax Lv.35 work; equivalence is not admitted here",
    "specimenId": "SPEC-0037",
    "providerId": "inspected-specimen",
    "sourceUrl": "https://github.com/user-attachments/assets/27f7d3f3-f5db-4ce2-a7a3-98e0a6e054a1",
    "corroborated": True,
    "markAssetUrl": None,
    "cardImageUrl": None,
    "evidence": (
        "The owner photographed and identified SPEC-0037 in issue #88 as the Korean Series 2 "
        "Burning Confrontation Snorlax Lv.35, number 30/40. The cwtcg listing cited in the same "
        "thread independently names 잠만보 and Burning Confrontation 30/40. The low-resolution "
        "photograph does not support a finish claim. This record establishes only the Korean "
        "local release and its identifiers; equivalence to the Japanese DP1 work remains "
        "unadmitted under ADR-0001 I5."
    ),
}


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:12].upper()}"


SET_PROFILE = {
    "sourceRecordId": stable_id("SET-SRC-SF", "KR", "BCR"),
    "sourceKind": "source-first-local-set-profile",
    "provider": "mixed-positive-evidence",
    "providerRecordKey": "KR\x1fBCR",
    "retrieved": "2026-08-20",
    "raw": {
        "localCode": "BCR",
        "localName": None,
        "locality": "KR",
        "languages": ["Korean"],
        "scripts": ["Hang"],
        "printIds": [RETRACTED_ENTRY["printId"]],
        "providers": ["inspected-specimen"],
        "sourceUrls": [RETRACTED_ENTRY["sourceUrl"]],
        "printedSetSize": 40,
        "printedSetSizeBasis": "the denominator in the positively identified 30/40 card number",
        "localeSuffix": None,
        "observedCollectorNumbers": ["30/40"],
        "observedCoverage": (
            "one owner specimen and its referenced Korean retailer listing, not a set enumeration"
        ),
        "markAssetUrls": [],
        "cardImageUrls": [],
    },
}

HELD_ENTRY = {
    "specimenId": "SPEC-0037",
    "proposedSetCode": None,
    "localNumber": "30/40",
    "language": "Korean",
    "blockedBy": (
        "the retained owner photograph and retailer reference establish Burning Confrontation "
        "Series 2 and 30/40, but do not state a source-native Korean local set code"
    ),
    "reason": (
        "BCR was an internal abbreviation and already identifies the unrelated Western "
        "Boundaries Crossed set. Positive evidence does not permit using it as the Korean raw "
        "identifier; hold until a source-native code is recorded."
    ),
}


def main() -> int:
    specimen_document = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    specimens = specimen_document["specimens"]
    specimen = next((row for row in specimens if row["specimenId"] == "SPEC-0037"), None)
    expected_specimen_keys = {
        ("BCR", "30/40", "base", "Korean"),
        ("", "30/40", "base", "Korean"),
    }
    actual_specimen_key = None if specimen is None else (
        specimen["setCode"], str(specimen["number"]), specimen["variant"], specimen["language"]
    )
    if actual_specimen_key not in expected_specimen_keys:
        raise ValueError(
            f"SPEC-0037 identity drift: expected one of {expected_specimen_keys}, "
            f"got {actual_specimen_key}"
        )
    specimen["setCode"] = ""

    document = json.loads(PRINTS.read_text(encoding="utf-8"))
    matches = [
        row for row in document["prints"]
        if row["printId"] == RETRACTED_ENTRY["printId"]
    ]
    if len(matches) > 1:
        raise ValueError(f"duplicate source-first print {RETRACTED_ENTRY['printId']}")
    if matches and matches[0] != RETRACTED_ENTRY:
        raise ValueError(f"retracted source-first print drifted: {RETRACTED_ENTRY['printId']}")
    if matches:
        document["prints"].remove(matches[0])

    held_matches = [
        row for row in document.get("held", []) if row["specimenId"] == HELD_ENTRY["specimenId"]
    ]
    if len(held_matches) > 1:
        raise ValueError(f"duplicate held specimen {HELD_ENTRY['specimenId']}")
    if held_matches and held_matches[0] != HELD_ENTRY:
        raise ValueError(f"held specimen drifted: {HELD_ENTRY['specimenId']}")
    if not held_matches:
        document.setdefault("held", []).append(HELD_ENTRY)
    document["meta"]["generated"] = "2026-08-20"
    document["meta"]["counts"] = {
        "admitted": len(document["prints"]),
        "held": len(document.get("held", [])),
    }
    set_document = json.loads(SETS.read_text(encoding="utf-8"))
    set_matches = [
        row for row in set_document["sourceRecords"]
        if row["providerRecordKey"] == SET_PROFILE["providerRecordKey"]
    ]
    if len(set_matches) > 1:
        raise ValueError(f"duplicate local-set profile {SET_PROFILE['providerRecordKey']!r}")
    if set_matches and set_matches[0] != SET_PROFILE:
        raise ValueError(f"existing local-set profile drifted: {SET_PROFILE['providerRecordKey']!r}")
    if set_matches:
        set_document["sourceRecords"].remove(set_matches[0])
    set_document["meta"]["counts"]["sourceRecords"] = len(set_document["sourceRecords"])
    set_document["meta"]["counts"]["sourceFirstLocalSets"] = sum(
        row["sourceKind"] == "source-first-local-set-profile"
        for row in set_document["sourceRecords"]
    )
    PRINTS.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    SETS.write_text(
        json.dumps(set_document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    specimen_document["count"] = len(specimens)
    SPECIMENS.write_text(
        json.dumps(specimen_document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"held {HELD_ENTRY['specimenId']} with its local set code unresolved; "
        f"store now {document['meta']['counts']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

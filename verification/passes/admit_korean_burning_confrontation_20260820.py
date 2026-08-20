#!/usr/bin/env python3
"""Resolve the Korean Burning Confrontation 30/40 specimen from issues #88/#240.

SPEC-0037 was held after #233 because the retained photograph and retailer listing established the
card and number but did not provide a safe local set code. Issue #240 adds an exact positive chain:

* Pokémon Korea card record BS2010002030 names 잠만보 Lv.35, 30/40 and 불꽃 튀는 대결;
* a Pokémon Korea rules PDF calls that product expansion pack number 2;
* Daldagury displays human catalogue code BS2 for the same card; and
* Collectory retains its distinct catalogue set id BS2010002-kr.

The reviewed observations live in verification/evidence/issue-240-korean-burning-confrontation.json.
This pass keeps those identifiers reversible, resolves the held specimen to KR:BS2:30/40:base, and
does not infer finish or Japanese DP1 work equivalence.

    python verification/passes/admit_korean_burning_confrontation_20260820.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
PRINTS = ROOT / "verification" / "source_first_prints.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
SETS = ROOT / "verification" / "set_catalogue_sources.json"
EVIDENCE = ROOT / "verification" / "evidence" / "issue-240-korean-burning-confrontation.json"

OFFICIAL_CARD_URL = "https://pokemoncard.co.kr/cards/detail/BS2010002030"
OFFICIAL_RULES_URL = (
    "https://pokemonkorea.co.kr/templates/default/special_site/Wcs2014/battle_p.pdf"
)
DALDAGURY_URL = "https://daldagury.com/tcg/pokemon/card/8473"
COLLECTORY_URL = (
    "https://collectory.cc/cards/d097dd94-c89c-4c3f-b3b6-d4d3b7baca79?lang=en"
)
SPECIMEN_URL = "https://github.com/user-attachments/assets/27f7d3f3-f5db-4ce2-a7a3-98e0a6e054a1"

IDENTITY = {
    "locality": "KR",
    "language": "Korean",
    "script": "Hang",
    "localSetCode": "BS2",
    "officialProviderSetId": "BS2010002",
    "catalogueSetId": "BS2010002-kr",
    "localSetName": "불꽃 튀는 대결",
    "setOrdinal": 2,
    "localNumber": "30/40",
    "officialCardRecordId": "BS2010002030",
    "specimenId": "SPEC-0037",
}

EXPECTED_OBSERVATIONS = {
    "KR-OFFICIAL-CARD-BS2010002030": {
        "providerId": "pokemon-card-korea", "sourceUrl": OFFICIAL_CARD_URL,
        "observed": {"providerRecordId": "BS2010002030", "name": "잠만보 Lv. 35",
                     "localNumber": "30/40", "rarity": "U", "hp": 100,
                     "illustrator": "Ken Sugimori", "localSetName": "불꽃 튀는 대결"},
    },
    "KR-OFFICIAL-RULES-EXPANSION-2": {
        "providerId": "pokemon-card-korea", "sourceUrl": OFFICIAL_RULES_URL,
        "observed": {"statement": "포켓몬 카드 게임 확장팩 제 2 탄 「불꽃 튀는 대결」",
                     "localSetName": "불꽃 튀는 대결", "setOrdinal": 2},
    },
    "KR-DALDAGURY-BS2-30": {
        "providerId": "retailer-listing", "sourceUrl": DALDAGURY_URL,
        "observed": {"name": "잠만보", "localSetCode": "BS2", "localNumber": "30",
                     "rarity": "U", "localSetName": "불꽃 튀는 대결"},
    },
    "KR-COLLECTORY-BS2010002-30": {
        "providerId": "retailer-listing", "sourceUrl": COLLECTORY_URL,
        "observed": {"name": "잠만보", "catalogueSetId": "BS2010002-kr",
                     "localNumber": "30/40", "rarity": "U",
                     "localSetName": "불꽃 튀는 대결"},
    },
    "KR-OWNER-SPEC-0037": {
        "providerId": "inspected-specimen", "sourceUrl": SPECIMEN_URL,
        "observed": {"specimenId": "SPEC-0037", "language": "Korean",
                     "localNumber": "30/40", "localSetName": "불꽃 튀는 대결"},
    },
}


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:12].upper()}"


def read_evidence(path: Path = EVIDENCE) -> dict[str, Any]:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    meta = snapshot.get("meta", {})
    if (meta.get("schema"), meta.get("schemaVersion"), meta.get("issue")) != (
            "snoredex-reviewed-card-evidence", "1.0.0", 240):
        raise ValueError("issue #240 evidence schema or issue binding drifted")
    if snapshot.get("identity") != IDENTITY:
        raise ValueError("issue #240 resolved identity drifted")
    observations = snapshot.get("observations", [])
    by_id = {row.get("observationId"): row for row in observations}
    if len(by_id) != len(observations) or set(by_id) != set(EXPECTED_OBSERVATIONS):
        raise ValueError("issue #240 observation universe drifted")
    for observation_id, expected in EXPECTED_OBSERVATIONS.items():
        actual = by_id[observation_id]
        for field in ("providerId", "sourceUrl", "observed"):
            if actual.get(field) != expected[field]:
                raise ValueError(f"{observation_id} {field} drifted")
        if not actual.get("establishes") or not actual.get("doesNotEstablish"):
            raise ValueError(f"{observation_id} must retain positive scope and guardrails")
    return snapshot


ADMITTED_ENTRY = {
    "printId": "KR:BS2:30/40:base", "locality": "KR", "localSetCode": "BS2",
    "localNumber": "30/40", "variant": "base", "language": "Korean", "script": "Hang",
    "name": "잠만보", "cardName": "Snorlax Lv.35", "catchUpOf": None,
    "specimenId": "SPEC-0037", "providerId": "pokemon-card-korea",
    "providerRecordId": "BS2010002030", "providerSetId": "BS2010002",
    "catalogueSetId": "BS2010002-kr", "localSetName": "불꽃 튀는 대결",
    "sourceUrl": OFFICIAL_CARD_URL, "corroborated": True, "markAssetUrl": None,
    "cardImageUrl": None,
    "evidenceSnapshot": "verification/evidence/issue-240-korean-burning-confrontation.json",
    "corroboratingSourceUrls": [OFFICIAL_RULES_URL, DALDAGURY_URL, COLLECTORY_URL, SPECIMEN_URL],
    "evidence": (
        "The retained exact Pokémon Korea card observation BS2010002030 identifies Korean "
        "잠만보 Lv.35, 30/40, rarity U, in DP 확장팩 불꽃 튀는 대결. The publisher rules call "
        "불꽃 튀는 대결 expansion pack number 2; Daldagury displays the same card as BS2 30; "
        "Collectory retains the distinct catalogue set id BS2010002-kr; and the owner photograph "
        "remains SPEC-0037. BS2 is the human catalogue code, BS2010002 is the opaque official "
        "provider set id, and BS2010002-kr is a separate catalogue id. This record establishes "
        "only Korean language and local card identity. The low-resolution specimen establishes no "
        "finish, and no same-work equivalence to the Japanese DP1 product is asserted. Reviewed "
        "2026-08-20."
    ),
}

RETRACTED_ENTRY = {
    "printId": "KR:BCR:30/40:base", "locality": "KR", "localSetCode": "BCR",
    "localNumber": "30/40", "variant": "base", "language": "Korean", "script": "Hang",
    "name": "잠만보", "cardName": "Snorlax Lv.35",
    "catchUpOf": "the legacy Japanese DP1 Snorlax Lv.35 work; equivalence is not admitted here",
    "specimenId": "SPEC-0037", "providerId": "inspected-specimen", "sourceUrl": SPECIMEN_URL,
    "corroborated": True, "markAssetUrl": None, "cardImageUrl": None,
    "evidence": (
        "The owner photographed and identified SPEC-0037 in issue #88 as the Korean Series 2 "
        "Burning Confrontation Snorlax Lv.35, number 30/40. The cwtcg listing cited in the same "
        "thread independently names 잠만보 and Burning Confrontation 30/40. The low-resolution "
        "photograph does not support a finish claim. This record establishes only the Korean "
        "local release and its identifiers; equivalence to the Japanese DP1 work remains "
        "unadmitted under ADR-0001 I5."
    ),
}

HELD_ENTRY = {
    "specimenId": "SPEC-0037", "proposedSetCode": None, "localNumber": "30/40",
    "language": "Korean",
    "blockedBy": ("the retained owner photograph and retailer reference establish Burning "
                  "Confrontation Series 2 and 30/40, but do not state a source-native Korean "
                  "local set code"),
    "reason": ("BCR was an internal abbreviation and already identifies the unrelated Western "
               "Boundaries Crossed set. Positive evidence does not permit using it as the Korean "
               "raw identifier; hold until a source-native code is recorded."),
}

RETRACTED_SET_KEY = "KR\x1fBCR"
SET_PROFILE = {
    "sourceRecordId": stable_id("SET-SRC-SF", "KR", "BS2"),
    "sourceKind": "source-first-local-set-profile", "provider": "mixed-positive-evidence",
    "providerRecordKey": "KR\x1fBS2", "retrieved": "2026-08-20",
    "raw": {
        "localCode": "BS2", "localName": "불꽃 튀는 대결", "locality": "KR",
        "languages": ["Korean"], "scripts": ["Hang"], "printIds": [ADMITTED_ENTRY["printId"]],
        "providers": ["pokemon-card-korea", "retailer-listing", "inspected-specimen"],
        "sourceUrls": [OFFICIAL_CARD_URL, OFFICIAL_RULES_URL, DALDAGURY_URL, COLLECTORY_URL,
                       SPECIMEN_URL],
        "printedSetSize": 40,
        "printedSetSizeBasis": ("the official card observation and two Korean catalogues identify "
                                "30/40; the Collectory bounded set page lists 40 cards"),
        "localeSuffix": None, "observedCollectorNumbers": ["30/40"],
        "observedCoverage": ("one exact publisher card record plus bounded nomenclature "
                             "corroboration, not a provider-wide Korean enumeration"),
        "markAssetUrls": [], "cardImageUrls": [],
        "providerIdentifiers": {"officialCardRecordId": "BS2010002030",
                                "officialProviderSetId": "BS2010002",
                                "catalogueSetId": "BS2010002-kr",
                                "humanCatalogueCode": "BS2"},
        "evidenceSnapshot": ADMITTED_ENTRY["evidenceSnapshot"],
    },
}

SPECIMEN_NOTE = (
    " RESOLVED 2026-08-20 (#240): the reviewed positive evidence snapshot binds this exact "
    "Korean 30/40 card to local catalogue code BS2, official record BS2010002030, official "
    "provider set id BS2010002 and catalogue id BS2010002-kr. These identifiers remain distinct. "
    "The photograph still establishes no finish and no Japanese DP1 work equivalence."
)


def main() -> int:
    read_evidence()
    specimen_document = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    specimens = specimen_document["specimens"]
    specimen = next((row for row in specimens if row["specimenId"] == "SPEC-0037"), None)
    expected_specimen_keys = {("BCR", "30/40", "base", "Korean"),
                              ("", "30/40", "base", "Korean"),
                              ("BS2", "30/40", "base", "Korean")}
    actual_specimen_key = None if specimen is None else (
        specimen["setCode"], str(specimen["number"]), specimen["variant"], specimen["language"])
    if actual_specimen_key not in expected_specimen_keys:
        raise ValueError(f"SPEC-0037 identity drift: expected one of {expected_specimen_keys}, "
                         f"got {actual_specimen_key}")
    specimen["setCode"] = "BS2"
    if "RESOLVED 2026-08-20 (#240)" not in specimen["observed"]:
        specimen["observed"] = specimen["observed"].rstrip() + SPECIMEN_NOTE
    cited = specimen.setdefault("citedBy", [])
    if ADMITTED_ENTRY["printId"] not in cited:
        cited.append(ADMITTED_ENTRY["printId"])

    document = json.loads(PRINTS.read_text(encoding="utf-8"))
    retracted = [row for row in document["prints"] if row["printId"] == RETRACTED_ENTRY["printId"]]
    if len(retracted) > 1 or (retracted and retracted[0] != RETRACTED_ENTRY):
        raise ValueError(f"retracted source-first print drifted: {RETRACTED_ENTRY['printId']}")
    if retracted:
        document["prints"].remove(retracted[0])
    admitted = [row for row in document["prints"] if row["printId"] == ADMITTED_ENTRY["printId"]]
    if len(admitted) > 1 or (admitted and admitted[0] != ADMITTED_ENTRY):
        raise ValueError(f"admitted source-first print drifted: {ADMITTED_ENTRY['printId']}")
    if not admitted:
        document["prints"].append(ADMITTED_ENTRY)
    held = [row for row in document.get("held", []) if row["specimenId"] == "SPEC-0037"]
    if len(held) > 1 or (held and held[0] != HELD_ENTRY):
        raise ValueError("held SPEC-0037 disposition drifted")
    document["held"] = [row for row in document.get("held", [])
                        if row["specimenId"] != "SPEC-0037"]
    document["meta"]["generated"] = "2026-08-20"
    document["meta"]["counts"] = {"admitted": len(document["prints"]),
                                   "held": len(document.get("held", []))}

    set_document = json.loads(SETS.read_text(encoding="utf-8"))
    set_document["sourceRecords"] = [row for row in set_document["sourceRecords"]
                                     if row["providerRecordKey"] != RETRACTED_SET_KEY]
    set_matches = [row for row in set_document["sourceRecords"]
                   if row["providerRecordKey"] == SET_PROFILE["providerRecordKey"]]
    if len(set_matches) > 1 or (set_matches and set_matches[0] != SET_PROFILE):
        raise ValueError(f"existing local-set profile drifted: {SET_PROFILE['providerRecordKey']!r}")
    if not set_matches:
        set_document["sourceRecords"].append(SET_PROFILE)
    set_document["meta"]["counts"]["sourceRecords"] = len(set_document["sourceRecords"])
    set_document["meta"]["counts"]["sourceFirstLocalSets"] = sum(
        row["sourceKind"] == "source-first-local-set-profile"
        for row in set_document["sourceRecords"])

    PRINTS.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SETS.write_text(json.dumps(set_document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    specimen_document["count"] = len(specimens)
    SPECIMENS.write_text(json.dumps(specimen_document, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    print(f"resolved SPEC-0037 -> {ADMITTED_ENTRY['printId']}; store now "
          f"{document['meta']['counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

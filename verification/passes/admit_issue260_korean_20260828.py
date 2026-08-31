"""Admit exact positive Korean card evidence researched for issue #260."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import authoritative_graph as graph_projection  # noqa: E402
from admit_issue257_simplified_chinese_20260827 import (  # noqa: E402
    append_unique,
    encoded,
    stable_profile_id,
    upsert_edge,
    upsert_entity,
    upsert_migration,
)


PRINTS = ROOT / "verification" / "source_first_prints.json"
REKEYS = ROOT / "verification" / "legacy_issue_rekeys.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
SET_SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
CAPABILITIES = ROOT / "verification" / "source_capabilities.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
SPECIMEN_DIR = ROOT / "verification" / "specimens"
UNITS = ROOT / "verification" / "units.json"

IMAGE_ROOT = "https://cards.image.pokemonkorea.co.kr/data/wmimages"


def card(
    specimen: str,
    code: str,
    number: str,
    work: str,
    legacy: str,
    rarity: tuple[str, str],
    asset: str,
    *,
    card_name: str = "Snorlax",
    provider_record: str | None = None,
) -> dict[str, Any]:
    image_url = f"{IMAGE_ROOT}/{asset}?w=512"
    return {
        "printId": f"KR:{code}:{number}:base",
        "localSetCode": code,
        "localNumber": number,
        "work": work,
        "legacy": [legacy],
        "rarity": rarity,
        "specimenId": specimen,
        "cardName": card_name,
        "providerRecordId": provider_record,
        "sourceUrl": (
            f"https://pokemoncard.co.kr/cards/detail/{provider_record}"
            if provider_record else image_url
        ),
        "cardImageUrl": image_url,
    }


OFFICIAL = [
    card("SPEC-0236", "s10a", "058/071", "Snorlax-Unfazed-Fat-Thumping-Snore", "U0344", ("R", "rare"), "S/S10a/S10a_058.png", provider_record="BS2022011097"),
    card("SPEC-0237", "s10a", "077/071", "Snorlax-Unfazed-Fat-Thumping-Snore", "U0168", ("CHR", "character-rare"), "S/S10a/S10a_077.png", provider_record="BS2022011126"),
    card("SPEC-0238", "s10b", "056/071", "Snorlax-Block-Collapse", "U0202", ("R", "rare"), "S/S10b/S10b_056.png", provider_record="BS2022010056"),
    card("SPEC-0239", "s2", "077/096", "Snorlax-Collect-Collapse", "U0532", ("U", "uncommon"), "S/S2/S2_077.png"),
    card("SPEC-0240", "s4", "084/100", "Snorlax-Gormandize-Body-Slam", "U0291", ("R", "rare"), "S/S4/S4_084.png", provider_record="BS2020014084"),
    card("SPEC-0241", "s8b", "126/184", "Snorlax-Gormandize-Body-Slam", "U0173", ("no printed rarity symbol", "fixed"), "S/S8b/S8b_126.png", provider_record="BS2022001126"),
    card("SPEC-0242", "sI", "341/414", "Snorlax-Heavy-Impact", "U0653", ("no printed rarity symbol", "fixed"), "S/SI/SI_341.png"),
    card("SPEC-0243", "sI", "342/414", "Snorlax-Heavy-Impact", "U0657", ("no printed rarity symbol", "fixed"), "S/SI/SI_342.png"),
    card("SPEC-0244", "s1H", "045/060", "Snorlax-V-Swallow-Falling-Down", "U0511", ("RR", "double-rare"), "S/S1H/S1H_045.png", card_name="Snorlax V"),
    card("SPEC-0245", "s1H", "046/060", "Snorlax-VMAX-G-Max-Fall", "U0287", ("RRR", "triple-rare"), "S/S1H/S1H_046.png", card_name="Snorlax VMAX"),
    card("SPEC-0246", "s1H", "066/060", "Snorlax-V-Swallow-Falling-Down", "U0548", ("SR", "super-rare"), "S/S1H/S1H_066.png", card_name="Snorlax V"),
    card("SPEC-0247", "sN", "008/024", "Snorlax-Heavy-Impact", "U0770", ("no printed rarity symbol", "fixed"), "S/SN/SN_008.png"),
    card("SPEC-0248", "sm10", "076/095", "Snorlax-Lazy-Eating-Big-Counter", "U0264", ("R", "rare"), "SM/SM10/SM10_076.png"),
    card("SPEC-0249", "smL", "038/051", "Snorlax-Incredible-Snore", "U0583", ("no printed rarity symbol", "fixed"), "SM/SML/SML_038.png", provider_record="BS2019006059"),
    card("SPEC-0250", "sm9", "106/095", "Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX", "U0633", ("SR", "super-rare"), "SM/SM9/SM9_106.png", card_name="Eevee & Snorlax GX"),
    card("SPEC-0251", "sv4a", "310/190", "Snorlax-Voraciousness-Thudding-Press", "U0384", ("S", "shiny-rare"), "SV/SV4a/SV4a_310.png", provider_record="BS2024001310"),
    card("SPEC-0252", "svG", "021/049", "Snorlax-Unfazed-Fat-Thumping-Snore", "U0466", ("no printed rarity symbol", "fixed"), "SV/SVG/SVG_021.png", provider_record="BS2023023021"),
]


PROMOS = [
    {
        "printId": "KR:S-P:101:base", "localSetCode": "S-P", "localNumber": "101",
        "work": "Snorlax-Slap-Push-Single-Strike-Tackle", "legacy": ["U0523"],
        "rarity": ("PROMO", "promo"), "specimenId": "SPEC-0014", "cardName": "Snorlax",
        "providerId": "pokemon-card-korea", "providerRecordId": "SP000000101",
        "sourceUrl": "https://pokemoncard.co.kr/cards/detail/SP000000101",
        "corroboratingSourceUrls": ["https://pokumon.com/card/snorlax-101-s-p-korean-promo/"],
        "corroborated": True,
        "releaseDate": "2021", "releaseDatePrecision": "year",
    },
    {
        "printId": "KR:SM-P:140:base", "localSetCode": "SM-P", "localNumber": "140",
        "work": "Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX", "legacy": ["U0627"],
        "rarity": ("PROMO", "promo"), "specimenId": "SPEC-0028", "cardName": "Eevee & Snorlax GX",
        "providerId": "pokumon", "sourceUrl": "https://pokumon.com/card/eevee-snorlax-tag-teamgx-140-sm-p-korean-promo/",
        "corroborated": True,
        "releaseDate": "2019", "releaseDatePrecision": "year",
    },
    {
        "printId": "KR:XY-P:167:base", "localSetCode": "XY-P", "localNumber": "167",
        "work": "Snorlax-Plump-Body-Knock-Away", "legacy": ["U0661"],
        "rarity": ("PROMO", "promo"), "specimenId": "SPEC-0031", "cardName": "Snorlax",
        "providerId": "pokumon", "sourceUrl": "https://pokumon.com/card/snorlax-167-xy-p-korean-promo/",
        "corroborated": True,
        "releaseDate": "2017", "releaseDatePrecision": "year",
    },
]


ISSUE_UNITS = sorted({
    "U0049", "U0103", "U0127", "U0168", "U0173", "U0202", "U0233", "U0257",
    "U0260", "U0264", "U0287", "U0291", "U0306", "U0344", "U0370", "U0379",
    "U0384", "U0402", "U0413", "U0440", "U0466", "U0508", "U0511", "U0523",
    "U0532", "U0541", "U0548", "U0557", "U0561", "U0579", "U0583", "U0586",
    "U0590", "U0601", "U0610", "U0623", "U0627", "U0633", "U0641", "U0648",
    "U0653", "U0657", "U0661", "U0677", "U0680", "U0683", "U0763", "U0770",
    "U0775", "U0780", "U0785", "U0790",
})


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(encoded(payload), encoding="utf-8", newline="\n")


def release_id(row: dict[str, Any]) -> str:
    return f"RELEASE:KR:Korean:{row['localSetCode']}:{row['localNumber']}:{row['work']}"


def source_first_row(row: dict[str, Any]) -> dict[str, Any]:
    result = {
        "printId": row["printId"], "locality": "KR", "localSetCode": row["localSetCode"],
        "localNumber": row["localNumber"], "variant": "base", "language": "Korean",
        "script": "Hang", "name": "이브이&잠만보 GX" if row["cardName"].startswith("Eevee") else "잠만보",
        "cardName": row["cardName"],
        "catchUpOf": "the exact Korean counterpart established by the printed Korean attacks and card traits",
        "specimenId": row["specimenId"], "providerId": row.get("providerId", "pokemon-card-korea"),
        "sourceUrl": row["sourceUrl"],
        "corroborated": bool(row.get("corroborated")), "markAssetUrl": None,
        "cardImageUrl": row.get("cardImageUrl"),
        "evidence": (
            f"The retained exact Korean card image {row['specimenId']} shows {row['localSetCode']} "
            f"{row['localNumber']}, including its Korean name, printed attacks and rarity {row['rarity'][0]}. "
            "Those positive traits establish the local card identity and explicit Work mapping. "
            "A publisher/database render is not a physical finish photograph; no finish is inferred."
        ),
    }
    for field in ("providerRecordId", "corroboratingSourceUrls", "releaseDate", "releaseDatePrecision"):
        if row.get(field) is not None:
            result[field] = row[field]
    if row.get("releaseDate"):
        result["releaseApproximate"] = False
    return result


def specimen_row(row: dict[str, Any]) -> dict[str, Any]:
    path = SPECIMEN_DIR / f"{row['specimenId']}.png"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "specimenId": row["specimenId"], "setCode": row["localSetCode"],
        "number": row["localNumber"], "variant": "base", "language": "Korean",
        "heldBy": "publisher or database", "inspectedFrom": "official Pokémon Korea card render",
        "photograph": f"{row['specimenId']}.png", "photographSource": row["cardImageUrl"],
        "photographSha256": "sha256:" + digest,
        "observed": (
            f"Complete official Korean render for {row['cardName']} {row['localSetCode']} "
            f"{row['localNumber']}. The printed Korean name, collector identity, attacks and "
            f"rarity {row['rarity'][0]} establish this card release and Work equivalence. "
            "Retained as identity and rarity evidence only; no physical finish is inferred."
        ),
        "recordedAt": "2026-08-28", "citedBy": [*row["legacy"], row["printId"]],
        "listingUrl": row["sourceUrl"],
    }


def update_promo_specimens(document: dict[str, Any]) -> None:
    by_id = {row["specimenId"]: row for row in document["specimens"]}
    updates = {
        "SPEC-0014": {
            "listingUrl": PROMOS[0]["sourceUrl"],
            "physicalObservation": {"finish": "non-holo", "foilPattern": None, "markings": None, "markingRole": None, "cardSize": "standard", "basis": "Pokumon's exact Korean 101/S-P record positively classifies this purchase promo as Non-holo."},
        },
        "SPEC-0028": {
            "listingUrl": PROMOS[1]["sourceUrl"],
            "physicalObservation": {"finish": "holo", "foilPattern": "ripple", "markings": None, "markingRole": None, "cardSize": "standard", "basis": "Pokumon's exact Korean 140/SM-P record positively identifies the Full Art purchase promo with Ripple treatment."},
        },
        "SPEC-0031": {
            "listingUrl": PROMOS[2]["sourceUrl"],
            "physicalObservation": {"finish": "non-holo", "foilPattern": None, "markings": None, "markingRole": None, "cardSize": "standard", "basis": "Pokumon's exact Korean 167/XY-P Kisstick promotion record positively classifies the card as Non-holo."},
        },
    }
    for promo, (specimen_id, values) in zip(PROMOS, updates.items()):
        specimen = by_id[specimen_id]
        specimen.update(values)
        specimen["citedBy"] = sorted(set(specimen.get("citedBy") or []) | set(promo["legacy"]) | {promo["printId"]})
        conclusion = " The exact card traits and cited positive record establish the Korean counterpart without merging its local release identity."
        base = specimen["observed"].split(" Note ", 1)[0].split(conclusion, 1)[0].rstrip()
        specimen["observed"] = base + conclusion


def build_profile(
    code: str,
    rows: list[dict[str, Any]],
    *,
    retrieved_at: str = "2026-08-28",
) -> dict[str, Any]:
    numbers = sorted(row["localNumber"] for row in rows)
    denominators = {number.partition("/")[2] for number in numbers if number.partition("/")[2].isdigit()}
    return {
        "sourceRecordId": stable_profile_id("KR", code), "sourceKind": "source-first-local-set-profile",
        "provider": "mixed-positive-evidence", "providerRecordKey": f"KR\x1f{code}", "retrieved": retrieved_at,
        "raw": {
            "localCode": code, "localName": None, "locality": "KR", "languages": ["Korean"],
            "scripts": ["Hang"], "printIds": sorted(row["printId"] for row in rows),
            "providers": sorted({row.get("providerId", "pokemon-card-korea") for row in rows}),
            "sourceUrls": sorted({row["sourceUrl"] for row in rows}),
            "printedSetSize": int(next(iter(denominators))) if len(denominators) == 1 else None,
            "printedSetSizeBasis": "the denominator printed on every observed card" if len(denominators) == 1 else "no common printed denominator is inferred",
            "localeSuffix": None, "observedCollectorNumbers": numbers,
            "observedCoverage": "exact positive Korean Snorlax cards reviewed for issue #260, not a set enumeration",
            "markAssetUrls": [], "cardImageUrls": sorted({row["cardImageUrl"] for row in rows if row.get("cardImageUrl")}),
        },
    }


def apply_profiles(
    document: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    retrieved_at: str = "2026-08-28",
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["localSetCode"], []).append(row)
    profiles = {
        code: build_profile(code, group, retrieved_at=retrieved_at)
        for code, group in grouped.items()
    }
    by_id = {row["sourceRecordId"]: row for row in document["sourceRecords"]}
    by_id.update({profile["sourceRecordId"]: profile for profile in profiles.values()})
    document["sourceRecords"] = sorted(by_id.values(), key=lambda row: row["sourceRecordId"])
    document["meta"]["counts"]["sourceRecords"] = len(document["sourceRecords"])
    document["meta"]["counts"]["sourceFirstLocalSets"] = sum(row["sourceKind"] == "source-first-local-set-profile" for row in document["sourceRecords"])
    return profiles


def apply_capabilities(document: dict[str, Any]) -> None:
    surface = {
        "surfaceId": "pokemon-card-korea-image", "providerId": "pokemon-card-korea",
        "label": "Pokémon Korea exact card renders",
        "match": {"urlPrefixes": [IMAGE_ROOT + "/"], "nonUrlEvidenceIds": []},
        "state": "incomplete", "failureState": "Only retained exact positive renders are covered; failed or missing image requests prove nothing.",
        "accessMode": "direct-download", "adapterState": "planned", "lastCheckedAt": "2026-08-28",
        "freshnessPolicy": "Retain each exact render URL, retrieval date and SHA-256; never interpret image-host silence as absence.",
        "query": {"method": "GET", "endpoint": IMAGE_ROOT + "/{era}/{set}/{asset}", "parameters": ["era", "set", "asset"], "pagination": "not paginated; every render establishes only its pictured card", "expectedIdentifiers": ["Korean card name", "printed local set code", "collector number", "printed rarity"]},
        "finishCapability": {"mode": "none", "vocabulary": [], "publicationForm": "publisher/database render, not a physical card photograph", "closedWithinScope": False},
        "coverageEdges": [{
            "edgeId": "pokemon-card-korea-image-positive",
            "coverage": {"localities": ["KR"], "languages": ["Korean"], "scripts": ["Hang"], "productCategories": ["card"], "timeRange": {"start": None, "end": None, "basis": "retained exact positive renders only"}},
            "positiveEvidenceCapabilities": ["identity", "image", "language", "card-existence", "card-release", "local-set-identifier", "collector-number", "rarity", "set-membership"],
            "exhaustive": False,
            "absenceCapability": {"enabled": False, "dimensions": [], "exactScopes": [], "rationale": "A retained render proves only the pictured card; an unavailable image proves nothing."},
            "knownPositiveObservationId": "obs-pokemon-card-korea-image",
            "boundary": {"outsideScope": ["unretained Korean cards", "physical finish", "complete set or era"], "zeroResultMeans": "unknown", "challenge": "The image host is positive-only and does not publish a completeness contract."},
        }],
    }
    observation = {
        "observationId": "obs-pokemon-card-korea-image", "surfaceId": surface["surfaceId"], "kind": "known-positive",
        "queryUrl": OFFICIAL[0]["cardImageUrl"], "queryParameters": {"era": "S", "set": "S10a", "asset": "S10a_058.png"},
        "retrievedAt": "2026-08-28",
        "fixtureRef": {"kind": "inline-record", "record": {"specimenId": "SPEC-0236", "sha256": "sha256:" + hashlib.sha256((SPECIMEN_DIR / "SPEC-0236.png").read_bytes()).hexdigest(), "localSetCode": "s10a", "collectorNumber": "058/071", "cardName": "잠만보", "absenceCapability": False, "finishCapability": False}},
        "expectedIdentifiers": ["SPEC-0236", "s10a", "058/071", "잠만보"], "validatesEdges": ["pokemon-card-korea-image-positive"],
        "outcome": "The retained exact publisher render positively identifies Korean Snorlax s10a 058/071 and its printed rarity; it establishes no physical finish.",
    }
    surfaces = {row["surfaceId"]: row for row in document["surfaces"]}
    surfaces[surface["surfaceId"]] = surface
    document["surfaces"] = list(surfaces.values())
    observations = {row["observationId"]: row for row in document["observations"]}
    observations[observation["observationId"]] = observation
    document["observations"] = list(observations.values())


def apply_set_graph(graph: dict[str, Any], profile: dict[str, Any], code: str, claim_ids: list[str]) -> None:
    source_id = profile["sourceRecordId"]
    local_set_id = f"LOCALSET:KR:{quote(code, safe='')}"
    edition_id = f"EDITION:KR:Korean:{code}"
    localization_id = "LOCALIZATION:KR:ko"
    upsert_entity(graph, "set-source-record", source_id, profile, origin="reviewed-evidence-issue-260")
    disposition = {"sourceRecordId": source_id, "disposition": "mapped", "targetRef": local_set_id, "reason": "positive Korean source-first card records establish this local set"}
    upsert_entity(graph, "set-source-disposition", source_id, disposition, origin="reviewed-evidence-issue-260")
    upsert_edge(graph, "set-source-disposition", source_id, "disposes", "set-source-record", source_id)
    upsert_migration(graph, {"sourceKind": "set-catalogue-source", "sourceId": source_id, "disposition": "mapped", "targetRef": local_set_id, "reason": disposition["reason"]})
    matches = [row for row in graph["entities"] if row.get("entityType") == "local-set" and row.get("entityId") == local_set_id]
    if matches:
        append_unique(matches[0]["payload"].setdefault("sourceRecordIds", []), source_id)
    else:
        upsert_entity(graph, "local-set", local_set_id, {"localSetId": local_set_id, "locality": "KR", "localCode": code, "observedNames": [], "productKind": "physical-card-set-or-product", "sourceRecordIds": [source_id]}, origin="reviewed-evidence-issue-260")
    upsert_edge(graph, "local-set", local_set_id, "observed-by", "set-source-record", source_id)
    editions = [row for row in graph["entities"] if row.get("entityType") == "set-edition" and row.get("entityId") == edition_id]
    if editions:
        append_unique(editions[0]["payload"]["identity"].setdefault("establishingClaimIds", []), *claim_ids)
        append_unique(editions[0]["payload"]["catalogue"].setdefault("establishingEvidenceIds", []), source_id)
        editions[0]["payload"]["catalogue"]["localSetId"] = local_set_id
    else:
        upsert_entity(graph, "set-edition", edition_id, {"setEditionId": edition_id, "identity": {"setEditionId": edition_id, "locality": "KR", "language": "Korean", "script": "Hang", "localSetCode": code, "localIdentifierKnown": True, "state": "identified", "viaLegacySetCodes": [], "establishingClaimIds": claim_ids, "localizationId": localization_id}, "catalogue": {"setEditionId": edition_id, "localSetId": local_set_id, "locality": "KR", "language": "Korean", "script": "Hang", "localCode": code, "state": "identified", "establishingEvidenceIds": [source_id], "localizationId": localization_id}}, origin="reviewed-evidence-issue-260")
    upsert_edge(graph, "set-edition", edition_id, "belongs-to", "local-set", local_set_id)
    upsert_edge(graph, "set-edition", edition_id, "localized-as", "localization", localization_id, {"decisionRef": "https://github.com/m4s-ai/snoredex-data/issues/254", "reviewedAt": "2026-08-24"})


def remove_obsolete_release(
    graph: dict[str, Any], row: dict[str, Any], target: str,
) -> tuple[list[tuple[str, str | None]], list[str], dict[str, list[str]]]:
    legacy_number = row["localNumber"].partition("/")[0].lstrip("0")

    def is_old_ref(value: Any) -> bool:
        text = str(value or "")
        marker = f":via-{row['localSetCode']}:unknown-local-set:via-"
        if not text.startswith("RELEASE:KR:Korean:") or marker not in text:
            return False
        observed_number = text.split(marker, 1)[1].split(":", 1)[0].lstrip("0")
        return observed_number == legacy_number

    obsolete = {
        item["entityId"] for item in graph["entities"]
        if item.get("entityType") == "card-release" and item.get("entityId") != target
        and item.get("payload", {}).get("language") == "Korean"
        and (item.get("payload", {}).get("localSetCode") or item.get("payload", {}).get("viaLegacySetCode")) == row["localSetCode"]
        and str(item.get("payload", {}).get("localNumber") or item.get("payload", {}).get("viaLegacyNumber") or "").partition("/")[0].lstrip("0") == row["localNumber"].partition("/")[0].lstrip("0")
    }
    legacy_claims = []
    finish_claims = []
    old_payloads = [
        item.get("payload", {}) for item in graph["entities"]
        if item.get("entityType") == "card-release"
        and (item.get("entityId") in obsolete or item.get("entityId") == target)
    ]
    for item in graph["entities"]:
        payload = item.get("payload", {})
        if item.get("entityType") != "candidate-claim":
            continue
        if payload.get("sourceKind") == "legacy-language-unit" \
                and payload.get("sourceId") in row["legacy"] \
                and payload.get("materializedTargetId") in {*obsolete, target}:
            payload["proposedTargetId"] = target
            payload["materializedTargetId"] = target
            legacy_claims.append((item["entityId"], payload.get("sourceRecord")))
            upsert_migration(graph, {"sourceKind": "legacy-language-unit", "sourceId": payload["sourceId"], "disposition": "established-and-mapped", "targetRef": target, "reason": payload["reason"]})
        proposed = str(payload.get("proposedCardReleaseId") or "")
        finish_matches = is_old_ref(proposed)
        if payload.get("sourceKind") == "finish-printing-record" \
                and (payload.get("proposedCardReleaseId") in obsolete or finish_matches):
            payload["proposedCardReleaseId"] = target
            finish_claims.append(item["entityId"])
    catalogue = {item["entityId"] for item in graph["entities"] if item.get("entityType") == "catalogue-card-release-ref" and item.get("payload", {}).get("cardReleaseId") in obsolete}
    for disposition in graph["migrationDispositions"]:
        if disposition.get("targetRef") in obsolete or is_old_ref(disposition.get("targetRef")):
            disposition["targetRef"] = target
        if "targetRefs" in disposition:
            disposition["targetRefs"] = [
                target if item in obsolete or is_old_ref(item) else item
                for item in disposition["targetRefs"]
            ]
    graph["entities"] = [item for item in graph["entities"] if not ((item.get("entityType") == "card-release" and item.get("entityId") in obsolete) or (item.get("entityType") == "catalogue-card-release-ref" and item.get("entityId") in catalogue))]
    graph["edges"] = [edge for edge in graph["edges"] if not ((edge.get("fromType") == "card-release" and edge.get("fromId") in obsolete) or (edge.get("toType") == "card-release" and edge.get("toId") in obsolete) or (edge.get("fromType") == "catalogue-card-release-ref" and edge.get("fromId") in catalogue) or (edge.get("toType") == "catalogue-card-release-ref" and edge.get("toId") in catalogue))]
    graph["edges"] = [edge for edge in graph["edges"] if not (edge.get("fromId") in finish_claims and edge.get("relation") == "proposes-for" and edge.get("toId") != target)]
    heritage = {
        "legacyProducts": sorted({
            *{item for payload in old_payloads for item in payload.get("legacyProducts", [])},
            *{
                str(disposition["sourceId"])
                for disposition in graph["migrationDispositions"]
                if disposition.get("sourceKind") == "legacy-cardmarket-product"
                and target in (disposition.get("targetRefs") or [])
            },
        }),
        "legacyVariants": sorted({item for payload in old_payloads for item in payload.get("legacyVariants", [])}),
    }
    return legacy_claims, finish_claims, heritage


def apply_release_graph(graph: dict[str, Any], profile: dict[str, Any], row: dict[str, Any]) -> None:
    rid = release_id(row)
    legacy_claims, finish_claims, heritage = remove_obsolete_release(graph, row, rid)
    claim_id = f"CLAIM:source-first:{row['printId']}"
    edition_id = f"EDITION:KR:Korean:{row['localSetCode']}"
    claim = {"claimId": claim_id, "claimKind": "card-release", "sourceKind": "source-first-record", "sourceId": row["printId"], "sourceRecord": row["sourceUrl"], "evidenceStatus": "confirmed", "disposition": "established-and-mapped", "proposedTargetId": rid, "materializedTargetId": rid, "reason": "positive exact Korean card record and retained image"}
    upsert_entity(graph, "candidate-claim", claim_id, claim, origin="reviewed-evidence-issue-260")
    upsert_edge(graph, "candidate-claim", claim_id, "materializes", "card-release", rid, {"disposition": "established-and-mapped"})
    upsert_migration(graph, {"sourceKind": "source-first-record", "sourceId": row["printId"], "disposition": "established-and-mapped", "targetRef": rid, "reason": claim["reason"]})
    claim_ids = sorted([claim_id, *(item[0] for item in legacy_claims)])
    source_records = sorted({row["sourceUrl"], *(item[1] for item in legacy_claims if item[1])})
    payload = {"cardReleaseId": rid, "setEditionId": edition_id, "locality": "KR", "language": "Korean", "script": "Hang", "localSetCode": row["localSetCode"], "localNumber": row["localNumber"], "localIdentifierKnown": True, "state": "identified", "work": row["work"], "workMappingState": "mapped-by-explicit-equivalence", "viaLegacySetCode": None, "viaLegacyNumber": None, "claimIds": claim_ids, "establishingClaimIds": claim_ids, "nonEstablishingClaimIds": [], "legacyVariants": sorted(set(heritage["legacyVariants"]) | set(row["legacyVariants"])), "legacyProducts": heritage["legacyProducts"], "sourceRecords": source_records, "sourceFirstRecordIds": [row["printId"]], "legacyCounterpartUnitIds": row["legacy"]}
    for field in ("releaseDate", "releaseDatePrecision", "releaseApproximate"):
        if row.get(field) is not None:
            payload[field] = row[field]
    upsert_entity(graph, "card-release", rid, payload, origin="reviewed-evidence-issue-260")
    for legacy_claim_id, _ in legacy_claims:
        upsert_edge(graph, "candidate-claim", legacy_claim_id, "materializes", "card-release", rid, {"disposition": "established-and-mapped"})
    for finish_claim_id in finish_claims:
        upsert_edge(graph, "candidate-claim", finish_claim_id, "proposes-for", "card-release", rid)
    upsert_edge(graph, "card-release", rid, "belongs-to", "set-edition", edition_id)
    upsert_edge(graph, "card-release", rid, "implements", "work", f"WORK:{row['work']}", {"state": "mapped-by-explicit-equivalence", "basis": "exact Korean printed attacks and card traits"})
    upsert_entity(graph, "catalogue-card-release-ref", rid, {"cardReleaseId": rid, "setEditionId": edition_id, "collectorNumber": row["localNumber"], "origin": "issue-260-positive-evidence"}, origin="reviewed-evidence-issue-260")
    upsert_edge(graph, "catalogue-card-release-ref", rid, "belongs-to", "set-edition", edition_id)
    upsert_edge(graph, "catalogue-card-release-ref", rid, "references", "card-release", rid)
    rarity_id = "RARITYCLAIM:issue260:" + rid.removeprefix("RELEASE:KR:Korean:")
    rarity = {"rarityClaimId": rarity_id, "cardReleaseId": rid, "sourceRecordId": profile["sourceRecordId"], "sourceProvider": "mixed-positive-evidence", "sourceVocabulary": "printed-Korean-card", "sourceNativeValue": row["rarity"][0], "normalizedRarityId": row["rarity"][1], "sourceProductKey": row["sourceUrl"]}
    upsert_entity(graph, "rarity-claim", rarity_id, rarity, origin="reviewed-evidence-issue-260")
    upsert_edge(graph, "rarity-claim", rarity_id, "asserts-rarity-for", "card-release", rid)
    upsert_edge(graph, "rarity-claim", rarity_id, "observed-by", "set-source-record", profile["sourceRecordId"])


def mapping(
    row: dict[str, Any],
    legacy_id: str,
    *,
    asserted_at: str = "2026-08-28",
) -> dict[str, Any]:
    return {"legacyUnitId": legacy_id, "sourceFirstRecordId": row["printId"], "assertionType": "same-work-decision", "assertedBy": "repository verification pass", "assertedAt": asserted_at, "evidenceUrl": row["sourceUrl"], "evidence": "The exact Korean card identity and printed attacks establish this local counterpart without merging release identities."}


def apply_mapping_graph(
    graph: dict[str, Any],
    row: dict[str, Any],
    legacy_id: str,
    *,
    asserted_at: str = "2026-08-28",
) -> None:
    rid = release_id(row)
    assertion_id = f"ASSERT:same-work:{legacy_id}:{row['printId']}"
    assertion = {"assertionId": assertion_id, "assertionType": "same-work-decision", "fromId": rid, "toId": f"WORK:{row['work']}", "legacyUnitId": legacy_id, "sourceFirstRecordId": row["printId"], "assertedBy": "repository verification pass", "assertedAt": asserted_at, "evidenceUrl": row["sourceUrl"], "evidence": "The exact Korean card identity and printed attacks establish this local counterpart without merging release identities.", "destructiveMergeAllowed": False}
    upsert_entity(graph, "equivalence-assertion", assertion_id, assertion, origin="reviewed-evidence-issue-260")
    upsert_edge(graph, "equivalence-assertion", assertion_id, "relates", "card-release", rid, assertion)
    upsert_edge(graph, "equivalence-assertion", assertion_id, "relates", "work", f"WORK:{row['work']}", assertion)
    upsert_migration(graph, {"sourceKind": "legacy-issue-rekey", "sourceId": legacy_id, "disposition": "linked-local-counterpart", "targetRef": rid, "targetRefs": [rid], "reason": "issue #260 re-key"})


def apply_graph(
    graph: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    asserted_at: str = "2026-08-28",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    for disposition in graph["migrationDispositions"]:
        if disposition.get("sourceKind") not in {"legacy-cardmarket-product", "legacy-issue-rekey"} \
                and disposition.get("targetRefs") == []:
            disposition.pop("targetRefs")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["localSetCode"], []).append(row)
    for code, group in grouped.items():
        apply_set_graph(graph, profiles[code], code, sorted(f"CLAIM:source-first:{row['printId']}" for row in group))
    mappings = []
    for row in rows:
        apply_release_graph(graph, profiles[row["localSetCode"]], row)
        for legacy_id in row["legacy"]:
            apply_mapping_graph(graph, row, legacy_id, asserted_at=asserted_at)
            mappings.append(mapping(row, legacy_id, asserted_at=asserted_at))
    mapped_ids = {row["legacyUnitId"] for row in mappings}
    for legacy_id in set(ISSUE_UNITS) - mapped_ids:
        upsert_migration(graph, {"sourceKind": "legacy-issue-rekey", "sourceId": legacy_id, "disposition": "needs-positive-local-identity", "targetRef": None, "targetRefs": [], "reason": "issue #260 re-key"})
    return graph_projection.project_physical_evidence(graph), sorted(mappings, key=lambda row: row["legacyUnitId"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows = OFFICIAL + PROMOS
    units = {row["unitId"]: row for row in read(UNITS)}
    for row in rows:
        row["legacyVariants"] = sorted({str(units[unit_id].get("variant") or "base") for unit_id in row["legacy"]})
    source_rows = [source_first_row(row) for row in rows]

    prints = read(PRINTS)
    before_prints = encoded(prints)
    by_print = {row["printId"]: row for row in prints["prints"]}
    by_print.update({row["printId"]: row for row in source_rows})
    prints["prints"] = sorted(by_print.values(), key=lambda row: row["printId"])
    prints["meta"]["generated"] = "2026-08-28"
    prints["meta"]["counts"]["admitted"] = len(prints["prints"])

    specimens = read(SPECIMENS)
    before_specimens = encoded(specimens)
    by_specimen = {row["specimenId"]: row for row in specimens["specimens"]}
    by_specimen.update({row["specimenId"]: specimen_row(row) for row in OFFICIAL})
    specimens["specimens"] = sorted(by_specimen.values(), key=lambda row: int(row["specimenId"].split("-")[1]))
    specimens["count"] = len(specimens["specimens"])
    update_promo_specimens(specimens)

    sources = read(SET_SOURCES)
    before_sources = encoded(sources)
    profiles = apply_profiles(sources, rows)

    capabilities = read(CAPABILITIES)
    before_capabilities = encoded(capabilities)
    apply_capabilities(capabilities)

    rekeys = read(REKEYS)
    before_rekeys = encoded(rekeys)

    graph = read(GRAPH)
    before_graph = encoded(graph)

    if not args.check:
        write(PRINTS, prints)
        write(SPECIMENS, specimens)
        write(SET_SOURCES, sources)
        write(CAPABILITIES, capabilities)

    graph, mappings = apply_graph(graph, profiles, rows)
    question = {"issueNumber": 260, "locality": "KR", "language": "Korean", "legacyUnitIds": ISSUE_UNITS, "defaultDisposition": "needs-positive-local-identity", "mappings": mappings}
    by_issue = {row["issueNumber"]: row for row in rekeys["questionSets"]}
    by_issue[260] = question
    rekeys["questionSets"] = sorted(by_issue.values(), key=lambda row: row["issueNumber"])

    stale = [
        label for label, before, after in (
            ("prints", before_prints, encoded(prints)),
            ("specimens", before_specimens, encoded(specimens)),
            ("set sources", before_sources, encoded(sources)),
            ("capabilities", before_capabilities, encoded(capabilities)),
            ("rekeys", before_rekeys, encoded(rekeys)),
            ("graph", before_graph, encoded(graph)),
        ) if before != after
    ]
    if args.check:
        if stale:
            raise SystemExit("issue #260 Korean reviewed inputs are stale: " + ", ".join(stale))
        print("issue #260 Korean reviewed inputs are current")
        return 0

    write(REKEYS, rekeys)
    write(GRAPH, graph)
    print(f"admitted {len(rows)} Korean source-first records, {len(mappings)} positive re-keys and {len(OFFICIAL)} new image specs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Admit reviewed positive Thai card evidence from issue #262."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
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
FINISHES = ROOT / "verification" / "finish_overrides.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
DISCOVERY = ROOT / "verification" / "card_discovery_records.jsonl"
DISCOVERY_ADAPTERS = ROOT / "verification" / "card_discovery_adapters.json"
SPECIMEN_DIR = ROOT / "verification" / "specimens"
UNITS = ROOT / "verification" / "units.json"


def card(
    detail: str,
    specimen: str,
    code: str,
    number: str,
    work: str,
    rarity: tuple[str, str],
    *legacy: str,
    variant: str = "base",
    card_name: str = "Snorlax",
    date: tuple[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "detail": detail,
        "specimenId": specimen,
        "printId": f"TH:{code}:{number}:{variant}",
        "localSetCode": code,
        "localNumber": number,
        "variant": variant,
        "work": work,
        "rarity": rarity,
        "legacy": list(legacy),
        "cardName": card_name,
        "date": date,
    }


SET_DATES = {
    "sc1a T": ("2020-09-08", "day"),
    "sc1b T": ("2020-09-08", "day"),
    "sc1D T": ("2020-09-08", "day"),
    "sc3b T": ("2021-01-29", "day"),
    "scA T": ("2021-01-29", "day"),
    "scD T": ("2022-01-28", "day"),
    "s8b": ("2021-12-17", "day"),
    "s10b": ("2022-06-24", "day"),
    "SH": ("2021-11-26", "day"),
    "s10a": ("2022-07-29", "day"),
    "sv2a": ("2023-07-28", "day"),
    "sv4K": ("2023-12-15", "day"),
    "sv4a": ("2024-01-26", "day"),
    "sv5a": ("2024-04-26", "day"),
    "svM": ("2025-02-07", "day"),
    "SV9s": ("2025-04-11", "day"),
    "MA3": ("2026-01-16", "day"),
    "MA4": ("2026-03-20", "day"),
}


OFFICIAL = [
    card("127", "SPEC-0253", "sc1a T", "127/154", "Snorlax-Collect-Collapse", ("U", "uncommon")),
    card("273", "SPEC-0254", "sc1b T", "119/153", "Snorlax-V-Swallow-Falling-Down", ("RR", "double-rare"), card_name="Snorlax V"),
    card("274", "SPEC-0255", "sc1b T", "120/153", "Snorlax-VMAX-G-Max-Fall", ("RRR", None), card_name="Snorlax VMAX"),
    card("439", "SPEC-0256", "sc1D T", "132/164", "Snorlax-Rolling-Tackle-Heavy-Impact", ("no printed rarity symbol", "fixed")),
    card("440", "SPEC-0257", "sc1D T", "133/164", "Snorlax-V-Swallow-Falling-Down", ("no printed rarity symbol", "fixed"), card_name="Snorlax V"),
    card("1006", "SPEC-0258", "sc3b T", "126/158", "Snorlax-Gormandize-Body-Slam", ("R", "rare")),
    card("1806", "SPEC-0259", "scA T", "084/135", "Snorlax-Gormandize-Body-Slam", ("no printed rarity symbol", "fixed")),
    card("2297", "SPEC-0260", "scD T", "111/159", "Snorlax-Slap-Push-Single-Strike-Tackle", ("no printed rarity symbol", "fixed")),
    card("2468", "SPEC-0261", "s8b", "126/184", "Snorlax-Gormandize-Body-Slam", ("R", "rare"), "U0176"),
    card("3281", "SPEC-0262", "s10b", "056/071", "Snorlax-Block-Collapse", ("R", "rare"), "U0205"),
    card("3343", "SPEC-0263", "SH", "026/038", "Snorlax-Heavy-Impact", ("no printed rarity symbol", "fixed")),
    card("3495", "SPEC-0264", "s10a", "058/071", "Snorlax-Unfazed-Fat-Thumping-Snore", ("R", "rare"), "U0347"),
    card("6241", "SPEC-0265", "sv2a", "143/165", "Snorlax-Voraciousness-Thudding-Press", ("U", "uncommon"), "U0106"),
    card("6363", "SPEC-0266", "sv2a", "181/165", "Snorlax-Voraciousness-Thudding-Press", ("AR", "illustration-rare"), "U0052"),
    card("6835", "SPEC-0267", "SV-P", "082/SV-P", "Snorlax-Voraciousness-Thudding-Press", ("PROMO", "promo"), "U0753", date=("2023-11-07", "day")),
    card("7440", "SPEC-0268", "sv4K", "059/066", "Snorlax-Doll", ("U", "uncommon"), "U0262", card_name="Snorlax Doll"),
    card("7755", "SPEC-0269", "sv4a", "145/190", "Snorlax-Voraciousness-Thudding-Press", ("no printed rarity symbol", "fixed"), "U0309"),
    card("8167", "SPEC-0270", "sv5a", "051/066", "Snorlax-But-First-Food-Heavy-Impact", ("U", "uncommon"), "U0235"),
    card("8631", "SPEC-0271", "sv4a", "310/190", "Snorlax-Voraciousness-Thudding-Press", ("S", "shiny-rare"), "U0387"),
    card("10595", "SPEC-0272", "svM", "094/175", "Snorlax-ex-Strength-Toss-and-Turn-Press", ("no printed rarity symbol", "fixed"), "U0405", card_name="Snorlax ex"),
    card("11193", "SPEC-0273", "SV9s", "109/139", "Hops-Snorlax-Extra-Helpings-Dynamic-Press", ("R", "rare"), card_name="Hop's Snorlax"),
    card("13046", "SPEC-0274", "MA3", "136/193", "Hops-Snorlax-Extra-Helpings-Dynamic-Press", ("no printed rarity symbol", "fixed"), "U0130", card_name="Hop's Snorlax"),
    card("13749", "SPEC-0275", "MA3", "136/193", "Hops-Snorlax-Extra-Helpings-Dynamic-Press", ("no printed rarity symbol", "fixed"), "U0788", variant="V1", card_name="Hop's Snorlax"),
    card("13750", "SPEC-0276", "MA3", "136/193", "Hops-Snorlax-Extra-Helpings-Dynamic-Press", ("no printed rarity symbol", "fixed"), "U0793", variant="V2", card_name="Hop's Snorlax"),
    card("13857", "SPEC-0277", "MA4", "091/123", "Snorlax-Glutton-Topple-Over", ("C", "common")),
]


PROMO = {
    "printId": "TH:SM-P:083:base",
    "locality": "TH",
    "localSetCode": "SM-P",
    "localNumber": "083",
    "variant": "base",
    "language": "Thai",
    "script": "Thai",
    "name": "อีวุย&คาบิกอน GX",
    "cardName": "Eevee & Snorlax GX",
    "catchUpOf": "the Thai Eevee & Snorlax GX counterpart positively shown by SPEC-0026",
    "specimenId": "SPEC-0026",
    "providerId": "pokumon",
    "sourceUrl": "https://pokumon.com/card/eevee-snorlax-tag-team-gx-083-sm-p-thai-promo/",
    "corroborated": True,
    "markAssetUrl": None,
    "cardImageUrl": None,
    "releaseDate": "2020",
    "releaseDatePrecision": "year",
    "releaseApproximate": False,
    "evidence": "SPEC-0026 positively shows the exact Thai 083/SM-P card. Pokumon independently identifies its 2020 FunFromHome Gym Battle distribution, Ripple treatment and event stamp.",
    "work": "Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX",
    "rarity": ("PROMO", "promo"),
    "legacy": [],
}


ISSUE_UNITS = sorted({
    "U0052", "U0106", "U0130", "U0171", "U0176", "U0205", "U0235",
    "U0262", "U0309", "U0347", "U0387", "U0405", "U0604", "U0753",
    "U0788", "U0793",
})

def read(path: Path) -> dict[str, Any] | list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(encoded(payload), encoding="utf-8", newline="\n")


def discovery_rows() -> dict[str, dict[str, Any]]:
    rows = {}
    for line in DISCOVERY.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        detail = str(row.get("rawProviderId") or "")
        if row.get("locality") == "TH" and detail in {item["detail"] for item in OFFICIAL}:
            rows[detail] = row
    if len(rows) != len(OFFICIAL):
        raise ValueError("retained Thai discovery frontier differs from reviewed issue #262 detail ids")
    return rows


def official_rows() -> list[dict[str, Any]]:
    discovered = discovery_rows()
    result = []
    for facts in OFFICIAL:
        raw = discovered[facts["detail"]]
        date, precision = facts["date"] or SET_DATES[facts["localSetCode"]]
        row = {
            **facts,
            "locality": "TH",
            "language": "Thai",
            "script": "Thai",
            "name": raw["raw"]["localName"],
            "catchUpOf": "the exact Thai counterpart established by its printed Thai attacks and card traits",
            "providerId": "pokemon-card-asia",
            "sourceUrl": raw["sourceUrl"],
            "corroborated": False,
            "markAssetUrl": raw["raw"].get("setSymbolUrl"),
            "cardImageUrl": raw["raw"]["cardImageUrl"],
            "releaseDate": date,
            "releaseDatePrecision": precision,
            "releaseApproximate": False,
            "evidence": (
                f"The retained official Thai detail {facts['detail']} and {facts['specimenId']} show "
                f"{raw['raw']['localName']} {facts['localSetCode']} {facts['localNumber']}, including "
                f"the printed attacks used for the explicit Work mapping and rarity {facts['rarity'][0]}. "
                "The publisher render is identity and rarity evidence only; no physical finish is inferred."
            ),
        }
        if facts["detail"] == "13857":
            row["corroboratingSourceUrls"] = [
                "https://asia.pokemon-card.com/id/card-search/detail/18362/"
            ]
            row["evidence"] += (
                " The official Indonesian 091/123 detail independently shows the same HP, attack "
                "effects, illustrator and collector identity, supporting the Work equivalence."
            )
        result.append(row)
    return result


def persisted_source_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in row.items()
        if key not in {"detail", "work", "rarity", "legacy", "date"}
    }


def specimen_row(row: dict[str, Any]) -> dict[str, Any]:
    photograph = SPECIMEN_DIR / f"{row['specimenId']}.png"
    digest = hashlib.sha256(photograph.read_bytes()).hexdigest()
    return {
        "specimenId": row["specimenId"],
        "setCode": row["localSetCode"],
        "number": row["localNumber"],
        "variant": row["variant"],
        "language": "Thai",
        "heldBy": "publisher or database",
        "inspectedFrom": "official Pokémon Asia Thai card-detail render",
        "photograph": photograph.name,
        "photographSource": row["cardImageUrl"],
        "photographSha256": "sha256:" + digest,
        "observed": (
            f"Complete official Thai render for {row['cardName']} {row['localSetCode']} "
            f"{row['localNumber']} ({row['variant']}). The printed Thai name, collector identity, "
            f"attacks and rarity {row['rarity'][0]} establish this card release and Work equivalence. "
            "Retained as identity and rarity evidence only; no physical finish is inferred."
        ),
        "recordedAt": "2026-08-28",
        "citedBy": sorted({*row["legacy"], row["printId"]}),
        "listingUrl": row["sourceUrl"],
    }


def build_profile(code: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    numbers = sorted(row["localNumber"] for row in rows)
    denominators = {number.partition("/")[2] for number in numbers if number.partition("/")[2].isdigit()}
    return {
        "sourceRecordId": stable_profile_id("TH", code),
        "sourceKind": "source-first-local-set-profile",
        "provider": "mixed-positive-evidence",
        "providerRecordKey": f"TH\x1f{code}",
        "retrieved": "2026-08-28",
        "raw": {
            "localCode": code,
            "localName": None,
            "locality": "TH",
            "languages": ["Thai"],
            "scripts": ["Thai"],
            "printIds": sorted(row["printId"] for row in rows),
            "providers": sorted({row["providerId"] for row in rows}),
            "sourceUrls": sorted({row["sourceUrl"] for row in rows}),
            "printedSetSize": int(next(iter(denominators))) if len(denominators) == 1 else None,
            "printedSetSizeBasis": "the denominator printed on every observed card" if len(denominators) == 1 else "no common printed denominator is inferred",
            "localeSuffix": None,
            "observedCollectorNumbers": numbers,
            "observedCoverage": "exact positive Thai cards reviewed for issue #262, not a set enumeration",
            "markAssetUrls": sorted({row["markAssetUrl"] for row in rows if row.get("markAssetUrl")}),
            "cardImageUrls": sorted({row["cardImageUrl"] for row in rows if row.get("cardImageUrl")}),
        },
    }


def apply_profiles(document: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["localSetCode"], []).append(row)
    profiles = {code: build_profile(code, group) for code, group in grouped.items()}
    by_id = {row["sourceRecordId"]: row for row in document["sourceRecords"]}
    by_id.update({profile["sourceRecordId"]: profile for profile in profiles.values()})
    document["sourceRecords"] = sorted(by_id.values(), key=lambda row: row["sourceRecordId"])
    document["meta"]["counts"]["sourceRecords"] = len(document["sourceRecords"])
    document["meta"]["counts"]["sourceFirstLocalSets"] = sum(row["sourceKind"] == "source-first-local-set-profile" for row in document["sourceRecords"])
    return profiles


def release_id(row: dict[str, Any]) -> str:
    return f"RELEASE:TH:Thai:{row['localSetCode']}:{row['localNumber']}:{row['work']}"


def apply_set_graph(graph: dict[str, Any], profile: dict[str, Any], code: str, claim_ids: list[str]) -> None:
    source_id = profile["sourceRecordId"]
    local_set_id = f"LOCALSET:TH:{quote(code, safe='')}"
    edition_id = f"EDITION:TH:Thai:{code}"
    localization_id = "LOCALIZATION:TH:th"
    upsert_entity(graph, "set-source-record", source_id, profile, origin="reviewed-evidence-issue-262")
    disposition = {"sourceRecordId": source_id, "disposition": "mapped", "targetRef": local_set_id, "reason": "positive Thai source-first records establish this local set"}
    upsert_entity(graph, "set-source-disposition", source_id, disposition, origin="reviewed-evidence-issue-262")
    upsert_edge(graph, "set-source-disposition", source_id, "disposes", "set-source-record", source_id)
    upsert_migration(graph, {"sourceKind": "set-catalogue-source", "sourceId": source_id, "disposition": "mapped", "targetRef": local_set_id, "reason": disposition["reason"]})
    matches = [item for item in graph["entities"] if item.get("entityType") == "local-set" and item.get("entityId") == local_set_id]
    if matches:
        append_unique(matches[0]["payload"].setdefault("sourceRecordIds", []), source_id)
    else:
        upsert_entity(graph, "local-set", local_set_id, {"localSetId": local_set_id, "locality": "TH", "localCode": code, "observedNames": [], "productKind": "physical-card-set-or-product", "sourceRecordIds": [source_id]}, origin="reviewed-evidence-issue-262")
    upsert_edge(graph, "local-set", local_set_id, "observed-by", "set-source-record", source_id)
    editions = [item for item in graph["entities"] if item.get("entityType") == "set-edition" and item.get("entityId") == edition_id]
    if editions:
        payload = editions[0]["payload"]
        append_unique(payload["identity"].setdefault("establishingClaimIds", []), *claim_ids)
        append_unique(payload["catalogue"].setdefault("establishingEvidenceIds", []), source_id)
        payload["catalogue"]["localSetId"] = local_set_id
    else:
        upsert_entity(graph, "set-edition", edition_id, {
            "setEditionId": edition_id,
            "identity": {"setEditionId": edition_id, "locality": "TH", "language": "Thai", "script": "Thai", "localSetCode": code, "localIdentifierKnown": True, "state": "identified", "viaLegacySetCodes": [], "establishingClaimIds": claim_ids, "localizationId": localization_id},
            "catalogue": {"setEditionId": edition_id, "localSetId": local_set_id, "locality": "TH", "language": "Thai", "script": "Thai", "localCode": code, "state": "identified", "establishingEvidenceIds": [source_id], "localizationId": localization_id},
        }, origin="reviewed-evidence-issue-262")
    upsert_edge(graph, "set-edition", edition_id, "belongs-to", "local-set", local_set_id)
    upsert_edge(graph, "set-edition", edition_id, "localized-as", "localization", localization_id, {"decisionRef": "https://github.com/m4s-ai/snoredex-data/issues/254", "reviewedAt": "2026-08-24"})


def remove_obsolete_group(
    graph: dict[str, Any], group: list[dict[str, Any]], target: str, units: dict[str, dict[str, Any]],
) -> tuple[list[tuple[str, str | None]], list[str], dict[str, list[str]]]:
    first = group[0]
    legacy_ids = {unit_id for row in group for unit_id in row["legacy"]}
    patterns = {
        (str(units[unit_id]["setCode"]), str(units[unit_id]["number"]).lstrip("0"))
        for unit_id in legacy_ids
    }

    def matches_old_ref(value: Any) -> bool:
        text = str(value or "")
        if not text.startswith("RELEASE:TH:Thai:"):
            return False
        return any(
            f":via-{code}:unknown-local-set:via-{number}:" in text
            for code, number in patterns
        )

    obsolete = {
        item["entityId"] for item in graph["entities"]
        if item.get("entityType") == "card-release"
        and item.get("entityId") != target
        and item.get("payload", {}).get("language") == "Thai"
        and (
            (
                item.get("payload", {}).get("localSetCode") == first["localSetCode"]
                and str(item.get("payload", {}).get("localNumber") or "").partition("/")[0].lstrip("0")
                == first["localNumber"].partition("/")[0].lstrip("0")
            )
            or matches_old_ref(item.get("entityId"))
        )
    }
    for item in graph["entities"]:
        payload = item.get("payload", {})
        if item.get("entityType") == "candidate-claim" and payload.get("sourceKind") == "legacy-language-unit" and payload.get("sourceId") in legacy_ids:
            old_target = payload.get("materializedTargetId")
            if old_target and old_target != target:
                obsolete.add(old_target)

    old_payloads = [
        item.get("payload", {}) for item in graph["entities"]
        if item.get("entityType") == "card-release" and item.get("entityId") in {*obsolete, target}
    ]
    legacy_claims: list[tuple[str, str | None]] = []
    finish_claims: list[str] = []
    for item in graph["entities"]:
        payload = item.get("payload", {})
        if item.get("entityType") != "candidate-claim":
            continue
        if payload.get("sourceKind") == "legacy-language-unit" and payload.get("sourceId") in legacy_ids:
            payload["proposedTargetId"] = target
            payload["materializedTargetId"] = target
            legacy_claims.append((item["entityId"], payload.get("sourceRecord")))
            upsert_migration(graph, {"sourceKind": "legacy-language-unit", "sourceId": payload["sourceId"], "disposition": "established-and-mapped", "targetRef": target, "reason": payload["reason"]})
        proposed = payload.get("proposedCardReleaseId")
        if payload.get("sourceKind") == "finish-printing-record" and (proposed in obsolete or matches_old_ref(proposed)):
            payload["proposedCardReleaseId"] = target
            finish_claims.append(item["entityId"])
    for disposition in graph["migrationDispositions"]:
        if disposition.get("targetRef") in obsolete or matches_old_ref(disposition.get("targetRef")):
            disposition["targetRef"] = target
        if "targetRefs" in disposition:
            disposition["targetRefs"] = [target if value in obsolete or matches_old_ref(value) else value for value in disposition["targetRefs"]]
    catalogue = {item["entityId"] for item in graph["entities"] if item.get("entityType") == "catalogue-card-release-ref" and item.get("payload", {}).get("cardReleaseId") in obsolete}
    graph["entities"] = [item for item in graph["entities"] if not ((item.get("entityType") == "card-release" and item.get("entityId") in obsolete) or (item.get("entityType") == "catalogue-card-release-ref" and item.get("entityId") in catalogue))]
    graph["edges"] = [edge for edge in graph["edges"] if not ((edge.get("fromType") == "card-release" and edge.get("fromId") in obsolete) or (edge.get("toType") == "card-release" and edge.get("toId") in obsolete) or (edge.get("fromType") == "catalogue-card-release-ref" and edge.get("fromId") in catalogue) or (edge.get("toType") == "catalogue-card-release-ref" and edge.get("toId") in catalogue))]
    graph["edges"] = [edge for edge in graph["edges"] if not (edge.get("fromId") in finish_claims and edge.get("relation") == "proposes-for" and edge.get("toId") != target)]
    return legacy_claims, finish_claims, {
        "legacyProducts": sorted({item for payload in old_payloads for item in payload.get("legacyProducts", [])}),
        "legacyVariants": sorted({item for payload in old_payloads for item in payload.get("legacyVariants", [])}),
    }


def apply_release_group(
    graph: dict[str, Any], profile: dict[str, Any], group: list[dict[str, Any]], units: dict[str, dict[str, Any]],
) -> None:
    first = group[0]
    rid = release_id(first)
    legacy_claims, finish_claims, heritage = remove_obsolete_group(graph, group, rid, units)
    source_claim_ids = []
    for row in group:
        claim_id = f"CLAIM:source-first:{row['printId']}"
        source_claim_ids.append(claim_id)
        claim = {"claimId": claim_id, "claimKind": "card-release", "sourceKind": "source-first-record", "sourceId": row["printId"], "sourceRecord": row["sourceUrl"], "evidenceStatus": "confirmed", "disposition": "established-and-mapped", "proposedTargetId": rid, "materializedTargetId": rid, "reason": "positive exact Thai card record and retained image"}
        upsert_entity(graph, "candidate-claim", claim_id, claim, origin="reviewed-evidence-issue-262")
        upsert_edge(graph, "candidate-claim", claim_id, "materializes", "card-release", rid, {"disposition": "established-and-mapped"})
        upsert_migration(graph, {"sourceKind": "source-first-record", "sourceId": row["printId"], "disposition": "established-and-mapped", "targetRef": rid, "reason": claim["reason"]})
    legacy_ids = sorted({unit_id for row in group for unit_id in row["legacy"]})
    claim_ids = sorted({*source_claim_ids, *(item[0] for item in legacy_claims)})
    mapping_state = "mapped-by-explicit-equivalence" if legacy_ids else "mapped"
    payload = {
        "cardReleaseId": rid,
        "setEditionId": f"EDITION:TH:Thai:{first['localSetCode']}",
        "locality": "TH",
        "language": "Thai",
        "script": "Thai",
        "localSetCode": first["localSetCode"],
        "localNumber": first["localNumber"],
        "localIdentifierKnown": True,
        "state": "identified",
        "work": first["work"],
        "workMappingState": mapping_state,
        "viaLegacySetCode": None,
        "viaLegacyNumber": None,
        "claimIds": claim_ids,
        "establishingClaimIds": claim_ids,
        "nonEstablishingClaimIds": [],
        "legacyVariants": sorted(set(heritage["legacyVariants"]) | {row["variant"] for row in group}),
        "legacyProducts": heritage["legacyProducts"],
        "sourceRecords": sorted({row["sourceUrl"] for row in group} | {value for _, value in legacy_claims if value}),
        "sourceFirstRecordIds": sorted(row["printId"] for row in group),
        "legacyCounterpartUnitIds": legacy_ids,
        "legacyIdentityAliases": sorted(
            {
                (str(units[unit_id]["setCode"]), str(units[unit_id]["number"]))
                for unit_id in legacy_ids
            }
        ),
        "releaseDate": first["releaseDate"],
        "releaseDatePrecision": first["releaseDatePrecision"],
        "releaseApproximate": False,
    }
    upsert_entity(graph, "card-release", rid, payload, origin="reviewed-evidence-issue-262")
    work_id = f"WORK:{first['work']}"
    if not any(item.get("entityType") == "work" and item.get("entityId") == work_id for item in graph["entities"]):
        upsert_entity(
            graph,
            "work",
            work_id,
            {"workId": work_id, "cardKey": first["work"]},
            origin="reviewed-evidence-issue-262",
        )
    for claim_id, _ in legacy_claims:
        upsert_edge(graph, "candidate-claim", claim_id, "materializes", "card-release", rid, {"disposition": "established-and-mapped"})
    for claim_id in finish_claims:
        upsert_edge(graph, "candidate-claim", claim_id, "proposes-for", "card-release", rid)
    upsert_edge(graph, "card-release", rid, "belongs-to", "set-edition", payload["setEditionId"])
    upsert_edge(graph, "card-release", rid, "implements", "work", f"WORK:{first['work']}", {"state": mapping_state, "basis": "exact Thai printed attacks and card traits"})
    upsert_entity(graph, "catalogue-card-release-ref", rid, {"cardReleaseId": rid, "setEditionId": payload["setEditionId"], "collectorNumber": first["localNumber"], "origin": "issue-262-positive-evidence"}, origin="reviewed-evidence-issue-262")
    upsert_edge(graph, "catalogue-card-release-ref", rid, "belongs-to", "set-edition", payload["setEditionId"])
    upsert_edge(graph, "catalogue-card-release-ref", rid, "references", "card-release", rid)
    rarity_id = "RARITYCLAIM:issue262:" + rid.removeprefix("RELEASE:TH:Thai:")
    rarity = {"rarityClaimId": rarity_id, "cardReleaseId": rid, "sourceRecordId": profile["sourceRecordId"], "sourceProvider": "mixed-positive-evidence", "sourceVocabulary": "printed-Thai-card", "sourceNativeValue": first["rarity"][0], "normalizedRarityId": first["rarity"][1], "sourceProductKey": first["sourceUrl"]}
    upsert_entity(graph, "rarity-claim", rarity_id, rarity, origin="reviewed-evidence-issue-262")
    upsert_edge(graph, "rarity-claim", rarity_id, "asserts-rarity-for", "card-release", rid)
    upsert_edge(graph, "rarity-claim", rarity_id, "observed-by", "set-source-record", profile["sourceRecordId"])


def apply_graph(
    graph: dict[str, Any], profiles: dict[str, dict[str, Any]], rows: list[dict[str, Any]], units: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_code: dict[str, list[dict[str, Any]]] = {}
    by_release: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_code.setdefault(row["localSetCode"], []).append(row)
        by_release.setdefault(release_id(row), []).append(row)
    for code, group in by_code.items():
        apply_set_graph(graph, profiles[code], code, sorted(f"CLAIM:source-first:{row['printId']}" for row in group))
    for group in by_release.values():
        apply_release_group(graph, profiles[group[0]["localSetCode"]], group, units)

    mappings = []
    for row in rows:
        rid = release_id(row)
        for legacy_id in row["legacy"]:
            assertion_id = f"ASSERT:same-work:{legacy_id}:{row['printId']}"
            evidence = "The exact Thai card identity and printed attacks establish this local counterpart without merging release identities."
            assertion = {"assertionId": assertion_id, "assertionType": "same-work-decision", "fromId": rid, "toId": f"WORK:{row['work']}", "legacyUnitId": legacy_id, "sourceFirstRecordId": row["printId"], "assertedBy": "repository verification pass", "assertedAt": "2026-08-28", "evidenceUrl": row["sourceUrl"], "evidence": evidence, "destructiveMergeAllowed": False}
            upsert_entity(graph, "equivalence-assertion", assertion_id, assertion, origin="reviewed-evidence-issue-262")
            upsert_edge(graph, "equivalence-assertion", assertion_id, "relates", "card-release", rid, assertion)
            upsert_edge(graph, "equivalence-assertion", assertion_id, "relates", "work", f"WORK:{row['work']}", assertion)
            upsert_migration(graph, {"sourceKind": "legacy-issue-rekey", "sourceId": legacy_id, "disposition": "linked-local-counterpart", "targetRef": rid, "targetRefs": [rid], "reason": "issue #262 re-key"})
            mappings.append({key: assertion[key] for key in ("legacyUnitId", "sourceFirstRecordId", "assertionType", "assertedBy", "assertedAt", "evidenceUrl", "evidence")})
    mapped = {row["legacyUnitId"] for row in mappings}
    for legacy_id in set(ISSUE_UNITS) - mapped:
        upsert_migration(graph, {"sourceKind": "legacy-issue-rekey", "sourceId": legacy_id, "disposition": "needs-positive-local-identity", "targetRef": None, "targetRefs": [], "reason": "issue #262 re-key"})
    return graph_projection.project_physical_evidence(graph), sorted(mappings, key=lambda row: row["legacyUnitId"])


def apply_finish_evidence(document: dict[str, Any]) -> None:
    document["sources"].update({
        "pokumon-th-smp083": {"url": PROMO["sourceUrl"], "sourceType": "Specialist per-language promo record", "authorityTier": "specialist-reference", "coverage": "positive-only", "supportsAbsence": False, "languages": ["Thai"], "retrievedAt": "2026-08-28", "evidence": "The exact Thai 083/SM-P record positively identifies the 2020 FunFromHome event card, Ripple treatment and event stamp."},
        "pokumon-th-svp082": {"url": "https://pokumon.com/card/snorlax-082-sv-p-thai-promo/", "sourceType": "Specialist per-language promo record", "authorityTier": "specialist-reference", "coverage": "positive-only", "supportsAbsence": False, "languages": ["Thai"], "retrievedAt": "2026-08-28", "evidence": "The exact Thai 082/SV-P record positively identifies the Central Pattana Great Celebration distribution, event stamp and Non-holo treatment."},
    })
    rows = [
        {"setCode": "xm2a", "releaseSetCode": "MA3", "number": "136", "languages": ["Thai"], "printings": []},
        {"setCode": "SM-P/TH", "releaseSetCode": "SM-P", "number": "083", "languages": ["Thai"], "printings": [{"finish": "holo", "foilPattern": "ripple", "markings": [{"kind": "stamp", "text": "POKÉMON TCG GYM", "role": "distribution-promo"}], "distribution": {"kind": "event-prize", "name": "FunFromHome: Bring the Gym Battle Home round 3"}, "cardSize": "standard", "mappedVariants": ["base"], "verificationStatus": "confirmed", "sourceRefs": ["pokumon-th-smp083"]}]},
        {"setCode": "SV-P/TH", "releaseSetCode": "SV-P", "number": "082/SV-P", "languages": ["Thai"], "printings": [{"finish": "non-holo", "foilPattern": None, "markings": [{"kind": "stamp", "text": "The Great Celebration 2024", "role": "distribution-promo"}], "distribution": {"kind": "purchase-promo", "name": "Central Pattana Great Celebration"}, "cardSize": "standard", "mappedVariants": ["base"], "verificationStatus": "confirmed", "sourceRefs": ["pokumon-th-svp082"]}]},
    ]
    keys = {(row["setCode"], row["number"], tuple(row["languages"])) for row in rows}
    document["overrides"] = [row for row in document["overrides"] if (row["setCode"], row["number"], tuple(row.get("languages") or [])) not in keys] + rows
    document["meta"]["lastUpdated"] = "2026-08-28"


def apply_discovery_adapters(document: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    discovered = discovery_rows()
    mappings = {(row["providerId"], row["rawLocale"], str(row["rawProviderId"])): row for row in document["explicitMappings"]}
    by_detail = {row["detail"]: row for row in rows}
    for detail, raw in discovered.items():
        if raw.get("bucket") != "new-candidate":
            continue
        source = by_detail[detail]
        key = (raw["providerId"], raw["rawLocale"], detail)
        mappings[key] = {"providerId": raw["providerId"], "surfaceId": raw["surfaceId"], "rawLocale": raw["rawLocale"], "rawProviderId": detail, "mode": "exact-match", "targetCardReleaseId": release_id(source), "evidence": "The retained official Thai detail and exact image establish this local card release and its printed Work traits."}
    document["explicitMappings"] = sorted(mappings.values(), key=lambda row: (row["providerId"], row["rawLocale"], str(row["rawProviderId"])))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    official = official_rows()
    rows = official + [PROMO]
    units = {row["unitId"]: row for row in read(UNITS)}

    prints = read(PRINTS)
    before_prints = encoded(prints)
    by_print = {row["printId"]: row for row in prints["prints"]}
    by_print.update({row["printId"]: persisted_source_row(row) for row in rows})
    prints["prints"] = sorted(by_print.values(), key=lambda row: row["printId"])
    prints["meta"]["generated"] = "2026-08-28"
    prints["meta"]["counts"]["admitted"] = len(prints["prints"])

    specimens = read(SPECIMENS)
    before_specimens = encoded(specimens)
    by_specimen = {row["specimenId"]: row for row in specimens["specimens"]}
    by_specimen.update({row["specimenId"]: specimen_row(row) for row in official})
    promo = by_specimen["SPEC-0026"]
    promo["listingUrl"] = PROMO["sourceUrl"]
    promo["citedBy"] = sorted(set(promo.get("citedBy") or []) | {PROMO["printId"]})
    promo["physicalObservation"] = {"finish": "holo", "foilPattern": "ripple", "markings": "POKÉMON TCG GYM stamp in artwork", "markingRole": "distribution-promo", "distribution": {"kind": "event-prize", "name": "FunFromHome: Bring the Gym Battle Home round 3"}, "cardSize": "standard", "basis": "The owner photograph establishes the exact stamped card identity; Pokumon's exact 083/SM-P Thai record independently classifies its Ripple treatment and event distribution."}
    promo["observed"] = promo["observed"].replace(" — a distribution marking, markings.role distribution-promo, which implies no finish. This is the printing pokumon listed and nothing else here recorded.", ". The exact physical finish is recorded separately from the card identity.")
    specimens["specimens"] = sorted(by_specimen.values(), key=lambda row: int(row["specimenId"].split("-")[1]))
    specimens["count"] = len(specimens["specimens"])
    if not args.check:
        # The physical-evidence projection reads canonical specimens from disk.
        write(SPECIMENS, specimens)

    sources = read(SET_SOURCES)
    before_sources = encoded(sources)
    profiles = apply_profiles(sources, rows)

    finishes = read(FINISHES)
    before_finishes = encoded(finishes)
    apply_finish_evidence(finishes)
    if not args.check:
        # Existing Thai finish units still use Cardmarket's legacy xm2a label. Rebuild the
        # canonical finish projection after recording its reviewed MA3 release-set redirect,
        # so the physical-evidence graph can bind those confirmed printings to the exact card.
        write(FINISHES, finishes)
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "finishes.py"), "--offline"],
            cwd=ROOT,
            check=True,
        )

    adapters = read(DISCOVERY_ADAPTERS)
    before_adapters = encoded(adapters)
    apply_discovery_adapters(adapters, official)

    rekeys = read(REKEYS)
    before_rekeys = encoded(rekeys)
    graph = read(GRAPH)
    before_graph = encoded(graph)
    graph, mappings = apply_graph(graph, profiles, rows, units)
    question = {"issueNumber": 262, "locality": "TH", "language": "Thai", "legacyUnitIds": ISSUE_UNITS, "defaultDisposition": "needs-positive-local-identity", "mappings": mappings}
    by_issue = {row["issueNumber"]: row for row in rekeys["questionSets"]}
    by_issue[262] = question
    rekeys["questionSets"] = sorted(by_issue.values(), key=lambda row: row["issueNumber"])

    stale = [
        label for label, before, after in (
            ("prints", before_prints, encoded(prints)),
            ("specimens", before_specimens, encoded(specimens)),
            ("set sources", before_sources, encoded(sources)),
            ("finishes", before_finishes, encoded(finishes)),
            ("discovery adapters", before_adapters, encoded(adapters)),
            ("rekeys", before_rekeys, encoded(rekeys)),
            ("graph", before_graph, encoded(graph)),
        ) if before != after
    ]
    if args.check:
        if stale:
            raise SystemExit("issue #262 Thai reviewed inputs are stale: " + ", ".join(stale))
        print("issue #262 Thai reviewed inputs are current")
        return 0

    for path, document in (
        (PRINTS, prints), (SPECIMENS, specimens), (SET_SOURCES, sources),
        (FINISHES, finishes), (DISCOVERY_ADAPTERS, adapters),
        (REKEYS, rekeys), (GRAPH, graph),
    ):
        write(path, document)
    print(f"admitted {len(rows)} Thai source-first records, {len(mappings)} positive re-keys and {len(official)} new image specs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

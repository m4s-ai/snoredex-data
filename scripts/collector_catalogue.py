#!/usr/bin/env python3
"""Build the locality-aware collector contract for snoredex-checklist (#254).

The authoritative graph decides what exists.  ``analysis_checklist.json`` is read only
as the 1.5.0 predecessor whose ids must migrate without disappearing.  Personal
collection state is neither read nor written.

    python scripts/collector_catalogue.py
    python scripts/collector_catalogue.py --check
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = ROOT / "verification" / "authoritative_graph.json"
CHECKLIST_PATH = ROOT / "analysis_checklist.json"
FINISH_UNITS_PATH = ROOT / "verification" / "finish_units.json"
SOURCE_FIRST_PATH = ROOT / "verification" / "source_first_prints.json"
SPECIMENS_PATH = ROOT / "verification" / "specimens.json"
COMPLETENESS_PATH = ROOT / "verification" / "completeness_gate.json"

CATALOGUE_PATH = ROOT / "collector_catalogue.json"
SCHEMA_PATH = ROOT / "collector_catalogue.schema.json"
MIGRATIONS_PATH = ROOT / "collector_migrations.json"
FIXTURE_PATH = ROOT / "collector_catalogue.fixture.json"

SCHEMA_NAME = "snoredex-collector-catalogue"
SCHEMA_VERSION = "1.0.0"
DATASET_ID = "snoredex-data/snorlax-current-known"
SOURCE_REPOSITORY = "https://github.com/m4s-ai/snoredex-data"
ASSET_BASE_URL = "https://m4s-ai.github.io/snoredex-data/"
CORRECTION_URL = SOURCE_REPOSITORY + "/issues/new?template=data-correction.yml"
FINISH_FAMILY = {
    "non-holo": "non-holo",
    "holo": "holo",
    "reverse-holo": "reverse-holo",
    "mirror-holo": "reverse-holo",
    "unknown": "unknown",
}
IMAGE_SCOPE_RANK = {"unknown": 0, "legacy-product": 1, "card-release": 2, "exact-printing": 3}
CUMULATIVE_CHECKLIST_REKEYS = {
    "ju-11-dutch-1e-unresolved-unknown": "ju-11-dutch-1e-holo-edition-stamp-editie-1",
    "ju-11-dutch-unl-unresolved-unknown": "ju-11-dutch-unl-holo",
    "ju-27-dutch-1e-unresolved-unknown": "ju-27-dutch-1e-non-holo-edition-stamp-editie-1",
    "ju-27-dutch-unl-unresolved-unknown": "ju-27-dutch-unl-non-holo",
}


class ContractError(ValueError):
    pass


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def semantic_fingerprint(document: dict[str, Any]) -> str:
    payload = copy.deepcopy(document)
    payload.get("meta", {}).pop("catalogueFingerprint", None)
    return sha256_bytes(canonical_bytes(payload))


def write_json(path: Path, document: Any) -> None:
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def item_id(anchor: str) -> str:
    value = uuid.uuid5(uuid.NAMESPACE_URL, SOURCE_REPOSITORY + "/collector-item/v1/" + anchor)
    return "item-" + str(value)


def group_id(anchor: str) -> str:
    value = uuid.uuid5(uuid.NAMESPACE_URL, SOURCE_REPOSITORY + "/finish-group/v1/" + anchor)
    return "finish-group-" + str(value)


def asset_id(path: str) -> str:
    value = uuid.uuid5(uuid.NAMESPACE_URL, SOURCE_REPOSITORY + "/asset/v1/" + path)
    return "asset-" + str(value)


def state_transition(from_item_id: str, to_item_ids: list[str]) -> dict[str, Any]:
    targets = sorted(set(to_item_ids))
    if not targets:
        raise ContractError(f"state transition has no target: {from_item_id}")
    split = len(targets) > 1
    return {
        "fromItemId": from_item_id,
        "toItemIds": targets,
        "changeKind": "split-1:N" if split else "rekey-1:1",
        "automaticStateAction": "none" if split else "preserve",
        "reconciliation": "requires-user-resolution" if split else "one-to-one-preserve",
    }


def natural_key(value: Any) -> str:
    return re.sub(r"\d+", lambda match: match.group(0).zfill(12), str(value or "").casefold())


def edition_identity(payload: dict[str, Any]) -> dict[str, Any]:
    return payload["identity"] if isinstance(payload.get("identity"), dict) else payload


def edition_catalogue(payload: dict[str, Any]) -> dict[str, Any]:
    catalogue = payload.get("catalogue")
    if not isinstance(catalogue, dict):
        raise ContractError(f"set edition has no catalogue parent: {payload.get('setEditionId')}")
    return catalogue


def entity_payloads(graph: dict[str, Any], entity_type: str) -> list[dict[str, Any]]:
    return [row["payload"] for row in graph["entities"] if row["entityType"] == entity_type]


def image_mime(path: Path) -> str:
    data = path.read_bytes()[:16]
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    raise ContractError(f"unsupported image bytes: {path.relative_to(ROOT)}")


def normalized_markings(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list) or any(
        not isinstance(row, dict)
        or any(not isinstance(row.get(key), str) or not row[key] for key in ("kind", "role", "text"))
        for row in value
    ):
        raise ContractError("markings must be structured objects with explicit roles")
    return [dict(row) for row in value]


def split_collector_number(value: Any) -> tuple[str | None, str | None]:
    text = str(value or "").strip()
    if not text:
        return None, None
    match = re.fullmatch(r"(.+?)/(\d+)", text)
    return (match.group(1), match.group(2)) if match else (text, None)


def release_lookup(releases: list[dict[str, Any]]) -> dict[tuple[str, str, str], list[str]]:
    lookup: defaultdict[tuple[str, str, str], list[str]] = defaultdict(list)
    for release in releases:
        codes = {release.get("localSetCode"), release.get("viaLegacySetCode")} - {None}
        numbers = {
            str(value or "") for value in (release.get("localNumber"), release.get("viaLegacyNumber"))
        }
        for code in codes:
            for number in numbers:
                lookup[(str(code), number, release["language"])].append(release["cardReleaseId"])
    return lookup


def legacy_release_id(
    item: dict[str, Any], lookup: dict[tuple[str, str, str], list[str]]
) -> str:
    key = (item["setCode"], str(item.get("number") or ""), item["language"])
    targets = sorted(set(lookup.get(key, [])))
    if len(targets) != 1:
        raise ContractError(f"legacy checklist row does not resolve exactly once: {item['checklistId']} -> {targets}")
    return targets[0]


def release_event_view(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_edition: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        for edition_id in event.get("setEditionIds") or []:
            by_edition[edition_id].append(event)
    result: dict[str, dict[str, Any]] = {}
    for edition_id, rows in by_edition.items():
        row = min(rows, key=lambda event: (event.get("dateValue") or "9999", event["releaseEventId"]))
        result[edition_id] = {
            "releaseDate": row.get("dateValue"),
            "releaseDatePrecision": row.get("datePrecision"),
            "releaseApproximate": bool(row.get("approximate")),
            "releaseEventId": row["releaseEventId"],
        }
    return result


def normalized_rarity(
    release_id: str,
    old_item: dict[str, Any] | None,
    claims_by_release: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    claims = claims_by_release.get(release_id, [])
    normalized = sorted({row.get("normalizedRarityId") for row in claims if row.get("normalizedRarityId")})
    if len(normalized) > 1:
        status = "conflicting"
        normalized_id = None
    elif normalized:
        status = "source-backed"
        normalized_id = normalized[0]
    elif old_item and old_item.get("rarity"):
        status = "marketplace-claimed"
        normalized_id = None
    else:
        status = "unknown"
        normalized_id = None
    display = (old_item or {}).get("rarity") or next(
        (row.get("sourceNativeValue") for row in claims if row.get("sourceNativeValue")), None
    )
    return {
        "display": display,
        "normalizedId": normalized_id,
        "evidenceStatus": status,
        "claimRefs": sorted(row["rarityClaimId"] for row in claims),
    }


def schema_document() -> dict[str, Any]:
    nullable_string = {"type": ["string", "null"]}
    string_array = {"type": "array", "items": {"type": "string"}, "uniqueItems": True}
    uri_array = {
        "type": "array", "items": {"type": "string", "format": "uri"}, "uniqueItems": True,
    }
    marking = {
        "type": "object",
        "additionalProperties": False,
        "required": ["kind", "role", "text"],
        "properties": {
            key: {"type": "string", "minLength": 1} for key in ("kind", "role", "text")
        },
    }
    distribution = {
        "type": ["object", "null"],
        "additionalProperties": False,
        "properties": {key: nullable_string for key in ("kind", "name", "region", "date", "text")},
    }
    item_properties: dict[str, Any] = {
        "itemId": {"type": "string", "pattern": "^item-[0-9a-f-]{36}$"},
        "legacyChecklistIds": string_array,
        "active": {"type": "boolean"},
        "itemKind": {"enum": ["verified-printing", "finish-candidate", "research-placeholder"]},
        "progressClass": {"enum": ["current-known", "research"]},
        "workId": nullable_string,
        "workMappingState": {"type": "string"},
        "setEditionId": {"type": "string"},
        "localSetId": {"type": "string"},
        "cardReleaseId": {"type": "string"},
        "physicalPrintingId": nullable_string,
        "sourcePrintingId": nullable_string,
        "finishUnitId": nullable_string,
        "sourceClaimRefs": string_array,
        "localizationId": {"type": "string"},
        "cardName": {"type": "string", "minLength": 1},
        "localCardName": nullable_string,
        "localSetCode": nullable_string,
        "localSetName": nullable_string,
        "collectorNumber": nullable_string,
        "collectorNumberDenominator": nullable_string,
        "collectorNumberSortKey": {"type": "string"},
        "edition": nullable_string,
        "editionAssignmentStatus": {"enum": ["assigned", "not-applicable", "unresolved"]},
        "finishVerificationStatus": {"type": "string"},
        "finish": nullable_string,
        "finishFamily": nullable_string,
        "finishGroupId": {"type": "string"},
        "foilPattern": nullable_string,
        "markings": {"type": "array", "items": marking},
        "distribution": distribution,
        "cardSize": {"type": "string"},
        "errorClass": nullable_string,
        "rarity": {
            "type": "object",
            "additionalProperties": False,
            "required": ["display", "normalizedId", "evidenceStatus", "claimRefs"],
            "properties": {
                "display": nullable_string,
                "normalizedId": nullable_string,
                "evidenceStatus": {"enum": ["source-backed", "marketplace-claimed", "conflicting", "unknown"]},
                "claimRefs": string_array,
            },
        },
        "completenessStatus": {"type": "string"},
        "releaseDate": nullable_string,
        "releaseDatePrecision": nullable_string,
        "releaseApproximate": {"type": "boolean"},
        "releaseSortKey": {"type": "string"},
        "imageAssetId": nullable_string,
        "imageScope": {"enum": ["exact-printing", "card-release", "legacy-product", "unknown"]},
        "sourceLinks": uri_array,
        "evidenceLinks": uri_array,
        "correctionLink": {"type": "string", "format": "uri"},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": ASSET_BASE_URL + "collector_catalogue.schema.json",
        "title": "Snoredex collector catalogue",
        "type": "object",
        "additionalProperties": False,
        "required": ["meta", "localizations", "localSets", "setEditions", "works", "items", "assets", "qualitySummary"],
        "properties": {
            "meta": {
                "type": "object",
                "additionalProperties": False,
                "required": ["schema", "schemaVersion", "datasetId", "sourceRepository", "dataAsOf", "catalogueFingerprint", "previousFingerprint", "assetBaseUrl", "scope", "licenceRefs"],
                "properties": {
                    "schema": {"const": SCHEMA_NAME},
                    "schemaVersion": {"const": SCHEMA_VERSION},
                    "datasetId": {"type": "string"},
                    "sourceRepository": {"type": "string", "format": "uri"},
                    "dataAsOf": {"type": "string", "format": "date"},
                    "catalogueFingerprint": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                    "previousFingerprint": nullable_string,
                    "assetBaseUrl": {"type": "string", "format": "uri"},
                    "scope": {
                        "type": "object", "additionalProperties": False,
                        "required": ["policy", "allLocalitiesComplete", "absenceIsNotEvidence"],
                        "properties": {
                            "policy": {"const": "positive-evidence/current-known"},
                            "allLocalitiesComplete": {"const": False},
                            "absenceIsNotEvidence": {"const": True},
                        },
                    },
                    "licenceRefs": string_array,
                },
            },
            "localizations": {"type": "array", "items": {"$ref": "#/$defs/localization"}},
            "localSets": {"type": "array", "items": {"$ref": "#/$defs/localSet"}},
            "setEditions": {"type": "array", "items": {"$ref": "#/$defs/setEdition"}},
            "works": {"type": "array", "items": {"$ref": "#/$defs/work"}},
            "items": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": list(item_properties), "properties": item_properties}},
            "assets": {"type": "array", "items": {"$ref": "#/$defs/asset"}},
            "qualitySummary": {"type": "object"},
        },
        "$defs": {
            "localization": {
                "type": "object", "additionalProperties": False,
                "required": ["localizationId", "locality", "languageId", "language", "languageTag", "script", "displayName", "displayOrder"],
                "properties": {
                    "localizationId": {"type": "string"}, "locality": {"type": "string"},
                    "languageId": {"type": "string"}, "language": {"type": "string"},
                    "languageTag": {"type": "string"}, "script": {"type": "string"},
                    "displayName": {"type": "string"}, "displayOrder": {"type": "integer"},
                },
            },
            "localSet": {
                "type": "object", "additionalProperties": False,
                "required": ["localSetId", "locality", "localSetCode", "localSetName", "productKind", "identityState", "sourceRefs", "sortKey"],
                "properties": {
                    "localSetId": {"type": "string"}, "locality": {"type": "string"},
                    "localSetCode": nullable_string, "localSetName": nullable_string,
                    "productKind": {"type": "string"}, "identityState": {"type": "string"},
                    "sourceRefs": string_array, "sortKey": {"type": "string"},
                },
            },
            "setEdition": {
                "type": "object", "additionalProperties": False,
                "required": ["setEditionId", "localSetId", "localizationId", "localSetCode", "localSetName", "identityState", "releaseDate", "releaseDatePrecision", "releaseApproximate", "releaseEventId", "sortKey"],
                "properties": {
                    "setEditionId": {"type": "string"}, "localSetId": {"type": "string"},
                    "localizationId": {"type": "string"}, "localSetCode": nullable_string,
                    "localSetName": nullable_string, "identityState": {"type": "string"},
                    "releaseDate": nullable_string, "releaseDatePrecision": nullable_string,
                    "releaseApproximate": {"type": "boolean"}, "releaseEventId": nullable_string,
                    "sortKey": {"type": "string"},
                },
            },
            "work": {
                "type": "object", "additionalProperties": False,
                "required": ["workId", "cardKey", "displayName"],
                "properties": {"workId": {"type": "string"}, "cardKey": {"type": "string"}, "displayName": nullable_string},
            },
            "asset": {
                "type": "object", "additionalProperties": False,
                "required": ["assetId", "path", "url", "sha256", "mimeType", "imageScope", "altTextBasis", "attribution"],
                "properties": {
                    "assetId": {"type": "string"}, "path": {"type": "string"},
                    "url": {"type": "string", "format": "uri"},
                    "sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                    "mimeType": {"enum": ["image/png", "image/jpeg", "image/webp"]},
                    "imageScope": {"enum": ["exact-printing", "card-release", "legacy-product", "unknown"]},
                    "altTextBasis": {"type": "string"},
                    "attribution": {
                        "type": "object", "additionalProperties": False,
                        "required": ["rightsStatus", "licenceRef", "noticeRef"],
                        "properties": {
                            "rightsStatus": {"const": "third-party-rights-excluded-from-project-grants"},
                            "licenceRef": {"const": "LICENSE.md"},
                            "noticeRef": {"const": "THIRD_PARTY_NOTICES.md"},
                        },
                    },
                },
            },
        },
    }


def build_catalogue() -> tuple[dict[str, Any], dict[str, Any]]:
    graph = read_json(GRAPH_PATH)
    if graph.get("meta", {}).get("schemaVersion") != "1.1.0":
        raise ContractError("collector catalogue requires authoritative graph schema 1.1.0")
    predecessor = read_json(CHECKLIST_PATH)
    legacy_items = predecessor["items"]
    finish_units = read_json(FINISH_UNITS_PATH)["units"]
    source_first = {row["printId"]: row for row in read_json(SOURCE_FIRST_PATH)["prints"]}
    specimens = {row["specimenId"]: row for row in read_json(SPECIMENS_PATH)["specimens"]}
    completeness = read_json(COMPLETENESS_PATH)

    localizations = entity_payloads(graph, "localization")
    local_sets = {row["localSetId"]: row for row in entity_payloads(graph, "local-set")}
    editions = {row["setEditionId"]: row for row in entity_payloads(graph, "set-edition")}
    releases = {row["cardReleaseId"]: row for row in entity_payloads(graph, "card-release")}
    physicals = {row["physicalPrintingId"]: row for row in entity_payloads(graph, "physical-printing")}
    claims = {row["claimId"]: row for row in entity_payloads(graph, "candidate-claim")}
    works = entity_payloads(graph, "work")
    events = entity_payloads(graph, "release-event")
    rarity_claims = entity_payloads(graph, "rarity-claim")

    release_index = release_lookup(list(releases.values()))
    legacy_release = {
        row["checklistId"]: legacy_release_id(row, release_index) for row in legacy_items
    }
    legacy_by_printing = {row["printingId"]: row for row in legacy_items if row.get("printingId")}
    legacy_by_release: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in legacy_items:
        legacy_by_release[legacy_release[row["checklistId"]]].append(row)

    unit_by_id = {row["finishUnitId"]: row for row in finish_units}
    unit_by_printing: dict[str, dict[str, Any]] = {}
    printing_by_id: dict[str, dict[str, Any]] = {}
    for unit in finish_units:
        for printing in unit.get("printings", []):
            unit_by_printing[printing["printingId"]] = unit
            printing_by_id[printing["printingId"]] = printing

    physical_by_source = {
        row["sourcePrintingId"]: row for row in physicals.values() if row.get("sourcePrintingId")
    }
    candidate_by_source = {
        row["sourceId"]: row for row in claims.values()
        if row.get("sourceKind") == "finish-printing-record"
        and row.get("disposition") == "candidate-needs-evidence"
    }
    event_by_edition = release_event_view(events)
    rarity_by_release: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rarity_claims:
        rarity_by_release[row["cardReleaseId"]].append(row)
    work_id_by_key = {row["cardKey"]: row["workId"] for row in works}

    local_set_rows: list[dict[str, Any]] = []
    for row in local_sets.values():
        name = next(iter(row.get("observedNames") or []), None)
        local_set_rows.append({
            "localSetId": row["localSetId"],
            "locality": row["locality"],
            "localSetCode": row.get("localCode"),
            "localSetName": name,
            "productKind": row.get("productKind") or "unknown",
            "identityState": row.get("state") or "identified",
            "sourceRefs": sorted((row.get("sourceRecordIds") or []) + (row.get("evidenceRefs") or [])),
            "sortKey": "|".join((row["locality"], natural_key(row.get("localCode")), natural_key(name), row["localSetId"])),
        })
    local_set_rows.sort(key=lambda row: row["sortKey"])

    set_edition_rows: list[dict[str, Any]] = []
    for edition_id, row in editions.items():
        identity = edition_identity(row)
        catalogue = edition_catalogue(row)
        local_set = local_sets[catalogue["localSetId"]]
        event = event_by_edition.get(edition_id, {})
        name = next(iter(local_set.get("observedNames") or []), None)
        set_edition_rows.append({
            "setEditionId": edition_id,
            "localSetId": catalogue["localSetId"],
            "localizationId": identity["localizationId"],
            "localSetCode": catalogue.get("localCode"),
            "localSetName": name,
            "identityState": identity.get("state") or catalogue.get("state") or "identified",
            "releaseDate": event.get("releaseDate"),
            "releaseDatePrecision": event.get("releaseDatePrecision"),
            "releaseApproximate": bool(event.get("releaseApproximate")),
            "releaseEventId": event.get("releaseEventId"),
            "sortKey": "|".join((event.get("releaseDate") or "9999", identity["locality"], natural_key(catalogue.get("localCode")), edition_id)),
        })
    set_edition_rows.sort(key=lambda row: row["sortKey"])

    assets: dict[str, dict[str, Any]] = {}

    def register_asset(path_value: str | None, scope: str, alt_text: str) -> tuple[str | None, str]:
        if not path_value:
            return None, "unknown"
        relative = str(path_value).replace("\\", "/")
        path = ROOT / relative
        if not path.is_file():
            return None, "unknown"
        aid = asset_id(relative)
        existing = assets.get(aid)
        if existing and IMAGE_SCOPE_RANK[existing["imageScope"]] >= IMAGE_SCOPE_RANK[scope]:
            return aid, existing["imageScope"]
        assets[aid] = {
            "assetId": aid,
            "path": relative,
            "url": ASSET_BASE_URL + quote(relative, safe="/"),
            "sha256": sha256_bytes(path.read_bytes()),
            "mimeType": image_mime(path),
            "imageScope": scope,
            "altTextBasis": alt_text,
            "attribution": {
                "rightsStatus": "third-party-rights-excluded-from-project-grants",
                "licenceRef": "LICENSE.md",
                "noticeRef": "THIRD_PARTY_NOTICES.md",
            },
        }
        return aid, scope

    card_name_by_work: dict[str, str] = {}

    def item_context(release_id: str, old: dict[str, Any] | None) -> dict[str, Any]:
        release = releases[release_id]
        edition = editions[release["setEditionId"]]
        identity = edition_identity(edition)
        catalogue = edition_catalogue(edition)
        local_set = local_sets[catalogue["localSetId"]]
        source_first_row = next(
            (source_first[source_id] for source_id in release.get("sourceFirstRecordIds") or [] if source_id in source_first),
            None,
        )
        fallback = next(iter(legacy_by_release.get(release_id, [])), None)
        reference = old or fallback
        work_id = work_id_by_key.get(release.get("work"))
        card_name = (
            (reference or {}).get("cardName")
            or card_name_by_work.get(work_id)
            or (source_first_row or {}).get("cardName")
            or "Snorlax"
        )
        local_name = (source_first_row or {}).get("name")
        local_set_name = next(iter(local_set.get("observedNames") or []), None)
        number, denominator = split_collector_number(release.get("localNumber"))
        event = event_by_edition.get(release["setEditionId"], {})
        return {
            "release": release,
            "identity": identity,
            "catalogue": catalogue,
            "localSet": local_set,
            "sourceFirst": source_first_row,
            "reference": reference,
            "cardName": card_name,
            "localCardName": local_name,
            "localSetName": local_set_name,
            "collectorNumber": number,
            "collectorNumberDenominator": denominator,
            "event": event,
            "workId": work_id,
        }

    def common_item(
        *, anchor: str, kind: str, progress: str, release_id: str,
        physical: dict[str, Any] | None, source_printing_id: str | None,
        unit: dict[str, Any] | None, old: dict[str, Any] | None,
        claim: dict[str, Any] | None,
    ) -> dict[str, Any]:
        context = item_context(release_id, old)
        release = context["release"]
        reference = context["reference"]
        legacy_ids = [old["checklistId"]] if old else []
        source_first_row = context["sourceFirst"]

        if kind == "verified-printing":
            finish = physical.get("finish")
            foil_pattern = physical.get("foilPattern")
            markings = normalized_markings(physical.get("markings"))
            distribution = physical.get("distribution")
            card_size = physical.get("cardSize") or "unknown"
            error_class = physical.get("errorClass")
            verification_status = (claim or {}).get("evidenceStatus") or "confirmed"
        elif kind == "finish-candidate":
            finish = old.get("finish")
            foil_pattern = old.get("foilPattern")
            markings = normalized_markings(old.get("markings"))
            distribution = old.get("distribution")
            card_size = old.get("cardSize") or "unknown"
            error_class = None
            verification_status = old.get("finishVerificationStatus") or "marketplace-claimed"
        else:
            finish = None
            foil_pattern = None
            markings = []
            distribution = None
            card_size = (old or {}).get("cardSize") or "unknown"
            error_class = None
            verification_status = "pending"

        if physical and physical.get("edition"):
            edition_value = physical["edition"]
            edition_status = "assigned"
        elif old and old.get("edition") not in (None, "—"):
            edition_value = old["edition"]
            edition_status = "assigned" if old.get("editionScope") != "unresolved" else "unresolved"
        elif old and old.get("editionScope") == "no-edition-system":
            edition_value = None
            edition_status = "not-applicable"
        else:
            edition_value = None
            edition_status = "unresolved"

        finish_family = FINISH_FAMILY.get(finish) if finish is not None else None
        finish_group = group_id("|".join((
            release_id, edition_value or "unresolved", finish_family or "research",
            canonical_bytes(markings).decode("utf-8"), canonical_bytes(distribution).decode("utf-8"), card_size,
        )))
        release_date = (old or {}).get("releaseDate") or context["event"].get("releaseDate")
        release_precision = (old or {}).get("releaseDatePrecision") or context["event"].get("releaseDatePrecision")
        release_approximate = bool(
            (old or {}).get("releaseApproximate")
            if (old or {}).get("releaseDate") else context["event"].get("releaseApproximate")
        )
        release_sort = "|".join((
            release_date or "9999", str(context["identity"].get("localizationId")),
            natural_key(context["catalogue"].get("localCode")),
            natural_key(context["collectorNumber"] or release.get("viaLegacyNumber")), anchor,
        ))

        source_refs = set((old or {}).get("sourceIds") or [])
        if source_printing_id and source_printing_id in printing_by_id:
            source_refs.update(
                source.get("url") or source.get("sourceType")
                for source in printing_by_id[source_printing_id].get("sources") or []
                if source.get("url") or source.get("sourceType")
            )
        source_refs.update(release.get("sourceRecords") or [])
        if source_first_row and source_first_row.get("sourceUrl"):
            source_refs.add(source_first_row["sourceUrl"])
        source_links = sorted(
            value for value in source_refs if isinstance(value, str) and re.match(r"https?://", value)
        )

        image_path = (old or {}).get("image")
        image_scope = "legacy-product" if image_path else "unknown"
        if image_path and str(image_path).startswith("verification/specimens/"):
            image_scope = "exact-printing"
        if physical and physical["physicalPrintingId"].startswith("PHYSICAL:specimen:"):
            specimen_id = physical["physicalPrintingId"].split("PHYSICAL:specimen:", 1)[1]
            photograph = specimens.get(specimen_id, {}).get("photograph")
            if photograph:
                image_path = "verification/specimens/" + photograph
                image_scope = "exact-printing"
        image_asset, actual_scope = register_asset(
            image_path,
            image_scope,
            f"{context['cardName']} — {context['localSetName'] or context['catalogue'].get('localCode') or 'unknown local set'}; {image_scope}",
        )

        iid = item_id(anchor)
        return {
            "itemId": iid,
            "legacyChecklistIds": legacy_ids,
            "active": True,
            "itemKind": kind,
            "progressClass": progress,
            "workId": context["workId"],
            "workMappingState": release.get("workMappingState") or ("mapped" if context["workId"] else "unmapped"),
            "setEditionId": release["setEditionId"],
            "localSetId": context["catalogue"]["localSetId"],
            "cardReleaseId": release_id,
            "physicalPrintingId": physical.get("physicalPrintingId") if physical else None,
            "sourcePrintingId": source_printing_id,
            "finishUnitId": (unit or {}).get("finishUnitId") or (old or {}).get("finishUnitId"),
            "sourceClaimRefs": sorted({value for value in (
                (claim or {}).get("claimId"), *(release.get("establishingClaimIds") or [])
            ) if value}),
            "localizationId": context["identity"]["localizationId"],
            "cardName": context["cardName"],
            "localCardName": context["localCardName"],
            "localSetCode": context["catalogue"].get("localCode"),
            "localSetName": context["localSetName"],
            "collectorNumber": context["collectorNumber"],
            "collectorNumberDenominator": context["collectorNumberDenominator"],
            "collectorNumberSortKey": natural_key(
                context["collectorNumber"] or release.get("viaLegacyNumber")
            ),
            "edition": edition_value,
            "editionAssignmentStatus": edition_status,
            "finishVerificationStatus": verification_status,
            "finish": finish,
            "finishFamily": finish_family,
            "finishGroupId": finish_group,
            "foilPattern": foil_pattern,
            "markings": markings,
            "distribution": distribution,
            "cardSize": card_size,
            "errorClass": error_class,
            "rarity": normalized_rarity(release_id, reference, rarity_by_release),
            "completenessStatus": (old or {}).get("completenessStatus") or (unit or {}).get("completenessStatus") or "positive-evidence-only",
            "releaseDate": release_date,
            "releaseDatePrecision": release_precision,
            "releaseApproximate": release_approximate,
            "releaseSortKey": release_sort,
            "imageAssetId": image_asset,
            "imageScope": actual_scope,
            "sourceLinks": source_links,
            "evidenceLinks": source_links,
            "correctionLink": CORRECTION_URL,
        }

    items: list[dict[str, Any]] = []
    for physical in physicals.values():
        source_printing_id = physical.get("sourcePrintingId")
        old = legacy_by_printing.get(source_printing_id)
        unit = unit_by_printing.get(source_printing_id)
        claim = claims[physical["establishingClaimId"]]
        items.append(common_item(
            anchor="claim:" + claim["claimId"], kind="verified-printing", progress="current-known",
            release_id=physical["cardReleaseId"], physical=physical,
            source_printing_id=source_printing_id, unit=unit, old=old, claim=claim,
        ))

    for old in legacy_items:
        source_printing_id = old.get("printingId")
        if not source_printing_id or source_printing_id in physical_by_source:
            continue
        claim = candidate_by_source.get(source_printing_id)
        if not claim:
            raise ContractError(f"predecessor finish candidate has no graph claim: {source_printing_id}")
        release_id = legacy_release[old["checklistId"]]
        if claim.get("proposedCardReleaseId") != release_id:
            raise ContractError(f"finish candidate graph/legacy release mismatch: {source_printing_id}")
        items.append(common_item(
            anchor="claim:" + claim["claimId"], kind="finish-candidate", progress="research",
            release_id=release_id, physical=None, source_printing_id=source_printing_id,
            unit=unit_by_printing[source_printing_id], old=old, claim=claim,
        ))

    for old in legacy_items:
        if old.get("printingId"):
            continue
        release_id = legacy_release[old["checklistId"]]
        items.append(common_item(
            anchor="research:legacy-checklist:" + old["checklistId"],
            kind="research-placeholder", progress="research", release_id=release_id,
            physical=None, source_printing_id=None,
            unit=unit_by_id.get(old.get("finishUnitId")), old=old, claim=None,
        ))

    for row in items:
        work_id = row["workId"]
        if not work_id:
            continue
        previous_name = card_name_by_work.setdefault(work_id, row["cardName"])
        if previous_name != row["cardName"]:
            raise ContractError(f"mapped work has conflicting card names: {work_id}")

    represented_releases = {row["cardReleaseId"] for row in items}
    for release_id in sorted(set(releases) - represented_releases):
        items.append(common_item(
            anchor="research:card-release:" + release_id,
            kind="research-placeholder", progress="research", release_id=release_id,
            physical=None, source_printing_id=None, unit=None, old=None, claim=None,
        ))

    ids = [row["itemId"] for row in items]
    if len(ids) != len(set(ids)):
        raise ContractError("collector item ids are not unique")
    items.sort(key=lambda row: (row["releaseSortKey"], row["itemId"]))

    item_name_by_work: dict[str, str] = {}
    for row in items:
        if row["workId"]:
            item_name_by_work.setdefault(row["workId"], row["cardName"])
    work_rows = [
        {"workId": row["workId"], "cardKey": row["cardKey"], "displayName": item_name_by_work.get(row["workId"])}
        for row in sorted(works, key=lambda value: value["workId"])
    ]

    localization_rows = [
        {key: row[key] for key in (
            "localizationId", "locality", "languageId", "language", "languageTag", "script",
            "displayName", "displayOrder",
        )}
        for row in sorted(localizations, key=lambda value: (value["displayOrder"], value["localizationId"]))
    ]

    counts = defaultdict(int)
    for row in items:
        counts[row["itemKind"]] += 1
        counts[row["progressClass"]] += 1
    graph_hash = sha256_bytes(canonical_bytes(graph))
    document: dict[str, Any] = {
        "meta": {
            "schema": SCHEMA_NAME,
            "schemaVersion": SCHEMA_VERSION,
            "datasetId": DATASET_ID,
            "sourceRepository": SOURCE_REPOSITORY,
            "dataAsOf": graph["meta"]["generated"],
            "catalogueFingerprint": "",
            "previousFingerprint": None,
            "assetBaseUrl": ASSET_BASE_URL,
            "scope": {
                "policy": "positive-evidence/current-known",
                "allLocalitiesComplete": False,
                "absenceIsNotEvidence": True,
            },
            "licenceRefs": ["LICENSE.md", "THIRD_PARTY_NOTICES.md"],
        },
        "localizations": localization_rows,
        "localSets": local_set_rows,
        "setEditions": set_edition_rows,
        "works": work_rows,
        "items": items,
        "assets": sorted(assets.values(), key=lambda row: row["assetId"]),
        "qualitySummary": {
            "authoritativeGraphFingerprint": graph_hash,
            "authoritativeGraphSchemaVersion": graph["meta"]["schemaVersion"],
            "discoveryTerminalState": completeness["meta"]["terminalState"],
            "setDiscoveryRun": completeness["meta"]["setDiscoveryRun"],
            "cardDiscoveryRun": completeness["meta"]["cardDiscoveryRun"],
            "counts": {
                "localizations": len(localization_rows), "localSets": len(local_set_rows),
                "setEditions": len(set_edition_rows), "works": len(work_rows),
                "items": len(items), "verifiedPrintings": counts["verified-printing"],
                "finishCandidates": counts["finish-candidate"],
                "researchPlaceholders": counts["research-placeholder"],
                "currentKnown": counts["current-known"], "research": counts["research"],
                "assets": len(assets),
            },
            "predecessor": {
                "schema": predecessor["meta"]["schema"],
                "schemaVersion": predecessor["meta"]["schemaVersion"],
                "rows": len(legacy_items),
            },
            "graphAccounting": {
                "cardReleases": len(releases), "physicalPrintings": len(physicals),
            },
            "candidateProgressPolicy": {
                "progressClass": "research",
                "status": "fail-safe-default-pending-owner-decision",
                "basis": "positive-printing-evidence-or-explicit-owner-decision-required-for-current-known",
                "decisionRef": "https://github.com/m4s-ai/snoredex-data/issues/254",
            },
        },
    }
    document["meta"]["catalogueFingerprint"] = semantic_fingerprint(document)

    item_by_legacy = {
        legacy_id: row["itemId"] for row in items for legacy_id in row["legacyChecklistIds"]
    }
    if set(item_by_legacy) != {row["checklistId"] for row in legacy_items}:
        raise ContractError("initial catalogue does not account for every predecessor checklist id")
    item_by_physical = {
        row["physicalPrintingId"]: row["itemId"] for row in items if row["physicalPrintingId"]
    }
    if set(item_by_physical) != set(physicals):
        raise ContractError("initial catalogue does not account for every graph physical printing")
    cumulative_item_by_legacy = {
        old_id: item_by_legacy[new_id]
        for old_id, new_id in CUMULATIVE_CHECKLIST_REKEYS.items()
    }

    items_by_release: defaultdict[str, list[str]] = defaultdict(list)
    for row in items:
        items_by_release[row["cardReleaseId"]].append(row["itemId"])
    item_ids = {row["itemId"] for row in items}
    graph_only_transitions = [
        state_transition(
            item_id("research:card-release:" + release_id),
            items_by_release[release_id],
        )
        for release_id in sorted(set(releases) - set(legacy_by_release))
        if item_id("research:card-release:" + release_id) not in item_ids
    ]
    migrations = {
        "meta": {
            "schema": "snoredex-collector-migrations",
            "schemaVersion": "1.0.0",
            "datasetId": DATASET_ID,
            "fromSchema": predecessor["meta"]["schema"],
            "fromSchemaVersion": predecessor["meta"]["schemaVersion"],
            "fromFingerprint": sha256_bytes(canonical_bytes(predecessor)),
            "toSchema": SCHEMA_NAME,
            "toSchemaVersion": SCHEMA_VERSION,
            "toFingerprint": document["meta"]["catalogueFingerprint"],
            "cumulative": True,
        },
        "transitions": [
            {
                "fromItemId": legacy_id,
                "toItemIds": [target_id],
                "changeKind": "rekey-1:1",
                "automaticStateAction": "preserve",
            }
            for legacy_id, target_id in sorted(
                (item_by_legacy | cumulative_item_by_legacy).items()
            )
        ] + graph_only_transitions,
        "graphRekeys": [
            {
                "sourceKind": row["sourceKind"], "sourceId": row["sourceId"],
                "targetCardReleaseIds": row.get("targetRefs") or [],
                "reconciliation": (
                    "requires-user-resolution" if len(row.get("targetRefs") or []) != 1
                    else "one-to-one-reference"
                ),
                "automaticStateAction": (
                    "none" if len(row.get("targetRefs") or []) != 1 else "preserve-by-reference"
                ),
            }
            for row in graph["migrationDispositions"] if row.get("sourceKind") == "legacy-issue-rekey"
        ],
        "accounting": {
            "legacyChecklistRows": [
                {"legacyChecklistId": row["checklistId"], "disposition": "projected", "targetItemIds": [item_by_legacy[row["checklistId"]]]}
                for row in sorted(legacy_items, key=lambda value: value["checklistId"])
            ],
            "cardReleases": [
                {
                    "cardReleaseId": release_id,
                    "disposition": "projected" if items_by_release.get(release_id) else "no-collector-item",
                    "targetItemIds": sorted(items_by_release.get(release_id, [])),
                    "reason": None if items_by_release.get(release_id) else "No verified printing, selected predecessor finish candidate, or predecessor research slot exists for this release.",
                }
                for release_id in sorted(releases)
            ],
            "physicalPrintings": [
                {"physicalPrintingId": printing_id, "disposition": "projected", "targetItemId": item_by_physical[printing_id]}
                for printing_id in sorted(physicals)
            ],
            "summary": {
                "legacyChecklistRows": len(legacy_items), "cardReleases": len(releases),
                "physicalPrintings": len(physicals),
                "cardReleasesWithoutCollectorItem": sum(not items_by_release.get(release_id) for release_id in releases),
            },
        },
    }
    return document, migrations


def fixture_document() -> dict[str, Any]:
    def fixture_item(iid: str, kind: str, progress: str, loc: str, set_id: str, edition_id: str,
                     release_id: str, physical_id: str | None, finish: str | None) -> dict[str, Any]:
        return {
            "itemId": iid, "legacyChecklistIds": [], "active": True, "itemKind": kind,
            "progressClass": progress, "workId": "fixture-work", "workMappingState": "mapped",
            "setEditionId": edition_id, "localSetId": set_id, "cardReleaseId": release_id,
            "physicalPrintingId": physical_id, "sourcePrintingId": None, "finishUnitId": None,
            "sourceClaimRefs": ["fixture-claim"], "localizationId": loc, "cardName": "Snorlax",
            "localCardName": None, "localSetCode": "FX", "localSetName": "Fixture Set",
            "collectorNumber": "1", "collectorNumberDenominator": "10", "collectorNumberSortKey": "000000000001",
            "edition": None, "editionAssignmentStatus": "not-applicable",
            "finishVerificationStatus": "confirmed" if physical_id else ("marketplace-claimed" if kind == "finish-candidate" else "pending"),
            "finish": finish, "finishFamily": FINISH_FAMILY.get(finish) if finish else None,
            "finishGroupId": "fixture-group-" + kind, "foilPattern": None, "markings": [],
            "distribution": None, "cardSize": "standard", "errorClass": None,
            "rarity": {"display": None, "normalizedId": None, "evidenceStatus": "unknown", "claimRefs": []},
            "completenessStatus": "positive-evidence-only", "releaseDate": "2026-01-01",
            "releaseDatePrecision": "day", "releaseApproximate": False,
            "releaseSortKey": "2026-01-01|fixture", "imageAssetId": None, "imageScope": "unknown",
            "sourceLinks": [], "evidenceLinks": [], "correctionLink": CORRECTION_URL,
        }

    localizations = [
        {"localizationId": "fixture-loc-west-es", "locality": "WEST", "languageId": "LANG:Spanish", "language": "Spanish", "languageTag": "es-ES", "script": "Latn", "displayName": "Spanish (Europe)", "displayOrder": 10},
        {"localizationId": "fixture-loc-latam-es", "locality": "LATAM", "languageId": "LANG:Spanish", "language": "Spanish", "languageTag": "es-419", "script": "Latn", "displayName": "Spanish (Latin America)", "displayOrder": 20},
        {"localizationId": "fixture-loc-west-en", "locality": "WEST", "languageId": "LANG:English", "language": "English", "languageTag": "en", "script": "Latn", "displayName": "English", "displayOrder": 30},
        {"localizationId": "fixture-loc-west-pt", "locality": "WEST", "languageId": "LANG:Portuguese", "language": "Portuguese", "languageTag": "pt", "script": "Latn", "displayName": "Portuguese", "displayOrder": 40},
    ]
    sets = [
        {"localSetId": f"fixture-set-{n}", "locality": locality, "localSetCode": "FX", "localSetName": "Fixture Set", "productKind": "fixture", "identityState": "identified", "sourceRefs": ["fixture-source"], "sortKey": f"{n}"}
        for n, locality in ((1, "WEST"), (2, "LATAM"), (3, "WEST"))
    ]
    editions = [
        {"setEditionId": f"fixture-edition-{n}", "localSetId": f"fixture-set-{n}", "localizationId": loc, "localSetCode": "FX", "localSetName": "Fixture Set", "identityState": "identified", "releaseDate": "2026-01-01", "releaseDatePrecision": "day", "releaseApproximate": False, "releaseEventId": f"fixture-event-{n}", "sortKey": f"{n}"}
        for n, loc in ((1, "fixture-loc-west-es"), (2, "fixture-loc-latam-es"), (3, "fixture-loc-west-en"))
    ]
    items = [
        fixture_item("item-00000000-0000-5000-8000-000000000001", "verified-printing", "current-known", "fixture-loc-west-es", "fixture-set-1", "fixture-edition-1", "fixture-release-1", "fixture-physical-1", "holo"),
        fixture_item("item-00000000-0000-5000-8000-000000000002", "finish-candidate", "research", "fixture-loc-latam-es", "fixture-set-2", "fixture-edition-2", "fixture-release-2", None, "reverse-holo"),
        fixture_item("item-00000000-0000-5000-8000-000000000003", "research-placeholder", "research", "fixture-loc-west-en", "fixture-set-3", "fixture-edition-3", "fixture-release-3", None, None),
    ]
    catalogue = {
        "meta": {
            "schema": SCHEMA_NAME, "schemaVersion": SCHEMA_VERSION, "datasetId": "fixture",
            "sourceRepository": SOURCE_REPOSITORY, "dataAsOf": "2026-08-24",
            "catalogueFingerprint": "", "previousFingerprint": None,
            "assetBaseUrl": ASSET_BASE_URL,
            "scope": {"policy": "positive-evidence/current-known", "allLocalitiesComplete": False, "absenceIsNotEvidence": True},
            "licenceRefs": ["LICENSE.md", "THIRD_PARTY_NOTICES.md"],
        },
        "localizations": localizations, "localSets": sets, "setEditions": editions,
        "works": [{"workId": "fixture-work", "cardKey": "fixture-work", "displayName": "Snorlax"}],
        "items": items, "assets": [], "qualitySummary": {"fixture": True},
    }
    catalogue["meta"]["catalogueFingerprint"] = semantic_fingerprint(catalogue)
    return {
        "meta": {"schema": "snoredex-collector-catalogue-fixture", "schemaVersion": "1.0.0"},
        "catalogue": catalogue,
        "reconciliationCases": [{
            "caseId": "U0414-1-to-many",
            "sourceGraphRef": "legacy-issue-rekey:U0414",
            "fromItemId": "fixture-u0414-source",
            "toItemIds": ["fixture-u0414-target-a", "fixture-u0414-target-b"],
            "expectedAutomaticStateAction": "none",
            "expectedResolution": "requires-user-resolution",
        }],
    }


def validate_catalogue(
    document: dict[str, Any], graph: dict[str, Any] | None = None, *, check_asset_bytes: bool = True
) -> list[str]:
    errors: list[str] = []
    if document.get("meta", {}).get("catalogueFingerprint") != semantic_fingerprint(document):
        errors.append("catalogue semantic fingerprint differs")

    localizations = {row.get("localizationId"): row for row in document.get("localizations", [])}
    local_sets = {row.get("localSetId"): row for row in document.get("localSets", [])}
    editions = {row.get("setEditionId"): row for row in document.get("setEditions", [])}
    works = {row.get("workId"): row for row in document.get("works", [])}
    items = {row.get("itemId"): row for row in document.get("items", [])}
    assets = {row.get("assetId"): row for row in document.get("assets", [])}
    for name, rows, mapping in (
        ("localization", document.get("localizations", []), localizations),
        ("local set", document.get("localSets", []), local_sets),
        ("set edition", document.get("setEditions", []), editions),
        ("work", document.get("works", []), works),
        ("item", document.get("items", []), items),
        ("asset", document.get("assets", []), assets),
    ):
        if len(rows) != len(mapping) or None in mapping:
            errors.append(f"{name} ids are missing or duplicate")

    tag_rows = {(row.get("locality"), row.get("languageTag")): row for row in localizations.values()}
    if ("WEST", "es-ES") not in tag_rows or ("LATAM", "es-419") not in tag_rows:
        errors.append("WEST/es-ES and LATAM/es-419 are not distinct localizations")
    if not any(row.get("languageTag") == "pt" for row in localizations.values()):
        errors.append("Portuguese producer tag pt is missing")

    graph_releases: dict[str, dict[str, Any]] = {}
    graph_physicals: dict[str, dict[str, Any]] = {}
    graph_claims: dict[str, dict[str, Any]] = {}
    if graph is not None:
        graph_localization_ids = {
            row["localizationId"] for row in entity_payloads(graph, "localization")
        }
        graph_local_set_ids = {
            row["localSetId"] for row in entity_payloads(graph, "local-set")
        }
        graph_edition_ids = {
            row["setEditionId"] for row in entity_payloads(graph, "set-edition")
        }
        graph_work_ids = {row["workId"] for row in entity_payloads(graph, "work")}
        graph_releases = {
            row["cardReleaseId"]: row for row in entity_payloads(graph, "card-release")
        }
        graph_physicals = {
            row["physicalPrintingId"]: row for row in entity_payloads(graph, "physical-printing")
        }
        graph_claims = {row["claimId"]: row for row in entity_payloads(graph, "candidate-claim")}
        if set(localizations) != graph_localization_ids:
            errors.append("catalogue localization accounting differs from the graph")
        if set(local_sets) != graph_local_set_ids:
            errors.append("catalogue local-set accounting differs from the graph")
        if set(editions) != graph_edition_ids:
            errors.append("catalogue set-edition accounting differs from the graph")
        if set(works) != graph_work_ids:
            errors.append("catalogue work accounting differs from the graph")

    physical_item_refs: set[str] = set()
    legacy_ids: set[str] = set()
    for iid, item in items.items():
        edition = editions.get(item.get("setEditionId"))
        if not edition:
            errors.append(f"item set edition does not resolve: {iid}")
            continue
        if item.get("localSetId") not in local_sets \
                or edition.get("localSetId") != item.get("localSetId"):
            errors.append(f"item local set does not resolve through its edition: {iid}")
        if item.get("localizationId") not in localizations \
                or edition.get("localizationId") != item.get("localizationId"):
            errors.append(f"item localization does not resolve through its edition: {iid}")
        if item.get("workId") is not None and item.get("workId") not in works:
            errors.append(f"item work does not resolve: {iid}")
        if item.get("imageAssetId") is not None and item.get("imageAssetId") not in assets:
            errors.append(f"item asset does not resolve: {iid}")
        try:
            normalized_markings(item.get("markings"))
        except ContractError:
            errors.append(f"item markings are not role-structured: {iid}")

        kind = item.get("itemKind")
        physical_id = item.get("physicalPrintingId")
        if kind == "verified-printing":
            if not physical_id:
                errors.append(f"verified item has no physical printing: {iid}")
            elif physical_id in physical_item_refs:
                errors.append(f"physical printing is projected more than once: {physical_id}")
            physical_item_refs.add(physical_id)
            if item.get("progressClass") != "current-known":
                errors.append(f"verified item is not current-known: {iid}")
            if graph is not None:
                physical = graph_physicals.get(physical_id)
                if not physical or physical.get("cardReleaseId") != item.get("cardReleaseId"):
                    errors.append(f"verified item physical/release relation is invalid: {iid}")
        elif kind == "finish-candidate":
            if physical_id is not None or item.get("progressClass") != "research":
                errors.append(f"finish candidate invents a printing or progress: {iid}")
            if graph is not None:
                candidate_claims = [
                    graph_claims.get(ref) for ref in item.get("sourceClaimRefs") or []
                    if graph_claims.get(ref, {}).get("sourceKind") == "finish-printing-record"
                    and graph_claims.get(ref, {}).get("disposition") == "candidate-needs-evidence"
                ]
                if len(candidate_claims) != 1 \
                        or candidate_claims[0].get("proposedCardReleaseId") != item.get("cardReleaseId"):
                    errors.append(f"finish candidate has no exact graph claim/release: {iid}")
        elif kind == "research-placeholder":
            if physical_id is not None or item.get("progressClass") != "research" \
                    or item.get("finish") is not None:
                errors.append(f"research placeholder invents a printing or finish: {iid}")
        else:
            errors.append(f"item kind is invalid: {iid}")

        if graph is not None:
            release = graph_releases.get(item.get("cardReleaseId"))
            if not release or release.get("setEditionId") != item.get("setEditionId"):
                errors.append(f"item card release does not resolve through its edition: {iid}")
            unresolved_claims = set(item.get("sourceClaimRefs") or []) - set(graph_claims)
            if unresolved_claims:
                errors.append(f"item source claims do not resolve: {iid}")
        for legacy_id in item.get("legacyChecklistIds") or []:
            if legacy_id in legacy_ids:
                errors.append(f"legacy checklist id is projected more than once: {legacy_id}")
            legacy_ids.add(legacy_id)

    if graph is not None and physical_item_refs != set(graph_physicals):
        errors.append("catalogue physical-printing accounting differs from the graph")
    if graph is not None and {
        item.get("cardReleaseId") for item in items.values()
    } != set(graph_releases):
        errors.append("catalogue card-release accounting differs from the graph")

    for aid, asset in assets.items():
        path = ROOT / str(asset.get("path") or "")
        if check_asset_bytes and (
            not path.is_file() or asset.get("sha256") != sha256_bytes(path.read_bytes())
            or asset.get("mimeType") != image_mime(path)
        ):
            errors.append(f"asset bytes/hash/MIME differ: {aid}")
    return errors


def validate_migrations(
    migrations: dict[str, Any], catalogue: dict[str, Any], graph: dict[str, Any], predecessor: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if migrations.get("meta", {}).get("toFingerprint") != catalogue["meta"]["catalogueFingerprint"]:
        errors.append("migration target fingerprint differs")
    legacy_ids = {row["checklistId"] for row in predecessor["items"]}
    transitions = migrations.get("transitions", [])
    transition_by_source = {row.get("fromItemId"): row for row in transitions}
    if len(transition_by_source) != len(transitions) or None in transition_by_source:
        errors.append("migration transition sources are missing or duplicate")
    legacy_transitions = {
        source: row for source, row in transition_by_source.items() if source in legacy_ids
    }
    if set(legacy_transitions) != legacy_ids:
        errors.append("migration transitions do not account for every predecessor id exactly once")
    item_ids = {row["itemId"] for row in catalogue["items"]}
    if any(len(row.get("toItemIds") or []) != 1 or row["toItemIds"][0] not in item_ids
           for row in legacy_transitions.values()):
        errors.append("initial 1:1 migration has an unresolved target")
    item_by_legacy = {
        legacy_id: row["itemId"]
        for row in catalogue["items"]
        for legacy_id in row.get("legacyChecklistIds") or []
    }
    if any(
        transition_by_source.get(old_id, {}).get("toItemIds") != [item_by_legacy.get(new_id)]
        or transition_by_source.get(old_id, {}).get("changeKind") != "rekey-1:1"
        or transition_by_source.get(old_id, {}).get("automaticStateAction") != "preserve"
        for old_id, new_id in CUMULATIVE_CHECKLIST_REKEYS.items()
    ):
        errors.append("cumulative checklist rekeys differ from their replacement items")

    accounting = migrations.get("accounting", {})
    graph_releases = {row["cardReleaseId"] for row in entity_payloads(graph, "card-release")}
    graph_physicals = {row["physicalPrintingId"] for row in entity_payloads(graph, "physical-printing")}
    legacy_accounting = accounting.get("legacyChecklistRows", [])
    release_accounting = accounting.get("cardReleases", [])
    physical_accounting = accounting.get("physicalPrintings", [])
    item_release_by_id = {row["itemId"]: row["cardReleaseId"] for row in catalogue["items"]}
    releases_with_legacy_rows = {
        row["cardReleaseId"] for row in catalogue["items"] if row["legacyChecklistIds"]
    }
    graph_alias_by_release = {
        release_id: item_id("research:card-release:" + release_id)
        for release_id in graph_releases - releases_with_legacy_rows
        if item_id("research:card-release:" + release_id) not in item_ids
    }
    expected_transition_sources = (
        legacy_ids | set(CUMULATIVE_CHECKLIST_REKEYS) | set(graph_alias_by_release.values())
    )
    if set(transition_by_source) != expected_transition_sources:
        errors.append("cumulative graph-only item transitions differ from the catalogue")
    items_by_release: defaultdict[str, list[str]] = defaultdict(list)
    for iid, release_id in item_release_by_id.items():
        items_by_release[release_id].append(iid)
    if any(
        transition_by_source.get(alias) != state_transition(alias, items_by_release[release_id])
        for release_id, alias in graph_alias_by_release.items()
    ):
        errors.append("graph-only item transition does not preserve or reconcile collection state")
    if {row.get("legacyChecklistId") for row in legacy_accounting} != legacy_ids \
            or len(legacy_accounting) != len(legacy_ids):
        errors.append("legacy checklist accounting differs")
    if {row.get("cardReleaseId") for row in release_accounting} != graph_releases \
            or len(release_accounting) != len(graph_releases):
        errors.append("card-release accounting differs")
    if any(
        row.get("disposition") != "projected"
        or not row.get("targetItemIds")
        or row.get("reason") is not None
        or any(item_release_by_id.get(iid) != row.get("cardReleaseId")
               for iid in row.get("targetItemIds") or [])
        for row in release_accounting
    ):
        errors.append("card-release accounting does not project every release to its items")
    if {row.get("physicalPrintingId") for row in physical_accounting} != graph_physicals \
            or len(physical_accounting) != len(graph_physicals):
        errors.append("physical-printing accounting differs")
    u0414 = next((row for row in migrations.get("graphRekeys", []) if row.get("sourceId") == "U0414"), None)
    if not u0414 or len(u0414.get("targetCardReleaseIds") or []) != 2 \
            or u0414.get("reconciliation") != "requires-user-resolution" \
            or u0414.get("automaticStateAction") != "none":
        errors.append("U0414 does not preserve the 1:N user-resolution boundary")
    return errors


def build_all() -> dict[Path, Any]:
    catalogue, migrations = build_catalogue()
    graph = read_json(GRAPH_PATH)
    errors = validate_catalogue(catalogue, graph)
    errors.extend(validate_migrations(migrations, catalogue, graph, read_json(CHECKLIST_PATH)))
    if errors:
        raise ContractError("; ".join(errors[:20]))
    return {
        CATALOGUE_PATH: catalogue,
        SCHEMA_PATH: schema_document(),
        MIGRATIONS_PATH: migrations,
        FIXTURE_PATH: fixture_document(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed artifacts")
    args = parser.parse_args()
    try:
        outputs = build_all()
        if args.check:
            stale = [str(path.relative_to(ROOT)) for path, document in outputs.items()
                     if not path.is_file() or read_json(path) != document]
            if stale:
                print("collector contract artifacts are stale: " + ", ".join(stale), file=sys.stderr)
                return 1
            catalogue = outputs[CATALOGUE_PATH]
            print(
                f"collector catalogue current: {len(catalogue['items'])} items, "
                f"{catalogue['meta']['catalogueFingerprint']}"
            )
            return 0
        for path, document in outputs.items():
            write_json(path, document)
        catalogue = outputs[CATALOGUE_PATH]
        counts = catalogue["qualitySummary"]["counts"]
        print(
            f"collector catalogue: {counts['items']} items "
            f"({counts['verifiedPrintings']} verified + {counts['finishCandidates']} candidates + "
            f"{counts['researchPlaceholders']} research); {counts['assets']} assets"
        )
        print(catalogue["meta"]["catalogueFingerprint"])
        return 0
    except (OSError, KeyError, TypeError, ValueError) as error:
        print(f"collector catalogue failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

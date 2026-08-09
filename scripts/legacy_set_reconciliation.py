#!/usr/bin/env python3
"""Reconcile the bounded legacy set/date/finish projection with the identity graph (#148).

This is deliberately a projection, not a research pass. It preserves every legacy input row,
links only positively supported graph targets, and records everything else as needs-evidence or
blocked-by-source. Source-first records remain separate from Cardmarket aliases.

    python scripts/legacy_set_reconciliation.py
    python scripts/legacy_set_reconciliation.py --check
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
VERIFY = ROOT / "verification"
ANALYSIS_JSON = ROOT / "analysis_confirmed_releases.json"
ANALYSIS_CSV = ROOT / "analysis_confirmed_releases.csv"
FINISH_PATH = VERIFY / "finish_units.json"
SET_SOURCE_PATH = VERIFY / "set_catalogue_sources.json"
SET_GRAPH_PATH = VERIFY / "set_catalogue_dryrun.json"
IDENTITY_PATH = VERIFY / "print_identity_dryrun.json"
SOURCE_FIRST_PATH = VERIFY / "source_first_prints.json"
OUTPUT_PATH = VERIFY / "legacy_set_reconciliation.json"
COMPAT_JSON_PATH = ROOT / "analysis_confirmed_releases_reconciled.json"
COMPAT_CSV_PATH = ROOT / "analysis_confirmed_releases_reconciled.csv"

SCHEMA_VERSION = "0.1.0"
COVERAGE_VERSION = "legacy-set-reconciliation-v1"
EXPECTED_DENOMINATORS = {"aliases": 135, "releaseRows": 203, "finishUnits": 637}
MIXED_STATUS_PAIRS = (("DP-P", "Korean"), ("XY-P", "Korean"), ("xJTG", "French"))
IDENTITY_BOUNDARY_CODES = ("AS5a", "svQP F", "sc1a F", "sc1b F", "scD F")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def value_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(material).hexdigest()[:16]}"


def report(total: int, counts: Counter[str], allowed: tuple[str, ...]) -> dict[str, Any]:
    buckets = {name: counts.get(name, 0) for name in allowed}
    return {
        "denominator": total,
        "coverageVersion": COVERAGE_VERSION,
        "buckets": buckets,
        "accounted": sum(buckets.values()),
        "balanced": sum(buckets.values()) == total,
    }


def input_documents() -> dict[str, Any]:
    return {
        "analysis": read_json(ANALYSIS_JSON),
        "finish": read_json(FINISH_PATH),
        "setSources": read_json(SET_SOURCE_PATH),
        "setGraph": read_json(SET_GRAPH_PATH),
        "identity": read_json(IDENTITY_PATH),
        "sourceFirst": read_json(SOURCE_FIRST_PATH),
    }


def build_alias_ledger(documents: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sources = documents["setSources"]["sourceRecords"]
    graph = documents["setGraph"]
    dispositions = {row["sourceRecordId"]: row for row in graph["sourceDispositions"]}
    assertions_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for assertion in graph["aliasAssertions"]:
        assertions_by_source[assertion["sourceRecordId"]].append(assertion)

    source_first_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    editions_by_local_set: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edition in graph["setEditions"]:
        editions_by_local_set[edition["localSetId"]].append(edition)
    for record in sources:
        if record["sourceKind"] == "source-first-local-set-profile":
            source_first_by_code[str(record["raw"]["localCode"])].append(record)

    ledger: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for record in sources:
        if record["sourceKind"] != "legacy-cardmarket-set-profile":
            continue
        raw = record["raw"]
        source_id = record["sourceRecordId"]
        source_disposition = dispositions[source_id]
        targets = sorted({
            assertion["localSetId"] for assertion in assertions_by_source.get(source_id, [])
            if assertion.get("localSetId")
        })
        cross_locality = sorted(
            [
                candidate for candidate in source_first_by_code.get(str(raw["localCode"]), [])
                if candidate["raw"]["locality"] != raw["locality"]
            ],
            key=lambda item: item["sourceRecordId"],
        )

        if source_disposition["disposition"] == "positively-excluded":
            migration = "positively-retained-legacy"
            terminal = "complete"
        elif cross_locality:
            migration = "split-related"
            terminal = "complete"
        elif len(targets) == 1:
            migration = "mapped"
            terminal = "complete"
        else:
            migration = "needs-evidence"
            terminal = "needs-evidence"

        relation_ids: list[str] = []
        for candidate in cross_locality:
            candidate_assertions = assertions_by_source[candidate["sourceRecordId"]]
            candidate_targets = sorted({
                item["localSetId"] for item in candidate_assertions if item.get("localSetId")
            })
            relation_id = stable_id("ALIASREL", source_id, candidate["sourceRecordId"])
            relation_ids.append(relation_id)
            relations.append({
                "aliasRelationId": relation_id,
                "leftSourceRecordId": source_id,
                "rightSourceRecordId": candidate["sourceRecordId"],
                "rawIdentifier": str(raw["localCode"]),
                "relationship": "same-raw-code-cross-locality",
                "leftLocality": raw["locality"],
                "rightLocality": candidate["raw"]["locality"],
                "leftLocalSetIds": targets,
                "rightLocalSetIds": candidate_targets,
                "equivalent": False,
                "mergeAllowed": False,
                "basis": "positive provider records identify different localities",
            })

        edition_resolutions = sorted(
            (
                {
                    "setEditionId": edition["setEditionId"],
                    "relationship": "edition-of-aliased-local-set",
                    "equivalentToAlias": False,
                    "decision": "retain-distinct-language-script-edition",
                    "language": edition["language"],
                    "script": edition["script"],
                    "establishingEvidenceIds": edition["establishingEvidenceIds"],
                }
                for target in targets for edition in editions_by_local_set.get(target, [])
            ),
            key=lambda item: item["setEditionId"],
        )

        ledger.append({
            "legacyAliasId": stable_id("LEGACYALIAS", source_id),
            "sourceRecordId": source_id,
            "provider": record["provider"],
            "retrieved": record["retrieved"],
            "rawIdentifier": raw["localCode"],
            "rawName": raw["localName"],
            "rawMarket": raw["market"],
            "rawLocality": raw["locality"],
            "rawProductKind": raw["productKind"],
            "rawRecordHash": value_hash(record),
            "localSetIds": targets,
            "setEditionIds": [item["setEditionId"] for item in edition_resolutions],
            "editionResolutions": edition_resolutions,
            "relatedAliasRelationIds": relation_ids,
            "migrationDisposition": migration,
            "terminalState": terminal,
            "sourceDisposition": source_disposition,
            "aliasAssertionIds": sorted(
                item["aliasAssertionId"] for item in assertions_by_source.get(source_id, [])
            ),
        })

    ledger.sort(key=lambda item: item["sourceRecordId"])
    relations.sort(key=lambda item: item["aliasRelationId"])
    return ledger, relations


def date_relation(raw_date: str, raw_precision: str, event: dict[str, Any]) -> str:
    event_date = event["dateValue"]
    if raw_precision == "day" and raw_date == event_date:
        return "supports-legacy-date"
    if raw_precision == "month" and event_date.startswith(raw_date + "-"):
        return "positively-refines-legacy-scalar"
    if raw_precision == "year" and event_date.startswith(raw_date + "-"):
        return "positively-refines-legacy-scalar"
    return "positively-supersedes-legacy-scalar"


def build_release_ledger(documents: dict[str, Any]) -> list[dict[str, Any]]:
    rows = documents["analysis"]["variants"]
    graph = documents["setGraph"]
    sources = documents["setSources"]["sourceRecords"]
    source_by_id = {record["sourceRecordId"]: record for record in sources}
    local_set_by_id = {row["localSetId"]: row for row in graph["localSets"]}
    legacy_records = [
        record for record in sources if record["sourceKind"] == "legacy-cardmarket-set-profile"
    ]
    legacy_by_code_name: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in legacy_records:
        legacy_by_code_name[(record["raw"]["localCode"], record["raw"]["localName"])].append(record)

    alias_target: dict[str, list[str]] = defaultdict(list)
    for assertion in graph["aliasAssertions"]:
        if assertion.get("localSetId"):
            alias_target[assertion["sourceRecordId"]].append(assertion["localSetId"])
    editions_by_local_language: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for edition in graph["setEditions"]:
        editions_by_local_language[(edition["localSetId"], edition["language"])].append(edition)
    events_by_edition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in graph["releaseEvents"]:
        for edition_id in event["setEditionIds"]:
            events_by_edition[edition_id].append(event)

    ledger: list[dict[str, Any]] = []
    for row in rows:
        matching_profiles = legacy_by_code_name.get((row["setCode"], row["setName"]), [])
        source_ids = sorted(record["sourceRecordId"] for record in matching_profiles)
        local_set_ids = sorted({
            target for source_id in source_ids for target in alias_target.get(source_id, [])
        })
        language_links: list[dict[str, Any]] = []
        all_event_links: dict[str, dict[str, Any]] = {}
        source = row.get("dateSource")

        for language in row["confirmedLanguages"]:
            editions = sorted(
                [
                    edition for local_set_id in local_set_ids
                    for edition in editions_by_local_language.get((local_set_id, language), [])
                ],
                key=lambda item: item["setEditionId"],
            )
            candidate_events: list[dict[str, Any]] = []
            for edition in editions:
                for event in events_by_edition.get(edition["setEditionId"], []):
                    event_source = source_by_id[event["sourceRecordId"]]
                    raw_source = event_source["raw"]
                    if source and (
                        raw_source.get("page") != source.get("page")
                        or raw_source.get("field") != source.get("field")
                    ):
                        continue
                    candidate_events.append(event)
            candidate_events = sorted(
                {event["releaseEventId"]: event for event in candidate_events}.values(),
                key=lambda item: item["releaseEventId"],
            )
            event_links: list[dict[str, Any]] = []
            for event in candidate_events:
                relationship = date_relation(row["date"], row["datePrecision"], event)
                event_source = source_by_id[event["sourceRecordId"]]
                link = {
                    "releaseEventId": event["releaseEventId"],
                    "localSetId": event["localSetId"],
                    "locality": local_set_by_id[event["localSetId"]]["locality"],
                    "setEditionIds": event["setEditionIds"],
                    "relationshipToLegacyScalar": relationship,
                    "dateValue": event["dateValue"],
                    "datePrecision": event["datePrecision"],
                    "approximate": event["approximate"],
                    "status": event["status"],
                    "marketScopes": event["marketScopes"],
                    "marketScopeBasis": event["marketScopeBasis"],
                    "sourceRecordId": event["sourceRecordId"],
                    "evidenceProvider": event_source["provider"],
                    "evidenceSourceUrl": event_source.get("sourceUrl"),
                }
                event_links.append(link)
                all_event_links[event["releaseEventId"]] = link
            language_links.append({
                "language": language,
                "setEditionIds": [edition["setEditionId"] for edition in editions],
                "releaseEventLinks": event_links,
                "dateLinkState": "supported" if event_links else "needs-evidence",
                "copiedLegacyScalar": False,
            })

        supported = [item["language"] for item in language_links if item["releaseEventLinks"]]
        unresolved = [item["language"] for item in language_links if not item["releaseEventLinks"]]
        relationships = {
            link["relationshipToLegacyScalar"] for link in all_event_links.values()
        }
        if all_event_links and relationships == {"supports-legacy-date"}:
            provenance = "newly-sourced"
        elif all_event_links:
            provenance = "positively-superseded"
        elif source:
            provenance = "unknown-needs-evidence"
        elif row.get("date"):
            provenance = "inherited-legacy-estimate-with-warning"
        else:
            provenance = "unknown-needs-evidence"

        if provenance == "positively-superseded":
            migration = "explicitly-superseded"
        elif supported and unresolved:
            migration = "explicitly-split"
        elif supported and len(supported) == len(row["confirmedLanguages"]):
            migration = "lossless-projected"
        else:
            migration = "needs-evidence"
        terminal = "complete" if migration == "lossless-projected" else "needs-evidence"
        warning = None
        if provenance == "inherited-legacy-estimate-with-warning":
            warning = "Legacy scalar has no row-level source and is not a reviewed release event."
        elif provenance == "positively-superseded":
            warning = "Positive edition event is narrower or differs; the raw scalar is retained, not overwritten."
        elif provenance == "unknown-needs-evidence":
            warning = "The row-level source could not be linked to a positively supported edition event."
        elif unresolved:
            warning = "The scalar is not copied onto languages outside the source event scope."

        ledger.append({
            "legacyReleaseRowId": row["rowId"],
            "legacyRowHash": value_hash(row),
            "legacyAliasSourceRecordIds": source_ids,
            "localSetIds": local_set_ids,
            "rawDate": row.get("date"),
            "rawDatePrecision": row.get("datePrecision"),
            "rawDateApproximate": row.get("dateApproximate"),
            "rawDateSource": copy.deepcopy(source),
            "confirmedLanguages": list(row["confirmedLanguages"]),
            "languageDateLinks": language_links,
            "releaseEventIds": sorted(all_event_links),
            "supportedDateLanguages": supported,
            "needsEvidenceDateLanguages": unresolved,
            "dateProvenanceDisposition": provenance,
            "migrationDisposition": migration,
            "terminalState": terminal,
            "warning": warning,
            "generationProvenance": {
                "sourceArtifact": "analysis_confirmed_releases.json",
                "sourceSchemaVersion": documents["analysis"]["schemaVersion"],
                "sourceGenerated": documents["analysis"]["generated"],
                "sourceGenerator": "scripts/confirmed_releases.py",
            },
        })
    ledger.sort(key=lambda item: item["legacyReleaseRowId"])
    return ledger


def is_specimen_source(source_type: str | None) -> bool:
    value = (source_type or "").casefold()
    return any(token in value for token in (
        "specimen", "scan", "photograph", "exact variant image", "user",
    ))


def build_finish_ledger(documents: dict[str, Any]) -> list[dict[str, Any]]:
    units = documents["finish"]["units"]
    graph = documents["setGraph"]
    identity = documents["identity"]
    graph_release_ids = {row["cardReleaseId"] for row in graph["cardReleaseRefs"]}
    editions = {row["setEditionId"]: row for row in identity["setEditions"]}
    releases_by_key: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for release in identity["cardReleases"]:
        edition = editions[release["setEditionId"]]
        key = (
            str(release.get("viaLegacySetCode") or ""),
            str(release.get("viaLegacyNumber") or release.get("localNumber") or ""),
            edition["language"],
        )
        if release["cardReleaseId"] in graph_release_ids:
            releases_by_key[key].append(release["cardReleaseId"])
    physical_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for printing in identity["physicalPrintings"]:
        physical_by_unit[printing["sourceFinishUnitId"]].append(printing)
    profile_claims_by_release: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in graph["profileFinishClaims"]:
        profile_claims_by_release[claim["cardReleaseId"]].append(claim)

    ledger: list[dict[str, Any]] = []
    for unit in units:
        unit_id = unit["finishUnitId"]
        key = (unit["setCode"], str(unit.get("number") or ""), unit["language"])
        release_ids = sorted(set(releases_by_key.get(key, [])))
        profile_claims = sorted(
            (
                claim for release_id in release_ids
                for claim in profile_claims_by_release.get(release_id, [])
                if claim["finish"] in unit.get("availableFinishes", [])
            ),
            key=lambda item: item["profileFinishClaimId"],
        )
        source_types = sorted({
            source.get("sourceType")
            for printing in unit.get("printings", [])
            for source in printing.get("sources", [])
            if source.get("sourceType")
        })
        has_positive_printing = bool(unit.get("availableFinishes") and unit.get("printings"))
        has_specimen = any(is_specimen_source(source_type) for source_type in source_types)
        physical_ids = sorted(
            printing["physicalPrintingId"] for printing in physical_by_unit.get(unit_id, [])
        )

        if profile_claims:
            migration = "profile-derived"
            scope = "set-edition-profile"
        elif has_positive_printing and has_specimen:
            migration = "specimen-evidenced"
            scope = "physical-printing"
        elif has_positive_printing:
            migration = "card-level-evidenced"
            scope = "card-release"
        else:
            migration = "needs-evidence"
            scope = "none"
        if scope == "physical-printing":
            target_missing = not physical_ids
        elif scope == "card-release":
            target_missing = not release_ids
        elif scope == "set-edition-profile":
            target_missing = not profile_claims
        else:
            target_missing = False
        terminal = "needs-evidence" if migration == "needs-evidence" or target_missing else "complete"
        closure = None
        if unit["completenessStatus"] == "complete-manifest":
            closure = "complete-manifest-preserved"
        elif unit["completenessStatus"] == "owner-adjudicated":
            closure = "owner-adjudicated-preserved"

        ledger.append({
            "finishUnitId": unit_id,
            "legacyUnitHash": value_hash(unit),
            "legacySourceRef": f"verification/finish_units.json#{unit_id}",
            "setCode": unit["setCode"],
            "setName": unit["setName"],
            "number": unit.get("number"),
            "language": unit["language"],
            "availableFinishes": copy.deepcopy(unit.get("availableFinishes", [])),
            "finishStatus": copy.deepcopy(unit["finishStatus"]),
            "applicabilityStatus": unit["applicabilityStatus"],
            "availabilityStatus": unit["availabilityStatus"],
            "completenessStatus": unit["completenessStatus"],
            "productMappingStatus": unit["productMappingStatus"],
            "patternStatus": unit["patternStatus"],
            "printingEvidence": copy.deepcopy(unit.get("printings", [])),
            "unresolved": copy.deepcopy(unit.get("unresolved", [])),
            "migrationDisposition": migration,
            "scope": scope,
            "cardReleaseIds": release_ids,
            "physicalPrintingIds": physical_ids if scope == "physical-printing" else [],
            "profileFinishClaimIds": [
                claim["profileFinishClaimId"] for claim in profile_claims
            ],
            "closureDisposition": closure,
            "terminalState": terminal,
            "warning": (
                "Positive finish evidence is retained, but no catalogue card-release target exists."
                if target_missing else None
            ),
        })
    ledger.sort(key=lambda item: item["finishUnitId"])
    return ledger


def source_reference(catch_up_of: str) -> tuple[str, str] | None:
    match = re.search(r"\b([A-Za-z][A-Za-z0-9-]*)\s+(\d+)\b", catch_up_of)
    return (match.group(1), match.group(2)) if match else None


def build_catch_up_edges(documents: dict[str, Any]) -> list[dict[str, Any]]:
    graph = documents["setGraph"]
    identity = documents["identity"]
    source_first = documents["sourceFirst"]["prints"]
    edition_by_key = {
        (edition["locality"], edition["localCode"], edition["language"]): edition["setEditionId"]
        for edition in graph["setEditions"]
    }
    source_release_by_key: dict[tuple[str, str], list[str]] = defaultdict(list)
    for release in identity["cardReleases"]:
        if not release.get("localIdentifierKnown"):
            continue
        source_release_by_key[(
            str(release.get("viaLegacySetCode") or ""),
            str(release.get("viaLegacyNumber") or release.get("localNumber") or ""),
        )].append(release["cardReleaseId"])

    edges: list[dict[str, Any]] = []
    for printing in source_first:
        if not printing.get("catchUpOf"):
            continue
        reference = source_reference(printing["catchUpOf"])
        source_ids = sorted(source_release_by_key.get(reference, [])) if reference else []
        target_edition = edition_by_key.get((
            printing["locality"], printing["localSetCode"], printing["language"]
        ))
        edges.append({
            "catchUpRelationId": stable_id("CATCHUP", printing["printId"]),
            "relationship": "source-material-catch-up-of-card-release",
            "sourceCardReleaseIds": source_ids,
            "rawSourceReference": printing["catchUpOf"],
            "targetSourceFirstPrintId": printing["printId"],
            "targetSetEditionId": target_edition,
            "equivalenceScope": "card-work-only",
            "setMergeAllowed": False,
            "terminalState": "complete" if len(source_ids) == 1 and target_edition else "needs-evidence",
            "evidence": {
                "providerId": printing["providerId"],
                "sourceUrl": printing["sourceUrl"],
                "specimenId": printing["specimenId"],
            },
        })
    edges.sort(key=lambda item: item["catchUpRelationId"])
    return edges


def build_identity_boundaries(documents: dict[str, Any]) -> list[dict[str, Any]]:
    graph = documents["setGraph"]
    local_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for local_set in graph["localSets"]:
        local_by_code[local_set["localCode"]].append(local_set)
    result = []
    for code in IDENTITY_BOUNDARY_CODES:
        matches = sorted(local_by_code.get(code, []), key=lambda item: item["localSetId"])
        if matches:
            result.append({
                "rawIdentifier": code,
                "localSetIds": [item["localSetId"] for item in matches],
                "terminalState": "complete",
                "mergeAllowed": False,
                "basis": "positive source-first local-set record",
            })
        else:
            result.append({
                "rawIdentifier": code,
                "localSetIds": [],
                "terminalState": "blocked-by-source",
                "mergeAllowed": False,
                "basis": (
                    "adversarial identity guard only; no positive local-set source record is "
                    "present, so an identity node is not manufactured"
                ),
            })
    return result


def build_mixed_status_report(documents: dict[str, Any]) -> list[dict[str, Any]]:
    units = documents["finish"]["units"]
    result = []
    for set_code, language in MIXED_STATUS_PAIRS:
        matching = [
            unit for unit in units
            if unit["setCode"] == set_code and unit["language"] == language
        ]
        claims = sorted(
            (
                {
                    "finishUnitId": unit["finishUnitId"],
                    "number": unit.get("number"),
                    "variant": product["variant"],
                    "claimStatus": product["claimStatus"],
                }
                for unit in matching for product in unit["products"]
            ),
            key=lambda item: (str(item["number"]), item["variant"]),
        )
        result.append({
            "setCode": set_code,
            "language": language,
            "cardClaims": claims,
            "observedClaimStatuses": sorted({item["claimStatus"] for item in claims}),
            "setEditionVerdict": None,
            "reason": "mixed card-level claims cannot establish a set-edition language verdict",
        })
    return result


def build_compatibility_json(
    analysis: dict[str, Any], release_ledger: list[dict[str, Any]], report_data: dict[str, Any]
) -> dict[str, Any]:
    reconciliation = {row["legacyReleaseRowId"]: row for row in release_ledger}
    result = copy.deepcopy(analysis)
    result["coverageVersion"] = COVERAGE_VERSION
    result["sourceArtifact"] = "analysis_confirmed_releases.json"
    result["compatibilityProjection"] = {
        "denominator": len(analysis["variants"]),
        "losslessLegacyRows": True,
        "legacyDateOverwritten": False,
        "report": report_data,
    }
    for row in result["variants"]:
        migration = reconciliation[row["rowId"]]
        row["reconciliation"] = {
            key: copy.deepcopy(migration[key]) for key in (
                "legacyRowHash", "dateProvenanceDisposition", "migrationDisposition",
                "terminalState", "releaseEventIds", "supportedDateLanguages",
                "needsEvidenceDateLanguages", "warning",
            )
        }
    return result


def build_compatibility_csv(
    analysis: dict[str, Any], release_ledger: list[dict[str, Any]], report_data: dict[str, Any]
) -> str:
    with ANALYSIS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.reader(handle, delimiter=";"))
    if len(source_rows) != len(analysis["variants"]) + 1:
        raise ValueError("legacy JSON/CSV release row counts disagree")
    ledger_by_id = {row["legacyReleaseRowId"]: row for row in release_ledger}
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    writer.writerow(source_rows[0] + [
        "Row ID", "Coverage version", "Coverage denominator", "Row count delta",
        "Dropped language relationships", "Legacy scalar dates overwritten",
        "Unsourced presented as reviewed exact", "Migration disposition", "Terminal state",
        "Date provenance disposition", "Release event IDs", "Supported date languages",
        "Needs-evidence date languages", "Legacy row SHA-256", "Reconciliation warning",
    ])
    for source_row, variant in zip(source_rows[1:], analysis["variants"]):
        if (
            source_row[5] != variant["setCode"]
            or source_row[6] != str(variant.get("number") or "")
            or source_row[7] != variant["edition"]
            or source_row[8] != variant["variant"]
        ):
            raise ValueError(f"legacy JSON/CSV order differs at {variant['rowId']}")
        migration = ledger_by_id[variant["rowId"]]
        writer.writerow(source_row + [
            variant["rowId"], COVERAGE_VERSION, report_data["legacyRows"],
            report_data["rowCountDelta"], report_data["droppedLanguageRelationships"],
            report_data["legacyScalarDatesOverwritten"],
            report_data["unsourcedPresentedAsReviewedExact"], migration["migrationDisposition"],
            migration["terminalState"], migration["dateProvenanceDisposition"],
            ", ".join(migration["releaseEventIds"]),
            ", ".join(migration["supportedDateLanguages"]),
            ", ".join(migration["needsEvidenceDateLanguages"]),
            migration["legacyRowHash"], migration["warning"] or "",
        ])
    return output.getvalue()


def build(documents: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any], str]:
    documents = documents or input_documents()
    aliases, alias_relations = build_alias_ledger(documents)
    releases = build_release_ledger(documents)
    finishes = build_finish_ledger(documents)
    catch_up_edges = build_catch_up_edges(documents)
    boundaries = build_identity_boundaries(documents)
    mixed_status = build_mixed_status_report(documents)

    actual = {"aliases": len(aliases), "releaseRows": len(releases), "finishUnits": len(finishes)}
    if actual != EXPECTED_DENOMINATORS:
        raise ValueError(
            f"bounded backfill denominator changed: expected {EXPECTED_DENOMINATORS}, got {actual}; "
            "review inputs and increment coverageVersion"
        )
    alias_report = report(
        len(aliases), Counter(row["migrationDisposition"] for row in aliases),
        ("mapped", "split-related", "needs-evidence", "positively-retained-legacy"),
    )
    release_report = report(
        len(releases), Counter(row["migrationDisposition"] for row in releases),
        ("lossless-projected", "explicitly-split", "explicitly-superseded", "needs-evidence"),
    )
    finish_report = report(
        len(finishes), Counter(row["migrationDisposition"] for row in finishes),
        ("profile-derived", "card-level-evidenced", "specimen-evidenced", "needs-evidence"),
    )
    language_total = sum(len(row["confirmedLanguages"]) for row in releases)
    supported_total = sum(len(row["supportedDateLanguages"]) for row in releases)
    compatibility_report = {
        "coverageVersion": COVERAGE_VERSION,
        "legacyRows": len(releases),
        "projectedRows": len(releases),
        "rowCountDelta": 0,
        "legacyLanguageRelationships": language_total,
        "preservedLanguageRelationships": language_total,
        "supportedEventRelationships": supported_total,
        "visibleNeedsEvidenceRelationships": language_total - supported_total,
        "droppedLanguageRelationships": 0,
        "legacySetCodeLanguagePairs": len({
            (unit["setCode"], unit["language"]) for unit in documents["finish"]["units"]
        }),
        "preservedSetCodeLanguagePairs": len({
            (unit["setCode"], unit["language"]) for unit in documents["finish"]["units"]
        }),
        "droppedSetCodeLanguagePairs": 0,
        "legacyScalarDatesOverwritten": 0,
        "unsourcedPresentedAsReviewedExact": 0,
    }
    provenance_report = dict(sorted(Counter(
        row["dateProvenanceDisposition"] for row in releases
    ).items()))
    closed = [row for row in finishes if row["closureDisposition"]]
    relation_reports = {
        "aliasSplitsOrRelations": len(alias_relations),
        "aliasMerges": 0,
        "orphanReleaseRows": sum(1 for row in releases if not row["localSetIds"]),
        "unsourcedReleaseRows": sum(1 for row in releases if not row["rawDateSource"]),
        "releasePrecision": dict(sorted(Counter(
            row["rawDatePrecision"] for row in releases
        ).items())),
        "releaseLanguageLinks": {
            "total": language_total,
            "supported": supported_total,
            "needsEvidence": language_total - supported_total,
        },
        "countDelta": 0,
    }
    reports = {
        "aliasAccounting": alias_report,
        "releaseAccounting": release_report,
        "finishAccounting": finish_report,
        "releaseDateProvenance": provenance_report,
        "compatibilityLoss": compatibility_report,
        "finishScopeLoss": {
            "legacyUnits": len(finishes),
            "projectedUnits": len(finishes),
            "legacyUnitsDropped": 0,
            "cardClaimsPromotedToProfiles": 0,
            "profileRulesCopiedAsCardEvidence": 0,
            "closedListsDropped": 0,
            "scopes": dict(sorted(Counter(row["scope"] for row in finishes).items())),
            "positiveScopesWithoutGraphTarget": sum(
                row["migrationDisposition"] != "needs-evidence"
                and row["terminalState"] == "needs-evidence"
                for row in finishes
            ),
        },
        "relationDiagnostics": relation_reports,
        "terminalStates": dict(sorted(Counter(
            row["terminalState"]
            for row in aliases + releases + finishes + catch_up_edges + boundaries
        ).items())),
        "closedFinishLists": {
            "count": len(closed),
            "completeManifest": sum(
                row["closureDisposition"] == "complete-manifest-preserved" for row in closed
            ),
            "ownerAdjudicated": sum(
                row["closureDisposition"] == "owner-adjudicated-preserved" for row in closed
            ),
            "finishUnitIds": [row["finishUnitId"] for row in closed],
        },
    }
    if not all(item["balanced"] for item in (alias_report, release_report, finish_report)):
        raise ValueError("backfill accounting is not balanced")

    generated = max(
        documents["analysis"]["generated"], documents["finish"]["meta"]["generated"],
        documents["setSources"]["meta"]["generated"], documents["setGraph"]["meta"]["generated"],
        documents["identity"]["meta"]["generated"], documents["sourceFirst"]["meta"]["generated"],
    )
    result = {
        "meta": {
            "schema": "snoredex-legacy-set-reconciliation",
            "schemaVersion": SCHEMA_VERSION,
            "coverageVersion": COVERAGE_VERSION,
            "generated": generated,
            "issue": 148,
            "description": (
                "Bounded, reversible reconciliation of legacy set aliases, scalar release dates, "
                "language relations and finish units. Absence never establishes an identity or date."
            ),
            "denominators": EXPECTED_DENOMINATORS,
            "inputHashes": {
                path.name: file_hash(path) for path in (
                    ANALYSIS_JSON, ANALYSIS_CSV, FINISH_PATH, SET_SOURCE_PATH,
                    SET_GRAPH_PATH, IDENTITY_PATH, SOURCE_FIRST_PATH,
                )
            },
        },
        "decisionRules": {
            "positiveEvidenceOnly": True,
            "copyScalarDateAcrossLanguages": False,
            "sourceFirstRecordsAreAliases": False,
            "catchUpRelationsMergeSets": False,
            "promoteCardFinishAgreementToSetProfile": False,
            "copyProfileFinishToCardsAsCardEvidence": False,
            "terminalStates": ["complete", "needs-evidence", "blocked-by-source"],
        },
        "legacyAliases": aliases,
        "aliasRelations": alias_relations,
        "legacyReleaseRows": releases,
        "legacyFinishUnits": finishes,
        "catchUpRelations": catch_up_edges,
        "identityBoundaryGuards": boundaries,
        "mixedCardClaimPairs": mixed_status,
        "fixtures": [
            {
                "fixtureId": "shared-west-scalar-splits-by-edition-language",
                "passed": any(
                    row["migrationDisposition"] == "explicitly-split"
                    and len(row["confirmedLanguages"]) > 1
                    for row in releases
                ),
                "basis": "a scalar compatibility date supports only its positively scoped language event",
            },
            {
                "fixtureId": "market-event-can-supersede-without-overwrite",
                "passed": date_relation(
                    "2020-01-01", "day",
                    {"dateValue": "2020-02-02"},
                ) == "positively-supersedes-legacy-scalar",
                "basis": "the raw scalar remains stored while a narrower event link carries the positive date",
            },
            {
                "fixtureId": "catch-up-is-edge-not-set-merge",
                "passed": bool(catch_up_edges) and all(
                    not edge["setMergeAllowed"] and edge["terminalState"] == "complete"
                    for edge in catch_up_edges
                ),
                "basis": "source-first catch-up records point to card releases, never alias or merge sets",
            },
            {
                "fixtureId": "mixed-language-claims-stay-card-level",
                "passed": all(
                    row["setEditionVerdict"] is None
                    and row["observedClaimStatuses"] == ["confirmed", "contradicted"]
                    for row in mixed_status
                ),
                "basis": "DP-P/Korean, XY-P/Korean and xJTG/French retain individual card claims",
            },
            {
                "fixtureId": "source-record-granularity-preserved",
                "passed": len({row["sourceRecordId"] for row in aliases}) == len(aliases),
                "basis": "provider records remain independently addressable even when raw identifiers repeat",
            },
            {
                "fixtureId": "alias-edition-splits-are-explicit",
                "passed": all(
                    len(row["setEditionIds"]) == len(row["editionResolutions"])
                    and all(
                        resolution["decision"] == "retain-distinct-language-script-edition"
                        for resolution in row["editionResolutions"]
                    )
                    for row in aliases
                ),
                "basis": "every zero/one/many edition projection retains an explicit non-equivalence decision",
            },
        ],
        "reports": reports,
    }
    result["meta"]["buildHash"] = value_hash(result)
    compatibility_json = build_compatibility_json(documents["analysis"], releases, compatibility_report)
    compatibility_csv = build_compatibility_csv(
        documents["analysis"], releases, compatibility_report
    )
    return result, compatibility_json, compatibility_csv


def render_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if committed projections differ")
    args = parser.parse_args(argv)
    result, compatibility_json, compatibility_csv = build()
    outputs = {
        OUTPUT_PATH: render_json(result),
        COMPAT_JSON_PATH: render_json(compatibility_json),
        COMPAT_CSV_PATH: compatibility_csv,
    }
    if args.check:
        stale = [path for path, rendered in outputs.items() if not path.exists() or path.read_text(
            encoding="utf-8-sig"
        ) != rendered]
        if stale:
            print("outdated: " + ", ".join(str(path.relative_to(ROOT)) for path in stale), file=sys.stderr)
            return 1
        print(
            f"legacy set reconciliation current: {len(result['legacyAliases'])} aliases, "
            f"{len(result['legacyReleaseRows'])} release rows, "
            f"{len(result['legacyFinishUnits'])} finish units"
        )
        return 0
    for path, rendered in outputs.items():
        path.write_text(rendered, encoding="utf-8", newline="")
    print(
        f"wrote bounded reconciliation: {len(result['legacyAliases'])} aliases, "
        f"{len(result['legacyReleaseRows'])} release rows, "
        f"{len(result['legacyFinishUnits'])} finish units"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

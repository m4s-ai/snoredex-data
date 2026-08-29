#!/usr/bin/env python3
"""Validate and expose the reviewed #140 locality graph snapshot.

The migration graph is now an authoritative, committed input. This module deliberately
does not rebuild it from compatibility projections: consumers read the snapshot (or the
SQLite graph tables) and this command only checks that the snapshot is structurally sound.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "verification" / "authoritative_graph.json"
FINISH_UNITS = ROOT / "verification" / "finish_units.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
UNITS = ROOT / "verification" / "units.json"
GRAPH_SCHEMA = "snoredex-authoritative-locality-graph"
GRAPH_SCHEMA_VERSION = "1.1.0"
MARKING_ROLES = {"print-identity", "reverse-holo-treatment", "distribution-promo"}
WORK_MAPPING_STATES = {
    "mapped",
    "mapped-by-explicit-equivalence",
    "needs-explicit-equivalence",
    "unmapped",
}
WORK_REQUIRED_STATES = {"mapped", "mapped-by-explicit-equivalence"}
WORK_EMPTY_STATES = {"needs-explicit-equivalence", "unmapped"}
# These eight releases were explicitly reviewed in producer issue #304 as
# positive local releases whose Work identity is still unresolved.  They must
# retain the reviewed pending state until a separate equivalence decision exists.
ISSUE304_NEEDS_EXPLICIT_RELEASES = frozenset({
    "RELEASE:JP:Japanese:DP-P:126:None",
    "RELEASE:JP:Japanese:DP-P:127:None",
    "RELEASE:JP:Japanese:UNP:unnumbered:None",
    "RELEASE:KR:Korean:via-DP-P:unknown-local-set:via-127:None:unknown-local-id",
    "RELEASE:WEST:English:RR:111:None",
    "RELEASE:WEST:French:RR:111:None",
    "RELEASE:WEST:German:RR:111:None",
    "RELEASE:WEST:Italian:RR:111:None",
})
FOIL_PATTERN_ALIASES = {
    "poke ball mirror": "poke-ball",
    "poké ball mirror": "poke-ball",
    "master ball mirror": "master-ball",
}


def read_graph() -> dict[str, Any]:
    return json.loads(OUTPUT.read_text(encoding="utf-8"))


def _payloads(graph: dict[str, Any], entity_type: str) -> list[dict[str, Any]]:
    return [row["payload"] for row in graph["entities"] if row["entityType"] == entity_type]


def _graph_hash(graph: dict[str, Any]) -> str:
    body = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _number(value: Any) -> str:
    numerator = str(value or "").split("/", 1)[0]
    return numerator.lstrip("0") or ("0" if numerator else "")


def _identity_value(field: str, value: Any) -> str:
    return _number(value) if field == "number" else _normalized(value)


def normalized_foil_pattern(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return FOIL_PATTERN_ALIASES.get(value.strip().casefold(), value)


def _normalized(value: Any) -> str:
    return "" if value is None else str(value)


def _semantic_markings(value: Any) -> list[dict[str, Any]] | None:
    if not value:
        return None
    if not isinstance(value, list):
        return value
    return sorted(
        (dict(row) for row in value),
        key=lambda row: (str(row.get("kind", "")), str(row.get("role", "")), str(row.get("text", ""))),
    )


def printing_semantic_key(scope: Any, printing: dict[str, Any]) -> str:
    """Canonical identity for a physical finish printing, independent of its ordinal id."""
    payload = {
        "scope": str(scope or ""),
        "finish": printing.get("finish"),
        "edition": printing.get("edition"),
        "foilPattern": normalized_foil_pattern(printing.get("foilPattern")),
        "markings": _semantic_markings(printing.get("markings")),
        "distribution": printing.get("distribution") or None,
        "cardSize": printing.get("cardSize") or "unknown",
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_printing_id(semantic_key: str) -> str:
    return "PRINTING:" + hashlib.sha256(semantic_key.encode("utf-8")).hexdigest()[:24]


def finish_unit_release_key(unit: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(unit.get("releaseSetCode") or unit.get("setCode") or ""),
        _number(unit.get("number")),
        str(unit.get("language") or ""),
    )


def _release_index(graph: dict[str, Any]) -> dict[tuple[str, str, str], str]:
    """Index card releases by the typed local identity used by finish units."""
    index: dict[tuple[str, str, str], str] = {}
    for row in graph["entities"]:
        if row.get("entityType") != "card-release":
            continue
        payload = row.get("payload") or {}
        set_code = payload.get("localSetCode") or payload.get("viaLegacySetCode")
        number = payload.get("localNumber") or payload.get("viaLegacyNumber")
        language = payload.get("language")
        if set_code is not None and number is not None and language:
            key = (str(set_code), _number(number), str(language))
            previous = index.get(key)
            if previous and previous != row["entityId"]:
                raise ValueError(f"ambiguous card release identity: {key}")
            index[key] = row["entityId"]
    return index


def _entity(entity_type: str, entity_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "entityType": entity_type,
        "entityId": entity_id,
        "origin": "physical-evidence-projection",
        "payload": payload,
    }


def project_physical_evidence(graph: dict[str, Any]) -> dict[str, Any]:
    """Refresh source provenance and rebuild finish/specimen nodes from canonical inputs.

    The locality migration remains the graph's reviewed base. This projection owns only the
    physical-printing slice plus the source URL copied onto existing legacy-language claims, so
    stronger evidence can replace a source without hand-editing the graph snapshot.
    """
    unit_sources = {
        str(unit["unitId"]): unit.get("sourceUrl")
        for unit in _read_json(UNITS)
    }
    for row in graph["entities"]:
        payload = row.get("payload") or {}
        if row.get("entityType") == "candidate-claim" \
                and payload.get("sourceKind") == "legacy-language-unit":
            source_id = str(payload.get("sourceId"))
            if source_id in unit_sources:
                payload["sourceRecord"] = unit_sources[source_id]

    finish_document = _read_json(FINISH_UNITS)
    specimen_document = _read_json(SPECIMENS)
    finish_units = finish_document.get("units", [])
    specimens = [row for row in specimen_document.get("specimens", [])
                 if row.get("physicalObservation")]
    release_ids = _release_index(graph)
    specimen_by_id = {str(row["specimenId"]): row for row in specimens}
    existing_finish_proposals = {
        str(row.get("payload", {}).get("sourceId")): row.get("payload", {}).get("proposedCardReleaseId")
        for row in graph["entities"]
        if row.get("entityType") == "candidate-claim"
        and row.get("payload", {}).get("sourceKind") == "finish-printing-record"
    }
    existing_finish_proposals_by_semantic = {
        str(row.get("payload", {}).get("semanticPrintingId")): row.get("payload", {}).get("proposedCardReleaseId")
        for row in graph["entities"]
        if row.get("entityType") == "candidate-claim"
        and row.get("payload", {}).get("sourceKind") == "finish-printing-record"
        and row.get("payload", {}).get("semanticPrintingId")
    }
    previous_physical_by_semantic: dict[str, str] = {}
    previous_claim_by_physical: dict[str, str] = {}
    for row in graph["entities"]:
        if row.get("entityType") != "physical-printing":
            continue
        payload = row.get("payload") or {}
        if not payload.get("sourceFinishUnitId"):
            continue
        semantic_key = printing_semantic_key(payload.get("cardReleaseId"), payload)
        previous_physical_by_semantic[semantic_key] = str(row["entityId"])
        claim_id = payload.get("establishingClaimId")
        if claim_id:
            previous_claim_by_physical[str(row["entityId"])] = str(claim_id)

    generated_entities: list[dict[str, Any]] = []
    generated_edges: list[dict[str, Any]] = []
    generated_dispositions: list[dict[str, Any]] = []
    specimen_targets: dict[str, str] = {}
    conflicted_specimen_ids = {
        str(specimen_id)
        for unit in finish_units
        for printing in unit.get("printings", [])
        if printing.get("conflictsWith")
        for specimen_id in printing.get("specimenIds") or []
    }

    for unit in finish_units:
        unit_key = finish_unit_release_key(unit)
        release_id = release_ids.get(unit_key)
        for printing in sorted(unit.get("printings", []), key=lambda row: row.get("printingId", "")):
            printing_id = str(printing["printingId"])
            semantic_scope = release_id or "finish-unit:" + "|".join(unit_key)
            semantic_key = printing_semantic_key(semantic_scope, printing)
            semantic_id = stable_printing_id(semantic_key)
            physical_id = previous_physical_by_semantic.get(semantic_key, f"PHYSICAL:{semantic_id}")
            claim_id = previous_claim_by_physical.get(
                physical_id, f"CLAIM:finish:{semantic_id}"
            )
            confirmed = printing.get("verificationStatus") == "confirmed"
            if confirmed and not release_id:
                raise ValueError(f"confirmed finish unit has no card release: {unit_key}")
            specimen_ids = sorted({str(value) for value in printing.get("specimenIds") or []})
            specimen_ids = [value for value in specimen_ids if value in specimen_by_id]
            claim_payload = {
                "claimId": claim_id,
                "claimKind": "physical-printing",
                "sourceKind": "finish-printing-record",
                "sourceId": printing_id,
                "semanticPrintingId": semantic_id,
                "evidenceStatus": printing.get("verificationStatus", "pending"),
                "disposition": "established-and-mapped" if confirmed else "candidate-needs-evidence",
                "proposedTargetId": physical_id if confirmed else None,
                "materializedTargetId": physical_id if confirmed else None,
                "reason": (
                    "explicit specimen conflict requires resolution before materialization"
                    if printing.get("conflictsWith") else
                    "canonical specimen observations and finish evidence establish the exact "
                    "finish and edition"
                    if specimen_ids else
                    "finish printing record carries positive evidence"
                ),
            }
            if printing.get("conflictsWith"):
                claim_payload["conflictsWith"] = sorted(set(printing["conflictsWith"]))
            if not confirmed:
                proposal = (
                    release_id
                    or existing_finish_proposals_by_semantic.get(semantic_id)
                    or existing_finish_proposals.get(printing_id)
                )
                if proposal:
                    claim_payload["proposedCardReleaseId"] = proposal
            if specimen_ids:
                claim_payload["specimenIds"] = specimen_ids
            generated_entities.append(_entity("candidate-claim", claim_id, claim_payload))
            generated_dispositions.append({
                "sourceKind": "finish-printing-record",
                "sourceId": printing_id,
                "disposition": claim_payload["disposition"],
                "targetRef": physical_id if confirmed else None,
                "reason": claim_payload["reason"],
            })
            if not confirmed:
                proposal = claim_payload.get("proposedCardReleaseId")
                if proposal:
                    generated_edges.append({
                        "fromType": "candidate-claim", "fromId": claim_id,
                        "relation": "proposes-for", "toType": "card-release", "toId": proposal,
                        "provenance": {},
                    })
                continue

            physical_payload = {
                "physicalPrintingId": physical_id,
                "semanticPrintingId": semantic_id,
                "cardReleaseId": release_id,
                "finish": printing["finish"],
                "edition": printing.get("edition"),
                "foilPattern": printing.get("foilPattern"),
                "markings": printing.get("markings"),
                "distribution": printing.get("distribution"),
                "cardSize": printing.get("cardSize"),
                "errorClass": None,
                "classificationState": "classified-from-positive-evidence",
                "sourceFinishUnitId": unit["finishUnitId"],
                "sourcePrintingId": printing_id,
                "establishingClaimId": claim_id,
            }
            if specimen_ids:
                physical_payload["specimenIds"] = specimen_ids
            if printing.get("conflictsWith"):
                physical_payload["conflictsWith"] = sorted(set(printing["conflictsWith"]))
            generated_entities.append(_entity("physical-printing", physical_id, physical_payload))
            generated_edges.extend([
                {
                    "fromType": "candidate-claim", "fromId": claim_id,
                    "relation": "materializes", "toType": "physical-printing", "toId": physical_id,
                    "provenance": {"disposition": "established-and-mapped"},
                },
                {
                    "fromType": "physical-printing", "fromId": physical_id,
                    "relation": "established-by", "toType": "candidate-claim", "toId": claim_id,
                    "provenance": {},
                },
                {
                    "fromType": "physical-printing", "fromId": physical_id,
                    "relation": "realizes", "toType": "card-release", "toId": release_id,
                    "provenance": {},
                },
            ])
            for specimen_id in specimen_ids:
                specimen_targets[specimen_id] = physical_id

    for specimen_id, specimen in sorted(specimen_by_id.items()):
        target = specimen_targets.get(specimen_id)
        claim_id = f"CLAIM:specimen:{specimen_id}"
        observation = specimen.get("physicalObservation") or {}
        release_id = release_ids.get((
            str(specimen.get("setCode") or ""), _number(specimen.get("number")),
            str(specimen.get("language") or ""),
        ))
        standalone_target = None
        if (not target and release_id and not observation.get("coversMultipleCards")
                and not observation.get("conflictsWith")
                and specimen_id not in conflicted_specimen_ids):
            standalone_target = f"PHYSICAL:specimen:{specimen_id}"
            target = standalone_target
            physical_payload = {
                "physicalPrintingId": standalone_target,
                "cardReleaseId": release_id,
                "finish": observation.get("finish"),
                "edition": observation.get("edition"),
                "foilPattern": specimen_observation_value(observation, "foilPattern"),
                "markings": specimen_markings(observation),
                "distribution": observation.get("distribution"),
                "cardSize": observation.get("cardSize") or "unknown",
                "basis": observation.get("basis"),
                "errorClass": None,
                "classificationState": "classified-from-positive-evidence",
                "sourceFinishUnitId": None,
                "sourcePrintingId": None,
                "establishingClaimId": claim_id,
                "specimenIds": [specimen_id],
            }
            generated_entities.append(_entity("physical-printing", standalone_target,
                                              physical_payload))
            generated_edges.extend([
                {
                    "fromType": "candidate-claim", "fromId": claim_id,
                    "relation": "materializes", "toType": "physical-printing",
                    "toId": standalone_target,
                    "provenance": {"disposition": "established-and-mapped"},
                },
                {
                    "fromType": "physical-printing", "fromId": standalone_target,
                    "relation": "established-by", "toType": "candidate-claim",
                    "toId": claim_id, "provenance": {},
                },
                {
                    "fromType": "physical-printing", "fromId": standalone_target,
                    "relation": "realizes", "toType": "card-release", "toId": release_id,
                    "provenance": {},
                },
            ])
        # A specimen listed on a finish printing is the evidence used to derive that
        # printing, not an independent provider.  Keep the link as provenance so the
        # graph never counts an observation as corroborating its own projection.
        reason = (
            f"physical observation establishes standalone printing for {release_id}"
            if standalone_target else
            f"provides provenance for {target}, already established from the finish store"
            if target else "physical observation has no matching projected printing"
        )
        claim_payload = {
            "claimId": claim_id,
            "claimKind": "physical-printing",
            "sourceKind": "specimen-observation",
            "sourceId": specimen_id,
            "evidenceStatus": "observed",
            "disposition": "established-and-mapped" if standalone_target else "candidate-needs-evidence",
            "proposedTargetId": target or f"PHYSICAL:specimen:{specimen_id}",
            "materializedTargetId": standalone_target,
            "reason": reason,
        }
        if target:
            claim_payload["provenanceTargetId"] = target
        generated_entities.append(_entity("candidate-claim", claim_id, claim_payload))
        generated_dispositions.append({
            "sourceKind": "specimen-observation",
            "sourceId": specimen_id,
            "disposition": "established-and-mapped" if standalone_target else "candidate-needs-evidence",
            "targetRef": standalone_target,
            "reason": reason,
        })
        if target and not standalone_target:
            generated_edges.append({
                "fromType": "candidate-claim", "fromId": claim_id,
                "relation": "provenance", "toType": "physical-printing", "toId": target,
                "provenance": {"specimenId": specimen_id},
            })

    owned_claim_ids = {
        row["entityId"] for row in graph["entities"]
        if row.get("entityType") == "candidate-claim"
        and row.get("payload", {}).get("sourceKind") in {"finish-printing-record", "specimen-observation"}
    }
    owned_physical_ids = {
        row["entityId"] for row in graph["entities"]
        if row.get("entityType") == "physical-printing"
        and (row.get("payload", {}).get("sourceFinishUnitId")
             or str(row.get("entityId", "")).startswith("PHYSICAL:specimen:"))
    }
    owned_ids = owned_claim_ids | owned_physical_ids
    graph["entities"] = [row for row in graph["entities"] if row["entityId"] not in owned_ids]
    graph["entities"].extend(generated_entities)
    graph["edges"] = [
        row for row in graph["edges"]
        if row.get("fromId") not in owned_ids and row.get("toId") not in owned_ids
    ]
    graph["edges"].extend(generated_edges)
    graph["migrationDispositions"] = [
        row for row in graph["migrationDispositions"]
        if row.get("sourceKind") not in {"finish-printing-record", "specimen-observation"}
    ]
    graph["migrationDispositions"].extend(generated_dispositions)

    graph["entities"].sort(key=lambda row: (row["entityType"], row["entityId"]))
    graph["edges"].sort(key=lambda row: (
        row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"]
    ))
    graph["migrationDispositions"].sort(key=lambda row: (row["sourceKind"], row["sourceId"]))
    entity_counts = defaultdict(int)
    for row in graph["entities"]:
        entity_counts[row["entityType"]] += 1
    disposition_counts = defaultdict(int)
    for row in graph["migrationDispositions"]:
        disposition_counts[row["disposition"]] += 1
    graph["summary"] = {
        "entities": len(graph["entities"]),
        "edges": len(graph["edges"]),
        "migrationInputs": len(graph["migrationDispositions"]),
        "migrationDispositions": dict(sorted(disposition_counts.items())),
        "candidateClaims": entity_counts["candidate-claim"],
        "cardReleases": entity_counts["card-release"],
        "physicalPrintings": entity_counts["physical-printing"],
        "setSourceRecords": entity_counts["set-source-record"],
        "setSourceDispositions": sum(
            row["sourceKind"] == "set-catalogue-source"
            for row in graph["migrationDispositions"]
        ),
        "localizations": entity_counts["localization"],
    }
    graph["meta"]["generated"] = finish_document.get("meta", {}).get(
        "generated", graph["meta"].get("generated")
    )
    return graph


def write_graph(graph: dict[str, Any]) -> None:
    OUTPUT.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")


def specimen_markings(observation: dict[str, Any]) -> list[dict[str, Any]]:
    text = observation.get("markings")
    if not text:
        return []
    normalized = str(text).strip()
    if normalized.casefold() in {"editie 1", "edizione 1"}:
        kind = "edition-stamp"
    elif normalized.casefold() == "staff":
        kind, normalized = "staff", "Staff"
    elif normalized.casefold().endswith(" deck silhouette"):
        kind, normalized = "deck-logo", normalized[:-16].strip()
    elif normalized.casefold().endswith(" replica signature"):
        kind, normalized = "championship-signature", normalized[:-18].strip()
    else:
        kind = "observed-marking"
    return [{
        "kind": kind,
        "role": observation.get("markingRole"),
        "text": normalized,
    }]


def identity_view(graph: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the small identity-shaped view needed by discovery and locality checks.

    This is an in-memory compatibility adapter, not a generated artifact. Its rows come
    exclusively from the authoritative graph entities and migration dispositions.
    """
    graph = read_graph() if graph is None else graph
    claims = _payloads(graph, "candidate-claim")
    releases = _payloads(graph, "card-release")
    printings = _payloads(graph, "physical-printing")
    assertions = _payloads(graph, "equivalence-assertion")
    editions = _payloads(graph, "set-edition")
    products = {
        row["sourceId"]: {key: value for key, value in row.items() if key != "sourceId"}
        for row in _payloads(graph, "legacy-cardmarket-product")
    }
    releases_by_id = {row["cardReleaseId"]: row for row in releases}
    assertions_by_unit: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in assertions:
        if row.get("legacyUnitId"):
            assertions_by_unit[row["legacyUnitId"]].append(row)
    claims_by_unit = {row.get("sourceId"): row for row in claims
                      if row.get("sourceKind") == "legacy-language-unit"}
    rekey_rows: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for disposition in graph["migrationDispositions"]:
        if disposition.get("sourceKind") != "legacy-issue-rekey":
            continue
        unit_id = disposition["sourceId"]
        target_ids = list(disposition.get("targetRefs") or [])
        source_ids = sorted({
            source_id
            for target_id in target_ids
            for source_id in releases_by_id.get(target_id, {}).get("sourceFirstRecordIds", [])
        })
        assertion_ids = sorted(row["assertionId"] for row in assertions_by_unit.get(unit_id, []))
        match = re.search(r"issue #(\d+)", disposition.get("reason", ""))
        issue_number = int(match.group(1)) if match else 0
        claim = claims_by_unit.get(unit_id, {})
        row = {
            "legacyUnitId": unit_id,
            "legacyClaimId": claim.get("claimId", f"CLAIM:legacy:{unit_id}"),
            "legacyStatus": claim.get("evidenceStatus"),
            "disposition": disposition["disposition"],
            "sourceFirstRecordIds": source_ids,
            "localCardReleaseIds": target_ids,
            "assertionIds": assertion_ids,
        }
        rekey_rows[issue_number].append(row)
    reports = [
        {"issueNumber": issue, "rows": sorted(rows, key=lambda row: row["legacyUnitId"])}
        for issue, rows in sorted(rekey_rows.items())
    ]
    return {
        "meta": graph["meta"],
        "legacyProductDispositions": products,
        "reports": {"legacyIssueRekeys": reports},
        "equivalenceAssertions": assertions,
        "candidateClaims": claims,
        "setEditions": editions,
        "cardReleases": releases,
        "physicalPrintings": printings,
        "authoritativeGraphHash": _graph_hash(graph),
    }


def specimen_observation_value(observation: dict[str, Any], field: str) -> Any:
    """Use the finish projector's explicit default for an omitted card size."""
    value = observation.get(field)
    if field == "foilPattern" and isinstance(value, str):
        key = " ".join(value.casefold().replace("é", "e").split())
        return FOIL_PATTERN_ALIASES.get(key, value)
    return value or "unknown" if field == "cardSize" else value


def specimen_observation_field_matches(
    observation: dict[str, Any], physical: dict[str, Any], field: str,
) -> bool:
    """Allow another positive source to refine an unobserved specimen card size."""
    if field == "cardSize" and not observation.get(field):
        return True
    return physical.get(field) == specimen_observation_value(observation, field)


# Graph shape and migration container invariants.
def _validate_shape(
    graph: dict[str, Any],
    errors: list[str],
) -> tuple[
    list[dict[str, Any]],
    set[tuple[Any, Any]],
    defaultdict[str, dict[str, dict[str, Any]]],
    list[dict[str, Any]],
    list[tuple[Any, ...]],
    defaultdict[tuple[str, str, str], list[tuple[str, str]]],
    list[dict[str, Any]],
]:
    meta = graph.get("meta", {})
    if meta.get("schema") != GRAPH_SCHEMA:
        errors.append("unexpected graph schema")
    if meta.get("schemaVersion") != GRAPH_SCHEMA_VERSION:
        errors.append("unexpected graph schema version")
    if meta.get("status") != "authoritative-migrated":
        errors.append("graph is not marked authoritative")
    entities = graph.get("entities", [])
    entity_keys = [(row.get("entityType"), row.get("entityId")) for row in entities]
    if len(entity_keys) != len(set(entity_keys)):
        errors.append("duplicate graph entities")
    entity_set = set(entity_keys)
    by_type: defaultdict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in entities:
        entity_type = row.get("entityType")
        entity_id = row.get("entityId")
        payload = row.get("payload")
        if isinstance(entity_type, str) and isinstance(entity_id, str) and isinstance(payload, dict):
            by_type[entity_type][entity_id] = payload
    edges = graph.get("edges", [])
    edge_keys = [(
        row.get("fromType"), row.get("fromId"), row.get("relation"),
        row.get("toType"), row.get("toId"),
    ) for row in edges]
    if len(edge_keys) != len(set(edge_keys)):
        errors.append("duplicate graph edges")
    for row in edges:
        if (row.get("fromType"), row.get("fromId")) not in entity_set:
            errors.append(f"dangling edge source: {row}")
        if row.get("toType") != "node" and (row.get("toType"), row.get("toId")) not in entity_set:
            errors.append(f"dangling edge target: {row}")
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)
    for row in edges:
        relations[(row.get("fromType"), row.get("fromId"), row.get("relation"))].append(
            (row.get("toType"), row.get("toId"))
        )
    dispositions = graph.get("migrationDispositions", [])
    disposition_keys = [(row.get("sourceKind"), row.get("sourceId")) for row in dispositions]
    if len(disposition_keys) != len(set(disposition_keys)):
        errors.append("duplicate migration dispositions")
    for row in dispositions:
        refs = row.get("targetRefs")
        if refs is not None and row.get("targetRef") != (refs[0] if refs else None):
            errors.append(f"migration targetRef does not preserve targetRefs: {row.get('sourceId')}")
    return entities, entity_set, by_type, edges, edge_keys, relations, dispositions

# Candidate-claim promotion and finish-candidate invariants.
def _validate_claim_conflicts(
    errors: list[str],
    claims: dict[str, dict[str, Any]],
    printings: dict[str, dict[str, Any]],
    specimen_claim_ids: set[str],
) -> None:
    for claim_id, claim in claims.items():
        conflicts = claim.get("conflictsWith") or []
        if conflicts and (
            not isinstance(conflicts, list)
            or any(ref not in specimen_claim_ids or ref == claim.get("sourceId")
                   for ref in conflicts)
            or claim.get("evidenceStatus") != "pending"
            or claim.get("materializedTargetId") is not None
        ):
            errors.append(f"finish conflict claim is not an unresolved explicit conflict: {claim_id}")
    for printing_id, printing in printings.items():
        conflicts = printing.get("conflictsWith") or []
        if conflicts:
            errors.append(f"conflicted printing was materialized: {printing_id}")


def _validate_claim_materialization(
    errors: list[str],
    claims: dict[str, dict[str, Any]],
    by_type: defaultdict[str, dict[str, dict[str, Any]]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    for claim_id, claim in claims.items():
        target_id = claim.get("materializedTargetId")
        disposition = claim.get("disposition")
        claim_kind = claim.get("claimKind")
        if disposition == "established-and-mapped" and not target_id:
            errors.append(f"established claim has no materialized target: {claim_id}")
        if not target_id:
            continue
        if disposition != "established-and-mapped":
            errors.append(f"non-established claim materializes a target: {claim_id}")
        if claim.get("proposedTargetId") not in (None, target_id):
            errors.append(f"claim target differs from proposed target: {claim_id}")
        target_type = "physical-printing" if claim_kind == "physical-printing" else "card-release"
        if target_id not in by_type[target_type]:
            errors.append(f"claim target is missing: {claim_id} -> {target_type}:{target_id}")
        if (target_type, target_id) not in relations[("candidate-claim", claim_id, "materializes")]:
            errors.append(f"claim materialization edge is missing: {claim_id} -> {target_id}")
        permitted_evidence = {"confirmed"}
        if target_type == "physical-printing":
            permitted_evidence.add("observed")
        if claim.get("evidenceStatus") not in permitted_evidence:
            errors.append(f"claim lacks permitted positive evidence: {claim_id}")


def _validate_finish_candidates(
    errors: list[str],
    claims: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:

    # Collector-facing finish candidates stay non-materializing, but they must name
    # the one release they propose a treatment for.  This prevents a consumer from
    # repeating the lossy legacy set/number/language join.
    for claim_id, claim in claims.items():
        if claim.get("sourceKind") != "finish-printing-record" \
                or claim.get("disposition") != "candidate-needs-evidence":
            continue
        release_id = claim.get("proposedCardReleaseId")
        if release_id not in releases:
            errors.append(f"finish candidate has no exact card release: {claim_id}")
        if relations[("candidate-claim", claim_id, "proposes-for")] != [
            ("card-release", release_id)
        ]:
            errors.append(f"finish candidate release edge is missing or non-unique: {claim_id}")


def _validate_claims(
    errors: list[str],
    by_type: defaultdict[str, dict[str, dict[str, Any]]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    claims = by_type["candidate-claim"]
    releases = by_type["card-release"]
    printings = by_type["physical-printing"]
    specimen_claim_ids = {
        str(claim.get("sourceId")) for claim in claims.values()
        if claim.get("sourceKind") == "specimen-observation"
    }
    _validate_claim_conflicts(errors, claims, printings, specimen_claim_ids)
    _validate_claim_materialization(errors, claims, by_type, relations)
    _validate_finish_candidates(errors, claims, releases, relations)
    return claims, releases, printings

# Card-release/work/edition identity invariants.
def _validate_work_index(
    errors: list[str],
    works: dict[str, dict[str, Any]],
) -> dict[str, tuple[str, dict[str, Any]]]:
    works_by_key: dict[str, tuple[str, dict[str, Any]]] = {}
    for work_id, work in works.items():
        if work.get("workId") != work_id:
            errors.append(f"work payload id mismatch: {work_id}")
        card_key = work.get("cardKey")
        if not isinstance(card_key, str) or not card_key:
            errors.append(f"work has no cardKey: {work_id}")
        elif card_key in works_by_key and works_by_key[card_key][1] is not work:
            errors.append(f"duplicate Work cardKey: {card_key}")
        else:
            # The entity index is authoritative for relation targets.  The
            # payload workId is checked above but never used to derive an edge.
            works_by_key[card_key] = (work_id, work)
    return works_by_key


def _validate_explicit_equivalence(
    errors: list[str],
    release_id: str,
    expected_work_id: str | None,
    assertions: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    matching_assertions = []
    for assertion_id, assertion in assertions.items():
        if (
            assertion.get("fromId") != release_id
            or assertion.get("toId") != expected_work_id
        ):
            continue
        assertion_relates = relations[("equivalence-assertion", assertion_id, "relates")]
        if sorted(assertion_relates) == sorted([
            ("card-release", release_id), ("work", expected_work_id)
        ]):
            matching_assertions.append(assertion_id)
    if not matching_assertions:
        errors.append(
            "mapped-by-explicit-equivalence card release lacks a "
            f"matching equivalence assertion: {release_id}"
        )


def _validate_release_work_mappings(
    errors: list[str],
    releases: dict[str, dict[str, Any]],
    works_by_key: dict[str, tuple[str, dict[str, Any]]],
    assertions: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
    claims: dict[str, dict[str, Any]],
) -> None:
    mapping_by_release: dict[str, tuple[Any, Any]] = {}
    for release_id, release in releases.items():
        if release.get("cardReleaseId") != release_id:
            errors.append(f"card-release payload id mismatch: {release_id}")
        mapping_state = release.get("workMappingState")
        work_key = release.get("work")
        if release_id in ISSUE304_NEEDS_EXPLICIT_RELEASES \
                and mapping_state != "needs-explicit-equivalence":
            errors.append(f"issue #304 release has unexpected work mapping state: {release_id}")
        if mapping_state not in WORK_MAPPING_STATES:
            errors.append(f"card release has unknown work mapping state: {release_id}")
        elif mapping_state in WORK_REQUIRED_STATES:
            if not isinstance(work_key, str) or not work_key:
                errors.append(f"mapped card release has no Work relation: {release_id}")
            elif work_key not in works_by_key:
                errors.append(f"mapped card release Work does not resolve: {release_id}")
        elif mapping_state in WORK_EMPTY_STATES and work_key is not None:
            errors.append(f"unmapped card release carries a Work relation: {release_id}")
        card_release_id = release.get("cardReleaseId")
        previous_mapping = mapping_by_release.get(card_release_id)
        current_mapping = (mapping_state, work_key)
        if previous_mapping is not None and previous_mapping != current_mapping:
            errors.append(f"card release mapping is inconsistent: {card_release_id}")
        mapping_by_release[card_release_id] = current_mapping
        implements = relations[("card-release", release_id, "implements")]
        if mapping_state in WORK_REQUIRED_STATES:
            expected_work_id = works_by_key.get(work_key, (None, {}))[0] if isinstance(work_key, str) else None
            if implements != [("work", expected_work_id)]:
                errors.append(f"card release implements edge is missing or inconsistent: {release_id}")
            if mapping_state == "mapped-by-explicit-equivalence":
                _validate_explicit_equivalence(
                    errors, release_id, expected_work_id, assertions, relations
                )
        elif mapping_state in WORK_EMPTY_STATES and implements:
            errors.append(f"unmapped card release has an implements edge: {release_id}")

    # Every materialized card-release claim must be recorded by that release.
    for claim_id, claim in claims.items():
        target_id = claim.get("materializedTargetId")
        if target_id and claim.get("claimKind") == "card-release":
            if claim_id not in (releases.get(target_id, {}).get("establishingClaimIds") or []):
                errors.append(f"card release omits establishing claim: {target_id} -> {claim_id}")


def _validate_release_claim_refs(
    errors: list[str],
    release_id: str,
    release: dict[str, Any],
    claims: dict[str, dict[str, Any]],
) -> None:
    establishing = release.get("establishingClaimIds") or []
    if not establishing:
        errors.append(f"card release has no establishing claim: {release_id}")
    for claim_id in establishing:
        claim = claims.get(claim_id)
        if not claim:
            errors.append(f"card release establishing claim is missing: {release_id} -> {claim_id}")
            continue
        if (
            claim.get("claimKind") != "card-release"
            or claim.get("materializedTargetId") != release_id
            or claim.get("disposition") != "established-and-mapped"
            or claim.get("evidenceStatus") != "confirmed"
        ):
            errors.append(f"card release establishing claim is not positive: {release_id} -> {claim_id}")
    for claim_id in release.get("nonEstablishingClaimIds") or []:
        if claim_id not in claims:
            errors.append(f"card release non-establishing claim is missing: {release_id} -> {claim_id}")


def _validate_release_editions(
    errors: list[str],
    releases: dict[str, dict[str, Any]],
    editions: dict[str, dict[str, Any]],
    claims: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    for release_id, release in releases.items():
        edition_id = release.get("setEditionId")
        edition = editions.get(edition_id)
        if not edition:
            errors.append(f"card release has no set edition: {release_id}")
            continue
        belongs_to = relations[("card-release", release_id, "belongs-to")]
        if belongs_to != [("set-edition", edition_id)]:
            errors.append(f"card release edition edge is not one-to-one: {release_id}")
        edition_identity = edition.get("identity") if isinstance(edition.get("identity"), dict) else edition
        edition_catalogue = edition.get("catalogue") if isinstance(edition.get("catalogue"), dict) else edition
        for field in ("locality", "language", "script"):
            release_value = release.get(field)
            identity_value = edition_identity.get(field)
            catalogue_value = edition_catalogue.get(field)
            if not isinstance(release_value, str) or not release_value:
                errors.append(f"card release has no explicit {field}: {release_id}")
            if release_value != identity_value or identity_value != catalogue_value:
                errors.append(f"card release/edition {field} mismatch: {release_id}")
        known = release.get("localIdentifierKnown")
        has_set_code = release.get("localSetCode") is not None
        has_number = release.get("localNumber") is not None
        if not isinstance(known, bool) or has_set_code != has_number or known != has_set_code:
            errors.append(f"card release local identifier invariant failed: {release_id}")
        _validate_release_claim_refs(errors, release_id, release, claims)
    for release_id in ISSUE304_NEEDS_EXPLICIT_RELEASES - set(releases):
        errors.append(f"issue #304 release is missing: {release_id}")


def _validate_releases(
    errors: list[str],
    by_type: defaultdict[str, dict[str, dict[str, Any]]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
    claims: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
) -> None:
    works_by_key = _validate_work_index(errors, by_type["work"])
    _validate_release_work_mappings(
        errors, releases, works_by_key, by_type["equivalence-assertion"], relations, claims
    )
    _validate_release_editions(errors, releases, by_type["set-edition"], claims, relations)

# Physical-printing and legacy migration invariants.
def _validate_printings_and_migrations(
    errors: list[str],
    by_type: defaultdict[str, dict[str, dict[str, Any]]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
    claims: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    printings: dict[str, dict[str, Any]],
    dispositions: list[dict[str, Any]],
) -> dict[tuple[Any, Any], dict[str, Any]]:
    # Physical printings are classifications of an established card release and must
    # point back to their own positive establishing claim.
    for printing_id, printing in printings.items():
        if printing.get("physicalPrintingId") != printing_id:
            errors.append(f"physical-printing payload id mismatch: {printing_id}")
        card_release_id = printing.get("cardReleaseId")
        if card_release_id not in releases:
            errors.append(f"physical printing has no card release: {printing_id}")
        if relations[("physical-printing", printing_id, "realizes")] != [("card-release", card_release_id)]:
            errors.append(f"physical printing release edge is missing or non-unique: {printing_id}")
        claim_id = printing.get("establishingClaimId")
        claim = claims.get(claim_id)
        if not claim:
            errors.append(f"physical printing establishing claim is missing: {printing_id} -> {claim_id}")
        if relations[("physical-printing", printing_id, "established-by")] != [("candidate-claim", claim_id)]:
            errors.append(f"physical printing claim edge is missing or non-unique: {printing_id}")
        elif (
            claim.get("claimKind") != "physical-printing"
            or claim.get("materializedTargetId") != printing_id
            or claim.get("disposition") != "established-and-mapped"
            or claim.get("evidenceStatus") not in {"confirmed", "observed"}
        ):
            errors.append(f"physical printing establishing claim is not positive: {printing_id} -> {claim_id}")
        markings = printing.get("markings")
        if markings is not None and (
            not isinstance(markings, list)
            or any(
                not isinstance(marking, dict)
                or not isinstance(marking.get("kind"), str)
                or marking.get("role") not in MARKING_ROLES
                or not isinstance(marking.get("text"), str)
                for marking in markings
            )
        ):
            errors.append(f"physical printing markings are not role-structured: {printing_id}")

    # Candidate claims and legacy multi-target migrations must remain represented by
    # the migration interface, including every targetRefs entry.
    migration_by_key = {(row.get("sourceKind"), row.get("sourceId")): row for row in dispositions}
    for claim_id, claim in claims.items():
        key = (claim.get("sourceKind"), claim.get("sourceId"))
        migration = migration_by_key.get(key)
        if not migration:
            errors.append(f"candidate claim has no migration disposition: {claim_id}")
        elif (
            migration.get("disposition") != claim.get("disposition")
            or migration.get("targetRef") != claim.get("materializedTargetId")
        ):
            errors.append(f"candidate claim/migration mismatch: {claim_id}")
    for migration in dispositions:
        if migration.get("sourceKind") not in {"legacy-cardmarket-product", "legacy-issue-rekey"}:
            continue
        refs = migration.get("targetRefs") or ([] if migration.get("targetRef") is None else [migration["targetRef"]])
        if any(ref not in releases for ref in refs):
            errors.append(f"migration targetRefs contain unknown release: {migration.get('sourceId')}")
    return migration_by_key

# Load append-only identity inputs once.
def _load_identity_inputs(
    identity_inputs: dict[str, Any] | None,
    errors: list[str],
    claims: dict[str, dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[tuple[str, str], dict[str, dict[str, Any]]],
    dict[tuple[str, str], tuple[str, str | None, str | None]],
]:
    identity_inputs = identity_inputs or {}

    def read_identity_input(key: str, relative: str, fallback: Any) -> Any:
        if key in identity_inputs:
            return identity_inputs[key]
        try:
            return json.loads((ROOT / relative).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            errors.append(f"cannot read identity input {relative}: {error}")
            return fallback

    units_raw = read_identity_input("units", "verification/units.json", [])
    codecards_raw = read_identity_input("codecards", "verification/excluded_codecards.json", [])
    finishes_raw = read_identity_input("finishes", "verification/finish_units.json", {"units": []})
    source_first_raw = read_identity_input(
        "source_first", "verification/source_first_prints.json", {"prints": []}
    )
    specimens_raw = read_identity_input("specimens", "verification/specimens.json", {"specimens": []})
    rekeys_raw = read_identity_input(
        "rekeys", "verification/legacy_issue_rekeys.json", {"questionSets": []}
    )
    units = units_raw if isinstance(units_raw, list) else []
    codecards = codecards_raw if isinstance(codecards_raw, list) else []
    finish_units = finishes_raw.get("units", []) if isinstance(finishes_raw, dict) else []
    source_first = source_first_raw.get("prints", []) if isinstance(source_first_raw, dict) else []
    specimens = specimens_raw.get("specimens", []) if isinstance(specimens_raw, dict) else []
    claims_by_source = {(row.get("sourceKind"), row.get("sourceId")): row for row in claims.values()}
    expected_claims: dict[tuple[str, str], tuple[str, str | None, str | None]] = {}
    return units, codecards, finish_units, source_first, specimens, rekeys_raw, claims_by_source, expected_claims

# Identity input claim accounting and reviewed positive evidence.
def _expect_identity_claim(
    errors: list[str],
    expected_claims: dict[tuple[str, str], tuple[str, str | None, str | None]],
    source_kind: str,
    source_id: Any,
    evidence_status: str,
    disposition: str | None,
    source_record: str | None,
) -> None:
    key = (source_kind, str(source_id))
    if key in expected_claims:
        errors.append(f"duplicate identity input claim: {source_kind}:{source_id}")
    expected_claims[key] = (evidence_status, disposition, source_record)


def _collect_identity_claim_inputs(
    errors: list[str],
    by_type: defaultdict[str, dict[str, dict[str, Any]]],
    units: list[dict[str, Any]],
    codecards: list[dict[str, Any]],
    finish_units: list[dict[str, Any]],
    source_first: list[dict[str, Any]],
    specimens: list[dict[str, Any]],
    expected_claims: dict[tuple[str, str], tuple[str, str | None, str | None]],
) -> tuple[
    dict[str, tuple[dict[str, Any], str]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    for unit in units:
        status = unit.get("status")
        disposition = {
            "confirmed": "established-and-mapped",
            "contradicted": "bounded-contradicted",
        }.get(status)
        _expect_identity_claim(
            errors, expected_claims, "legacy-language-unit", unit.get("unitId"),
            status, disposition, unit.get("sourceUrl"),
        )
    for unit in codecards:
        _expect_identity_claim(
            errors, expected_claims, "legacy-code-card-unit", unit.get("unitId"),
            "out-of-scope-product", "positively-excluded", None,
        )

    finish_printings: dict[str, tuple[dict[str, Any], str]] = {}
    for finish_unit in finish_units:
        finish_unit_id = finish_unit.get("finishUnitId")
        for printing in finish_unit.get("printings", []):
            printing_id = printing.get("printingId")
            finish_printings[str(printing_id)] = (printing, str(finish_unit_id))
            status = printing.get("verificationStatus")
            disposition = "established-and-mapped" if status == "confirmed" else "candidate-needs-evidence"
            _expect_identity_claim(
                errors, expected_claims, "finish-printing-record", printing_id,
                status, disposition, None,
            )
    source_first_prints = {str(row.get("printId")): row for row in source_first}
    for row in source_first:
        _expect_identity_claim(
            errors, expected_claims, "source-first-record", row.get("printId"),
            "confirmed", "established-and-mapped", row.get("sourceUrl"),
        )
    observed_specimens = {
        str(row.get("specimenId")): row for row in specimens if row.get("physicalObservation")
    }
    for row in observed_specimens.values():
        _expect_identity_claim(
            errors, expected_claims, "specimen-observation", row.get("specimenId"),
            "observed", None, None,
        )
    reviewed_source_printings: dict[str, dict[str, Any]] = {}
    for source_id, source in by_type["set-source-record"].items():
        evidence = (source.get("raw") or {}).get("physicalPrintingEvidence")
        if not evidence:
            continue
        reviewed_source_printings[source_id] = evidence
        _expect_identity_claim(
            errors, expected_claims, "reviewed-positive-evidence", source_id,
            "confirmed", "established-and-mapped", evidence.get("sourceUrl"),
        )
    return finish_printings, source_first_prints, observed_specimens, reviewed_source_printings


def _validate_identity_claim_accounting(
    errors: list[str],
    claims_by_source: dict[tuple[str, Any], dict[str, Any]],
    expected_claims: dict[tuple[str, str], tuple[str, str | None, str | None]],
) -> None:

    actual_claim_keys = set(claims_by_source)
    if actual_claim_keys != set(expected_claims):
        errors.append("identity input claims and graph candidate claims differ")
    for key, (expected_status, expected_disposition, expected_source_record) in expected_claims.items():
        claim = claims_by_source.get(key)
        if not claim:
            continue
        if claim.get("evidenceStatus") != expected_status:
            errors.append(f"identity claim evidence is stale: {key[0]}:{key[1]}")
        if expected_disposition is not None and claim.get("disposition") != expected_disposition:
            errors.append(f"identity claim disposition is stale: {key[0]}:{key[1]}")
        if expected_source_record != claim.get("sourceRecord"):
            errors.append(f"identity claim source is stale: {key[0]}:{key[1]}")

def _validate_reviewed_positive_evidence(
    errors: list[str],
    reviewed_source_printings: dict[str, dict[str, Any]],
    claims_by_source: dict[tuple[str, Any], dict[str, Any]],
    printings: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    source_records: dict[str, dict[str, Any]],
) -> None:
    for source_id, evidence in reviewed_source_printings.items():
        claim = claims_by_source.get(("reviewed-positive-evidence", source_id))
        physical = printings.get((claim or {}).get("materializedTargetId"))
        release = releases.get((physical or {}).get("cardReleaseId"))
        source = source_records[source_id]
        if not physical or not release:
            errors.append(f"reviewed physical-printing evidence is not materialized: {source_id}")
            continue
        for field in (
            "cardReleaseId", "finish", "edition", "foilPattern", "markings",
            "distribution", "cardSize", "specimenIds",
        ):
            if physical.get(field) != evidence.get(field):
                errors.append(f"reviewed physical-printing evidence is stale: {source_id}:{field}")
        if source_id not in (physical.get("sourceRecordIds") or []):
            errors.append(f"reviewed physical printing omits its source record: {source_id}")
        if evidence.get("positiveOnly") is not True \
                or evidence.get("completenessClaim") is not False \
                or not evidence.get("basis"):
            errors.append(f"reviewed physical-printing evidence scope is incomplete: {source_id}")
        if (source.get("raw") or {}).get("locality") != release.get("locality"):
            errors.append(f"reviewed physical-printing evidence locality differs: {source_id}")


def _validate_identity_claims(
    errors: list[str],
    by_type: defaultdict[str, dict[str, dict[str, Any]]],
    claims: dict[str, dict[str, Any]],
    printings: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    units: list[dict[str, Any]],
    codecards: list[dict[str, Any]],
    finish_units: list[dict[str, Any]],
    source_first: list[dict[str, Any]],
    specimens: list[dict[str, Any]],
    claims_by_source: dict[tuple[str, Any], dict[str, Any]],
    expected_claims: dict[tuple[str, str], tuple[str, str | None, str | None]],
) -> tuple[
    dict[str, tuple[dict[str, Any], str]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    (
        finish_printings, source_first_prints, observed_specimens, reviewed_source_printings,
    ) = _collect_identity_claim_inputs(
        errors, by_type, units, codecards, finish_units, source_first, specimens, expected_claims
    )
    _validate_identity_claim_accounting(errors, claims_by_source, expected_claims)
    _validate_reviewed_positive_evidence(
        errors, reviewed_source_printings, claims_by_source, printings, releases,
        by_type["set-source-record"],
    )
    return finish_printings, source_first_prints, observed_specimens, reviewed_source_printings

def _matches_legacy_identity_alias(
    unit: dict[str, Any], release: dict[str, Any],
) -> bool:
    return any(
        _identity_value("setCode", unit.get("setCode"))
        == _identity_value("setCode", alias[0])
        and _identity_value("number", unit.get("number"))
        == _identity_value("number", alias[1])
        for alias in release.get("legacyIdentityAliases") or []
    )


def _identity_projection_field_matches(
    unit: dict[str, Any],
    release: dict[str, Any],
    input_field: str,
    release_field: str,
    legacy_identity_matches: bool,
) -> bool:
    if input_field in {"setCode", "number"} and legacy_identity_matches:
        return True
    return _identity_value(input_field, unit.get(input_field)) == _identity_value(
        input_field, release.get(release_field)
    )


# Identity input projections stay aligned with graph nodes.
def _validate_identity_projections(
    errors: list[str],
    units: list[dict[str, Any]],
    claims_by_source: dict[tuple[str, Any], dict[str, Any]],
    printings: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    finish_printings: dict[str, tuple[dict[str, Any], str]],
    source_first_prints: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    units_by_id = {str(row.get("unitId")): row for row in units}
    for unit_id, unit in units_by_id.items():
        claim = claims_by_source.get(("legacy-language-unit", unit_id))
        target_id = claim.get("materializedTargetId") if claim else None
        if not target_id:
            continue
        release = releases.get(target_id)
        if not release:
            errors.append(f"identity claim target release is missing: {unit_id}")
            continue
        set_field = "localSetCode" if release.get("localIdentifierKnown") else "viaLegacySetCode"
        number_field = "localNumber" if release.get("localIdentifierKnown") else "viaLegacyNumber"
        legacy_identity_matches = _matches_legacy_identity_alias(unit, release)
        for input_field, release_field in (
            ("language", "language"), ("setCode", set_field), ("number", number_field),
            ("cardKey", "work"),
        ):
            if not _identity_projection_field_matches(
                unit, release, input_field, release_field, legacy_identity_matches,
            ):
                errors.append(f"identity release is stale: {unit_id}:{input_field}")

    for print_id, (printing, finish_unit_id) in finish_printings.items():
        claim = claims_by_source.get(("finish-printing-record", print_id))
        if not claim or not claim.get("materializedTargetId"):
            continue
        physical = printings.get(claim["materializedTargetId"])
        if not physical:
            errors.append(f"finish printing target is missing: {print_id}")
            continue
        for field in ("finish", "edition", "foilPattern", "markings", "distribution", "cardSize"):
            if physical.get(field) != printing.get(field):
                errors.append(f"finish printing is stale: {print_id}:{field}")
        if physical.get("sourceFinishUnitId") != finish_unit_id or physical.get("sourcePrintingId") != print_id:
            errors.append(f"finish printing provenance is stale: {print_id}")

    for print_id, row in source_first_prints.items():
        claim = claims_by_source.get(("source-first-record", print_id))
        target_id = claim.get("materializedTargetId") if claim else None
        release = releases.get(target_id)
        if not release:
            errors.append(f"source-first release target is missing: {print_id}")
            continue
        for input_field, release_field in (
            ("locality", "locality"), ("language", "language"), ("script", "script"),
            ("localSetCode", "localSetCode"), ("localNumber", "localNumber"),
        ):
            if _normalized(row.get(input_field)) != _normalized(release.get(release_field)):
                errors.append(f"source-first release is stale: {print_id}:{input_field}")
    return units_by_id

# Same-work and reviewed re-key invariants.
def _build_rekey_expectations(
    errors: list[str],
    rekeys_raw: dict[str, Any],
    units_by_id: dict[str, dict[str, Any]],
    claims_by_source: dict[tuple[str, Any], dict[str, Any]],
    releases: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    # Same-work/re-key decisions are another reviewed identity input.  They drive both
    # equivalence assertions and the one-to-many migration targetRefs contract.
    question_sets = rekeys_raw.get("questionSets", []) if isinstance(rekeys_raw, dict) else []
    expected_assertions: dict[str, dict[str, Any]] = {}
    expected_rekeys: dict[str, dict[str, Any]] = {}
    for question_set in question_sets:
        issue_number = question_set.get("issueNumber")
        default_disposition = question_set.get("defaultDisposition")
        legacy_ids = {str(unit_id) for unit_id in question_set.get("legacyUnitIds", [])}
        for legacy_id in legacy_ids:
            if legacy_id in expected_rekeys:
                errors.append(f"duplicate re-key question scope: {legacy_id}")
            expected_rekeys[legacy_id] = {
                "issueNumber": issue_number,
                "defaultDisposition": default_disposition,
                "targets": [],
            }
        for mapping in question_set.get("mappings", []):
            legacy_id = str(mapping.get("legacyUnitId"))
            source_id = str(mapping.get("sourceFirstRecordId"))
            if legacy_id not in legacy_ids:
                errors.append(f"re-key mapping is outside its question scope: {legacy_id}")
                continue
            claim = claims_by_source.get(("source-first-record", source_id))
            target_id = claim.get("materializedTargetId") if claim else None
            release = releases.get(target_id)
            if not release or not target_id:
                errors.append(f"re-key source-first target is missing: {legacy_id}:{source_id}")
                continue
            expected_rekeys[legacy_id]["targets"].append(target_id)
            assertion_id = f"ASSERT:same-work:{legacy_id}:{source_id}"
            legacy_unit = units_by_id.get(legacy_id)
            expected_card_key = legacy_unit.get("cardKey") if legacy_unit else None
            if not isinstance(expected_card_key, str) or not expected_card_key:
                errors.append(f"re-key legacy unit has no canonical cardKey: {legacy_id}")
            expected_assertions[assertion_id] = {
                "assertionId": assertion_id,
                "assertionType": mapping.get("assertionType"),
                "fromId": target_id,
                # The legacy unit is an independent reviewed input.  Never
                # derive the expected Work from the mutable release payload.
                "toId": f"WORK:{expected_card_key}" if expected_card_key else None,
                "legacyUnitId": legacy_id,
                "sourceFirstRecordId": source_id,
                "assertedBy": mapping.get("assertedBy"),
                "assertedAt": mapping.get("assertedAt"),
                "evidenceUrl": mapping.get("evidenceUrl"),
                "evidence": mapping.get("evidence"),
                "destructiveMergeAllowed": False,
            }
    return expected_assertions, expected_rekeys


def _validate_rekey_assertions(
    errors: list[str],
    expected_assertions: dict[str, dict[str, Any]],
    graph_assertions: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    works: dict[str, dict[str, Any]],
) -> None:
    if set(graph_assertions) != set(expected_assertions):
        errors.append("re-key decisions and graph equivalence assertions differ")
    for assertion_id, expected in expected_assertions.items():
        assertion = graph_assertions.get(assertion_id)
        if not assertion:
            continue
        if any(assertion.get(field) != value for field, value in expected.items()):
            errors.append(f"re-key equivalence assertion is stale: {assertion_id}")
        if assertion.get("fromId") not in releases or assertion.get("toId") not in works:
            errors.append(f"re-key equivalence target is invalid: {assertion_id}")


def _validate_rekey_release_mappings(
    errors: list[str],
    expected_assertions: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    works: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    expected_equivalence_by_release: defaultdict[str, list[tuple[str, str | None]]] = defaultdict(list)
    for assertion_id, expected in expected_assertions.items():
        expected_equivalence_by_release[expected["fromId"]].append(
            (assertion_id, expected.get("toId"))
        )
    for release_id, expected in expected_equivalence_by_release.items():
        release = releases.get(release_id)
        if not release:
            continue
        if release.get("workMappingState") != "mapped-by-explicit-equivalence":
            errors.append(
                "re-keyed release must retain mapped-by-explicit-equivalence state: "
                f"{release_id}"
            )
    for release_id, release in releases.items():
        if release.get("workMappingState") != "mapped-by-explicit-equivalence":
            continue
        expected = expected_equivalence_by_release.get(release_id, [])
        expected_work_id = _canonical_rekey_work_id(errors, release_id, expected)
        if expected_work_id is None:
            continue
        expected_work = works.get(expected_work_id)
        expected_card_key = expected_work.get("cardKey") if expected_work else None
        if release.get("work") != expected_card_key:
            errors.append(f"mapped-by-explicit-equivalence release Work is not canonical: {release_id}")
        if relations[("card-release", release_id, "implements")] != [("work", expected_work_id)]:
            errors.append(f"mapped-by-explicit-equivalence implements edge is not canonical: {release_id}")
        _validate_rekey_assertion_edges(
            errors, release_id, expected_work_id, expected, relations
        )


def _validate_rekey_assertion_edges(
    errors: list[str],
    release_id: str,
    expected_work_id: str,
    expected: list[tuple[str, str | None]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    targets = sorted([("card-release", release_id), ("work", expected_work_id)])
    for assertion_id, _ in expected:
        if sorted(relations[("equivalence-assertion", assertion_id, "relates")]) != targets:
            errors.append(
                "mapped-by-explicit-equivalence assertion edge is not canonical: "
                f"{release_id}:{assertion_id}"
            )


def _canonical_rekey_work_id(
    errors: list[str], release_id: str, expected: list[tuple[str, str | None]],
) -> str | None:
    if not expected:
        errors.append(
            "mapped-by-explicit-equivalence release lacks a canonical re-key: "
            f"{release_id}"
        )
        return None
    expected_work_ids = {work_id for _, work_id in expected}
    if len(expected_work_ids) != 1:
        errors.append(
            "mapped-by-explicit-equivalence release has conflicting canonical re-keys: "
            f"{release_id}"
        )
        return None
    return next(iter(expected_work_ids))


def _validate_rekey_migrations(
    errors: list[str],
    expected_rekeys: dict[str, dict[str, Any]],
    migration_by_key: dict[tuple[Any, Any], dict[str, Any]],
) -> None:
    for legacy_id, expected in expected_rekeys.items():
        migration = migration_by_key.get(("legacy-issue-rekey", legacy_id))
        targets = expected["targets"]
        expected_disposition = "linked-local-counterpart" if targets else expected["defaultDisposition"]
        if not migration or migration.get("disposition") != expected_disposition                 or migration.get("targetRefs") != targets                 or migration.get("targetRef") != (targets[0] if targets else None)                 or migration.get("reason") != f"issue #{expected['issueNumber']} re-key":
            errors.append(f"re-key migration disposition is stale: {legacy_id}")


def _validate_rekeys(
    errors: list[str],
    rekeys_raw: dict[str, Any],
    units_by_id: dict[str, dict[str, Any]],
    claims_by_source: dict[tuple[str, Any], dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    by_type: defaultdict[str, dict[str, dict[str, Any]]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
    migration_by_key: dict[tuple[Any, Any], dict[str, Any]],
) -> None:
    expected_assertions, expected_rekeys = _build_rekey_expectations(
        errors, rekeys_raw, units_by_id, claims_by_source, releases
    )
    _validate_rekey_assertions(
        errors, expected_assertions, by_type["equivalence-assertion"], releases, by_type["work"]
    )
    _validate_rekey_release_mappings(
        errors, expected_assertions, releases, by_type["work"], relations
    )
    _validate_rekey_migrations(errors, expected_rekeys, migration_by_key)

# Specimen observation and physical-printing alignment.
def _validate_unmaterialized_specimen(
    errors: list[str],
    specimen_id: str,
    specimen: dict[str, Any],
    claim: dict[str, Any] | None,
    printings: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    edge_keys: list[tuple[Any, ...]],
) -> None:
    if specimen.get("physicalObservation", {}).get("coversMultipleCards"):
        return
    provenance_target = claim.get("provenanceTargetId") if claim else None
    corroborated = claim.get("corroboratedTargetId") if claim else None
    target_id = provenance_target or corroborated
    if not target_id:
        return
    physical = printings.get(target_id)
    if not physical:
        errors.append(f"specimen evidence target is missing: {specimen_id}")
    elif ("candidate-claim", claim["claimId"],
          "provenance" if provenance_target else "corroborates",
          "physical-printing", target_id) not in edge_keys:
        errors.append(f"specimen evidence edge is missing: {specimen_id}")
    else:
        observation = specimen.get("physicalObservation", {})
        for field in ("finish", "edition", "foilPattern", "cardSize"):
            if not specimen_observation_field_matches(observation, physical, field):
                errors.append(f"specimen printing is stale: {specimen_id}:{field}")
        if (physical.get("markings") or []) != specimen_markings(observation):
            errors.append(f"specimen printing is stale: {specimen_id}:markings")
        release = releases.get(physical.get("cardReleaseId"))
        if release:
            set_field = "localSetCode" if release.get("localIdentifierKnown") else "viaLegacySetCode"
            number_field = "localNumber" if release.get("localIdentifierKnown") else "viaLegacyNumber"
            for input_field, release_field in (
                ("language", "language"), ("setCode", set_field), ("number", number_field),
            ):
                left = _number(specimen.get(input_field)) if input_field == "number"                     else str(specimen.get(input_field) or "")
                right = _number(release.get(release_field)) if input_field == "number"                     else str(release.get(release_field) or "")
                if left != right:
                    errors.append(f"specimen release identity is stale: {specimen_id}:{input_field}")


def _validate_materialized_specimen(
    errors: list[str],
    specimen_id: str,
    specimen: dict[str, Any],
    claim: dict[str, Any],
    printings: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
) -> None:
    physical = printings.get(claim["materializedTargetId"])
    observation = specimen.get("physicalObservation", {})
    if not physical:
        errors.append(f"specimen printing target is missing: {specimen_id}")
        return
    for field in ("finish", "edition", "foilPattern", "cardSize"):
        if not specimen_observation_field_matches(observation, physical, field):
            errors.append(f"specimen printing is stale: {specimen_id}:{field}")
    if (physical.get("markings") or []) != specimen_markings(observation):
        errors.append(f"specimen printing is stale: {specimen_id}:markings")
    if physical.get("basis") != observation.get("basis"):
        errors.append(f"specimen basis is stale: {specimen_id}")
    release = releases.get(physical.get("cardReleaseId"))
    if not release:
        return
    set_field = "localSetCode" if release.get("localIdentifierKnown") else "viaLegacySetCode"
    number_field = "localNumber" if release.get("localIdentifierKnown") else "viaLegacyNumber"
    for input_field, release_field in (
        ("language", "language"), ("setCode", set_field), ("number", number_field),
    ):
        left = _number(specimen.get(input_field)) if input_field == "number"             else _normalized(specimen.get(input_field))
        right = _number(release.get(release_field)) if input_field == "number"             else _normalized(release.get(release_field))
        if left != right:
            errors.append(f"specimen release identity is stale: {specimen_id}:{input_field}")


def _validate_specimens(
    errors: list[str],
    observed_specimens: dict[str, dict[str, Any]],
    claims_by_source: dict[tuple[str, Any], dict[str, Any]],
    printings: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    edge_keys: list[tuple[Any, ...]],
) -> None:
    for specimen_id, specimen in observed_specimens.items():
        claim = claims_by_source.get(("specimen-observation", specimen_id))
        if not claim or not claim.get("materializedTargetId"):
            _validate_unmaterialized_specimen(
                errors, specimen_id, specimen, claim, printings, releases, edge_keys
            )
            continue
        _validate_materialized_specimen(
            errors, specimen_id, specimen, claim, printings, releases
        )

# Append-only raw catalogue source boundary.
def _validate_source_registry(
    errors: list[str],
    source_registry: dict[str, Any] | None,
    by_type: defaultdict[str, dict[str, dict[str, Any]]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    # The raw catalogue registry is append-only.  Every raw record must have exactly
    # one graph source node and one disposition, and the graph node must preserve the
    # raw record byte-for-byte as parsed JSON.
    if source_registry is None:
        registry_path = ROOT / "verification" / "set_catalogue_sources.json"
        try:
            source_registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            errors.append(f"cannot read set catalogue source registry: {error}")
            source_registry = {}
    raw_records = source_registry.get("sourceRecords", []) if isinstance(source_registry, dict) else []
    raw_by_id = {row.get("sourceRecordId"): row for row in raw_records if isinstance(row, dict)}
    graph_sources = by_type["set-source-record"]
    graph_source_dispositions = by_type["set-source-disposition"]
    if set(raw_by_id) != set(graph_sources):
        errors.append("raw catalogue source records and graph source nodes differ")
    if set(raw_by_id) != set(graph_source_dispositions):
        errors.append("raw catalogue source records and graph dispositions differ")
    for source_id, raw_record in raw_by_id.items():
        if graph_sources.get(source_id) != raw_record:
            errors.append(f"graph source record is stale: {source_id}")
        disposition = graph_source_dispositions.get(source_id)
        if disposition and disposition.get("sourceRecordId") != source_id:
            errors.append(f"graph source disposition key mismatch: {source_id}")
    return graph_sources, graph_source_dispositions

# Locality, localization, and local-set catalogue invariants.
def _validate_localizations_and_sets(
    errors: list[str],
    localizations: dict[str, dict[str, Any]],
    local_sets: dict[str, dict[str, Any]],
    graph_sources: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    localization_tuples: set[tuple[str, str, str]] = set()
    for localization_id, localization in localizations.items():
        identity = (
            localization.get("locality"), localization.get("language"), localization.get("script")
        )
        if localization.get("localizationId") != localization_id \
                or not all(isinstance(value, str) and value for value in identity) \
                or len(localization.get("script", "")) != 4 \
                or not localization.get("languageId") \
                or not localization.get("languageTag") \
                or not localization.get("displayName") \
                or not isinstance(localization.get("displayOrder"), int) \
                or not localization.get("reviewedAt") \
                or not localization.get("decisionRef"):
            errors.append(f"localization identity is incomplete: {localization_id}")
        if identity in localization_tuples:
            errors.append(f"duplicate locality/language/script localization: {identity}")
        localization_tuples.add(identity)

    for local_set_id, local_set in local_sets.items():
        identified = bool(local_set.get("localCode") and local_set.get("sourceRecordIds"))
        unresolved = (
            local_set.get("state") == "needs-local-identifier"
            and local_set.get("localCode") is None
            and not local_set.get("observedNames")
            and not local_set.get("sourceRecordIds")
            and bool(local_set.get("evidenceRefs"))
            and bool(local_set.get("reviewedAt"))
            and bool(local_set.get("decisionRef"))
        )
        if local_set.get("localSetId") != local_set_id or not local_set.get("locality") \
                or not (identified or unresolved):
            errors.append(f"local set identity is incomplete: {local_set_id}")
        for source_id in local_set.get("sourceRecordIds") or []:
            if source_id not in graph_sources:
                errors.append(f"local set source is missing: {local_set_id} -> {source_id}")
            if ("set-source-record", source_id) not in relations[("local-set", local_set_id, "observed-by")]:
                errors.append(f"local set source edge is missing: {local_set_id} -> {source_id}")

# Set-edition identity and graph edges.
def _validate_editions(
    errors: list[str],
    editions: dict[str, dict[str, Any]],
    local_sets: dict[str, dict[str, Any]],
    localizations: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    for edition_id, edition in editions.items():
        identity = edition.get("identity") if isinstance(edition.get("identity"), dict) else edition
        catalogue = edition.get("catalogue") if isinstance(edition.get("catalogue"), dict) else None
        if edition.get("setEditionId") != edition_id or not identity.get("locality") \
                or not identity.get("language") or len(identity.get("script", "")) != 4:
            errors.append(f"set edition identity is incomplete: {edition_id}")
        if catalogue is None:
            errors.append(f"set edition has no catalogue parent: {edition_id}")
            continue
        local_set_id = catalogue.get("localSetId")
        localization_id = identity.get("localizationId")
        local_set = local_sets.get(local_set_id)
        if not local_set or catalogue.get("setEditionId") != edition_id \
                or identity.get("locality") != catalogue.get("locality") \
                or identity.get("language") != catalogue.get("language") \
                or identity.get("script") != catalogue.get("script") \
                or identity.get("localSetCode") != catalogue.get("localCode") \
                or catalogue.get("localizationId") != localization_id \
                or local_set.get("locality") != identity.get("locality"):
            errors.append(f"set edition catalogue locality/identity mismatch: {edition_id}")
        if relations[("set-edition", edition_id, "belongs-to")] != [("local-set", local_set_id)]:
            errors.append(f"set edition local-set edge is missing or non-unique: {edition_id}")
        if localization_id not in localizations or relations[
            ("set-edition", edition_id, "localized-as")
        ] != [("localization", localization_id)]:
            errors.append(f"set edition localization edge is missing or non-unique: {edition_id}")

# Release-event identity and scope.
def _validate_events(
    errors: list[str],
    events: dict[str, dict[str, Any]],
    local_sets: dict[str, dict[str, Any]],
    editions: dict[str, dict[str, Any]],
    graph_sources: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    for event_id, event in events.items():
        local_set_id = event.get("localSetId")
        source_id = event.get("sourceRecordId")
        if event.get("releaseEventId") != event_id or local_set_id not in local_sets \
                or not event.get("setEditionIds") or not event.get("marketScopes") \
                or not event.get("datePrecision") or source_id not in graph_sources:
            errors.append(f"release event is incomplete: {event_id}")
        else:
            local_set = local_sets[local_set_id]
            raw_locality = (graph_sources[source_id].get("raw") or {}).get("locality")
            if raw_locality and raw_locality != local_set.get("locality"):
                errors.append(f"release event source locality mismatch: {event_id}")
            if relations[("release-event", event_id, "belongs-to")] != [("local-set", local_set_id)]:
                errors.append(f"release event local-set edge is missing or non-unique: {event_id}")
            for edition_id in event.get("setEditionIds", []):
                if edition_id not in editions:
                    errors.append(f"release event edition is missing: {event_id} -> {edition_id}")
                if ("set-edition", edition_id) not in relations[("release-event", event_id, "supports")]:
                    errors.append(f"release event edition edge is missing: {event_id} -> {edition_id}")

# Finish-profile identity and scoped rules.
def _validate_profiles(
    errors: list[str],
    profiles: dict[str, dict[str, Any]],
    local_sets: dict[str, dict[str, Any]],
    editions: dict[str, dict[str, Any]],
    graph_sources: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    for profile_id, profile in profiles.items():
        source_id = profile.get("sourceRecordId")
        if profile.get("finishProfileId") != profile_id or profile.get("localSetId") not in local_sets \
                or not profile.get("languageScope") or not profile.get("rules") \
                or source_id not in graph_sources:
            errors.append(f"finish profile is incomplete: {profile_id}")
        if profile.get("closedWithinScope") and not (
            profile.get("closureScope") and profile.get("closureAuthority")
        ):
            errors.append(f"closed finish profile lacks closure scope/authority: {profile_id}")
        if ("set-source-record", source_id) not in relations[("finish-profile", profile_id, "supported-by")]:
            errors.append(f"finish profile source edge is missing: {profile_id}")
        for edition_id in profile.get("setEditionIds", []):
            if edition_id not in editions:
                errors.append(f"finish profile edition is missing: {profile_id} -> {edition_id}")
            if ("set-edition", edition_id) not in relations[("finish-profile", profile_id, "scoped-to")]:
                errors.append(f"finish profile edition edge is missing: {profile_id} -> {edition_id}")
        for rule in profile.get("rules", []):
            if not rule.get("finishProfileRuleId") or not rule.get("effect") \
                    or not rule.get("finish") or rule.get("sourceRecordId") != source_id \
                    or rule.get("sourceRecordId") not in graph_sources:
                errors.append(f"finish profile rule is incomplete: {profile_id}")

# Catalogue card-release references.
def _validate_refs(
    errors: list[str],
    refs: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    editions: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    for ref_id, ref in refs.items():
        card_release_id = ref.get("cardReleaseId")
        set_edition_id = ref.get("setEditionId")
        release = releases.get(card_release_id)
        if ref_id != card_release_id or not release or set_edition_id not in editions \
                or release.get("setEditionId") != set_edition_id:
            errors.append(f"catalogue release reference is invalid: {ref_id}")
        if ("card-release", card_release_id) not in relations[("catalogue-card-release-ref", ref_id, "references")]:
            errors.append(f"catalogue release reference edge is missing: {ref_id}")
        if ("set-edition", set_edition_id) not in relations[("catalogue-card-release-ref", ref_id, "belongs-to")]:
            errors.append(f"catalogue release edition edge is missing: {ref_id}")

# Source-native rarity claims.
def _validate_rarities(
    errors: list[str],
    rarities: dict[str, dict[str, Any]],
    releases: dict[str, dict[str, Any]],
    graph_sources: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    for rarity_id, rarity in rarities.items():
        source_id = rarity.get("sourceRecordId")
        release = releases.get(rarity.get("cardReleaseId"))
        source = graph_sources.get(source_id)
        if rarity.get("rarityClaimId") != rarity_id or not release or not source \
                or not rarity.get("sourceNativeValue") or not rarity.get("sourceVocabulary") \
                or rarity.get("sourceProvider") != source.get("provider"):
            errors.append(f"rarity claim is incomplete: {rarity_id}")
        elif (source.get("raw") or {}).get("locality") != release.get("locality"):
            errors.append(f"rarity claim source locality mismatch: {rarity_id}")
        if ("card-release", rarity.get("cardReleaseId")) not in relations[("rarity-claim", rarity_id, "asserts-rarity-for")]:
            errors.append(f"rarity claim release edge is missing: {rarity_id}")
        if ("set-source-record", source_id) not in relations[("rarity-claim", rarity_id, "observed-by")]:
            errors.append(f"rarity claim source edge is missing: {rarity_id}")

# Finish-profile claims.
def _validate_profile_claims(
    errors: list[str],
    profile_claims: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    refs: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    for claim_id, claim in profile_claims.items():
        profile_id = claim.get("finishProfileId")
        card_release_id = claim.get("cardReleaseId")
        if claim.get("profileFinishClaimId") != claim_id or profile_id not in profiles \
                or card_release_id not in refs or not claim.get("finish") \
                or claim.get("closesCompleteFinishList") is not False:
            errors.append(f"profile finish claim is incomplete: {claim_id}")
        if ("finish-profile", profile_id) not in relations[("profile-finish-claim", claim_id, "uses-profile")]:
            errors.append(f"profile finish profile edge is missing: {claim_id}")
        if ("card-release", card_release_id) not in relations[("profile-finish-claim", claim_id, "asserts-finish-for")]:
            errors.append(f"profile finish release edge is missing: {claim_id}")

# Catalogue aliases.
def _validate_aliases(
    errors: list[str],
    aliases: dict[str, dict[str, Any]],
    graph_sources: dict[str, dict[str, Any]],
    local_sets: dict[str, dict[str, Any]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    for alias_id, alias in aliases.items():
        local_set_id = alias.get("localSetId")
        if alias.get("aliasAssertionId") != alias_id or alias.get("sourceRecordId") not in graph_sources \
                or local_set_id not in local_sets or not alias.get("rawIdentifier") \
                or alias.get("reversibleProjection") is not True:
            errors.append(f"catalogue alias is incomplete: {alias_id}")
        if ("set-source-record", alias.get("sourceRecordId")) not in relations[("catalogue-alias-assertion", alias_id, "asserted-by")]:
            errors.append(f"catalogue alias source edge is missing: {alias_id}")
        if ("local-set", local_set_id) not in relations[("catalogue-alias-assertion", alias_id, "identifies")]:
            errors.append(f"catalogue alias target edge is missing: {alias_id}")

# Provider assertion edges.
def _validate_source_assertions(
    errors: list[str],
    source_assertions: dict[str, dict[str, Any]],
    graph_sources: dict[str, dict[str, Any]],
    by_type: defaultdict[str, dict[str, dict[str, Any]]],
    relations: defaultdict[tuple[str, str, str], list[tuple[str, str]]],
) -> None:
    assertion_targets = {
        "asserts-rarity-claim": ("rarityClaimId", "rarity-claim"),
        "asserts-local-set": ("localSetId", "local-set"),
        "asserts-set-edition": ("setEditionId", "set-edition"),
        "asserts-release-event": ("releaseEventId", "release-event"),
        "asserts-finish-profile": ("finishProfileId", "finish-profile"),
    }
    for assertion_id, assertion in source_assertions.items():
        kind = assertion.get("assertionKind")
        target_field, target_type = assertion_targets.get(kind, (None, None))
        target_id = assertion.get(target_field) if target_field else None
        if assertion.get("sourceAssertionId") != assertion_id or assertion.get("sourceRecordId") not in graph_sources \
                or not target_field or target_id not in by_type[target_type]:
            errors.append(f"source assertion is incomplete: {assertion_id}")
        if ("set-source-record", assertion.get("sourceRecordId")) not in relations[("source-assertion", assertion_id, "asserted-by")]:
            errors.append(f"source assertion source edge is missing: {assertion_id}")
        if (target_type, target_id) not in relations[("source-assertion", assertion_id, kind)]:
            errors.append(f"source assertion target edge is missing: {assertion_id}")

# Graph summary counts.
def _validate_summary(
    errors: list[str],
    graph: dict[str, Any],
    entities: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    dispositions: list[dict[str, Any]],
) -> None:
    summary = graph.get("summary", {})
    if summary.get("entities") != len(entities) or summary.get("edges") != len(edges):
        errors.append("graph summary does not match entity/edge counts")
    if summary.get("migrationInputs") != len(dispositions):
        errors.append("graph summary does not match migration disposition count")
    for entity_type, summary_key in (
        ("candidate-claim", "candidateClaims"),
        ("card-release", "cardReleases"),
        ("physical-printing", "physicalPrintings"),
        ("localization", "localizations"),
        ("set-source-record", "setSourceRecords"),
        ("set-source-disposition", "setSourceDispositions"),
    ):
        if summary.get(summary_key) != sum(row["entityType"] == entity_type for row in entities):
            errors.append(f"graph summary does not match {entity_type} count")

def validate(
    graph: dict[str, Any],
    source_registry: dict[str, Any] | None = None,
    identity_inputs: dict[str, Any] | None = None,
) -> list[str]:
    """Validate graph structure and the evidence/promotion invariants it carries.

    The graph is the committed authority, but the raw catalogue registry remains the
    append-only source of source-record identities.  Keeping that comparison here
    prevents a newly appended source record from silently disappearing at the migration
    boundary.
    """
    errors: list[str] = []
    entities, entity_set, by_type, edges, edge_keys, relations, dispositions = _validate_shape(
        graph, errors
    )
    claims, releases, printings = _validate_claims(errors, by_type, relations)
    _validate_releases(errors, by_type, relations, claims, releases)
    migration_by_key = _validate_printings_and_migrations(
        errors, by_type, relations, claims, releases, printings, dispositions
    )
    (
        units, codecards, finish_units, source_first, specimens, rekeys_raw,
        claims_by_source, expected_claims,
    ) = _load_identity_inputs(identity_inputs, errors, claims)
    (
        finish_printings, source_first_prints, observed_specimens, reviewed_source_printings,
    ) = _validate_identity_claims(
        errors, by_type, claims, printings, releases, units, codecards, finish_units,
        source_first, specimens, claims_by_source, expected_claims,
    )
    units_by_id = _validate_identity_projections(
        errors, units, claims_by_source, printings, releases, finish_printings, source_first_prints
    )
    _validate_rekeys(
        errors, rekeys_raw, units_by_id, claims_by_source, releases, by_type,
        relations, migration_by_key,
    )
    _validate_specimens(errors, observed_specimens, claims_by_source, printings, releases, edge_keys)
    graph_sources, graph_source_dispositions = _validate_source_registry(
        errors, source_registry, by_type
    )
    local_sets = by_type["local-set"]
    localizations = by_type["localization"]
    editions = by_type["set-edition"]
    events = by_type["release-event"]
    profiles = by_type["finish-profile"]
    refs = by_type["catalogue-card-release-ref"]
    rarities = by_type["rarity-claim"]
    profile_claims = by_type["profile-finish-claim"]
    aliases = by_type["catalogue-alias-assertion"]
    source_assertions = by_type["source-assertion"]
    _validate_localizations_and_sets(errors, localizations, local_sets, graph_sources, relations)
    _validate_editions(errors, editions, local_sets, localizations, relations)
    _validate_events(errors, events, local_sets, editions, graph_sources, relations)
    _validate_profiles(errors, profiles, local_sets, editions, graph_sources, relations)
    _validate_refs(errors, refs, releases, editions, relations)
    _validate_rarities(errors, rarities, releases, graph_sources, relations)
    _validate_profile_claims(errors, profile_claims, profiles, refs, relations)
    _validate_aliases(errors, aliases, graph_sources, local_sets, relations)
    _validate_source_assertions(errors, source_assertions, graph_sources, by_type, relations)
    _validate_summary(errors, graph, entities, edges, dispositions)
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate the committed snapshot")
    parser.add_argument("--write", action="store_true",
                        help="project physical evidence into the committed graph snapshot")
    args = parser.parse_args()
    if args.check and args.write:
        parser.error("--check and --write are mutually exclusive")
    if not OUTPUT.is_file():
        print("authoritative_graph.py: missing verification/authoritative_graph.json")
        return 1
    try:
        graph = read_graph()
        if args.write:
            graph = project_physical_evidence(graph)
            write_graph(graph)
        elif args.check:
            projected = project_physical_evidence(deepcopy(graph))
            if projected != graph:
                print("authoritative_graph.py: committed snapshot differs from fresh projection")
                return 1
        errors = validate(graph)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"authoritative_graph.py: invalid snapshot: {error}")
        return 1
    if errors:
        print("authoritative_graph.py: " + "; ".join(errors[:5]))
        return 1
    print(
        f"authoritative_graph.py: OK ({len(graph['entities'])} entities, "
        f"{len(graph['edges'])} edges, {len(graph['migrationDispositions'])} migration inputs)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

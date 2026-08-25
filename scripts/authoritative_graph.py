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
    return str(value or "").split("/", 1)[0]


def normalized_foil_pattern(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return FOIL_PATTERN_ALIASES.get(value.strip().casefold(), value)


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
    """Rebuild finish/specimen graph nodes from canonical generated inputs.

    The locality migration remains the graph's reviewed base. This projection owns only the
    physical-printing slice, so a new specimen changes one canonical input and this function
    deterministically refreshes claims, nodes, edges and dispositions.
    """
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
        unit_key = (str(unit.get("setCode") or ""), _number(unit.get("number")),
                    str(unit.get("language") or ""))
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
    kind = "edition-stamp" if str(text).casefold() == "editie 1" else "observed-marking"
    return [{
        "kind": kind,
        "role": observation.get("markingRole"),
        "text": text,
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

    # I2: only positive evidence may promote a claim into an existence-bearing node.
    claims = by_type["candidate-claim"]
    releases = by_type["card-release"]
    printings = by_type["physical-printing"]
    specimen_claim_ids = {
        str(claim.get("sourceId")) for claim in claims.values()
        if claim.get("sourceKind") == "specimen-observation"
    }
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

    # I3/I8: releases have one language-bearing edition and their local identifiers
    # remain explicit (legacy anchors cannot be promoted into local identifiers).
    editions = by_type["set-edition"]
    works = by_type["work"]
    works_by_key: dict[str, dict[str, Any]] = {}
    for work_id, work in works.items():
        card_key = work.get("cardKey")
        if not isinstance(card_key, str) or not card_key:
            errors.append(f"work has no cardKey: {work_id}")
        elif card_key in works_by_key and works_by_key[card_key] is not work:
            errors.append(f"duplicate Work cardKey: {card_key}")
        else:
            works_by_key[card_key] = work
    mapping_by_release: dict[str, tuple[Any, Any]] = {}
    for release_id, release in releases.items():
        if release.get("cardReleaseId") != release_id:
            errors.append(f"card-release payload id mismatch: {release_id}")
        mapping_state = release.get("workMappingState")
        work_key = release.get("work")
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
            expected_work_id = works_by_key.get(work_key, {}).get("workId") if isinstance(work_key, str) else None
            if implements != [("work", expected_work_id)]:
                errors.append(f"card release implements edge is missing or inconsistent: {release_id}")
        elif mapping_state in WORK_EMPTY_STATES and implements:
            errors.append(f"unmapped card release has an implements edge: {release_id}")
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

    # Every materialized card-release claim must be recorded by that release.  This
    # closes the opposite direction of the promotion invariant above.
    for claim_id, claim in claims.items():
        target_id = claim.get("materializedTargetId")
        if target_id and claim.get("claimKind") == "card-release":
            if claim_id not in (releases.get(target_id, {}).get("establishingClaimIds") or []):
                errors.append(f"card release omits establishing claim: {target_id} -> {claim_id}")

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

    # Candidate claims are projections of several append-only identity stores.  Keep
    # their keys and promotion-relevant fields accounted for here so a new confirmed
    # unit, finish printing, source-first record, or specimen cannot vanish while the
    # committed graph still passes its own summary checks.
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

    def expect_claim(
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

    for unit in units:
        status = unit.get("status")
        disposition = {
            "confirmed": "established-and-mapped",
            "contradicted": "bounded-contradicted",
        }.get(status)
        expect_claim("legacy-language-unit", unit.get("unitId"), status, disposition, unit.get("sourceUrl"))
    for unit in codecards:
        expect_claim("legacy-code-card-unit", unit.get("unitId"), "out-of-scope-product",
                     "positively-excluded", None)

    finish_printings: dict[str, tuple[dict[str, Any], str]] = {}
    for finish_unit in finish_units:
        finish_unit_id = finish_unit.get("finishUnitId")
        for printing in finish_unit.get("printings", []):
            printing_id = printing.get("printingId")
            finish_printings[str(printing_id)] = (printing, str(finish_unit_id))
            status = printing.get("verificationStatus")
            disposition = "established-and-mapped" if status == "confirmed" else "candidate-needs-evidence"
            expect_claim("finish-printing-record", printing_id, status, disposition, None)
    source_first_prints = {str(row.get("printId")): row for row in source_first}
    for row in source_first:
        expect_claim("source-first-record", row.get("printId"), "confirmed",
                     "established-and-mapped", row.get("sourceUrl"))
    observed_specimens = {
        str(row.get("specimenId")): row for row in specimens if row.get("physicalObservation")
    }
    for row in observed_specimens.values():
        expect_claim("specimen-observation", row.get("specimenId"), "observed", None, None)
    reviewed_source_printings: dict[str, dict[str, Any]] = {}
    for source_id, source in by_type["set-source-record"].items():
        evidence = (source.get("raw") or {}).get("physicalPrintingEvidence")
        if not evidence:
            continue
        reviewed_source_printings[source_id] = evidence
        expect_claim(
            "reviewed-positive-evidence", source_id, "confirmed",
            "established-and-mapped", evidence.get("sourceUrl"),
        )

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

    for source_id, evidence in reviewed_source_printings.items():
        claim = claims_by_source.get(("reviewed-positive-evidence", source_id))
        physical = printings.get((claim or {}).get("materializedTargetId"))
        release = releases.get((physical or {}).get("cardReleaseId"))
        source = by_type["set-source-record"][source_id]
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

    def normalized(value: Any) -> str:
        return "" if value is None else str(value)

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
        for input_field, release_field in (
            ("language", "language"), ("setCode", set_field), ("number", number_field),
            ("cardKey", "work"),
        ):
            if normalized(unit.get(input_field)) != normalized(release.get(release_field)):
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
            if normalized(row.get(input_field)) != normalized(release.get(release_field)):
                errors.append(f"source-first release is stale: {print_id}:{input_field}")

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
            expected_assertions[assertion_id] = {
                "assertionId": assertion_id,
                "assertionType": mapping.get("assertionType"),
                "fromId": target_id,
                "toId": f"WORK:{release.get('work')}" if release.get("work") else None,
                "legacyUnitId": legacy_id,
                "sourceFirstRecordId": source_id,
                "assertedBy": mapping.get("assertedBy"),
                "assertedAt": mapping.get("assertedAt"),
                "evidenceUrl": mapping.get("evidenceUrl"),
                "evidence": mapping.get("evidence"),
                "destructiveMergeAllowed": False,
            }
    graph_assertions = by_type["equivalence-assertion"]
    if set(graph_assertions) != set(expected_assertions):
        errors.append("re-key decisions and graph equivalence assertions differ")
    for assertion_id, expected in expected_assertions.items():
        assertion = graph_assertions.get(assertion_id)
        if not assertion:
            continue
        if any(assertion.get(field) != value for field, value in expected.items()):
            errors.append(f"re-key equivalence assertion is stale: {assertion_id}")
        if assertion.get("fromId") not in releases or assertion.get("toId") not in by_type["work"]:
            errors.append(f"re-key equivalence target is invalid: {assertion_id}")
    for legacy_id, expected in expected_rekeys.items():
        migration = migration_by_key.get(("legacy-issue-rekey", legacy_id))
        targets = expected["targets"]
        expected_disposition = "linked-local-counterpart" if targets else expected["defaultDisposition"]
        if not migration or migration.get("disposition") != expected_disposition \
                or migration.get("targetRefs") != targets \
                or migration.get("targetRef") != (targets[0] if targets else None) \
                or migration.get("reason") != f"issue #{expected['issueNumber']} re-key":
            errors.append(f"re-key migration disposition is stale: {legacy_id}")

    for specimen_id, specimen in observed_specimens.items():
        claim = claims_by_source.get(("specimen-observation", specimen_id))
        if not claim or not claim.get("materializedTargetId"):
            if specimen.get("physicalObservation", {}).get("coversMultipleCards"):
                continue
            provenance_target = claim.get("provenanceTargetId") if claim else None
            corroborated = claim.get("corroboratedTargetId") if claim else None
            target_id = provenance_target or corroborated
            if target_id:
                physical = printings.get(target_id)
                if not physical:
                    errors.append(f"specimen evidence target is missing: {specimen_id}")
                elif ("candidate-claim", claim["claimId"],
                      "provenance" if provenance_target else "corroborates",
                      "physical-printing", target_id) \
                        not in edge_keys:
                    errors.append(f"specimen evidence edge is missing: {specimen_id}")
                else:
                    observation = specimen.get("physicalObservation", {})
                    for field in ("finish", "edition", "foilPattern", "cardSize"):
                        if physical.get(field) != specimen_observation_value(observation, field):
                            errors.append(f"specimen printing is stale: {specimen_id}:{field}")
                    if (physical.get("markings") or []) != specimen_markings(observation):
                        errors.append(f"specimen printing is stale: {specimen_id}:markings")
                    release = releases.get(physical.get("cardReleaseId"))
                    if release:
                        set_field = "localSetCode" if release.get("localIdentifierKnown") else "viaLegacySetCode"
                        number_field = "localNumber" if release.get("localIdentifierKnown") else "viaLegacyNumber"
                        for input_field, release_field in (
                            ("language", "language"), ("setCode", set_field),
                            ("number", number_field),
                        ):
                            left = _number(specimen.get(input_field)) if input_field == "number" \
                                else str(specimen.get(input_field) or "")
                            right = _number(release.get(release_field)) if input_field == "number" \
                                else str(release.get(release_field) or "")
                            if left != right:
                                errors.append(f"specimen release identity is stale: {specimen_id}:{input_field}")
            continue
        physical = printings.get(claim["materializedTargetId"])
        observation = specimen.get("physicalObservation", {})
        if not physical:
            errors.append(f"specimen printing target is missing: {specimen_id}")
            continue
        for field in ("finish", "edition", "foilPattern", "cardSize"):
            if physical.get(field) != specimen_observation_value(observation, field):
                errors.append(f"specimen printing is stale: {specimen_id}:{field}")
        if (physical.get("markings") or []) != specimen_markings(observation):
            errors.append(f"specimen printing is stale: {specimen_id}:markings")
        if physical.get("basis") != observation.get("basis"):
            errors.append(f"specimen basis is stale: {specimen_id}")
        release = releases.get(physical.get("cardReleaseId"))
        if not release:
            continue
        set_field = "localSetCode" if release.get("localIdentifierKnown") else "viaLegacySetCode"
        number_field = "localNumber" if release.get("localIdentifierKnown") else "viaLegacyNumber"
        for input_field, release_field in (
            ("language", "language"), ("setCode", set_field), ("number", number_field),
        ):
            left = _number(specimen.get(input_field)) if input_field == "number" \
                else normalized(specimen.get(input_field))
            right = _number(release.get(release_field)) if input_field == "number" \
                else normalized(release.get(release_field))
            if left != right:
                errors.append(f"specimen release identity is stale: {specimen_id}:{input_field}")

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

    # Catalogue entities retain the old N9-N11 safety boundary: availability and
    # aliases decorate established identities, while source, locality and closure
    # semantics remain checked before the graph reaches SQLite consumers.
    local_sets = by_type["local-set"]
    localizations = by_type["localization"]
    events = by_type["release-event"]
    profiles = by_type["finish-profile"]
    refs = by_type["catalogue-card-release-ref"]
    rarities = by_type["rarity-claim"]
    profile_claims = by_type["profile-finish-claim"]
    aliases = by_type["catalogue-alias-assertion"]
    source_assertions = by_type["source-assertion"]

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

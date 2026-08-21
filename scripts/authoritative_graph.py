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
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "verification" / "authoritative_graph.json"
GRAPH_SCHEMA = "snoredex-authoritative-locality-graph"


def read_graph() -> dict[str, Any]:
    return json.loads(OUTPUT.read_text(encoding="utf-8"))


def _payloads(graph: dict[str, Any], entity_type: str) -> list[dict[str, Any]]:
    return [row["payload"] for row in graph["entities"] if row["entityType"] == entity_type]


def _graph_hash(graph: dict[str, Any]) -> str:
    body = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


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


def validate(
    graph: dict[str, Any],
    source_registry: dict[str, Any] | None = None,
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
    if meta.get("schemaVersion") != "1.0.0":
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

    # I3/I8: releases have one language-bearing edition and their local identifiers
    # remain explicit (legacy anchors cannot be promoted into local identifiers).
    editions = by_type["set-edition"]
    for release_id, release in releases.items():
        if release.get("cardReleaseId") != release_id:
            errors.append(f"card-release payload id mismatch: {release_id}")
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
    summary = graph.get("summary", {})
    if summary.get("entities") != len(entities) or summary.get("edges") != len(edges):
        errors.append("graph summary does not match entity/edge counts")
    if summary.get("migrationInputs") != len(dispositions):
        errors.append("graph summary does not match migration disposition count")
    for entity_type, summary_key in (
        ("candidate-claim", "candidateClaims"),
        ("card-release", "cardReleases"),
        ("physical-printing", "physicalPrintings"),
        ("set-source-record", "setSourceRecords"),
        ("set-source-disposition", "setSourceDispositions"),
    ):
        if summary.get(summary_key) != sum(row["entityType"] == entity_type for row in entities):
            errors.append(f"graph summary does not match {entity_type} count")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate the committed snapshot")
    parser.parse_args()
    if not OUTPUT.is_file():
        print("authoritative_graph.py: missing verification/authoritative_graph.json")
        return 1
    try:
        graph = read_graph()
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

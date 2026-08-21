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


def validate(graph: dict[str, Any]) -> list[str]:
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
    dispositions = graph.get("migrationDispositions", [])
    disposition_keys = [(row.get("sourceKind"), row.get("sourceId")) for row in dispositions]
    if len(disposition_keys) != len(set(disposition_keys)):
        errors.append("duplicate migration dispositions")
    for row in dispositions:
        refs = row.get("targetRefs")
        if refs is not None and row.get("targetRef") != (refs[0] if refs else None):
            errors.append(f"migration targetRef does not preserve targetRefs: {row.get('sourceId')}")
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

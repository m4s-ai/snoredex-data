#!/usr/bin/env python3
"""Regression checks for the #140 authoritative graph boundary."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from authoritative_graph import identity_view, validate  # noqa: E402


def main() -> None:
    graph = json.loads((ROOT / "verification/authoritative_graph.json").read_text(encoding="utf-8"))
    assert not validate(graph)
    meta = graph["meta"]
    assert meta["schema"] == "snoredex-authoritative-locality-graph"
    assert meta["schemaVersion"] == "1.0.0"
    assert meta["status"] == "authoritative-migrated"
    assert "inputs" not in meta

    entities = {(row["entityType"], row["entityId"]): row for row in graph["entities"]}
    edges = graph["edges"]
    edge_keys = {
        (row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"])
        for row in edges
    }
    assert len(entities) == graph["summary"]["entities"]
    assert len(edge_keys) == len(edges)
    assert graph["summary"]["candidateClaims"] > 0
    assert graph["summary"]["cardReleases"] > 0
    assert graph["summary"]["physicalPrintings"] > 0
    assert graph["summary"]["setSourceRecords"] == graph["summary"]["setSourceDispositions"]

    identity = identity_view(graph)
    migrations = {
        (row["sourceKind"], row["sourceId"]): row
        for row in graph["migrationDispositions"]
    }
    u0414 = migrations[("legacy-issue-rekey", "U0414")]
    assert u0414["targetRefs"] == [
        "RELEASE:TW:T-Chinese:AS5a:117/184:Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX",
        "RELEASE:TW:T-Chinese:SM-P:053:Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX",
    ]
    assert u0414["targetRef"] == u0414["targetRefs"][0]
    rekey = next(row for row in identity["reports"]["legacyIssueRekeys"][0]["rows"]
                 if row["legacyUnitId"] == "U0414")
    assert rekey["localCardReleaseIds"] == u0414["targetRefs"]

    with sqlite3.connect(ROOT / "snoredex.sqlite") as connection:
        target_ref, target_refs_json = connection.execute(
            "SELECT target_ref, target_refs_json "
            "FROM graph_migration_dispositions "
            "WHERE source_kind = 'legacy-issue-rekey' AND source_id = 'U0414'"
        ).fetchone()
    assert target_ref == u0414["targetRef"]
    assert json.loads(target_refs_json) == u0414["targetRefs"]
    print(
        "authoritative graph regression passed: "
        f"{len(entities)} entities, {len(edges)} edges, "
        f"{len(graph['migrationDispositions'])} dispositions"
    )


if __name__ == "__main__":
    main()

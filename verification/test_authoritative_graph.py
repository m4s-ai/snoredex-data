#!/usr/bin/env python3
"""Regression checks for the #140 authoritative graph boundary."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    graph = json.loads((ROOT / "verification/authoritative_graph.json").read_text(encoding="utf-8"))
    meta = graph["meta"]
    assert meta["schema"] == "snoredex-authoritative-locality-graph"
    assert meta["schemaVersion"] == "1.0.0"
    assert meta["status"] == "authoritative-migrated"

    entities = {(row["entityType"], row["entityId"]): row for row in graph["entities"]}
    assert len(entities) == graph["summary"]["entities"]
    edges = graph["edges"]
    assert len({(row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"])
                for row in edges}) == len(edges)
    for row in edges:
        assert (row["fromType"], row["fromId"]) in entities
        if row["toType"] != "node":
            assert (row["toType"], row["toId"]) in entities

    dispositions = graph["migrationDispositions"]
    keys = [(row["sourceKind"], row["sourceId"]) for row in dispositions]
    assert len(keys) == len(set(keys)) == graph["summary"]["migrationInputs"]
    assert all(row["disposition"] and row["reason"] for row in dispositions)
    assert graph["summary"]["candidateClaims"] > 0
    assert graph["summary"]["cardReleases"] > 0
    assert graph["summary"]["physicalPrintings"] > 0
    assert graph["summary"]["setSourceRecords"] == graph["summary"]["setSourceDispositions"]
    print(
        "authoritative graph regression passed: "
        f"{len(entities)} entities, {len(edges)} edges, {len(dispositions)} dispositions"
    )


if __name__ == "__main__":
    main()

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
    edge_keys = {
        (row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"])
        for row in edges
    }
    assert len({(row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"])
                for row in edges}) == len(edges)
    for row in edges:
        assert (row["fromType"], row["fromId"]) in entities
        if row["toType"] != "node":
            assert (row["toType"], row["toId"]) in entities
    assert not any(row["toType"] == "node" for row in edges)

    dispositions = graph["migrationDispositions"]
    keys = [(row["sourceKind"], row["sourceId"]) for row in dispositions]
    assert len(keys) == len(set(keys)) == graph["summary"]["migrationInputs"]
    assert all(row["disposition"] and row["reason"] for row in dispositions)
    assert graph["summary"]["candidateClaims"] > 0
    assert graph["summary"]["cardReleases"] > 0
    assert graph["summary"]["physicalPrintings"] > 0
    assert graph["summary"]["setSourceRecords"] == graph["summary"]["setSourceDispositions"]

    identity = json.loads(
        (ROOT / "verification/print_identity_dryrun.json").read_text(encoding="utf-8")
    )
    migrations = {
        (row["sourceKind"], row["sourceId"]): row for row in dispositions
    }
    for source_id, record in identity["legacyProductDispositions"].items():
        targets = list(record.get("cardReleaseIds") or [])
        migration = migrations[("legacy-cardmarket-product", source_id)]
        assert migration["targetRefs"] == targets
        assert migration["targetRef"] == (targets[0] if targets else None)
        product_id = f"LEGACYPRODUCT:{source_id}"
        assert ("legacy-cardmarket-product", product_id) in entities
        mapped = {
            row["toId"] for row in edges
            if row["fromType"] == "legacy-cardmarket-product"
            and row["fromId"] == product_id and row["relation"] == "maps-to"
        }
        assert mapped == set(targets)

    catalogue = json.loads(
        (ROOT / "verification/set_catalogue_dryrun.json").read_text(encoding="utf-8")
    )
    for row in catalogue["cardReleaseRefs"]:
        key = ("catalogue-card-release-ref", row["cardReleaseId"])
        assert key in entities
        assert (key[0], key[1], "references", "card-release", row["cardReleaseId"]) in edge_keys
        assert (key[0], key[1], "belongs-to", "set-edition", row["setEditionId"]) in edge_keys
    for row in catalogue["rarityClaims"]:
        key = ("rarity-claim", row["rarityClaimId"])
        assert (key[0], key[1], "asserts-rarity-for", "card-release", row["cardReleaseId"]) in edge_keys
        assert (key[0], key[1], "observed-by", "set-source-record", row["sourceRecordId"]) in edge_keys
    for row in catalogue["profileFinishClaims"]:
        key = ("profile-finish-claim", row["profileFinishClaimId"])
        assert (key[0], key[1], "uses-profile", "finish-profile", row["finishProfileId"]) in edge_keys
        assert (key[0], key[1], "asserts-finish-for", "card-release", row["cardReleaseId"]) in edge_keys
    for row in catalogue["finishProfiles"]:
        key = ("finish-profile", row["finishProfileId"])
        assert (key[0], key[1], "scoped-to", "local-set", row["localSetId"]) in edge_keys
        assert (key[0], key[1], "supported-by", "set-source-record", row["sourceRecordId"]) in edge_keys
        for edition_id in row.get("setEditionIds", []):
            assert (key[0], key[1], "scoped-to", "set-edition", edition_id) in edge_keys
    for row in catalogue["aliasAssertions"]:
        key = ("catalogue-alias-assertion", row["aliasAssertionId"])
        assert (key[0], key[1], "asserted-by", "set-source-record", row["sourceRecordId"]) in edge_keys
        target_type = "local-set" if row.get("localSetId") else "set-edition"
        target_id = row.get("localSetId") or row.get("setEditionId")
        assert target_id
        assert (key[0], key[1], row["relationship"], target_type, target_id) in edge_keys
    source_target_fields = (
        ("rarityClaimId", "rarity-claim"),
        ("localSetId", "local-set"),
        ("releaseEventId", "release-event"),
        ("setEditionId", "set-edition"),
        ("finishProfileId", "finish-profile"),
    )
    for row in catalogue["sourceAssertions"]:
        key = ("source-assertion", row["sourceAssertionId"])
        assert (key[0], key[1], "asserted-by", "set-source-record", row["sourceRecordId"]) in edge_keys
        field, target_type = next((item for item in source_target_fields if row.get(item[0])), (None, None))
        assert field
        assert (key[0], key[1], row["assertionKind"], target_type, row[field]) in edge_keys
    print(
        "authoritative graph regression passed: "
        f"{len(entities)} entities, {len(edges)} edges, {len(dispositions)} dispositions"
    )


if __name__ == "__main__":
    main()

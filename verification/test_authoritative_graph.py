#!/usr/bin/env python3
"""Regression checks for the #140 authoritative graph boundary."""

from __future__ import annotations

import json
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from authoritative_graph import identity_view, validate  # noqa: E402


def main() -> None:
    graph = json.loads((ROOT / "verification/authoritative_graph.json").read_text(encoding="utf-8"))
    assert not validate(graph)
    meta = graph["meta"]
    assert meta["schema"] == "snoredex-authoritative-locality-graph"
    assert meta["schemaVersion"] == "1.1.0"
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
    assert graph["summary"]["localizations"] == 16
    assert graph["summary"]["setSourceRecords"] == graph["summary"]["setSourceDispositions"]

    dutch_printings = {
        row["entityId"]: row["payload"]
        for row in graph["entities"]
        if row["entityType"] == "physical-printing"
        and row["entityId"] in {
            "PHYSICAL:F0167-P01", "PHYSICAL:F0167-P02",
            "PHYSICAL:F0174-P01", "PHYSICAL:F0174-P02",
        }
    }
    assert {
        printing_id: (row["finish"], row["edition"])
        for printing_id, row in dutch_printings.items()
    } == {
        "PHYSICAL:F0167-P01": ("holo", "1st Edition"),
        "PHYSICAL:F0167-P02": ("holo", "Unlimited"),
        "PHYSICAL:F0174-P01": ("non-holo", "1st Edition"),
        "PHYSICAL:F0174-P02": ("non-holo", "Unlimited"),
    }
    assert all(
        row["markings"] == ([{
            "kind": "edition-stamp", "text": "EDITIE 1", "role": "print-identity",
        }] if row["edition"] == "1st Edition" else [])
        for row in dutch_printings.values()
    )
    for specimen_id in ("SPEC-0040", "SPEC-0041", "SPEC-0042", "SPEC-0043", "SPEC-0044"):
        claim = entities[("candidate-claim", f"CLAIM:specimen:{specimen_id}")]["payload"]
        assert claim["evidenceStatus"] == "observed"
        assert claim["materializedTargetId"] is None
        assert claim["reason"].startswith("corroborates PHYSICAL:F")

    localizations = {
        row["payload"]["languageTag"]: row["payload"]
        for row in graph["entities"] if row["entityType"] == "localization"
    }
    assert localizations["es-ES"]["locality"] == "WEST"
    assert localizations["es-419"]["locality"] == "LATAM"
    assert localizations["pt"]["language"] == "Portuguese"

    unresolved_editions = [
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "set-edition"
        and row["payload"]["identity"]["state"] == "needs-local-identifier"
    ]
    assert unresolved_editions
    assert all(row["catalogue"]["localSetId"] for row in unresolved_editions)

    finish_candidate = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("sourceKind") == "finish-printing-record"
        and row["payload"].get("disposition") == "candidate-needs-evidence"
    )
    assert ("candidate-claim", finish_candidate["claimId"], "proposes-for", "card-release",
            finish_candidate["proposedCardReleaseId"]) in edge_keys

    # A contradicted claim must not be promotable merely by changing its disposition
    # and pointing it at an existing release.
    tampered = deepcopy(graph)
    tampered_claim = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("evidenceStatus") == "contradicted"
    )
    release_id = next(
        row["entityId"] for row in tampered["entities"]
        if row["entityType"] == "card-release"
    )
    tampered_claim["disposition"] = "established-and-mapped"
    tampered_claim["proposedTargetId"] = release_id
    tampered_claim["materializedTargetId"] = release_id
    assert any("positive evidence" in error for error in validate(tampered))

    # Appending to the raw registry without adding graph nodes/dispositions must fail
    # the cross-store accounting check.
    registry = json.loads((ROOT / "verification/set_catalogue_sources.json").read_text(encoding="utf-8"))
    extra = deepcopy(registry["sourceRecords"][0])
    extra["sourceRecordId"] = "SET-SRC-TEST-UNACCOUNTED"
    registry["sourceRecords"].append(extra)
    assert any("source records" in error for error in validate(graph, registry))

    # The other append-only identity stores are covered by the same graph boundary.
    identity_inputs = {
        "source_first": json.loads(
            (ROOT / "verification/source_first_prints.json").read_text(encoding="utf-8")
        ),
    }
    identity_inputs["source_first"]["prints"].append(
        {**identity_inputs["source_first"]["prints"][0], "printId": "TEST-UNACCOUNTED"}
    )
    assert any("identity input claims" in error for error in validate(graph, identity_inputs=identity_inputs))

    # Closed finish profiles require an explicit scope and closure authority.
    tampered = deepcopy(graph)
    next(row["payload"] for row in tampered["entities"] if row["entityType"] == "finish-profile")[
        "closureAuthority"
    ] = None
    assert any("closure scope/authority" in error for error in validate(tampered))

    # Rarity observations must stay in the locality of the release they describe.
    tampered = deepcopy(graph)
    rarity = next(row["payload"] for row in tampered["entities"] if row["entityType"] == "rarity-claim")
    release = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "card-release" and row["entityId"] == rarity["cardReleaseId"]
    )
    other_source = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "set-source-record"
        and (row["payload"].get("raw") or {}).get("locality")
        and (row["payload"].get("raw") or {}).get("locality") != release["locality"]
    )
    rarity["sourceRecordId"] = other_source["sourceRecordId"]
    rarity["sourceProvider"] = other_source["provider"]
    assert any("rarity claim source locality mismatch" in error for error in validate(tampered))

    # Re-key decisions must round-trip into both equivalence assertions and migration
    # targetRefs, including one-to-many decisions such as U0414.
    rekeys = json.loads(
        (ROOT / "verification/legacy_issue_rekeys.json").read_text(encoding="utf-8")
    )
    rekeys["questionSets"][0]["mappings"][0]["sourceFirstRecordId"] = "TW:AS5a:117/184:base"
    assert any("re-key" in error for error in validate(graph, identity_inputs={"rekeys": rekeys}))

    # A specimen observation must remain attached to a release with the same local
    # set, number and language, not merely to a printing with matching finish fields.
    tampered = deepcopy(graph)
    specimen_claim = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("sourceId") == "SPEC-0001"
    )
    specimen_printing = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "physical-printing"
        and row["entityId"] == specimen_claim["corroboratedTargetId"]
    )
    specimen_printing["cardReleaseId"] = next(
        row["entityId"] for row in tampered["entities"]
        if row["entityType"] == "card-release"
        and row["entityId"] != specimen_printing["cardReleaseId"]
    )
    assert any("specimen release identity is stale" in error for error in validate(tampered))

    # Explicit specimen conflicts remain reviewable candidates; they never materialize
    # a physical printing until the conflict is resolved.
    conflict_graph = deepcopy(graph)
    conflict_claim = next(
        row["payload"] for row in conflict_graph["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("sourceKind") == "finish-printing-record"
        and row["payload"].get("disposition") == "candidate-needs-evidence"
    )
    conflict_claim["evidenceStatus"] = "pending"
    conflict_claim["conflictsWith"] = ["SPEC-0040"]
    conflicted_finishes = json.loads(
        (ROOT / "verification/finish_units.json").read_text(encoding="utf-8")
    )
    conflicted_printing_id = conflict_claim["sourceId"]
    for finish_unit in conflicted_finishes["units"]:
        for printing in finish_unit.get("printings", []):
            if printing.get("printingId") == conflicted_printing_id:
                printing["verificationStatus"] = "pending"
    assert not validate(conflict_graph, identity_inputs={"finishes": conflicted_finishes})
    conflict_claim["conflictsWith"] = ["SPEC-NOT-RECORDED"]
    assert any(
        "finish conflict claim" in error
        for error in validate(conflict_graph, identity_inputs={"finishes": conflicted_finishes})
    )

    identity = identity_view(graph)
    migrations = {
        (row["sourceKind"], row["sourceId"]): row
        for row in graph["migrationDispositions"]
    }
    assert all(
        migrations[("finish-printing-record", printing_id)]["targetRef"]
        == f"PHYSICAL:{printing_id}"
        for printing_id in ("F0167-P01", "F0167-P02", "F0174-P01", "F0174-P02")
    )
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

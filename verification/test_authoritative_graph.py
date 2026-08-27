#!/usr/bin/env python3
"""Regression checks for the #140 authoritative graph boundary."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import authoritative_graph as graph_module  # noqa: E402
from authoritative_graph import identity_view, project_physical_evidence, validate  # noqa: E402


def main() -> None:
    graph = json.loads((ROOT / "verification/authoritative_graph.json").read_text(encoding="utf-8"))
    assert not validate(graph)
    assert graph_module.specimen_markings({
        "markings": "EDIZIONE 1", "markingRole": "print-identity"
    }) == [{"kind": "edition-stamp", "role": "print-identity", "text": "EDIZIONE 1"}]
    repaired_releases = [
        row["payload"] for row in graph["entities"] if row["entityType"] == "card-release"
    ]
    assert all(
        row["workMappingState"] in graph_module.WORK_MAPPING_STATES
        and (
            row["workMappingState"] in graph_module.WORK_REQUIRED_STATES
            and isinstance(row.get("work"), str)
            or row["workMappingState"] in graph_module.WORK_EMPTY_STATES
            and row.get("work") is None
        )
        for row in repaired_releases
    )
    tampered = deepcopy(graph)
    mapped_release = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "card-release" and row["payload"]["workMappingState"] == "mapped"
    )
    mapped_release["work"] = None
    assert any("mapped card release has no Work relation" in error for error in validate(tampered))
    tampered = deepcopy(graph)
    mapped_release = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "card-release" and row["payload"]["workMappingState"] == "mapped"
    )
    mapped_release["workMappingState"] = "needs-explicit-equivalence"
    assert any("unmapped card release carries a Work relation" in error for error in validate(tampered))
    tampered = deepcopy(graph)
    next(row["payload"] for row in tampered["entities"] if row["entityType"] == "card-release")[
        "workMappingState"
    ] = "future-state"
    assert any("unknown work mapping state" in error for error in validate(tampered))
    tampered = deepcopy(graph)
    mapped_release_id = next(
        row["entityId"] for row in tampered["entities"]
        if row["entityType"] == "card-release" and row["payload"]["workMappingState"] == "mapped"
    )
    implements_edge = next(
        edge for edge in tampered["edges"]
        if edge["fromType"] == "card-release"
        and edge["fromId"] == mapped_release_id
        and edge["relation"] == "implements"
    )
    other_work_id = next(
        row["entityId"] for row in tampered["entities"]
        if row["entityType"] == "work" and row["entityId"] != implements_edge["toId"]
    )
    implements_edge["toId"] = other_work_id
    assert any("implements edge is missing or inconsistent" in error for error in validate(tampered))
    tampered = deepcopy(graph)
    empty_release = next(
        row for row in tampered["entities"]
        if row["entityType"] == "card-release"
        and row["payload"]["workMappingState"] == "needs-explicit-equivalence"
    )
    empty_release["payload"]["workMappingState"] = "unmapped"
    empty_release["payload"]["work"] = None
    tampered["edges"].append({
        "fromType": "card-release", "fromId": empty_release["entityId"],
        "relation": "implements", "toType": "work", "toId": other_work_id,
    })
    assert any("unmapped card release has an implements edge" in error for error in validate(tampered))
    # Work entity IDs are the stable relation targets.  Swapping only the
    # payload workId values (and retargeting release edges to those values)
    # must fail instead of silently changing collector identity grouping.
    tampered = deepcopy(graph)
    work_rows = [row for row in tampered["entities"] if row["entityType"] == "work"][:2]
    first_work_id, second_work_id = (row["entityId"] for row in work_rows)
    first_work, second_work = (row["payload"] for row in work_rows)
    first_work["workId"], second_work["workId"] = second_work_id, first_work_id
    for release_row in tampered["entities"]:
        if release_row["entityType"] != "card-release":
            continue
        work_key = release_row["payload"].get("work")
        target_id = second_work_id if work_key == first_work["cardKey"] else (
            first_work_id if work_key == second_work["cardKey"] else None
        )
        if target_id is None:
            continue
        for edge in tampered["edges"]:
            if (
                edge["fromType"] == "card-release"
                and edge["fromId"] == release_row["entityId"]
                and edge["relation"] == "implements"
            ):
                edge["toId"] = target_id
    assert any("work payload id mismatch" in error for error in validate(tampered))
    # An explicit-equivalence mapping is only promotable with at least one
    # reviewed assertion that names both the exact release and Work relation.
    tampered = deepcopy(graph)
    equivalence_release = next(
        row for row in tampered["entities"]
        if row["entityType"] == "card-release"
        and row["payload"]["workMappingState"] == "mapped-by-explicit-equivalence"
    )
    assertion_ids = {
        edge["fromId"] for edge in tampered["edges"]
        if edge["fromType"] == "equivalence-assertion"
        and edge["relation"] == "relates"
        and edge["toType"] == "card-release"
        and edge["toId"] == equivalence_release["entityId"]
    }
    tampered["entities"] = [
        row for row in tampered["entities"] if not (
            row["entityType"] == "equivalence-assertion"
            and row["entityId"] in assertion_ids
        )
    ]
    tampered["edges"] = [
        edge for edge in tampered["edges"]
        if not (edge["fromType"] == "equivalence-assertion" and edge["fromId"] in assertion_ids)
    ]
    assert any(
        "mapped-by-explicit-equivalence card release lacks a matching equivalence assertion"
        in error for error in validate(tampered)
    )
    # Retargeting the release, implements edge, assertion payload and
    # assertion relation together must still fail against the legacy unit's
    # independently reviewed cardKey.
    tampered = deepcopy(graph)
    equivalence_release = next(
        row for row in tampered["entities"]
        if row["entityType"] == "card-release"
        and row["payload"]["workMappingState"] == "mapped-by-explicit-equivalence"
    )
    assertion_id = next(
        edge["fromId"] for edge in tampered["edges"]
        if edge["fromType"] == "equivalence-assertion"
        and edge["relation"] == "relates"
        and edge["toType"] == "card-release"
        and edge["toId"] == equivalence_release["entityId"]
    )
    alternate_work = next(
        row for row in tampered["entities"]
        if row["entityType"] == "work"
        and row["entityId"] != next(
            edge["toId"] for edge in tampered["edges"]
            if edge["fromType"] == "card-release"
            and edge["fromId"] == equivalence_release["entityId"]
            and edge["relation"] == "implements"
        )
    )
    equivalence_release["payload"]["work"] = alternate_work["payload"]["cardKey"]
    for edge in tampered["edges"]:
        if edge["fromType"] == "card-release" and edge["fromId"] == equivalence_release["entityId"] \
                and edge["relation"] == "implements":
            edge["toId"] = alternate_work["entityId"]
        if edge["fromType"] == "equivalence-assertion" and edge["fromId"] == assertion_id:
            if edge["toType"] == "work":
                edge["toId"] = alternate_work["entityId"]
    assertion = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "equivalence-assertion" and row["entityId"] == assertion_id
    )
    assertion["toId"] = alternate_work["entityId"]
    assert any(
        "re-key equivalence assertion is stale" in error
        or "mapped-by-explicit-equivalence release Work is not canonical" in error
        for error in validate(tampered)
    )
    # A canonical re-key cannot silently fall back to the ordinary mapped
    # state while changing the release's Work relation.
    tampered = deepcopy(graph)
    stateful_release = next(
        row for row in tampered["entities"]
        if row["entityType"] == "card-release"
        and row["payload"]["workMappingState"] == "mapped-by-explicit-equivalence"
    )
    current_work_id = next(
        edge["toId"] for edge in tampered["edges"]
        if edge["fromType"] == "card-release"
        and edge["fromId"] == stateful_release["entityId"]
        and edge["relation"] == "implements"
    )
    alternate_work = next(
        row for row in tampered["entities"]
        if row["entityType"] == "work" and row["entityId"] != current_work_id
    )
    stateful_release["payload"]["workMappingState"] = "mapped"
    stateful_release["payload"]["work"] = alternate_work["payload"]["cardKey"]
    next(
        edge for edge in tampered["edges"]
        if edge["fromType"] == "card-release"
        and edge["fromId"] == stateful_release["entityId"]
        and edge["relation"] == "implements"
    )["toId"] = alternate_work["entityId"]
    assert any(
        "re-keyed release must retain mapped-by-explicit-equivalence state" in error
        for error in validate(tampered)
    )
    # The reviewed #304 pending state is distinct from generic unmapped: a
    # later downgrade would discard the explicit-equivalence research signal.
    tampered = deepcopy(graph)
    pending_release = next(
        row for row in tampered["entities"]
        if row["entityType"] == "card-release"
        and row["entityId"] == "RELEASE:JP:Japanese:DP-P:126:None"
    )
    pending_release["payload"]["workMappingState"] = "unmapped"
    pending_release["payload"]["work"] = None
    assert any(
        "issue #304 release has unexpected work mapping state" in error
        for error in validate(tampered)
    )
    assert project_physical_evidence(deepcopy(graph)) == graph
    # A positional printing id may change when a new printing sorts before it.  The
    # existing physical node and claim must nevertheless follow the same semantics.
    with tempfile.TemporaryDirectory() as directory:
        finish_path = Path(directory) / "finish_units.json"
        finish_copy = json.loads(
            (ROOT / "verification" / "finish_units.json").read_text(encoding="utf-8")
        )
        shifted = next(
            printing for unit in finish_copy["units"]
            for printing in unit.get("printings", [])
            if printing.get("printingId") == "F0167-P01"
        )
        shifted["printingId"] = "F0167-P99"
        finish_path.write_text(json.dumps(finish_copy), encoding="utf-8")
        original_finish_path = graph_module.FINISH_UNITS
        graph_module.FINISH_UNITS = finish_path
        try:
            shifted_projection = project_physical_evidence(deepcopy(graph))
        finally:
            graph_module.FINISH_UNITS = original_finish_path
    shifted_physical = next(
        row["payload"] for row in shifted_projection["entities"]
        if row["entityType"] == "physical-printing"
        and row["entityId"] == "PHYSICAL:F0167-P01"
    )
    assert shifted_physical["sourcePrintingId"] == "F0167-P99"
    assert shifted_physical["establishingClaimId"] == "CLAIM:finish:F0167-P01"
    standalone_claim = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("sourceId") == "SPEC-0030"
    )
    assert standalone_claim["disposition"] == "established-and-mapped"
    assert standalone_claim["materializedTargetId"] == "PHYSICAL:specimen:SPEC-0030"
    assert any(
        row["entityType"] == "physical-printing"
        and row["entityId"] == "PHYSICAL:specimen:SPEC-0030"
        for row in graph["entities"]
    )
    specimens_with_denominator = json.loads(
        (ROOT / "verification/specimens.json").read_text(encoding="utf-8")
    )
    next(row for row in specimens_with_denominator["specimens"]
         if row["specimenId"] == "SPEC-0030")["number"] = "145/999"
    assert not validate(graph, identity_inputs={"specimens": specimens_with_denominator})
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
        assert claim["reason"].startswith("provides provenance for PHYSICAL:F")
        assert claim["provenanceTargetId"].startswith("PHYSICAL:F")
        assert "corroboratedTargetId" not in claim

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
        and row["entityId"] == specimen_claim["provenanceTargetId"]
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

    # A conflicted specimen may identify a source-first release, but it must remain pending
    # rather than materializing through the standalone-specimen fallback.
    with tempfile.TemporaryDirectory() as directory:
        finish_path = Path(directory) / "finish_units.json"
        specimens_path = Path(directory) / "specimens.json"
        finish_copy = json.loads(
            (ROOT / "verification/finish_units.json").read_text(encoding="utf-8")
        )
        conflicted_printing = next(
            printing for unit in finish_copy["units"]
            for printing in unit.get("printings", [])
        )
        conflicted_printing["verificationStatus"] = "pending"
        conflicted_printing["specimenIds"] = ["SPEC-0030"]
        conflicted_printing["conflictsWith"] = ["SPEC-0040"]
        finish_path.write_text(json.dumps(finish_copy), encoding="utf-8")
        specimens_path.write_text(
            (ROOT / "verification/specimens.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        original_finish_path = graph_module.FINISH_UNITS
        original_specimens_path = graph_module.SPECIMENS
        graph_module.FINISH_UNITS = finish_path
        graph_module.SPECIMENS = specimens_path
        try:
            conflict_projection = project_physical_evidence(deepcopy(graph))
        finally:
            graph_module.FINISH_UNITS = original_finish_path
            graph_module.SPECIMENS = original_specimens_path
    conflict_specimen_claim = next(
        row["payload"] for row in conflict_projection["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("sourceId") == "SPEC-0030"
    )
    assert conflict_specimen_claim["disposition"] == "candidate-needs-evidence"
    assert conflict_specimen_claim["materializedTargetId"] is None
    assert not any(
        row["entityId"] == "PHYSICAL:specimen:SPEC-0030"
        for row in conflict_projection["entities"]
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

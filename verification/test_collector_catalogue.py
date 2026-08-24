#!/usr/bin/env python3
"""Contract, graph-reference and reconciliation regressions for issue #254."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import collector_catalogue as collector  # noqa: E402
import collector_deployment as deployment  # noqa: E402


def read(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    graph = read("verification/authoritative_graph.json")
    catalogue = read("collector_catalogue.json")
    migrations = read("collector_migrations.json")
    fixture = read("collector_catalogue.fixture.json")
    schema = read("collector_catalogue.schema.json")
    predecessor = read("analysis_checklist.json")

    assert not collector.validate_catalogue(catalogue, graph)
    assert not collector.validate_migrations(migrations, catalogue, graph, predecessor)
    assert not collector.validate_catalogue(
        fixture["catalogue"], check_asset_bytes=False
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["meta"]["properties"]["schemaVersion"]["const"] == "1.0.0"

    counts = catalogue["qualitySummary"]["counts"]
    graph_printing_ids = {
        row["payload"].get("sourcePrintingId")
        for row in graph["entities"] if row["entityType"] == "physical-printing"
    }
    graph_release_ids = {
        row["payload"]["cardReleaseId"]
        for row in graph["entities"] if row["entityType"] == "card-release"
    }
    predecessor_items = predecessor["items"]
    expected_candidates = sum(
        bool(row.get("printingId")) and row["printingId"] not in graph_printing_ids
        for row in predecessor_items
    )
    prior_projection_release_ids = {
        row["cardReleaseId"] for row in catalogue["items"]
        if row["itemKind"] != "research-placeholder" or row["legacyChecklistIds"]
    }
    expected_placeholders = (
        sum(not row.get("printingId") for row in predecessor_items)
        + len(graph_release_ids - prior_projection_release_ids)
    )
    assert counts["items"] == len(catalogue["items"])
    assert counts["verifiedPrintings"] == len([
        row for row in graph["entities"] if row["entityType"] == "physical-printing"
    ])
    assert counts["finishCandidates"] == expected_candidates
    assert counts["researchPlaceholders"] == expected_placeholders
    assert {row["cardReleaseId"] for row in catalogue["items"]} == graph_release_ids
    assert counts["currentKnown"] == counts["verifiedPrintings"]
    assert counts["research"] == counts["finishCandidates"] + counts["researchPlaceholders"]
    assert catalogue["qualitySummary"]["candidateProgressPolicy"] == {
        "progressClass": "research",
        "status": "fail-safe-default-pending-owner-decision",
        "basis": "positive-printing-evidence-or-explicit-owner-decision-required-for-current-known",
        "decisionRef": "https://github.com/m4s-ai/snoredex-data/issues/254",
    }
    assert all(
        isinstance(item["markings"], list)
        and all(marking.get("role") for marking in item["markings"])
        for item in catalogue["items"]
    )

    # Fail closed if a research candidate is silently promoted into ordinary
    # collection progress or given an invented physical printing.
    tampered = copy.deepcopy(catalogue)
    candidate = next(row for row in tampered["items"] if row["itemKind"] == "finish-candidate")
    candidate["physicalPrintingId"] = "invented"
    candidate["progressClass"] = "current-known"
    assert any("finish candidate" in error for error in collector.validate_catalogue(
        tampered, graph, check_asset_bytes=False
    ))

    # An established graph release may have no physical printing or predecessor
    # row yet, but it must still remain visible as a neutral research item.
    tampered = copy.deepcopy(catalogue)
    release_placeholder = next(
        row for row in tampered["items"]
        if row["itemKind"] == "research-placeholder" and not row["legacyChecklistIds"]
    )
    tampered["items"].remove(release_placeholder)
    assert any("card-release accounting" in error for error in collector.validate_catalogue(
        tampered, graph, check_asset_bytes=False
    ))

    # Locality is identity: changing the LATAM record into WEST cannot leave a
    # catalogue that passes the contract boundary.
    tampered = copy.deepcopy(catalogue)
    next(row for row in tampered["localizations"] if row["languageTag"] == "es-419")[
        "locality"
    ] = "WEST"
    assert any("LATAM/es-419" in error for error in collector.validate_catalogue(
        tampered, graph, check_asset_bytes=False
    ))

    # Removing even one predecessor transition is data loss, and U0414 remains a
    # visible 1:N conflict rather than an automatic state copy.
    tampered_migrations = copy.deepcopy(migrations)
    tampered_migrations["transitions"].pop()
    assert any("predecessor" in error for error in collector.validate_migrations(
        tampered_migrations, catalogue, graph, predecessor
    ))
    u0414 = next(row for row in fixture["reconciliationCases"] if row["caseId"] == "U0414-1-to-many")
    assert u0414["expectedAutomaticStateAction"] == "none"
    assert u0414["expectedResolution"] == "requires-user-resolution"

    # The semantic fingerprint excludes only its own field.
    tampered = copy.deepcopy(catalogue)
    tampered["meta"]["catalogueFingerprint"] = "sha256:" + "0" * 64
    assert collector.semantic_fingerprint(tampered) == catalogue["meta"]["catalogueFingerprint"]
    tampered["items"][0]["active"] = False
    assert collector.semantic_fingerprint(tampered) != catalogue["meta"]["catalogueFingerprint"]

    # Runtime publication metadata binds a real commit-shaped identity to the
    # exact deterministic catalogue bytes without contaminating regeneration.
    manifest = deployment.build_manifest(
        ROOT / "collector_catalogue.json", "a" * 40, "2026-08-24T12:00:00Z",
        deployment.DEFAULT_URL,
    )
    assert not deployment.validate_manifest(
        manifest, ROOT / "collector_catalogue.json", "a" * 40
    )
    manifest["byteDigest"] = "sha256:" + "0" * 64
    assert "catalogue byte digest differs" in deployment.validate_manifest(
        manifest, ROOT / "collector_catalogue.json", "a" * 40
    )
    manifest["unexpected"] = True
    assert "deployment manifest fields differ from the contract" in deployment.validate_manifest(
        manifest, ROOT / "collector_catalogue.json", "a" * 40
    )

    print(
        "collector contract regressions passed: "
        f"{counts['items']} items, {counts['assets']} assets, "
        f"{catalogue['meta']['catalogueFingerprint']}"
    )


if __name__ == "__main__":
    main()

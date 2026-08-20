#!/usr/bin/env python3
"""Regression and acceptance checks for the bounded #148 reconciliation."""

from __future__ import annotations

import copy
import csv
from collections import Counter
import io
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.legacy_set_reconciliation import (  # noqa: E402
    COMPAT_CSV_PATH,
    COMPAT_JSON_PATH,
    COVERAGE_VERSION,
    EXPECTED_DENOMINATORS,
    MIXED_STATUS_PAIRS,
    OUTPUT_PATH,
    build,
    portable_file_hash,
    read_json,
    render_json,
    value_hash,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def csv_rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text), delimiter=";"))


def main() -> int:
    first, compat_json, compat_csv = build()
    second, second_compat_json, second_compat_csv = build()
    require(first == second, "two empty reconciliation builds differ")
    require(compat_json == second_compat_json, "two JSON compatibility builds differ")
    require(compat_csv == second_compat_csv, "two CSV compatibility builds differ")
    require(first["meta"]["coverageVersion"] == COVERAGE_VERSION, "coverage version missing")
    require(
        portable_file_hash(b"one\r\ntwo\r\n") == portable_file_hash(b"one\ntwo\n"),
        "tracked-text hashes depend on CRLF versus LF checkout policy",
    )

    require(
        len(first["legacyAliases"]) == EXPECTED_DENOMINATORS["aliases"],
        "legacy alias denominator changed",
    )
    require(
        len(first["legacyReleaseRows"]) == EXPECTED_DENOMINATORS["releaseRows"],
        "legacy release denominator changed",
    )
    require(
        len(first["legacyFinishUnits"]) == EXPECTED_DENOMINATORS["finishUnits"],
        "legacy finish denominator changed",
    )
    for name in ("aliasAccounting", "releaseAccounting", "finishAccounting"):
        require(first["reports"][name]["balanced"], f"{name} is not balanced")
    for alias in first["legacyAliases"]:
        require(
            alias["setEditionIds"]
            == [resolution["setEditionId"] for resolution in alias["editionResolutions"]],
            f"alias edition resolutions are not explicit: {alias['legacyAliasId']}",
        )

    require(first["reports"]["compatibilityLoss"]["rowCountDelta"] == 0, "release row lost")
    require(
        first["reports"]["compatibilityLoss"]["droppedLanguageRelationships"] == 0,
        "release language relationship lost",
    )
    require(
        first["reports"]["compatibilityLoss"]["legacyScalarDatesOverwritten"] == 0,
        "legacy scalar date overwritten",
    )
    require(
        first["reports"]["compatibilityLoss"]["unsourcedPresentedAsReviewedExact"] == 0,
        "unsourced scalar presented as reviewed exact",
    )
    require(
        first["reports"]["compatibilityLoss"]["legacySetCodeLanguagePairs"] == 490
        and first["reports"]["compatibilityLoss"]["droppedSetCodeLanguagePairs"] == 0,
        "490 legacy set-code/language pairs are not losslessly visible",
    )
    allowed_unsourced = {
        "newly-sourced", "inherited-legacy-estimate-with-warning",
        "unknown-needs-evidence", "positively-superseded",
    }
    for row in first["legacyReleaseRows"]:
        if not row["rawDateSource"]:
            require(
                row["dateProvenanceDisposition"] in allowed_unsourced,
                f"unsourced row lacks an explicit disposition: {row['legacyReleaseRowId']}",
            )
        require(
            row["generationProvenance"]["sourceArtifact"]
            == "analysis_confirmed_releases.json",
            "release generation provenance missing",
        )
        for link in row["languageDateLinks"]:
            if link["dateLinkState"] == "needs-evidence":
                require(not link["copiedLegacyScalar"], "scalar copied into an unsupported language")
            for event in link["releaseEventLinks"]:
                require(event["locality"], "release event link lacks locality")
                require(event["marketScopes"], "release event link lacks market scope")
                require(event["datePrecision"] in {"year", "month", "day"}, "bad event precision")
                require(event["status"], "release event link lacks status")
                require(event["sourceRecordId"], "release event link lacks evidence")

    analysis = read_json(ROOT / "analysis_confirmed_releases.json")
    require(len(compat_json["variants"]) == len(analysis["variants"]), "JSON projection row loss")
    for source, projected in zip(analysis["variants"], compat_json["variants"]):
        restored = copy.deepcopy(projected)
        restored.pop("reconciliation")
        require(restored == source, f"JSON compatibility row mutated: {source['rowId']}")
    source_csv = (ROOT / "analysis_confirmed_releases.csv").read_text(encoding="utf-8-sig")
    source_csv_rows = csv_rows(source_csv)
    projected_csv_rows = csv_rows(compat_csv)
    require(len(source_csv_rows) == len(projected_csv_rows), "CSV projection row loss")
    width = len(source_csv_rows[0])
    for source, projected in zip(source_csv_rows, projected_csv_rows):
        require(projected[:width] == source, "CSV compatibility prefix mutated")
    appended_header = projected_csv_rows[0][width:]
    require("Coverage denominator" in appended_header, "CSV denominator missing")
    require("Row count delta" in appended_header, "CSV loss diagnostics missing")
    denominator_index = projected_csv_rows[0].index("Coverage denominator")
    require(
        all(row[denominator_index] == "203" for row in projected_csv_rows[1:]),
        "CSV denominator is not explicit on every row",
    )

    source_finish = read_json(ROOT / "verification" / "finish_units.json")
    source_finish_by_id = {unit["finishUnitId"]: unit for unit in source_finish["units"]}
    for unit in first["legacyFinishUnits"]:
        source_unit = source_finish_by_id[unit["finishUnitId"]]
        require(value_hash(source_unit) == unit["legacyUnitHash"], "finish unit hash is not exact")
        require(
            unit["legacySourceRef"]
            == f"verification/finish_units.json#{unit['finishUnitId']}",
            "finish provenance reference missing",
        )
        require(unit["availableFinishes"] == source_unit["availableFinishes"], "finish list mutated")
        require(
            unit["completenessStatus"] == source_unit["completenessStatus"],
            "finish completeness mutated",
        )
        require(unit["printingEvidence"] == source_unit["printings"], "finish evidence mutated")
        if unit["migrationDisposition"] == "profile-derived":
            require(unit["scope"] == "set-edition-profile", "profile finish has wrong scope")
            require(unit["profileFinishClaimIds"], "profile finish lacks a profile claim")
        elif unit["migrationDisposition"] == "specimen-evidenced":
            require(unit["scope"] == "physical-printing", "specimen finish has wrong scope")
            require(unit["physicalPrintingIds"], "specimen finish lacks physical printing target")
        elif unit["migrationDisposition"] == "card-level-evidenced":
            require(unit["scope"] == "card-release", "card finish has wrong scope")
    closed = [unit for unit in first["legacyFinishUnits"] if unit["closureDisposition"]]
    require(len(closed) == 5, "closed finish-list count changed")
    require(
        sum(unit["closureDisposition"] == "complete-manifest-preserved" for unit in closed) == 4,
        "complete manifests were not preserved",
    )
    require(
        sum(unit["closureDisposition"] == "owner-adjudicated-preserved" for unit in closed) == 1,
        "owner-adjudicated list was not preserved",
    )
    scope_loss = first["reports"]["finishScopeLoss"]
    require(scope_loss["legacyUnitsDropped"] == 0, "finish unit lost")
    require(scope_loss["cardClaimsPromotedToProfiles"] == 0, "card finish promoted to profile")
    require(scope_loss["profileRulesCopiedAsCardEvidence"] == 0, "profile copied as card evidence")
    require(scope_loss["closedListsDropped"] == 0, "closed finish list lost")

    boundaries = {row["rawIdentifier"]: row for row in first["identityBoundaryGuards"]}
    for code in ("AS5a", "sc1a F", "sc1b F", "scD F"):
        require(boundaries[code]["terminalState"] == "complete", f"{code} identity missing")
        require(len(boundaries[code]["localSetIds"]) == 1, f"{code} identity is not independent")
    require(
        boundaries["svQP F"]["terminalState"] == "blocked-by-source"
        and not boundaries["svQP F"]["localSetIds"],
        "svQP F must stay guarded without a manufactured identity",
    )
    # 6 -> 26 on 2026-08-10: ADR-0001 D5 admitted twenty Thai and Indonesian catch-up
    # prints. 26 -> 30 on 2026-08-11: issue #192 added three LATAM Spanish prints and
    # the SVP ES comparison, all with the complete printed language modifier preserved.
    # 30 -> 31 on 2026-08-20: #233 admitted the specimen-backed Korean Burning
    # Confrontation 30/40 print while keeping its DP1 work equivalence unresolved.
    # The pin stays exact rather than becoming a minimum — its job is to catch an edge
    # appearing or vanishing without a decision behind it, and a floor would not do that.
    require(len(first["catchUpRelations"]) == 31, "catch-up edge count changed")
    korean_bcr = [
        edge for edge in first["catchUpRelations"]
        if edge["targetSourceFirstPrintId"] == "KR:BCR:30/40:base"
    ]
    require(
        len(korean_bcr) == 1
        and korean_bcr[0]["terminalState"] == "needs-evidence"
        and korean_bcr[0]["evidence"]["specimenId"] == "SPEC-0037"
        and not korean_bcr[0]["setMergeAllowed"],
        "Korean Burning Confrontation relation is not specimen-grounded and unresolved",
    )
    official_spanish_targets = {
        edge["targetSourceFirstPrintId"]
        for edge in first["catchUpRelations"]
        if edge["evidence"]["providerId"] == "pokemon-official"
    }
    require(
        official_spanish_targets == {
            "LATAM:JTG LA:117/159:base",
            "LATAM:SVP LA:184:base",
            "WEST:SVP ES:184:base",
            "LATAM:POR LA:063/088:base",
        },
        "Spanish printed-code catch-up inventory changed",
    )
    # Terminal states are pinned per state, not asserted uniformly. The six specimen-backed edges
    # resolve to a card release and stay `complete`. The twenty D5 edges do not, and should not:
    # their `catchUpOf` says which Traditional Chinese print or set family they answer, which is a
    # statement about the *card work*, and ADR-0001's I5 wants an explicit decision before an
    # equivalence becomes a resolved edge. `needs-evidence` is the honest state for them, so the
    # guard checks the split rather than demanding a completeness nobody established.
    states = Counter(edge["terminalState"] for edge in first["catchUpRelations"])
    require(states == Counter({"complete": 6, "needs-evidence": 25}),
            f"catch-up terminal states changed: {dict(states)}")
    for edge in first["catchUpRelations"]:
        require(not edge["setMergeAllowed"], "catch-up edge merges sets")
        require(edge["terminalState"] in {"complete", "needs-evidence"},
                f"unknown catch-up terminal state: {edge['terminalState']}")
        if edge["terminalState"] == "needs-evidence":
            require(not edge["sourceCardReleaseIds"],
                    "an unresolved catch-up edge must not already name a source release")
        else:
            require(len(edge["sourceCardReleaseIds"]) == 1, "catch-up source is ambiguous")
        require(edge["targetSetEditionId"], "catch-up target edition missing")

    mixed = {
        (row["setCode"], row["language"]): row for row in first["mixedCardClaimPairs"]
    }
    require(set(mixed) == set(MIXED_STATUS_PAIRS), "mixed-status pair inventory changed")
    for pair, row in mixed.items():
        require(row["setEditionVerdict"] is None, f"mixed pair promoted to set verdict: {pair}")
        require(
            row["observedClaimStatuses"] == ["confirmed", "contradicted"],
            f"mixed card statuses lost: {pair}",
        )
    require(all(fixture["passed"] for fixture in first["fixtures"]), "acceptance fixture failed")
    require(
        "blocked-by-source" in first["reports"]["terminalStates"],
        "blocked terminal state invisible",
    )

    require(OUTPUT_PATH.read_text(encoding="utf-8-sig") == render_json(first), "ledger is stale")
    require(
        COMPAT_JSON_PATH.read_text(encoding="utf-8-sig") == render_json(compat_json),
        "JSON compatibility projection is stale",
    )
    require(COMPAT_CSV_PATH.read_text(encoding="utf-8-sig") == compat_csv, "CSV projection is stale")
    print(
        "legacy reconciliation passed: 135 aliases + 203 release rows + 637 finish units; "
        "all accounting balanced"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

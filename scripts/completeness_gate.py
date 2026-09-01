#!/usr/bin/env python3
"""Validate the bounded source-first release gate and write its run summary (#141).

This is deliberately a read-only gate.  Network acquisition belongs to the two immutable
source-first loops; ``discovery_cycle.py --refresh`` runs those loops, while this command proves
that their newest retained runs, locality matrices and authoritative graph are accounted.

    python scripts/completeness_gate.py
    python scripts/completeness_gate.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import asia_locality_matrix
import locality_matrix

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "verification" / "completeness_gate.json"
SOURCE_STAGING = ROOT / "verification" / "source_adapter_staging.json"
SOURCE_RECORDS = ROOT / "verification" / "source_adapter_records.jsonl"
CARD_STAGING = ROOT / "verification" / "card_discovery_staging.json"
CARD_RECORDS = ROOT / "verification" / "card_discovery_records.jsonl"
ASIA_MATRIX = ROOT / "verification" / "asia_locality_matrix.json"
LOCALITY_MATRIX = ROOT / "verification" / "locality_era_matrix.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"

TERMINAL_STATES = {"complete", "needs-evidence", "blocked-by-source"}
EXPECTED_LOCALITY_BOUNDARIES = {
    "west-es-eu": ("WEST", "es-ES"),
    "latam-es": ("LATAM", "es-419"),
    "sea-en-coordinated": ("SEA", "en-035"),
}
EXPECTED_ASIA_REGRESSIONS = {
    "tw-svqp-f-012", "tw-sv-p-215", "tw-as5a-142", "cn-sv9-075",
    "id-sv9s-i-109", "id-sv4s-i-118", "id-sv6s-i-136",
    "kr-renumbered-positive-printings", "kr-spec-0037-positive",
}


class GateError(ValueError):
    """A release-gate invariant failed."""


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def validate_staging(document: dict[str, Any], name: str) -> list[str]:
    errors: list[str] = []
    meta = document.get("meta", {})
    for field in ("coverageVersion", "generatedFromRun", "contractHash"):
        if not meta.get(field):
            errors.append(f"{name}: meta.{field} is required")
    if meta.get("sourceFirst") is not True:
        errors.append(f"{name}: sourceFirst must remain true")
    if meta.get("verdictMutationAllowed") is not False:
        errors.append(f"{name}: verdictMutationAllowed must remain false")
    if meta.get("counts", {}).get("runErrors", 0):
        errors.append(f"{name}: latest run has {meta['counts']['runErrors']} run error(s)")

    bucket_names = (
        ("mapped", "newCandidate", "ambiguousNeedsEvidence", "positivelyExcluded")
        if name == "set-discovery"
        else ("matched", "ambiguous", "newCandidate", "positivelyExcluded", "needsEvidence")
    )
    slices = document.get("slices")
    if not isinstance(slices, list) or not slices:
        return errors + [f"{name}: no retained slices"]
    seen: set[str] = set()
    total_fetched = 0
    for row in slices:
        slice_id = row.get("sliceId", "<missing>")
        if slice_id in seen:
            errors.append(f"{name}: duplicate slice {slice_id}")
        seen.add(slice_id)
        state = row.get("terminalState")
        if state not in TERMINAL_STATES:
            errors.append(f"{name}: {slice_id} has invalid terminal state {state!r}")
        accounting = row.get("accounting", {})
        fetched = accounting.get("fetched")
        accounted = accounting.get("accounted")
        if not isinstance(fetched, int) or fetched < 0:
            errors.append(f"{name}: {slice_id} has invalid fetched count")
            continue
        total_fetched += fetched
        buckets = [accounting.get(key, 0) for key in bucket_names]
        if any(not isinstance(value, int) or value < 0 for value in buckets):
            errors.append(f"{name}: {slice_id} has invalid bucket count")
            continue
        if fetched != accounted or fetched != sum(buckets):
            errors.append(
                f"{name}: {slice_id} does not balance fetched={fetched}, "
                f"accounted={accounted}, buckets={sum(buckets)}"
            )
        if state == "complete" and fetched == 0:
            errors.append(f"{name}: zero-result complete slice {slice_id} must be retried or blocked")
        if state == "complete" and row.get("sourceFailureState"):
            errors.append(f"{name}: complete slice {slice_id} carries a source failure")
    declared = meta.get("counts", {}).get("records")
    if isinstance(declared, int) and declared != total_fetched:
        errors.append(f"{name}: meta.records={declared} differs from slice total {total_fetched}")
    return errors


def validate_card_records(path: Path = CARD_RECORDS) -> list[str]:
    """Set-only rows cannot enter the card discovery output."""
    errors: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("bucket") not in {"matched", "new-candidate"}:
                continue
            source = row.get("sourceRecord") or {}
            missing = [
                field for field in ("detailId", "localCollectorNumber", "productScope")
                if not source.get(field)
            ]
            if source.get("productScope") != "physical-tcg":
                missing.append("physical-tcg product scope")
            if missing:
                errors.append(
                    f"card discovery record {row.get('recordId', line_number)} is not card-level: "
                    + ", ".join(missing)
                )
    return errors


def validate_graph(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entities = {
        (row.get("entityType"), row.get("entityId")): row
        for row in graph.get("entities", [])
    }
    if len(entities) != len(graph.get("entities", [])):
        errors.append("authoritative graph has duplicate typed entity ids")
    edges = graph.get("edges", [])
    adjacency: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for row in edges:
        source = (row.get("fromType"), row.get("fromId"))
        target = (row.get("toType"), row.get("toId"))
        if source not in entities:
            errors.append(f"edge source does not resolve: {source}")
        if row.get("toType") != "node" and target not in entities:
            errors.append(f"edge target does not resolve: {target}")
        # materializes/established-by is the intentional evidence ↔ printing loop.
        if row.get("relation") not in {"materializes", "established-by"}:
            adjacency[source].append(target)

    state: dict[tuple[str, str], int] = {}

    def visit(node: tuple[str, str]) -> None:
        state[node] = 1
        for target in adjacency.get(node, []):
            if state.get(target) == 1:
                raise GateError(f"unexpected graph cycle: {node} -> {target}")
            if not state.get(target):
                visit(target)
        state[node] = 2

    try:
        for node in adjacency:
            if not state.get(node):
                visit(node)
    except GateError as error:
        errors.append(str(error))

    for entity in graph.get("entities", []):
        kind = entity.get("entityType")
        payload = entity.get("payload", {})
        key = (kind, entity.get("entityId"))
        if kind == "card-release":
            if not payload.get("establishingClaimIds"):
                errors.append(f"card release has no establishing claim: {key}")
            if not any(row.get("fromType") == kind and row.get("fromId") == key[1]
                       and row.get("relation") == "belongs-to" for row in edges):
                errors.append(f"card release has no set-edition edge: {key}")
        elif kind == "physical-printing":
            if not payload.get("establishingClaimId"):
                errors.append(f"physical printing has no establishing claim: {key}")
            if not any(row.get("fromType") == kind and row.get("fromId") == key[1]
                       and row.get("relation") == "realizes" for row in edges):
                errors.append(f"physical printing has no card-release edge: {key}")
        elif kind == "candidate-claim" and payload.get("evidenceStatus") == "contradicted":
            if payload.get("materializedTargetId"):
                errors.append(f"contradicted claim materializes a target: {key}")
    return errors


def validate_boundaries(locality: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tracks = {row.get("trackId"): row for row in locality.get("tracks", [])}
    for track_id, expected in EXPECTED_LOCALITY_BOUNDARIES.items():
        row = tracks.get(track_id)
        if row is None:
            errors.append(f"locality matrix is missing boundary track {track_id}")
            continue
        actual = (row.get("locality"), row.get("bcp47"))
        if actual != expected:
            errors.append(f"{track_id} locality boundary changed: {actual!r} != {expected!r}")
    return errors


def validate_regressions(asia: dict[str, Any]) -> list[str]:
    rows = {row.get("regressionId"): row for row in asia.get("minimumRegressions", [])}
    errors: list[str] = []
    if set(rows) != EXPECTED_ASIA_REGRESSIONS:
        errors.append(
            "Asia minimum-regression set differs: "
            f"missing={sorted(EXPECTED_ASIA_REGRESSIONS - set(rows))}, "
            f"extra={sorted(set(rows) - EXPECTED_ASIA_REGRESSIONS)}"
        )
    for regression_id, row in rows.items():
        if not row.get("evidenceRefs"):
            errors.append(f"Asia regression {regression_id} has no evidence reference")
        if row.get("disposition") not in {"positive-node", "positive-candidate", "held-positive"}:
            errors.append(f"Asia regression {regression_id} is not positively visible")
        if not row.get("expectedPrints"):
            errors.append(f"Asia regression {regression_id} has no expected print/candidate")
    return errors


def validate_inputs() -> tuple[dict[str, Any], list[str]]:
    source = read_json(SOURCE_STAGING)
    card = read_json(CARD_STAGING)
    asia = read_json(ASIA_MATRIX)
    locality = read_json(LOCALITY_MATRIX)
    graph = read_json(GRAPH)
    errors = []
    errors.extend(validate_staging(source, "set-discovery"))
    errors.extend(validate_staging(card, "card-discovery"))
    errors.extend(validate_card_records())
    errors.extend(validate_graph(graph))
    errors.extend(asia_locality_matrix.validate(asia, asia_locality_matrix.indexes(asia)))
    locality_indexes = locality_matrix.reference_indexes()
    errors.extend(locality_matrix.validate(locality, locality_indexes))
    errors.extend(validate_boundaries(locality))
    errors.extend(validate_regressions(asia))
    return {
        "source": source, "card": card, "asia": asia, "locality": locality, "graph": graph,
    }, errors


def summary(inputs: dict[str, Any]) -> dict[str, Any]:
    source, card, asia, locality, graph = (
        inputs["source"], inputs["card"], inputs["asia"], inputs["locality"], inputs["graph"]
    )
    source_run = source["meta"]["generatedFromRun"]
    card_run = card["meta"]["generatedFromRun"]
    gaps = []
    adapter_gaps = {row["gapId"]: row for row in card.get("gaps", [])}
    for row in asia.get("localGaps", []):
        gaps.append({"id": row["gapId"], "state": row["terminalState"], "reason": row["reason"]})
    for track in asia.get("tracks", []):
        for gap_id in track.get("gapIds", []):
            if not any(item["id"] == gap_id for item in gaps):
                gap = adapter_gaps.get(gap_id, track) if track["terminalState"] == "complete" else track
                gaps.append({"id": gap_id, "state": gap["terminalState"], "reason": gap.get("reason", track["scope"])})
    return {
        "meta": {
            "schema": "snoredex-completeness-gate",
            "schemaVersion": "1.0.0",
            "coverageVersion": {
                "setDiscovery": source["meta"]["coverageVersion"],
                "cardDiscovery": card["meta"]["coverageVersion"],
                "asia": asia["meta"]["schemaVersion"],
                "locality": locality["meta"]["schemaVersion"],
                "graph": graph["meta"]["generated"],
            },
            "setDiscoveryRun": source_run,
            "cardDiscoveryRun": card_run,
            "previousSetDiscoveryRun": source["meta"].get("previousRun"),
            "previousCardDiscoveryRun": card["meta"].get("previousRun"),
            "setDiscoveryRecordsHash": sha256(SOURCE_RECORDS),
            "cardDiscoveryRecordsHash": sha256(CARD_RECORDS),
            "terminalState": "complete",
            "terminalMeaning": (
                "Both bounded discovery loops and the authoritative graph are accounted; "
                "needs-evidence and blocked-by-source gaps remain explicit and are not absence claims."
            ),
        },
        "counts": {
            "setDiscoverySlices": source["meta"]["counts"]["slices"],
            "setDiscoveryRecords": source["meta"]["counts"]["records"],
            "cardDiscoverySlices": card["meta"]["counts"]["slices"],
            "cardDiscoveryRecords": card["meta"]["counts"]["records"],
            "graphEntities": graph["summary"]["entities"],
            "graphEdges": graph["summary"]["edges"],
            "asiaTracks": len(asia.get("tracks", [])),
            "localityTracks": len(locality.get("tracks", [])),
        },
        "gaps": gaps,
        "mutationChecks": [
            "missing source-first regression",
            "collapsed LATAM-ES locality boundary",
            "set-only card confirmation",
            "zero-result provider slice",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate the committed summary")
    args = parser.parse_args()
    try:
        inputs, errors = validate_inputs()
        if errors:
            raise GateError("\n".join(f"- {error}" for error in errors))
        rendered = json.dumps(summary(inputs), ensure_ascii=False, indent=2) + "\n"
        if args.check:
            if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
                raise GateError(f"stale summary: {OUTPUT.relative_to(ROOT)}")
        else:
            OUTPUT.write_text(rendered, encoding="utf-8")
        print(
            f"[ ok ] completeness gate: {inputs['source']['meta']['generatedFromRun']} + "
            f"{inputs['card']['meta']['generatedFromRun']}; "
            f"{len(inputs['asia']['tracks'])} Asia tracks; "
            f"{len(inputs['locality']['tracks'])} non-Asian tracks"
        )
        return 0
    except (GateError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        print(f"[FAIL] completeness gate: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

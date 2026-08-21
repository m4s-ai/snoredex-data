#!/usr/bin/env python3
"""Validate and render the positive-only Asian locality terminal matrix (#238)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "verification" / "asia_locality_matrix.json"
OUTPUT = ROOT / "verification" / "ASIA-LOCALITY-MATRIX.md"

REQUIRED_TRACKS = {
    "asia-jp", "asia-tw", "asia-hk", "asia-cn", "asia-kr",
    "asia-id", "asia-th", "asia-sea-en",
}
REQUIRED_REGRESSIONS = {
    "tw-svqp-f-012", "tw-sv-p-215", "tw-as5a-142", "cn-sv9-075",
    "id-sv9s-i-109", "id-sv4s-i-118", "id-sv6s-i-136",
    "kr-renumbered-positive-printings", "kr-spec-0037-positive",
}
REQUIRED_SAME_WORK_REGRESSIONS = {"cn-sv9-075"}
TERMINAL_STATES = {"complete", "needs-evidence", "blocked-by-source"}
DISPOSITIONS = {"positive-node", "positive-candidate", "needs-evidence", "held-positive"}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def indexes(manifest: dict[str, Any]) -> dict[str, Any]:
    from authoritative_graph import identity_view

    adapter = read_json(ROOT / "verification" / "card_discovery_adapters.json")
    staging = read_json(ROOT / "verification" / "card_discovery_staging.json")
    source_first = read_json(ROOT / "verification" / "source_first_prints.json")
    units = read_json(ROOT / "verification" / "units.json")
    identity = identity_view(read_json(ROOT / "verification" / "authoritative_graph.json"))
    records: dict[str, Any] = {}
    with (ROOT / "verification" / "card_discovery_records.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                records[record["recordId"]] = record
    record_context = {
        (contract["providerId"], contract["surfaceId"], item["rawLocale"]): item
        for contract in adapter["adapters"] for item in contract["slices"]
    }
    rekeys = {
        f"{report['issueNumber']}/{row['legacyUnitId']}": row
        for report in identity["reports"]["legacyIssueRekeys"]
        for row in report["rows"]
    }
    releases_by_source = {
        source_id: release
        for release in identity["cardReleases"]
        for source_id in release.get("sourceFirstRecordIds", [])
    }
    unit_claims: dict[str, list[dict[str, Any]]] = {}
    for claim in identity["candidateClaims"]:
        if (claim.get("claimKind"), claim.get("sourceKind")) != (
                "card-release", "legacy-language-unit"):
            continue
        unit_claims.setdefault(claim["sourceId"], []).append(claim)
    adapter_gaps = {item["gapId"]: item for item in adapter["gaps"]}
    local_gap_rows = manifest.get("localGaps", [])
    local_gaps = {item["gapId"]: item for item in local_gap_rows}
    return {
        "card-slice-contract": {
            item["sliceId"]: item
            for contract in adapter["adapters"] for item in contract["slices"]
        },
        "card-slice": {item["sliceId"]: item for item in staging["slices"]},
        "gap": {**adapter_gaps, **local_gaps},
        "adapter-gap-ids": set(adapter_gaps),
        "local-gap-ids": set(local_gaps),
        "local-gap-count": len(local_gap_rows),
        "source-first": {item["printId"]: item for item in source_first["prints"]},
        "unit": {item["unitId"]: item for item in units},
        "held": {item["specimenId"]: item for item in source_first["held"]},
        "card-record": records,
        "card-record-context": record_context,
        "legacy-rekey": rekeys,
        "release-by-source": releases_by_source,
        "release": {item["cardReleaseId"]: item for item in identity["cardReleases"]},
        "unit-claim": unit_claims,
        "specimen": {
            item["specimenId"]: item
            for item in read_json(ROOT / "verification" / "specimens.json")["specimens"]
        },
    }


def resolve(reference: str, data: dict[str, Any]) -> tuple[str, Any] | None:
    if ":" not in reference:
        return None
    kind, identifier = reference.split(":", 1)
    item = data.get(kind, {}).get(identifier)
    return (kind, item) if item is not None else None


def print_identity(kind: str, item: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    if kind == "source-first":
        return {
            "locality": item["locality"], "language": item["language"],
            "localSetCode": item["localSetCode"], "localNumber": item["localNumber"],
        }
    if kind == "unit":
        locality = {
            ("S-Chinese", "Simplified Chinese"): "CN",
        }.get((item["language"], item["market"]))
        return {
            "locality": locality, "language": item["language"],
            "localSetCode": item["setCode"], "localNumber": item["number"],
        }
    if kind == "card-record":
        context = data["card-record-context"][
            (item["providerId"], item["surfaceId"], item["rawLocale"])
        ]
        proposal = item["normalizationProposal"]
        return {
            "locality": item["locality"], "language": context["language"],
            "localSetCode": proposal["assertedLocalSetCode"],
            "localNumber": proposal["localCollectorNumber"],
        }
    if kind == "held":
        specimen = data["specimen"][item["specimenId"]]
        locality = {"Korean": "KR"}.get(specimen["language"])
        return {
            "locality": locality, "language": specimen["language"],
            "localSetCode": specimen.get("setCode") or None,
            "localNumber": specimen["number"],
        }
    raise ValueError(f"{kind} is not a printing evidence kind")


def validate_unit_materialization(
        label: str, unit: dict[str, Any], data: dict[str, Any], errors: list[str],
        *, expected_target: str | None = None, expected_work: str | None = None,
) -> None:
    unit_id = unit["unitId"]
    claims = data["unit-claim"].get(unit_id, [])
    if len(claims) != 1:
        errors.append(f"{label}: unit:{unit_id} resolves to {len(claims)} card-release claims")
        return
    claim = claims[0]
    target = claim.get("materializedTargetId")
    if (claim.get("evidenceStatus"), claim.get("disposition")) != (
            "confirmed", "established-and-mapped") or not target:
        errors.append(f"{label}: unit:{unit_id} does not materialize an established release")
        return
    if expected_target is not None and target != expected_target:
        errors.append(
            f"{label}: unit:{unit_id} materializes {target!r}, not {expected_target!r}")
    release = data["release"].get(target)
    if release is None:
        errors.append(f"{label}: unit:{unit_id} materialized release {target!r} is missing")
        return
    if claim["claimId"] not in release.get("establishingClaimIds", []):
        errors.append(f"{label}: unit:{unit_id} is not bound to release {target!r}")
    if expected_work is not None:
        if unit.get("cardKey") != expected_work:
            errors.append(
                f"{label}: unit:{unit_id} cardKey differs from expected work {expected_work!r}")
        if release.get("work") != expected_work:
            errors.append(
                f"{label}: unit:{unit_id} release work differs from {expected_work!r}")


def validate(manifest: dict[str, Any], data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    meta = manifest.get("meta", {})
    if (meta.get("schema"), meta.get("schemaVersion")) != (
            "snoredex-asia-locality-terminal-matrix", "1.0.0"):
        errors.append("meta must declare snoredex-asia-locality-terminal-matrix 1.0.0")
    overlap = data["adapter-gap-ids"] & data["local-gap-ids"]
    if overlap:
        errors.append(f"local gaps duplicate card-discovery gaps: {sorted(overlap)}")
    if data["local-gap-count"] != len(data["local-gap-ids"]):
        errors.append("local gaps contain duplicate ids")
    for gap in manifest.get("localGaps", []):
        if gap.get("terminalState") not in {"needs-evidence", "blocked-by-source"}:
            errors.append(f"local gap {gap.get('gapId')} has invalid terminal state")
        if not gap.get("reason") or not gap.get("retryCondition"):
            errors.append(f"local gap {gap.get('gapId')} needs reason and retryCondition")

    tracks = manifest.get("tracks", [])
    track_ids = [item.get("trackId") for item in tracks]
    if any(not isinstance(item, str) or not item for item in track_ids):
        errors.append("every track needs a non-empty string trackId")
        track_ids = [item for item in track_ids if isinstance(item, str) and item]
    duplicates = sorted(item for item, count in Counter(track_ids).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate tracks: {duplicates}")
    if set(track_ids) != REQUIRED_TRACKS:
        errors.append(
            f"track universe differs: missing={sorted(REQUIRED_TRACKS - set(track_ids))}, "
            f"extra={sorted(set(track_ids) - REQUIRED_TRACKS)}")

    for track in tracks:
        track_id = track.get("trackId", "<missing>")
        required = {
            "label", "locality", "language", "terminalState", "scope",
            "cardSliceIds", "gapIds", "evidenceRefs", "retryCondition",
        }
        missing = sorted(required - set(track))
        if missing:
            errors.append(f"{track_id}: missing fields {missing}")
            continue
        state = track["terminalState"]
        if state not in TERMINAL_STATES:
            errors.append(f"{track_id}: invalid terminalState {state!r}")
        if not track["scope"] or not track["retryCondition"]:
            errors.append(f"{track_id}: scope and retryCondition are required")
        if state == "complete" and not track["cardSliceIds"]:
            errors.append(f"{track_id}: complete requires a bounded card slice")
        if state != "complete" and not track["gapIds"]:
            errors.append(f"{track_id}: {state} requires an explicit gap")

        for slice_id in track["cardSliceIds"]:
            contract = data["card-slice-contract"].get(slice_id)
            retained = data["card-slice"].get(slice_id)
            if contract is None or retained is None:
                errors.append(f"{track_id}: unresolved card slice {slice_id}")
                continue
            if (contract["locality"], contract["language"]) != (
                    track["locality"], track["language"]):
                errors.append(f"{track_id}: card slice {slice_id} has another locality/language")
            accounting = retained.get("accounting", {})
            if retained.get("terminalState") != "complete":
                errors.append(f"{track_id}: card slice {slice_id} is not complete")
            if accounting.get("fetched") != accounting.get("accounted"):
                errors.append(f"{track_id}: card slice {slice_id} does not balance")

        for gap_id in track["gapIds"]:
            gap = data["gap"].get(gap_id)
            if gap is None:
                errors.append(f"{track_id}: unresolved gap {gap_id}")
            elif state != "complete" and gap.get("terminalState") != state:
                errors.append(
                    f"{track_id}: gap {gap_id} is {gap.get('terminalState')}, not {state}")

        for reference in track["evidenceRefs"]:
            resolved = resolve(reference, data)
            if resolved is None:
                errors.append(f"{track_id}: unresolved evidence reference {reference}")
                continue
            kind, item = resolved
            if kind == "source-first":
                if (item["locality"], item["language"]) != (
                        track["locality"], track["language"]):
                    errors.append(f"{track_id}: {reference} has another locality/language")
                if item["printId"] not in data["release-by-source"]:
                    errors.append(f"{track_id}: {reference} does not materialize a release")
            elif kind == "unit":
                identity = print_identity(kind, item, data)
                if (identity["locality"], identity["language"]) != (
                        track["locality"], track["language"]):
                    errors.append(f"{track_id}: {reference} has another locality/language")
                if item.get("status") != "confirmed" or not item.get("sourceUrl"):
                    errors.append(f"{track_id}: {reference} lacks positive source evidence")
                validate_unit_materialization(track_id, item, data, errors)
            elif kind == "card-record" and (
                    item["locality"] != track["locality"]):
                errors.append(f"{track_id}: {reference} has another locality")
            elif kind == "held" and item.get("language") != track["language"]:
                errors.append(f"{track_id}: {reference} has another language")

    regressions = manifest.get("minimumRegressions", [])
    regression_ids = [item.get("regressionId") for item in regressions]
    if set(regression_ids) != REQUIRED_REGRESSIONS:
        errors.append(
            "minimum regression universe differs: "
            f"missing={sorted(REQUIRED_REGRESSIONS - set(regression_ids))}, "
            f"extra={sorted(set(regression_ids) - REQUIRED_REGRESSIONS)}")
    if len(regression_ids) != len(set(regression_ids)):
        errors.append("minimum regressions contain duplicate ids")

    required_kind = {
        "positive-node": {"source-first", "unit", "legacy-rekey"},
        "positive-candidate": {"card-record"},
        "needs-evidence": {"gap"},
        "held-positive": {"held"},
    }
    for regression in regressions:
        regression_id = regression.get("regressionId", "<missing>")
        disposition = regression.get("disposition")
        if disposition not in DISPOSITIONS:
            errors.append(f"{regression_id}: invalid disposition {disposition!r}")
            continue
        refs = regression.get("evidenceRefs", [])
        expected_prints = regression.get("expectedPrints")
        if not refs or not regression.get("note"):
            errors.append(f"{regression_id}: evidenceRefs and note are required")
            continue
        if not isinstance(expected_prints, list):
            errors.append(f"{regression_id}: expectedPrints must be an array")
            expected_prints = []
        if disposition != "needs-evidence" and not expected_prints:
            errors.append(f"{regression_id}: {disposition} requires expectedPrints")
        kinds: set[str] = set()
        for reference in refs:
            resolved = resolve(reference, data)
            if resolved is None:
                errors.append(f"{regression_id}: unresolved evidence reference {reference}")
                continue
            kind, item = resolved
            kinds.add(kind)
            if kind == "source-first" and item["printId"] not in data["release-by-source"]:
                errors.append(f"{regression_id}: {reference} does not materialize a release")
            elif kind == "card-record" and item.get("bucket") != "new-candidate":
                errors.append(f"{regression_id}: {reference} is not a visible new candidate")
            elif kind == "legacy-rekey" and item.get("disposition") != "linked-local-counterpart":
                errors.append(f"{regression_id}: {reference} is not positively linked")
            elif kind == "unit" and (
                    item.get("status") != "confirmed" or not item.get("sourceUrl")):
                errors.append(f"{regression_id}: {reference} lacks positive source evidence")
            if kind == "unit":
                validate_unit_materialization(regression_id, item, data, errors)
        if not kinds & required_kind[disposition]:
            errors.append(f"{regression_id}: {disposition} lacks its required evidence kind")
        printing_refs = {
            reference for reference in refs
            if reference.split(":", 1)[0] in {"source-first", "unit", "card-record", "held"}
        }
        expected_refs = [item.get("reference") for item in expected_prints]
        if len(expected_refs) != len(set(expected_refs)):
            errors.append(f"{regression_id}: expectedPrints contain duplicate references")
        if set(expected_refs) != printing_refs:
            errors.append(
                f"{regression_id}: expected printing references differ: "
                f"expected={sorted(printing_refs)}, actual={sorted(set(expected_refs))}")
        for expected in expected_prints:
            reference = expected.get("reference")
            resolved = resolve(str(reference), data)
            if resolved is None:
                continue
            kind, item = resolved
            if kind not in {"source-first", "unit", "card-record", "held"}:
                errors.append(f"{regression_id}: {reference} is not printing evidence")
                continue
            required_fields = {"locality", "language", "localSetCode", "localNumber"}
            expected_fields = required_fields | {"reference"}
            if kind == "unit":
                expected_fields.add("materializedTargetId")
            if set(expected) != expected_fields:
                errors.append(f"{regression_id}: {reference} has incomplete expected identity")
                continue
            actual = print_identity(kind, item, data)
            declared = {field: expected[field] for field in required_fields}
            if actual != declared:
                errors.append(
                    f"{regression_id}: {reference} identity differs: "
                    f"expected={declared}, actual={actual}")
            if kind == "unit":
                validate_unit_materialization(
                    regression_id, item, data, errors,
                    expected_target=expected["materializedTargetId"],
                )
        expected_same_work = regression.get("expectedSameWork")
        if regression_id in REQUIRED_SAME_WORK_REGRESSIONS:
            if (not isinstance(expected_same_work, dict) or
                    set(expected_same_work) != {"cardKey", "counterpartUnitIds"} or
                    not isinstance(expected_same_work.get("cardKey"), str) or
                    not expected_same_work["cardKey"] or
                    not isinstance(expected_same_work.get("counterpartUnitIds"), list) or
                    not expected_same_work["counterpartUnitIds"] or
                    any(not isinstance(unit_id, str) or not unit_id
                        for unit_id in expected_same_work["counterpartUnitIds"])):
                errors.append(f"{regression_id}: expectedSameWork contract is incomplete")
            else:
                work = expected_same_work["cardKey"]
                primary_unit_ids = [reference.split(":", 1)[1] for reference in refs
                                    if reference.startswith("unit:")]
                if not primary_unit_ids:
                    errors.append(
                        f"{regression_id}: expectedSameWork requires a unit evidence reference")
                unit_ids = primary_unit_ids + expected_same_work["counterpartUnitIds"]
                if len(unit_ids) != len(set(unit_ids)):
                    errors.append(f"{regression_id}: same-work units contain duplicates")
                for unit_id in unit_ids:
                    unit = data["unit"].get(unit_id)
                    if unit is None:
                        errors.append(f"{regression_id}: unresolved same-work unit {unit_id}")
                        continue
                    validate_unit_materialization(
                        regression_id, unit, data, errors, expected_work=work)
        elif expected_same_work is not None:
            errors.append(f"{regression_id}: unexpected expectedSameWork contract")
        rekey_refs = {
            reference for reference in refs
            if reference.split(":", 1)[0] == "legacy-rekey"
        }
        expected_rekeys = regression.get("expectedRekeys", [])
        if not isinstance(expected_rekeys, list):
            errors.append(f"{regression_id}: expectedRekeys must be an array")
            expected_rekeys = []
        expected_rekey_refs = [item.get("reference") for item in expected_rekeys]
        if len(expected_rekey_refs) != len(set(expected_rekey_refs)):
            errors.append(f"{regression_id}: expectedRekeys contain duplicate references")
        if set(expected_rekey_refs) != rekey_refs:
            errors.append(
                f"{regression_id}: expected re-key references differ: "
                f"expected={sorted(rekey_refs)}, actual={sorted(set(expected_rekey_refs))}")
        for expected in expected_rekeys:
            required_fields = {"reference", "legacyUnitId", "sourceFirstRecordId"}
            if set(expected) != required_fields:
                errors.append(f"{regression_id}: expected re-key is incomplete")
                continue
            resolved = resolve(expected["reference"], data)
            if resolved is None or resolved[0] != "legacy-rekey":
                continue
            row = resolved[1]
            if (row["legacyUnitId"] != expected["legacyUnitId"] or
                    expected["sourceFirstRecordId"] not in row["sourceFirstRecordIds"]):
                errors.append(
                    f"{regression_id}: {expected['reference']} relationship differs")
    return errors


def render(manifest: dict[str, Any], data: dict[str, Any]) -> str:
    lines = [
        "<!-- doc: role=Asian locality terminal-state matrix; stage=generated -->",
        "<!-- generated by scripts/asia_locality_matrix.py; do not hand-edit -->",
        "# Asian locality terminal matrix",
        "",
        f"Reviewed **{manifest['meta']['reviewedAt']}** for [#{manifest['meta']['issue']}]"
        f"(https://github.com/m4s-ai/snoredex-data/issues/{manifest['meta']['issue']})",
        f"under parent [#{manifest['meta']['parentIssue']}]"
        f"(https://github.com/m4s-ai/snoredex-data/issues/{manifest['meta']['parentIssue']}).",
        "",
        manifest["meta"]["rule"],
        "",
        "| Track | Terminal state | Bounded slice accounting | Explicit gaps |",
        "|---|---|---|---|",
    ]
    for track in manifest["tracks"]:
        accounts = []
        for slice_id in track["cardSliceIds"]:
            accounting = data["card-slice"][slice_id]["accounting"]
            accounts.append(
                f"`{slice_id}` {accounting['accounted']}/{accounting['fetched']} "
                f"({accounting['newCandidate']} new candidates)")
        lines.append(
            f"| `{track['trackId']}` {track['label']} | `{track['terminalState']}` | "
            f"{'; '.join(accounts) or 'none'} | "
            f"{', '.join(f'`{item}`' for item in track['gapIds']) or 'none'} |")

    lines += ["", "## Minimum regressions", "",
              "| Regression | Disposition | Evidence |", "|---|---|---|"]
    for item in manifest["minimumRegressions"]:
        lines.append(
            f"| `{item['regressionId']}` {item['label']} | `{item['disposition']}` | "
            f"{', '.join(f'`{ref}`' for ref in item['evidenceRefs'])} — {item['note']} |")

    residual = [
        item for item in manifest["minimumRegressions"]
        if item["disposition"] in {"needs-evidence", "held-positive"}
    ]
    lines += ["", "## Residual blockers", ""]
    if residual:
        for item in residual:
            lines.append(f"- `{item['regressionId']}` — {item['note']}")
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = read_json(MANIFEST)
    data = indexes(manifest)
    errors = validate(manifest, data)
    if errors:
        print("Asia locality matrix validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    expected = render(manifest, data)
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("Asia locality matrix projection is stale", file=sys.stderr)
            return 1
        print(
            f"Asia locality matrix current ({len(manifest['tracks'])} tracks, "
            f"{len(manifest['minimumRegressions'])} regressions)")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

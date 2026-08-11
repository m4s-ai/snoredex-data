#!/usr/bin/env python3
"""Validate and render the evidenced non-Asian locality/era matrix (#139).

The reviewed JSON distinguishes established localities from candidate tracks and keeps every
era statement tied to an existing capability edge, retained observation, adapter slice, unit,
owner decision, or explicit source gap. It does not query the network or mutate verdicts.

    python scripts/locality_matrix.py
    python scripts/locality_matrix.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "verification" / "locality_era_matrix.json"
OUTPUT = ROOT / "verification" / "LOCALITY-ERA-MATRIX.md"

REQUIRED_TRACKS = {
    "west-en", "west-fr", "west-de", "west-it", "west-es-eu",
    "west-pt-unqualified", "latam-es", "latam-pt-br", "west-nl", "west-pl",
    "west-ru", "sea-en-coordinated",
}
REQUIRED_EXCLUSIONS = {"U0492": "Czech", "U0493": "Hungarian"}
UNIVERSE_STATES = {
    "established-positive", "owner-scoped", "provisional-legacy",
    "candidate-needs-evidence", "coordinated",
}
DISCOVERY_STATES = {
    "ready-for-child", "needs-evidence", "blocked-by-source", "coordinated",
}
ERA_STATES = {
    "positive-observations-only", "owner-scoped", "owner-bounded-end",
    "needs-evidence", "blocked-by-source", "coordinated",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def collect_refs(track: dict[str, Any]) -> Iterable[str]:
    yield from track.get("evidenceRefs", [])
    for era in track.get("eraSegments", []):
        yield from era.get("evidenceRefs", [])
    discovery = track.get("discovery", {})
    yield from discovery.get("sourceRefs", [])
    yield from discovery.get("gapRefs", [])


def reference_indexes() -> dict[str, Any]:
    capabilities = read_json(ROOT / "verification" / "source_capabilities.json")
    surfaces = {item["surfaceId"]: item for item in capabilities["surfaces"]}
    edges = {
        edge["edgeId"]: edge
        for surface in capabilities["surfaces"]
        for edge in surface.get("coverageEdges", [])
    }
    observations = {
        item["observationId"]: item for item in capabilities["observations"]
    }
    source_adapters = read_json(ROOT / "verification" / "source_adapters.json")
    source_slices = {
        item["sliceId"]: item
        for adapter in source_adapters["adapters"]
        for item in adapter["slices"]
    }
    retained_slices = {
        item["sliceId"]: item
        for item in read_json(ROOT / "verification" / "source_adapter_staging.json")["slices"]
    }
    card_discovery = read_json(ROOT / "verification" / "card_discovery_adapters.json")
    return {
        "surface": surfaces,
        "edge": edges,
        "observation": observations,
        "slice": source_slices,
        "retained-slice": retained_slices,
        "source-gap": {item["gapId"]: item for item in source_adapters["gaps"]},
        "card-gap": {item["gapId"]: item for item in card_discovery["gaps"]},
        "unit": {item["unitId"]: item for item in read_json(ROOT / "verification" / "units.json")},
        "adjudication": {
            item["adjudicationId"]: item
            for item in read_json(ROOT / "verification" / "owner_adjudications.json")["decisions"]
        },
        "decision": read_json(ROOT / "verification" / "print_identity_schema.json")["ownerDecisions"],
    }


def validate_reference(reference: str, track: dict[str, Any], indexes: dict[str, Any]) -> list[str]:
    if ":" not in reference:
        return [f"{track['trackId']}: malformed evidence reference {reference!r}"]
    kind, identifier = reference.split(":", 1)
    if kind == "document":
        path = (ROOT / identifier).resolve()
        if ROOT not in path.parents or not path.is_file():
            return [f"{track['trackId']}: document reference does not resolve: {identifier}"]
        return []
    if kind not in indexes:
        return [f"{track['trackId']}: unknown evidence reference kind {kind!r}"]
    if identifier not in indexes[kind]:
        return [f"{track['trackId']}: unresolved {kind} reference {identifier!r}"]

    item = indexes[kind][identifier]
    errors: list[str] = []
    if kind == "edge":
        coverage = item["coverage"]
        if track["locality"] not in coverage["localities"] and "GLOBAL" not in coverage["localities"]:
            errors.append(f"{track['trackId']}: edge {identifier} does not cover {track['locality']}")
        languages = coverage["languages"]
        if track["language"] not in languages and "MULTIPLE" not in languages:
            errors.append(f"{track['trackId']}: edge {identifier} does not cover {track['language']}")
    elif kind == "slice":
        if identifier not in indexes["retained-slice"]:
            errors.append(f"{track['trackId']}: slice {identifier} has no retained run")
        if item["locality"] != track["locality"] or item["language"] != track["language"]:
            errors.append(f"{track['trackId']}: slice {identifier} has another locality/language")
    elif kind == "unit" and item["language"] != track["language"]:
        errors.append(f"{track['trackId']}: unit {identifier} is {item['language']}, not {track['language']}")
    return errors


def validate(manifest: dict[str, Any], indexes: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    meta = manifest.get("meta", {})
    if meta.get("schema") != "snoredex-locality-era-matrix" or meta.get("schemaVersion") != "1.0.0":
        errors.append("meta must declare snoredex-locality-era-matrix schemaVersion 1.0.0")
    tracks = manifest.get("tracks")
    if not isinstance(tracks, list):
        return errors + ["tracks must be an array"]

    exclusions = manifest.get("excludedLegacyClaims")
    if not isinstance(exclusions, list):
        errors.append("excludedLegacyClaims must be an array")
    else:
        actual_exclusions = {
            item.get("unitId"): item.get("language") for item in exclusions
        }
        if actual_exclusions != REQUIRED_EXCLUSIONS:
            errors.append(
                f"excluded legacy claims differ: expected={REQUIRED_EXCLUSIONS}, "
                f"actual={actual_exclusions}"
            )
        for item in exclusions:
            unit = indexes["unit"].get(item.get("unitId"))
            if not unit or unit.get("language") != item.get("language"):
                errors.append(f"excluded claim does not resolve: {item}")
            elif unit.get("status") != "contradicted":
                errors.append(f"excluded claim {item['unitId']} is not contradicted")
            if not item.get("reason"):
                errors.append(f"excluded claim {item.get('unitId')} needs a reason")

    ids = [item.get("trackId") for item in tracks]
    duplicates = sorted(item for item, count in Counter(ids).items() if item and count > 1)
    if duplicates:
        errors.append(f"duplicate track ids: {duplicates}")
    missing = sorted(REQUIRED_TRACKS - set(ids))
    extra = sorted(set(ids) - REQUIRED_TRACKS)
    if missing or extra:
        errors.append(f"track universe differs: missing={missing}, extra={extra}")

    identity_pairs: set[tuple[str, str]] = set()
    for track in tracks:
        track_id = track.get("trackId", "<missing-trackId>")
        required = {
            "label", "locality", "language", "bcp47", "script", "universeStatus",
            "scope", "identityBoundary", "legacyUnitScope", "eraSegments", "discovery",
            "evidenceRefs", "childIssue",
        }
        absent = sorted(required - set(track))
        if absent:
            errors.append(f"{track_id}: missing fields {absent}")
            continue
        if track["universeStatus"] not in UNIVERSE_STATES:
            errors.append(f"{track_id}: invalid universeStatus {track['universeStatus']!r}")
        pair = (track["locality"], track["bcp47"])
        if pair in identity_pairs:
            errors.append(f"{track_id}: duplicate locality/BCP-47 identity {pair}")
        identity_pairs.add(pair)
        if track.get("absencePolicy") != "positive-only":
            errors.append(f"{track_id}: locality discovery must remain positive-only")
        child_issue = track["childIssue"]
        if not isinstance(child_issue, int) or isinstance(child_issue, bool) or child_issue < 1:
            errors.append(f"{track_id}: childIssue must be a positive GitHub issue number")
        if track.get("coordinationIssue") and child_issue != track["coordinationIssue"]:
            errors.append(f"{track_id}: coordinated track must link its coordination issue")

        discovery = track["discovery"]
        state = discovery.get("state")
        if state not in DISCOVERY_STATES:
            errors.append(f"{track_id}: invalid discovery state {state!r}")
        if state == "ready-for-child" and not any(
            ref.startswith("slice:") for ref in discovery.get("sourceRefs", [])
        ):
            errors.append(f"{track_id}: ready-for-child requires a retained source slice")
        if state in {"needs-evidence", "blocked-by-source"} and not discovery.get("gapRefs"):
            errors.append(f"{track_id}: {state} requires an explicit gap reference")
        if state == "coordinated" and not track.get("coordinationIssue"):
            errors.append(f"{track_id}: coordinated track requires coordinationIssue")

        eras = track["eraSegments"]
        if not eras:
            errors.append(f"{track_id}: at least one era segment is required")
        for era in eras:
            if era.get("state") not in ERA_STATES:
                errors.append(f"{track_id}/{era.get('eraId')}: invalid era state")
            if era.get("absenceAllowed") is not False:
                errors.append(f"{track_id}/{era.get('eraId')}: era discovery cannot imply absence")
            if not era.get("basis") or not era.get("evidenceRefs"):
                errors.append(f"{track_id}/{era.get('eraId')}: basis and evidenceRefs are required")

        references = list(collect_refs(track))
        for reference in references:
            errors.extend(validate_reference(reference, track, indexes))
        if track["universeStatus"] == "established-positive":
            positive = False
            for reference in references:
                kind, identifier = reference.split(":", 1)
                if kind == "observation":
                    positive = True
                elif kind == "unit" and indexes["unit"].get(identifier, {}).get("status") == "confirmed":
                    positive = True
            if not positive:
                errors.append(f"{track_id}: established-positive needs a positive observation or confirmed unit")
        if track["universeStatus"] == "candidate-needs-evidence":
            for reference in references:
                kind, identifier = reference.split(":", 1)
                if kind == "unit" and indexes["unit"].get(identifier, {}).get("status") == "confirmed":
                    errors.append(f"{track_id}: candidate track cites confirmed unit {identifier}")

        legacy = track["legacyUnitScope"]
        if legacy.get("include"):
            matching = [
                item for item in indexes["unit"].values()
                if item["language"] == track["language"]
                and (not legacy.get("market") or item.get("market") == legacy["market"])
            ]
            if not matching:
                errors.append(f"{track_id}: declared legacy unit scope is empty")
    return errors


def legacy_counts(track: dict[str, Any], units: dict[str, dict[str, Any]]) -> str:
    scope = track["legacyUnitScope"]
    if not scope.get("include"):
        return "not represented"
    rows = [
        item for item in units.values()
        if item["language"] == track["language"]
        and (not scope.get("market") or item.get("market") == scope["market"])
    ]
    counts = Counter(item["status"] for item in rows)
    return f"{counts['confirmed']} confirmed / {counts['contradicted']} contradicted"


def md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(manifest: dict[str, Any], indexes: dict[str, Any]) -> str:
    tracks = manifest["tracks"]
    lines = [
        "<!-- doc: role=evidenced locality and era coverage matrix; stage=generated -->",
        "<!-- generated by scripts/locality_matrix.py; do not hand-edit -->",
        "# Locality and era coverage matrix",
        "",
        f"Reviewed **{manifest['meta']['reviewedAt']}** for [#{manifest['meta']['issue']}](https://github.com/m4s-ai/snoredex-data/issues/{manifest['meta']['issue']}).",
        "",
        "This is a discovery contract, not a print manifest. A retained provider slice means every",
        "row returned by that request was accounted; it does not mean every set, era, card, finish,",
        "or regional edition is covered. A zero result is unknown. Candidate tracks are deliberately",
        "outside the established locality universe until positive evidence admits them.",
        "",
        "## Excluded legacy language claims",
        "",
        "These contradicted marketplace language claims are settled non-tracks and receive no child",
        "issue unless new positive physical-card evidence overturns the recorded decision:",
        "",
    ]
    for item in manifest["excludedLegacyClaims"]:
        lines.append(
            f"- `{item['unitId']}` / **{item['language']}** — {item['reason']}"
        )
    lines += [
        "",
        "| Track | Universe state | Locality / language | Era state | Discovery | Child | Legacy audit |",
        "|---|---|---|---|---|---|---|",
    ]
    for track in tracks:
        era_state = "; ".join(
            f"{era['eraId']}: {era['state']}" for era in track["eraSegments"]
        )
        lines.append(
            f"| `{md(track['trackId'])}` {md(track['label'])} | {md(track['universeStatus'])} | "
            f"`{md(track['locality'])}` / {md(track['language'])} (`{md(track['bcp47'])}`) | "
            f"{md(era_state)} | {md(track['discovery']['state'])} | "
            f"[#{track['childIssue']}](https://github.com/m4s-ai/snoredex-data/issues/{track['childIssue']}) | "
            f"{md(legacy_counts(track, indexes['unit']))} |"
        )

    lines += ["", "## Track detail", ""]
    for track in tracks:
        lines += [
            f"### {track['label']} (`{track['trackId']}`)",
            "",
            f"- **Scope:** {track['scope']}",
            f"- **Identity boundary:** {track['identityBoundary']}",
            f"- **Discovery:** `{track['discovery']['state']}` — {track['discovery']['retryCondition']}",
            f"- **Execution issue:** [#{track['childIssue']}](https://github.com/m4s-ai/snoredex-data/issues/{track['childIssue']})",
            f"- **Evidence:** {', '.join(f'`{item}`' for item in track['evidenceRefs']) or 'none'}",
        ]
        if track.get("distributionRegions"):
            lines.append(f"- **Distribution regions to split:** {', '.join(track['distributionRegions'])}")
        if track.get("coordinationIssue"):
            lines.append(f"- **Coordination:** #{track['coordinationIssue']}")
        if track.get("openQuestions"):
            lines.append(f"- **Open:** {'; '.join(track['openQuestions'])}")
        lines += ["", "Era segments:", ""]
        for era in track["eraSegments"]:
            boundary = " → ".join(item or "open" for item in (era.get("start"), era.get("end")))
            lines.append(
                f"- `{era['eraId']}` ({boundary}; `{era['state']}`): {era['basis']} "
                f"Evidence: {', '.join(f'`{item}`' for item in era['evidenceRefs'])}."
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    manifest = read_json(MANIFEST)
    indexes = reference_indexes()
    errors = validate(manifest, indexes)
    if errors:
        print("locality matrix validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    expected = render(manifest, indexes)
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("locality matrix projection is stale", file=sys.stderr)
            return 1
        print(f"locality matrix current ({len(manifest['tracks'])} tracks)")
        return 0

    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(expected)
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(manifest['tracks'])} tracks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

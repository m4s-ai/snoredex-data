#!/usr/bin/env python3
"""Fetch and project source-first local-set catalogue runs (#147).

The reviewed adapter contract is ``verification/source_adapters.json``. Network access occurs
only with ``--refresh``; normal generation and CI checks read committed immutable run
responses. Enumeration inputs are provider-native endpoints, never legacy set codes, known cards,
units, or verdict stores.

    python scripts/source_adapters.py --refresh --run-id 20260809T120000Z
    python scripts/source_adapters.py
    python scripts/source_adapters.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from bulbapedia_historical import HistoricalIndexError, parse_historical_index
from source_capabilities import schema_errors

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "verification" / "source_adapters.json"
SCHEMA_PATH = ROOT / "verification" / "source_adapter_schema.json"
CAPABILITY_PATH = ROOT / "verification" / "source_capability_graph.json"
RUNS_DIR = ROOT / "verification" / "runs" / "source-adapters"
OUTPUT_PATH = ROOT / "verification" / "source_adapter_staging.json"
RECORDS_PATH = ROOT / "verification" / "source_adapter_records.jsonl"
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
DATE_PATTERNS = (
    (re.compile(r"^[0-9]{4}$"), "year"),
    (re.compile(r"^[0-9]{4}-[0-9]{2}$"), "month"),
    (re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"), "day"),
)


class AdapterError(ValueError):
    """The adapter contract or a retained run violates #147."""


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def content_hash(value: bytes | Any) -> str:
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def capability_pin(capability: Any, surface_ids: Iterable[str] | None = None) -> str:
    """Hash the capability graph's *capabilities*, not the day it was written.

    The pin used the whole document, and the document carries `meta.generated`. So a retained run
    stopped validating the moment anyone regenerated the graph on a later date — no capability
    changed, only the calendar. Because a change to the language store flows into the source
    registry and from there into the graph, this fired on any ordinary write pass made the day after
    the graph was last written, and the documented command order regenerates the graph every time.

    (Spelling that store's filename here would trip `N12`, which scans this file's source text for
    forbidden seed inputs and does not distinguish prose from code.)

    Two things are dropped, and both are dropped for the same reason: they are not capabilities.

    `meta.generated` is the day the file was written. `sourceResolution` is the routing of whatever
    evidence rows the source registry happens to hold right now — one row per URL — so adding a
    single citation to any unit rewrote it and expired every retained run. A run was captured under
    a set of capabilities; which URLs exist today is not part of that set, and pinning it made
    ordinary evidence work impossible rather than making provenance stronger.

    What remains pinned is the contract itself: providers, surfaces, coverage edges, observations,
    and `meta.schemaVersion`. A surface, edge, boundary or absence scope that moves still changes
    this hash, which is the whole point of having one.

    THE PIN COVERS THE SURFACES THE RUN USED, NOT THE WHOLE GRAPH

    Pinning every provider made the graph unable to grow. This run touched `tcgdex` and nothing
    else, yet declaring an unrelated surface on `pokemon-official` — a different provider, no shared
    edge — changed the hash and expired it. Measured: adding a locale-archive surface takes the
    graph from 23 edges to 24, and both retained runs then fail with "captured under another
    capability graph" despite neither having fetched a single byte from that provider.

    That is not provenance, it is a coupling. A run was captured under the capabilities **it used**,
    and those are recorded per request: `providerId`, `surfaceId`, `coverageEdgeId`. So the pin is
    computed over exactly that slice, and a manifest records which surfaces it covers so validation
    reconstructs the same slice rather than guessing.

    A surface the run used still cannot move without expiring it, which is the property worth
    keeping. A surface it never touched no longer can, which is the defect.
    """
    document = capability_slice(capability, surface_ids)
    return content_hash(document)


def capability_slice(capability: Any, surface_ids: Iterable[str] | None) -> dict[str, Any]:
    """The part of the capability graph a run depends on.

    `surface_ids` of `None` means the whole graph, which is what the pin meant before it was
    scoped. It is kept so a manifest written under the old rule can still be read and explained,
    never so a new run can be written that way.
    """
    document = {key: value for key, value in capability.items() if key != "sourceResolution"}
    document["meta"] = {
        key: value for key, value in document.get("meta", {}).items() if key != "generated"
    }
    if surface_ids is None:
        return document

    # `meta` carries global tallies — `counts`, `surfaceStates` — that move whenever any provider
    # gains a surface. Keeping them would have re-introduced the very coupling this scoping removes,
    # by a quieter route: the slice's own rows would be identical and the hash would still change.
    # Only the contract's identity survives into a scoped pin.
    document["meta"] = {
        key: value for key, value in document.get("meta", {}).items()
        if key in ("schema", "schemaVersion")
    }

    wanted = set(surface_ids)
    surfaces = [row for row in document.get("surfaces", []) if row["surfaceId"] in wanted]
    missing = wanted - {row["surfaceId"] for row in surfaces}
    if missing:
        raise AdapterError(
            f"run cites surfaces the capability graph does not declare: {sorted(missing)}"
        )
    providers = {row["providerId"] for row in surfaces}
    document["surfaces"] = surfaces
    document["providers"] = [
        row for row in document.get("providers", []) if row["providerId"] in providers
    ]
    document["coverageEdges"] = [
        row for row in document.get("coverageEdges", []) if row["surfaceId"] in wanted
    ]
    document["observations"] = [
        row for row in document.get("observations", []) if row["surfaceId"] in wanted
    ]
    return document


def manifest_surfaces(manifest: dict[str, Any]) -> list[str] | None:
    """Which surfaces a manifest was pinned against.

    Recorded explicitly since the pin was scoped. A manifest without the field predates the change
    and was pinned against the whole graph; `None` preserves that reading rather than silently
    re-scoping a hash somebody else computed.
    """
    recorded = manifest.get("capabilityGraphSurfaces")
    if recorded is None:
        return None
    return sorted(recorded)


def surfaces_used(requests: Iterable[dict[str, Any]]) -> list[str]:
    return sorted({row["surfaceId"] for row in requests if row.get("surfaceId")})


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_projection(projection: dict[str, Any]) -> tuple[str, str]:
    records_text = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in projection["records"]
    )
    summary = {key: value for key, value in projection.items() if key != "records"}
    summary["recordsPath"] = "verification/source_adapter_records.jsonl"
    summary["recordsHash"] = content_hash(records_text.encode("utf-8"))
    return json.dumps(summary, ensure_ascii=False, indent=2) + "\n", records_text


def raw_key(provider_id: str, surface_id: str, raw_locale: str, raw_provider_id: str) -> str:
    return "|".join((provider_id, surface_id, raw_locale, raw_provider_id))


def validate_contract(contract: dict[str, Any], capability: dict[str, Any]) -> None:
    schema = read_json(SCHEMA_PATH)
    errors = schema_errors(contract, schema, schema)
    if errors:
        raise AdapterError(
            "contract violates source_adapter_schema.json:\n  - " + "\n  - ".join(errors[:30])
        )

    providers = {row["providerId"] for row in capability["providers"]}
    surfaces = {row["surfaceId"]: row for row in capability["surfaces"]}
    edges = {row["edgeId"]: row for row in capability["coverageEdges"]}
    seen_adapters: set[str] = set()
    seen_slices: set[str] = set()
    active_surfaces: set[str] = set()

    for adapter in contract["adapters"]:
        adapter_id = adapter["adapterId"]
        if adapter_id in seen_adapters:
            raise AdapterError(f"duplicate adapterId {adapter_id}")
        seen_adapters.add(adapter_id)
        if adapter["providerId"] not in providers:
            raise AdapterError(f"adapter {adapter_id} names unknown provider")
        response_format = adapter.get("responseFormat", "json-array")
        if response_format not in {"json-array", "bulbapedia-historical-wikitext"}:
            raise AdapterError(f"adapter {adapter_id} has an unsupported response format")
        if response_format == "bulbapedia-historical-wikitext" and (
            not isinstance(adapter.get("revisionId"), int)
            or not isinstance(adapter.get("pageTitle"), str)
        ):
            raise AdapterError(f"adapter {adapter_id} lacks its page title or revision id")
        surface = surfaces.get(adapter["surfaceId"])
        if not surface or surface["providerId"] != adapter["providerId"]:
            raise AdapterError(f"adapter {adapter_id} does not resolve to its provider surface")
        if surface["adapterState"] != "active":
            raise AdapterError(f"adapter {adapter_id} requires active surface {adapter['surfaceId']}")
        active_surfaces.add(adapter["surfaceId"])
        for slice_row in adapter["slices"]:
            slice_id = slice_row["sliceId"]
            if slice_id in seen_slices:
                raise AdapterError(f"duplicate sliceId {slice_id}")
            seen_slices.add(slice_id)
            edge = edges.get(slice_row["coverageEdgeId"])
            if not edge or edge["surfaceId"] != adapter["surfaceId"]:
                raise AdapterError(f"slice {slice_id} does not resolve to its surface edge")
            coverage = edge["coverage"]
            for field, value in (
                ("localities", slice_row["locality"]),
                ("languages", slice_row["language"]),
                ("scripts", slice_row["script"]),
            ):
                if value not in coverage[field] and "MULTIPLE" not in coverage[field]:
                    raise AdapterError(f"slice {slice_id} exceeds edge {field}: {value}")
            if adapter["category"] not in coverage["productCategories"]:
                raise AdapterError(f"slice {slice_id} exceeds edge product categories")

    mapping_keys: set[str] = set()
    for mapping in contract["explicitMappings"]:
        key = raw_key(
            mapping["providerId"], mapping["surfaceId"],
            mapping["rawLocale"], mapping["rawProviderId"],
        )
        if key in mapping_keys:
            raise AdapterError(f"duplicate explicit mapping {key}")
        mapping_keys.add(key)
        if mapping["surfaceId"] not in active_surfaces:
            raise AdapterError(f"mapping {key} does not belong to an active adapter surface")

    seen_gaps: set[str] = set()
    for gap in contract["gaps"]:
        if gap["gapId"] in seen_gaps:
            raise AdapterError(f"duplicate gapId {gap['gapId']}")
        seen_gaps.add(gap["gapId"])
        if gap["providerId"] not in providers:
            raise AdapterError(f"gap {gap['gapId']} names unknown provider")
        if gap["surfaceId"] is not None:
            surface = surfaces.get(gap["surfaceId"])
            if not surface or surface["providerId"] != gap["providerId"]:
                raise AdapterError(f"gap {gap['gapId']} does not resolve to its provider surface")


def load_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    contract = read_json(CONTRACT_PATH)
    capability = read_json(CAPABILITY_PATH)
    validate_contract(contract, capability)
    return contract, capability


def parse_response(
    adapter: dict[str, Any], slice_row: dict[str, Any], raw: bytes
) -> list[dict[str, Any]]:
    response_format = adapter.get("responseFormat", "json-array")
    if response_format == "bulbapedia-historical-wikitext":
        try:
            return parse_historical_index(
                raw,
                slice_row["language"],
                expected_revision=adapter["revisionId"],
                expected_title=adapter["pageTitle"],
            )
        except HistoricalIndexError as error:
            raise AdapterError(str(error)) from error
    payload = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(payload, list):
        raise AdapterError("response root is not an array")
    return payload


def date_precision(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    for pattern, precision in DATE_PATTERNS:
        if pattern.fullmatch(text):
            return precision
    return "source-native"


def finish_profile(
    source_record: dict[str, Any], record_id: str, run_errors: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, bool]:
    text = source_record.get("finishProfileText")
    if text is None:
        return None, False
    profile = {
        "verbatim": text,
        "section": source_record.get("finishProfileSection"),
        "revision": source_record.get("finishProfileRevision"),
        "clauses": source_record.get("finishProfileClauses"),
        "unparsedText": source_record.get("finishProfileUnparsedText"),
    }
    parked = False
    if not isinstance(text, str) or not text.strip():
        run_errors.append({"code": "invalid-finish-profile", "recordId": record_id})
        parked = True
    if not profile["section"] or not profile["revision"]:
        run_errors.append({"code": "finish-profile-missing-context", "recordId": record_id})
        parked = True
    clauses = profile["clauses"]
    if not isinstance(clauses, list) or not clauses:
        run_errors.append({"code": "unparsed-finish-profile", "recordId": record_id})
        parked = True
    else:
        for clause in clauses:
            if not isinstance(clause, dict) or not clause.get("verbatim") or clause.get(
                "disposition"
            ) not in {"mapped", "needs-evidence", "positively-excluded"}:
                run_errors.append({"code": "invalid-finish-clause", "recordId": record_id})
                parked = True
            elif clause["disposition"] == "needs-evidence":
                parked = True
    if profile["unparsedText"] not in {None, ""}:
        run_errors.append({"code": "silently-unparsed-finish-clause", "recordId": record_id})
        parked = True
    profile["disposition"] = "needs-evidence" if parked else "parsed-proposal"
    return profile, parked


def normalize_record(
    adapter: dict[str, Any],
    slice_row: dict[str, Any],
    request: dict[str, Any],
    source_record: Any,
    mappings: dict[str, dict[str, Any]],
    run_errors: list[dict[str, Any]],
    duplicate_occurrence: int | None = None,
) -> dict[str, Any]:
    if not isinstance(source_record, dict):
        provider_id = "<unparseable>"
        local_name = None
        local_code = None
        source_record = {"unparsedValue": source_record}
    else:
        provider_id = source_record.get("id")
        local_name = source_record.get("name")
        local_code = source_record.get("id")

    provider_key = raw_key(
        adapter["providerId"], adapter["surfaceId"], slice_row["rawLocale"],
        str(provider_id),
    )
    key = provider_key if duplicate_occurrence is None else (
        f"{provider_key}|duplicate-occurrence:{duplicate_occurrence}"
    )
    stable_id = "raw:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    mapping = mappings.get(key)
    profile, finish_parked = finish_profile(source_record, stable_id, run_errors)
    excluded = source_record.get("isDigitalOnly") is True
    ambiguous = duplicate_occurrence is not None or not isinstance(
        provider_id, str
    ) or not provider_id or not isinstance(
        local_name, str
    ) or not local_name

    if excluded:
        bucket = "positively-excluded"
        bucket_basis = "source record explicitly sets isDigitalOnly=true"
    elif ambiguous or finish_parked:
        bucket = "ambiguous/needs-evidence"
        bucket_basis = (
            "provider reuses this raw id within one locale; every occurrence stays separate"
            if duplicate_occurrence is not None else
            "required identity field or finish-profile parse needs evidence"
        )
    elif mapping:
        bucket = "mapped"
        bucket_basis = mapping["evidence"]
    else:
        bucket = "new-candidate"
        bucket_basis = "positive provider-native set record; no explicit identity mapping exists"

    release_date = source_record.get("releaseDate")
    raw = {
        "localName": local_name,
        "localCode": local_code,
        "category": adapter["category"],
        "language": slice_row["language"],
        "script": slice_row["script"],
        "cardCount": source_record.get("cardCount"),
        "releaseDate": release_date,
        "releaseStatus": source_record.get("releaseStatus"),
        "market": slice_row["locality"],
        "finishProfileText": source_record.get("finishProfileText"),
    }
    record_hash = content_hash(source_record)
    identity_hint = {
        "providerId": adapter["providerId"],
        "surfaceId": adapter["surfaceId"],
        "rawLocale": slice_row["rawLocale"],
        "category": adapter["category"],
        "localName": local_name,
        "releaseDate": release_date,
    }
    return {
        "recordId": stable_id,
        "stableKey": key,
        "identityHintHash": content_hash(identity_hint),
        "providerId": adapter["providerId"],
        "surfaceId": adapter["surfaceId"],
        "coverageEdgeId": slice_row["coverageEdgeId"],
        "endpoint": request["endpoint"],
        "queryParameters": request["queryParameters"],
        "rawProviderId": provider_id,
        "rawProviderIdOccurrence": duplicate_occurrence,
        "rawLocale": slice_row["rawLocale"],
        "locality": slice_row["locality"],
        "retrievedAt": request["retrievedAt"],
        "responseHash": request["responseHash"],
        "recordHash": record_hash,
        "runId": request["runId"],
        "raw": raw,
        "sourceRecord": source_record,
        "bucket": bucket,
        "bucketBasis": bucket_basis,
        "normalizationProposal": {
            "entityType": "local-set",
            "localName": local_name,
            "localCode": local_code,
            "locality": slice_row["locality"],
            "language": slice_row["language"],
            "script": slice_row["script"],
            "releaseDate": release_date,
            "releaseDatePrecision": date_precision(release_date),
            "target": None if mapping is None else {
                "targetType": mapping["targetType"], "targetId": mapping["targetId"]
            },
            "crossLocaleMerge": False,
            "finishProfile": profile,
        },
    }


def diff_records(current: list[dict[str, Any]], previous: list[dict[str, Any]]) -> dict[str, Any]:
    current_by_key = {row["stableKey"]: row for row in current}
    previous_by_key = {row["stableKey"]: row for row in previous}
    added = set(current_by_key) - set(previous_by_key)
    disappeared = set(previous_by_key) - set(current_by_key)
    changed = sorted(
        key for key in set(current_by_key) & set(previous_by_key)
        if current_by_key[key]["recordHash"] != previous_by_key[key]["recordHash"]
    )

    old_hints: dict[str, list[str]] = defaultdict(list)
    new_hints: dict[str, list[str]] = defaultdict(list)
    for key in disappeared:
        old_hints[previous_by_key[key]["identityHintHash"]].append(key)
    for key in added:
        new_hints[current_by_key[key]["identityHintHash"]].append(key)
    rekeyed = []
    for hint in sorted(set(old_hints) & set(new_hints)):
        old_keys = sorted(old_hints[hint])
        new_keys = sorted(new_hints[hint])
        for old_key, new_key in zip(old_keys, new_keys):
            rekeyed.append({"from": old_key, "to": new_key, "identityHintHash": hint})
            disappeared.remove(old_key)
            added.remove(new_key)
    return {
        "added": sorted(added),
        "changed": changed,
        "disappeared": sorted(disappeared),
        "rekeyedCandidates": rekeyed,
        "counts": {
            "added": len(added),
            "changed": len(changed),
            "disappeared": len(disappeared),
            "rekeyedCandidates": len(rekeyed),
        },
    }


def build_projection(
    contract: dict[str, Any], manifest: dict[str, Any], run_dir: Path,
    previous: dict[str, Any] | None,
    capability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    adapters = {row["adapterId"]: row for row in contract["adapters"]}
    slices = {
        row["sliceId"]: (adapter, row)
        for adapter in contract["adapters"] for row in adapter["slices"]
    }
    mappings = {
        raw_key(row["providerId"], row["surfaceId"], row["rawLocale"], row["rawProviderId"]): row
        for row in contract["explicitMappings"]
    }
    records: list[dict[str, Any]] = []
    run_errors: list[dict[str, Any]] = list(manifest.get("failures", []))
    slice_rows = []
    seen_keys: set[str] = set()

    if manifest.get("contractHash") != content_hash(contract):
        raise AdapterError(f"run {manifest.get('runId')} was captured under another contract")
    if manifest.get("coverageVersion") != contract["meta"]["coverageVersion"]:
        raise AdapterError(f"run {manifest.get('runId')} has another coverage version")
    if capability is not None and manifest.get("capabilityGraphHash") != capability_pin(
            capability, manifest_surfaces(manifest)):
        raise AdapterError(f"run {manifest.get('runId')} was captured under another capability graph")
    expected_slice_ids = set(slices)
    request_slice_ids = [row.get("sliceId") for row in manifest["requests"]]
    if set(request_slice_ids) != expected_slice_ids or len(request_slice_ids) != len(
        expected_slice_ids
    ):
        raise AdapterError(
            f"run {manifest.get('runId')} requests do not exactly cover adapter slices"
        )

    for request in sorted(manifest["requests"], key=lambda row: row["sliceId"]):
        adapter = adapters.get(request["adapterId"])
        pair = slices.get(request["sliceId"])
        if not adapter or not pair or pair[0]["adapterId"] != request["adapterId"]:
            raise AdapterError(f"run request has unknown adapter slice {request['sliceId']}")
        slice_row = pair[1]
        expected_endpoint = adapter["endpointTemplate"].format(rawLocale=slice_row["rawLocale"])
        request_contract = {
            "adapterVersion": adapter["adapterVersion"],
            "providerId": adapter["providerId"],
            "surfaceId": adapter["surfaceId"],
            "coverageEdgeId": slice_row["coverageEdgeId"],
            "rawLocale": slice_row["rawLocale"],
            "endpoint": expected_endpoint,
        }
        mismatched = [
            field for field, expected in request_contract.items()
            if request.get(field) != expected
        ]
        if mismatched:
            raise AdapterError(
                f"run request {request['sliceId']} differs from contract: {mismatched}"
            )
        request["runId"] = manifest["runId"]
        slice_records: list[dict[str, Any]] = []
        terminal_state = "blocked-by-source"
        if request.get("error") is None:
            raw_path = (run_dir / request["rawPath"]).resolve()
            if raw_path.parent != (run_dir / "raw").resolve():
                raise AdapterError(f"raw response escapes run raw directory: {request['rawPath']}")
            raw_bytes = raw_path.read_bytes()
            if content_hash(raw_bytes) != request["responseHash"]:
                raise AdapterError(f"raw response hash mismatch: {request['rawPath']}")
            payload = parse_response(adapter, slice_row, raw_bytes)
            if len(payload) != request["recordCount"]:
                raise AdapterError(f"record count mismatch: {request['rawPath']}")
            if not payload:
                run_errors.append({
                    "code": "empty-catalogue", "sliceId": request["sliceId"],
                    "meaning": "unknown; never negative evidence",
                })
                terminal_state = "needs-evidence"
            else:
                terminal_state = "complete"
            checkpoint = request.get("checkpoint", {})
            if checkpoint.get("complete") is not True or checkpoint.get("nextCursor") is not None:
                run_errors.append({
                    "code": "incomplete-pagination", "sliceId": request["sliceId"],
                    "checkpoint": checkpoint,
                    "meaning": "needs-evidence; never an empty or closed catalogue",
                })
                terminal_state = "needs-evidence"
            provider_id_counts = Counter(
                str(row.get("id")) if isinstance(row, dict) else "<unparseable>"
                for row in payload
            )
            provider_id_seen: Counter[str] = Counter()
            for source_record in payload:
                provider_id_text = (
                    str(source_record.get("id"))
                    if isinstance(source_record, dict) else "<unparseable>"
                )
                provider_id_seen[provider_id_text] += 1
                duplicate_occurrence = (
                    provider_id_seen[provider_id_text]
                    if provider_id_counts[provider_id_text] > 1 else None
                )
                record = normalize_record(
                    adapter, slice_row, request, source_record, mappings, run_errors,
                    duplicate_occurrence,
                )
                if record["stableKey"] in seen_keys:
                    raise AdapterError(f"internal stable-key collision: {record['stableKey']}")
                seen_keys.add(record["stableKey"])
                slice_records.append(record)
                records.append(record)
        accounting = Counter(row["bucket"] for row in slice_records)
        fetched = len(slice_records)
        accounted = sum(accounting.values())
        if fetched != accounted:
            raise AdapterError(f"slice {request['sliceId']} failed accounting")
        slice_rows.append({
            "sliceId": request["sliceId"],
            "adapterId": request["adapterId"],
            "terminalState": terminal_state,
            "terminalMeaning": (
                "all rows returned by this bounded request were retained and accounted; "
                "provider-universe completeness is not claimed"
                if terminal_state == "complete" else
                "source access or positive catalogue content needs evidence; no absence is inferred"
            ),
            "checkpoint": request["checkpoint"],
            "accounting": {
                "fetched": fetched,
                "mapped": accounting["mapped"],
                "newCandidate": accounting["new-candidate"],
                "ambiguousNeedsEvidence": accounting["ambiguous/needs-evidence"],
                "positivelyExcluded": accounting["positively-excluded"],
                "accounted": accounted,
            },
        })

    records.sort(key=lambda row: row["stableKey"])
    totals = Counter(row["bucket"] for row in records)
    previous_records = [] if previous is None else previous["records"]
    diff = diff_records(records, previous_records)
    return {
        "meta": {
            "schema": "snoredex-source-adapter-staging",
            "schemaVersion": "1.0.0",
            "coverageVersion": contract["meta"]["coverageVersion"],
            "generatedFromRun": manifest["runId"],
            "previousRun": None if previous is None else previous["meta"]["generatedFromRun"],
            "contract": "verification/source_adapters.json",
            "capabilityGraph": "verification/source_capability_graph.json",
            "contractHash": manifest["contractHash"],
            "capabilityGraphHash": manifest["capabilityGraphHash"],
            "sourceFirst": True,
            "verdictMutationAllowed": False,
            "counts": {
                "slices": len(slice_rows),
                "records": len(records),
                "mapped": totals["mapped"],
                "newCandidate": totals["new-candidate"],
                "ambiguousNeedsEvidence": totals["ambiguous/needs-evidence"],
                "positivelyExcluded": totals["positively-excluded"],
                "runErrors": len(run_errors),
                "gaps": len(contract["gaps"]),
            },
        },
        "slices": slice_rows,
        "runErrors": run_errors,
        "diff": diff,
        "gaps": contract["gaps"],
        "records": records,
    }


def run_directories() -> list[Path]:
    if not RUNS_DIR.exists():
        return []
    return sorted(
        path for path in RUNS_DIR.iterdir()
        if path.is_dir() and RUN_ID_PATTERN.fullmatch(path.name)
    )


def build_latest(
    contract: dict[str, Any], capability: dict[str, Any]
) -> tuple[dict[str, Any], Path]:
    directories = run_directories()
    if not directories:
        raise AdapterError("no retained source-adapter run exists")
    previous = None
    for run_dir in directories:
        manifest = read_json(run_dir / "manifest.json")
        if manifest.get("runId") != run_dir.name:
            raise AdapterError(f"run directory and manifest id differ: {run_dir.name}")
        run_contract = contract
        if manifest.get("contractHash") != content_hash(contract):
            snapshot_path = run_dir / "contract.json"
            if not snapshot_path.is_file():
                raise AdapterError(
                    f"historical run {run_dir.name} needs its immutable contract snapshot"
                )
            run_contract = read_json(snapshot_path)
            if manifest.get("contractHash") != content_hash(run_contract):
                raise AdapterError(f"contract snapshot hash mismatch: {run_dir.name}")
            validate_contract(run_contract, capability)
        previous = build_projection(
            run_contract, manifest, run_dir, previous, capability
        )
    return previous, directories[-1]


def fetch_one(
    adapter: dict[str, Any], slice_row: dict[str, Any], retrieved_at: str, run_id: str
) -> tuple[dict[str, Any], bytes | None]:
    endpoint = adapter["endpointTemplate"].format(rawLocale=slice_row["rawLocale"])
    request = urllib.request.Request(
        endpoint,
        headers={"User-Agent": "Snoredex-Data/1.0 source-first catalogue adapter"},
    )
    base = {
        "runId": run_id,
        "adapterId": adapter["adapterId"],
        "adapterVersion": adapter["adapterVersion"],
        "sliceId": slice_row["sliceId"],
        "providerId": adapter["providerId"],
        "surfaceId": adapter["surfaceId"],
        "coverageEdgeId": slice_row["coverageEdgeId"],
        "endpoint": endpoint,
        "queryParameters": (
            {
                "rawLocale": slice_row["rawLocale"],
                "resource": "English-set language column",
                "pageTitle": adapter["pageTitle"],
                "revisionId": adapter["revisionId"],
            }
            if adapter.get("responseFormat") == "bulbapedia-historical-wikitext"
            else {"rawLocale": slice_row["rawLocale"], "resource": "sets"}
        ),
        "rawLocale": slice_row["rawLocale"],
        "retrievedAt": retrieved_at,
        "checkpoint": {"page": 1, "nextCursor": None, "complete": False},
    }
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read()
            status = response.status
        payload = parse_response(adapter, slice_row, raw)
        return ({
            **base,
            "httpStatus": status,
            "rawPath": f"raw/{slice_row['sliceId']}.json",
            "responseHash": content_hash(raw),
            "recordCount": len(payload),
            "pageCount": 1,
            "checkpoint": {"page": 1, "nextCursor": None, "complete": True},
            "error": None,
        }, raw)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, AdapterError) as error:
        return ({
            **base,
            "httpStatus": getattr(error, "code", None),
            "rawPath": None,
            "responseHash": None,
            "recordCount": 0,
            "pageCount": 0,
            "error": {"code": "fetch-or-parse-failure", "message": str(error)},
        }, None)


def refresh(run_id: str, retrieved_at: str | None) -> None:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise AdapterError("--run-id must use YYYYMMDDTHHMMSSZ")
    run_dir = RUNS_DIR / run_id
    if run_dir.exists():
        raise AdapterError(f"immutable run already exists: {run_dir.relative_to(ROOT)}")
    contract, capability = load_inputs()
    timestamp = retrieved_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    jobs = [
        (adapter, slice_row)
        for adapter in contract["adapters"] for slice_row in adapter["slices"]
    ]
    results = []
    with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as executor:
        futures = {
            executor.submit(fetch_one, adapter, slice_row, timestamp, run_id):
            (adapter, slice_row)
            for adapter, slice_row in jobs
        }
        for future in as_completed(futures):
            results.append(future.result())

    run_dir.mkdir(parents=True)
    write_json(run_dir / "contract.json", contract)
    requests = []
    for request, raw in sorted(results, key=lambda pair: pair[0]["sliceId"]):
        requests.append(request)
        if raw is not None:
            raw_path = run_dir / request["rawPath"]
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(raw)
    failures = [
        {"code": "request-failure", "sliceId": row["sliceId"], "error": row["error"]}
        for row in requests if row["error"] is not None
    ]
    manifest = {
        "schema": "snoredex-source-adapter-run",
        "schemaVersion": "1.0.0",
        "runId": run_id,
        "coverageVersion": contract["meta"]["coverageVersion"],
        "startedAt": timestamp,
        "completedAt": timestamp,
        "status": "complete" if not failures else "incomplete",
        "contract": "verification/source_adapters.json",
        "contractHash": content_hash(contract),
        "capabilityGraph": "verification/source_capability_graph.json",
        "capabilityGraphHash": capability_pin(capability, surfaces_used(requests)),
        "capabilityGraphSurfaces": surfaces_used(requests),
        "requests": requests,
        "failures": failures,
    }
    write_json(run_dir / "manifest.json", manifest)
    projection, _ = build_latest(contract, capability)
    summary_text, records_text = render_projection(projection)
    OUTPUT_PATH.write_text(summary_text, encoding="utf-8")
    RECORDS_PATH.write_bytes(records_text.encode("utf-8"))
    print(
        f"retained {run_id}: {projection['meta']['counts']['records']} source-first records, "
        f"{len(failures)} request failures, {projection['meta']['counts']['runErrors']} run errors"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate immutable runs and projections")
    parser.add_argument("--refresh", action="store_true", help="create a new immutable live run")
    parser.add_argument("--refresh-tcgdex", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--run-id", help="immutable run id in YYYYMMDDTHHMMSSZ form")
    parser.add_argument("--retrieved-at", help="explicit ISO-8601 retrieval timestamp for a run")
    args = parser.parse_args()
    try:
        if args.refresh or args.refresh_tcgdex:
            if not args.run_id:
                raise AdapterError("--refresh requires --run-id")
            refresh(args.run_id, args.retrieved_at)
            return 0
        contract, capability = load_inputs()
        projection, run_dir = build_latest(contract, capability)
        rendered, records_rendered = render_projection(projection)
        if args.check:
            stale = []
            if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_text(encoding="utf-8") != rendered:
                stale.append(str(OUTPUT_PATH.relative_to(ROOT)))
            if not RECORDS_PATH.exists() or RECORDS_PATH.read_bytes() != records_rendered.encode(
                "utf-8"
            ):
                stale.append(str(RECORDS_PATH.relative_to(ROOT)))
            if stale:
                raise AdapterError("stale projection: " + ", ".join(stale))
            counts = projection["meta"]["counts"]
            if counts["runErrors"]:
                raise AdapterError(f"latest run has {counts['runErrors']} run error(s)")
            print(
                f"[ ok ] source adapters: {counts['records']} records across {counts['slices']} "
                f"accounted slices; {counts['gaps']} explicit gaps"
            )
            return 0
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
        RECORDS_PATH.write_bytes(records_rendered.encode("utf-8"))
        print(f"wrote {OUTPUT_PATH.relative_to(ROOT)} from immutable run {run_dir.name}")
        return 0
    except (AdapterError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        print(f"[FAIL] source adapters: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

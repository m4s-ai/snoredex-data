#!/usr/bin/env python3
"""Discover and reconcile provider-native card records without a legacy seed (#136).

The reviewed contract is ``verification/card_discovery_adapters.json``. Network access occurs
only with ``--refresh-asia``. Normal generation and CI checks replay committed immutable HTML
responses, then match the resulting positive card records against ADR-0001 identities without
mutating any verdict store.

    python scripts/card_discovery.py --refresh-asia --run-id 20260809T180000Z
    python scripts/card_discovery.py --refresh-asia --run-id 20260809T180000Z --resume
    python scripts/card_discovery.py
    python scripts/card_discovery.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

from source_capabilities import schema_errors

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "verification" / "card_discovery_adapters.json"
SCHEMA_PATH = ROOT / "verification" / "card_discovery_schema.json"
CAPABILITY_PATH = ROOT / "verification" / "source_capability_graph.json"
IDENTITY_PATH = ROOT / "verification" / "print_identity_dryrun.json"
RUNS_DIR = ROOT / "verification" / "runs" / "card-discovery"
OUTPUT_PATH = ROOT / "verification" / "card_discovery_staging.json"
RECORDS_PATH = ROOT / "verification" / "card_discovery_records.jsonl"
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
DETAIL_PATH_PATTERN = re.compile(r"/card-search/detail/([0-9]+)/?")
SET_SYMBOL_PATTERN = re.compile(r"_exp_([^./]+)\.(?:png|jpe?g|webp)$", re.IGNORECASE)


class DiscoveryError(ValueError):
    """The card discovery contract or a retained run violates #136."""


class AsiaListParser(HTMLParser):
    """Extract the bounded result count, page count and official detail ids."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.detail_ids: list[str] = []
        self.result_count: int | None = None
        self.total_pages: int | None = None
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            match = DETAIL_PATH_PATTERN.search(values["href"] or "")
            if match:
                self.detail_ids.append(match.group(1))
        if tag == "p":
            classes = set((values.get("class") or "").split())
            if "resultNumber" in classes:
                self._capture = "count"
            elif "resultTotalPages" in classes:
                self._capture = "pages"

    def handle_endtag(self, tag: str) -> None:
        if tag == "p":
            self._capture = None

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text or self._capture is None:
            return
        numbers = re.findall(r"[0-9]+", text)
        if not numbers:
            return
        if self._capture == "count" and self.result_count is None:
            self.result_count = int(numbers[0])
        elif self._capture == "pages" and self.total_pages is None:
            self.total_pages = int(numbers[-1])


class AsiaDetailParser(HTMLParser):
    """Extract only source-native identity fields from one official detail page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.local_name: str | None = None
        self.collector_number: str | None = None
        self.card_image_url: str | None = None
        self.set_symbol_url: str | None = None
        self.expansion_code: str | None = None
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._inside_evolve_marker = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "h1" and {"pageHeader", "cardDetail"}.issubset(classes):
            self._capture = "name"
            self._buffer = []
        elif tag == "span" and self._capture == "name" and "evolveMarker" in classes:
            self._inside_evolve_marker = True
        elif tag == "span" and "collectorNumber" in classes:
            self._capture = "number"
            self._buffer = []
        elif tag == "a" and values.get("href"):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(values["href"] or "").query)
            expansion_codes = query.get("expansionCodes", [])
            if len(expansion_codes) == 1 and expansion_codes[0]:
                self.expansion_code = expansion_codes[0]
        elif tag == "img" and values.get("src"):
            source = values["src"] or ""
            if "/card-img/mark/" in source:
                self.set_symbol_url = source
            elif "/card-img/" in source and self.card_image_url is None:
                self.card_image_url = source

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._inside_evolve_marker:
            self._inside_evolve_marker = False
            return
        if (tag == "h1" and self._capture == "name") or (
            tag == "span" and self._capture == "number"
        ):
            value = " ".join(part for part in self._buffer if part).strip()
            if self._capture == "name":
                self.local_name = value or None
            else:
                self.collector_number = value or None
            self._capture = None
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture is not None and not self._inside_evolve_marker and data.strip():
            self._buffer.append(data.strip())


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
    changed, only the calendar. Because a change to `units.json` flows into the source registry and
    from there into the graph, this fired on any ordinary write pass made the day after the graph
    was last written, and the documented command order regenerates the graph every time.

    Two things are dropped, and both are dropped for the same reason: they are not capabilities.

    `meta.generated` is the day the file was written. `sourceResolution` is the routing of whatever
    evidence rows the source registry happens to hold right now — one row per URL — so adding a
    single citation to any unit rewrote it and expired every retained run. A run was captured under
    a set of capabilities; which URLs exist today is not part of that set, and pinning it made
    ordinary evidence work impossible rather than making provenance stronger.

    What remains pinned is the contract itself: providers, surfaces, coverage edges, observations,
    and `meta.schemaVersion`. A surface, edge, boundary or absence scope that moves still changes
    this hash, which is the whole point of having one.
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
        raise DiscoveryError(
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
    summary["recordsPath"] = "verification/card_discovery_records.jsonl"
    summary["recordsHash"] = content_hash(records_text.encode("utf-8"))
    return json.dumps(summary, ensure_ascii=False, indent=2) + "\n", records_text


def raw_key(provider_id: str, surface_id: str, raw_locale: str, raw_provider_id: str) -> str:
    return "|".join((provider_id, surface_id, raw_locale, raw_provider_id))


def parse_list(raw: bytes) -> dict[str, Any]:
    parser = AsiaListParser()
    parser.feed(raw.decode("utf-8-sig"))
    detail_ids = list(dict.fromkeys(parser.detail_ids))
    if parser.result_count is None or parser.total_pages is None:
        raise DiscoveryError("official list page lacks result or pagination metadata")
    return {
        "resultCount": parser.result_count,
        "totalPages": parser.total_pages,
        "detailIds": detail_ids,
    }


def parse_detail(raw: bytes, raw_provider_id: str) -> dict[str, Any]:
    parser = AsiaDetailParser()
    parser.feed(raw.decode("utf-8-sig"))
    raw_set_code = parser.expansion_code
    if parser.set_symbol_url:
        match = SET_SYMBOL_PATTERN.search(parser.set_symbol_url)
        if raw_set_code is None and match:
            raw_set_code = match.group(1)
    return {
        "detailId": raw_provider_id,
        "localName": parser.local_name,
        "rawSetCode": raw_set_code,
        "localCollectorNumber": parser.collector_number,
        "cardImageUrl": parser.card_image_url,
        "setSymbolUrl": parser.set_symbol_url,
        "productScope": "physical-tcg",
    }


def validate_contract(
    contract: dict[str, Any], capability: dict[str, Any], identity: dict[str, Any]
) -> None:
    schema = read_json(SCHEMA_PATH)
    errors = schema_errors(contract, schema, schema)
    if errors:
        raise DiscoveryError(
            "contract violates card_discovery_schema.json:\n  - " + "\n  - ".join(errors[:30])
        )

    providers = {row["providerId"] for row in capability["providers"]}
    surfaces = {row["surfaceId"]: row for row in capability["surfaces"]}
    edges = {row["edgeId"]: row for row in capability["coverageEdges"]}
    releases = {row["cardReleaseId"] for row in identity["cardReleases"]}
    seen_adapters: set[str] = set()
    seen_slices: set[str] = set()
    active_surfaces: set[str] = set()

    for adapter in contract["adapters"]:
        adapter_id = adapter["adapterId"]
        if adapter_id in seen_adapters:
            raise DiscoveryError(f"duplicate adapterId {adapter_id}")
        seen_adapters.add(adapter_id)
        if adapter["providerId"] not in providers:
            raise DiscoveryError(f"adapter {adapter_id} names unknown provider")
        surface = surfaces.get(adapter["surfaceId"])
        if not surface or surface["providerId"] != adapter["providerId"]:
            raise DiscoveryError(f"adapter {adapter_id} does not resolve to its provider surface")
        if surface["state"] not in {"active", "incomplete"}:
            raise DiscoveryError(
                f"adapter {adapter_id} requires a usable registered surface {adapter['surfaceId']}"
            )
        active_surfaces.add(adapter["surfaceId"])
        for slice_row in adapter["slices"]:
            slice_id = slice_row["sliceId"]
            if slice_id in seen_slices:
                raise DiscoveryError(f"duplicate sliceId {slice_id}")
            seen_slices.add(slice_id)
            edge = edges.get(slice_row["coverageEdgeId"])
            if not edge or edge["surfaceId"] != adapter["surfaceId"]:
                raise DiscoveryError(f"slice {slice_id} does not resolve to its surface edge")
            coverage = edge["coverage"]
            for field, value in (
                ("localities", slice_row["locality"]),
                ("languages", slice_row["language"]),
                ("scripts", slice_row["script"]),
            ):
                if value not in coverage[field] and "MULTIPLE" not in coverage[field]:
                    raise DiscoveryError(f"slice {slice_id} exceeds edge {field}: {value}")
            if "card" not in coverage["productCategories"]:
                raise DiscoveryError(f"slice {slice_id} does not resolve to card coverage")
            if "card-existence" not in edge["positiveEvidenceCapabilities"]:
                raise DiscoveryError(f"slice {slice_id} lacks positive card capability")

    assertion_keys: set[str] = set()
    for assertion in contract["setCodeAssertions"]:
        key = raw_key(
            assertion["providerId"], assertion["surfaceId"],
            assertion["rawLocale"], assertion["rawSetCode"],
        )
        if key in assertion_keys:
            raise DiscoveryError(f"duplicate set-code assertion {key}")
        assertion_keys.add(key)
        if assertion["surfaceId"] not in active_surfaces:
            raise DiscoveryError(f"set-code assertion {key} is outside active adapters")

    mapping_keys: set[str] = set()
    for mapping in contract["explicitMappings"]:
        key = raw_key(
            mapping["providerId"], mapping["surfaceId"],
            mapping["rawLocale"], mapping["rawProviderId"],
        )
        if key in mapping_keys:
            raise DiscoveryError(f"duplicate explicit mapping {key}")
        mapping_keys.add(key)
        if mapping["surfaceId"] not in active_surfaces:
            raise DiscoveryError(f"mapping {key} is outside active adapters")
        if mapping["targetCardReleaseId"] not in releases:
            raise DiscoveryError(f"mapping {key} names unknown card release")

    seen_gaps: set[str] = set()
    for gap in contract["gaps"]:
        if gap["gapId"] in seen_gaps:
            raise DiscoveryError(f"duplicate gapId {gap['gapId']}")
        seen_gaps.add(gap["gapId"])
        if gap["providerId"] not in providers:
            raise DiscoveryError(f"gap {gap['gapId']} names unknown provider")
        if gap["surfaceId"] is not None:
            surface = surfaces.get(gap["surfaceId"])
            if not surface or surface["providerId"] != gap["providerId"]:
                raise DiscoveryError(f"gap {gap['gapId']} does not resolve to its provider surface")


def load_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract = read_json(CONTRACT_PATH)
    capability = read_json(CAPABILITY_PATH)
    identity = read_json(IDENTITY_PATH)
    validate_contract(contract, capability, identity)
    return contract, capability, identity


def normalize_record(
    adapter: dict[str, Any],
    slice_row: dict[str, Any],
    request: dict[str, Any],
    source_record: dict[str, Any],
    identity_releases: list[dict[str, Any]],
    mappings: dict[str, dict[str, Any]],
    assertions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    raw_provider_id = str(source_record.get("detailId") or "")
    stable_key = raw_key(
        adapter["providerId"], adapter["surfaceId"], slice_row["rawLocale"], raw_provider_id
    )
    record_id = "raw-card:" + hashlib.sha256(stable_key.encode("utf-8")).hexdigest()[:24]
    local_name = source_record.get("localName")
    raw_set_code = source_record.get("rawSetCode")
    local_number = source_record.get("localCollectorNumber")
    assertion = assertions.get(raw_key(
        adapter["providerId"], adapter["surfaceId"], slice_row["rawLocale"],
        str(raw_set_code or ""),
    ))
    proposed_set_code = (
        assertion["assertedLocalSetCode"] if assertion is not None else raw_set_code
    )
    mapping = mappings.get(stable_key)
    exclusions = [
        row for row in slice_row["positiveNameExclusions"]
        if isinstance(local_name, str) and local_name.startswith(row["prefix"])
    ]
    exact_matches = [
        row for row in identity_releases
        if row.get("locality") == slice_row["locality"]
        and row.get("language") == slice_row["language"]
        and row.get("localSetCode") == proposed_set_code
        and row.get("localNumber") == local_number
    ]
    missing = [
        field for field, value in (
            ("detailId", raw_provider_id), ("localName", local_name),
            ("rawSetCode", raw_set_code), ("localCollectorNumber", local_number),
        ) if not isinstance(value, str) or not value.strip()
    ]

    equivalence_proposals: list[dict[str, Any]] = []
    target = None
    if source_record.get("productScope") == "digital-pocket":
        bucket = "positively-excluded"
        bucket_basis = "source record explicitly identifies the digital-only Pokémon TCG Pocket product"
    elif exclusions:
        bucket = "positively-excluded"
        bucket_basis = exclusions[0]["reason"]
    elif missing:
        bucket = "needs-evidence"
        bucket_basis = "required source-native identity field is missing: " + ", ".join(missing)
    elif mapping and mapping["mode"] == "equivalence-proposal":
        bucket = "ambiguous"
        bucket_basis = mapping["evidence"]
        equivalence_proposals.append({
            "targetCardReleaseId": mapping["targetCardReleaseId"],
            "evidence": mapping["evidence"],
            "destructiveMergeAllowed": False,
        })
    elif mapping and mapping["mode"] == "exact-match":
        bucket = "matched"
        bucket_basis = mapping["evidence"]
        target = mapping["targetCardReleaseId"]
    elif len(exact_matches) == 1:
        bucket = "matched"
        bucket_basis = "exact locality, language, asserted local set code, and collector number tuple"
        target = exact_matches[0]["cardReleaseId"]
    elif len(exact_matches) > 1:
        bucket = "ambiguous"
        bucket_basis = "more than one ADR-0001 card release has the exact local identity tuple"
        equivalence_proposals.extend({
            "targetCardReleaseId": row["cardReleaseId"],
            "evidence": bucket_basis,
            "destructiveMergeAllowed": False,
        } for row in exact_matches)
    else:
        bucket = "new-candidate"
        bucket_basis = "positive provider-native card detail; no existing exact local identity tuple"

    list_hashes = sorted({page["responseHash"] for page in request["pages"]})
    detail = next(
        row for row in request["details"] if row["rawProviderId"] == raw_provider_id
    )
    source_url = adapter["detailEndpointTemplate"].format(
        rawLocale=slice_row["rawLocale"], rawProviderId=raw_provider_id
    )
    return {
        "recordId": record_id,
        "stableKey": stable_key,
        "identityHintHash": content_hash({
            "locality": slice_row["locality"], "language": slice_row["language"],
            "localSetCode": proposed_set_code, "localCollectorNumber": local_number,
            "localName": local_name,
        }),
        "providerId": adapter["providerId"],
        "surfaceId": adapter["surfaceId"],
        "coverageEdgeId": slice_row["coverageEdgeId"],
        "sourceUrl": source_url,
        "queryParameters": request["queryParameters"],
        "rawProviderId": raw_provider_id,
        "rawLocale": slice_row["rawLocale"],
        "locality": slice_row["locality"],
        "retrievedAt": request["retrievedAt"],
        "listResponseHashes": list_hashes,
        "detailResponseHash": detail["responseHash"],
        "recordHash": content_hash(source_record),
        "runId": request["runId"],
        "raw": {
            "localName": local_name,
            "rawSetCode": raw_set_code,
            "localCollectorNumber": local_number,
            "cardImageUrl": source_record.get("cardImageUrl"),
            "setSymbolUrl": source_record.get("setSymbolUrl"),
        },
        "sourceRecord": source_record,
        "bucket": bucket,
        "bucketBasis": bucket_basis,
        "normalizationProposal": {
            "entityType": "card-release",
            "locality": slice_row["locality"],
            "language": slice_row["language"],
            "script": slice_row["script"],
            "localName": local_name,
            "rawSetCode": raw_set_code,
            "assertedLocalSetCode": proposed_set_code,
            "setCodeAssertion": None if assertion is None else {
                "assetUrl": assertion["assetUrl"],
                "evidence": assertion["evidence"],
            },
            "localCollectorNumber": local_number,
            "targetCardReleaseId": target,
            "equivalenceProposals": equivalence_proposals,
            "destructiveMergeAllowed": False,
            "verdictMutationAllowed": False,
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
        for old_key, new_key in zip(sorted(old_hints[hint]), sorted(new_hints[hint])):
            rekeyed.append({"from": old_key, "to": new_key, "identityHintHash": hint})
            disappeared.remove(old_key)
            added.remove(new_key)
    return {
        "added": sorted(added),
        "changed": changed,
        "disappeared": sorted(disappeared),
        "rekeyedCandidates": rekeyed,
        "counts": {
            "added": len(added), "changed": len(changed),
            "disappeared": len(disappeared), "rekeyedCandidates": len(rekeyed),
        },
    }


def checked_raw_path(run_dir: Path, relative: str) -> Path:
    path = (run_dir / relative).resolve()
    if (run_dir / "raw").resolve() not in path.parents:
        raise DiscoveryError(f"raw response escapes run raw directory: {relative}")
    return path


def build_projection(
    contract: dict[str, Any], capability: dict[str, Any], identity: dict[str, Any],
    manifest: dict[str, Any], run_dir: Path, previous: dict[str, Any] | None,
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
    assertions = {
        raw_key(row["providerId"], row["surfaceId"], row["rawLocale"], row["rawSetCode"]): row
        for row in contract["setCodeAssertions"]
    }
    if manifest.get("contractHash") != content_hash(contract):
        raise DiscoveryError(f"run {manifest.get('runId')} was captured under another contract")
    if manifest.get("capabilityGraphHash") != capability_pin(
            capability, manifest_surfaces(manifest)):
        raise DiscoveryError(f"run {manifest.get('runId')} was captured under another capability graph")
    if manifest.get("coverageVersion") != contract["meta"]["coverageVersion"]:
        raise DiscoveryError(f"run {manifest.get('runId')} has another coverage version")
    expected_slice_ids = set(slices)
    request_slice_ids = [row.get("sliceId") for row in manifest["requests"]]
    if set(request_slice_ids) != expected_slice_ids or len(request_slice_ids) != len(
        expected_slice_ids
    ):
        raise DiscoveryError("run requests do not exactly cover adapter slices")

    records: list[dict[str, Any]] = []
    run_errors: list[dict[str, Any]] = list(manifest.get("failures", []))
    slice_rows = []
    seen_keys: set[str] = set()
    for request in sorted(manifest["requests"], key=lambda row: row["sliceId"]):
        pair = slices.get(request["sliceId"])
        adapter = adapters.get(request["adapterId"])
        if not pair or not adapter or pair[0]["adapterId"] != request["adapterId"]:
            raise DiscoveryError(f"run request has unknown slice {request['sliceId']}")
        slice_row = pair[1]
        expected_list = adapter["listEndpointTemplate"].format(rawLocale=slice_row["rawLocale"])
        if request.get("endpoint") != expected_list:
            raise DiscoveryError(f"run request endpoint differs for {request['sliceId']}")

        slice_records: list[dict[str, Any]] = []
        terminal_state = "blocked-by-source"
        source_failure_state = "source-failed" if request.get("error") else None
        if request.get("error") is None:
            discovered_ids: list[str] = []
            list_hashes: set[str] = set()
            pages_by_query: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for page in request["pages"]:
                raw = checked_raw_path(run_dir, page["rawPath"]).read_bytes()
                if content_hash(raw) != page["responseHash"]:
                    raise DiscoveryError(f"list response hash mismatch: {page['rawPath']}")
                parsed = parse_list(raw)
                if parsed != {
                    "resultCount": page["resultCount"],
                    "totalPages": page["totalPages"],
                    "detailIds": page["detailIds"],
                }:
                    raise DiscoveryError(f"list parse drift: {page['rawPath']}")
                list_hashes.add(page["responseHash"])
                discovered_ids.extend(page["detailIds"])
                pages_by_query[page["query"]].append(page)
            for query in slice_row["nameQueries"]:
                pages = sorted(pages_by_query.get(query, []), key=lambda row: row["pageNo"])
                if not pages or [row["pageNo"] for row in pages] != list(
                    range(1, pages[0]["totalPages"] + 1)
                ) or any(row["totalPages"] != pages[0]["totalPages"] for row in pages):
                    run_errors.append({
                        "code": "incomplete-pagination", "sliceId": request["sliceId"],
                        "query": query, "meaning": "needs-evidence; never a closed catalogue",
                    })
            discovered_unique = sorted(set(discovered_ids), key=lambda value: int(value))
            details = {row["rawProviderId"]: row for row in request["details"]}
            if set(details) != set(discovered_unique):
                raise DiscoveryError(f"detail accounting differs for {request['sliceId']}")
            for raw_provider_id in discovered_unique:
                detail = details[raw_provider_id]
                raw = checked_raw_path(run_dir, detail["rawPath"]).read_bytes()
                if content_hash(raw) != detail["responseHash"]:
                    raise DiscoveryError(f"detail response hash mismatch: {detail['rawPath']}")
                source_record = parse_detail(raw, raw_provider_id)
                record = normalize_record(
                    adapter, slice_row, request, source_record, identity["cardReleases"],
                    mappings, assertions,
                )
                if record["stableKey"] in seen_keys:
                    raise DiscoveryError(f"internal stable-key collision: {record['stableKey']}")
                seen_keys.add(record["stableKey"])
                slice_records.append(record)
                records.append(record)

            used_assertions = {
                row["normalizationProposal"]["rawSetCode"]
                for row in slice_records if row["normalizationProposal"]["setCodeAssertion"]
            }
            assets = {row["rawSetCode"]: row for row in request.get("assets", [])}
            if set(assets) != used_assertions:
                raise DiscoveryError(f"set-symbol asset accounting differs for {request['sliceId']}")
            for asset in assets.values():
                raw = checked_raw_path(run_dir, asset["rawPath"]).read_bytes()
                if content_hash(raw) != asset["responseHash"]:
                    raise DiscoveryError(f"set-symbol response hash mismatch: {asset['rawPath']}")
                assertion = assertions[raw_key(
                    adapter["providerId"], adapter["surfaceId"], slice_row["rawLocale"],
                    asset["rawSetCode"],
                )]
                if asset["url"] != assertion["assetUrl"]:
                    raise DiscoveryError(f"set-symbol URL differs for {asset['rawSetCode']}")

            if not slice_records:
                run_errors.append({
                    "code": "zero-result", "sliceId": request["sliceId"],
                    "meaning": "source-failed/needs-evidence; never negative evidence",
                })
                terminal_state = "needs-evidence"
                source_failure_state = "source-failed"
            elif request["checkpoint"].get("complete") is not True:
                run_errors.append({
                    "code": "incomplete-checkpoint", "sliceId": request["sliceId"],
                    "meaning": "needs-evidence; never a closed catalogue",
                })
                terminal_state = "needs-evidence"
            else:
                terminal_state = "complete"

        accounting = Counter(row["bucket"] for row in slice_records)
        fetched = len(slice_records)
        accounted = sum(accounting.values())
        if fetched != accounted:
            raise DiscoveryError(f"slice {request['sliceId']} failed accounting")
        slice_rows.append({
            "sliceId": request["sliceId"],
            "adapterId": request["adapterId"],
            "terminalState": terminal_state,
            "sourceFailureState": source_failure_state,
            "terminalMeaning": (
                "every positive detail returned by the bounded native-name query was retained and accounted; historical or provider-universe completeness is not claimed"
                if terminal_state == "complete" else
                "source access, pagination, parsing, or positive content needs evidence; no absence is inferred"
            ),
            "checkpoint": request["checkpoint"],
            "accounting": {
                "fetched": fetched,
                "matched": accounting["matched"],
                "ambiguous": accounting["ambiguous"],
                "newCandidate": accounting["new-candidate"],
                "positivelyExcluded": accounting["positively-excluded"],
                "needsEvidence": accounting["needs-evidence"],
                "accounted": accounted,
            },
        })

    records.sort(key=lambda row: row["stableKey"])
    totals = Counter(row["bucket"] for row in records)
    previous_records = [] if previous is None else previous["records"]
    return {
        "meta": {
            "schema": "snoredex-card-discovery-staging",
            "schemaVersion": "1.0.0",
            "coverageVersion": contract["meta"]["coverageVersion"],
            "generatedFromRun": manifest["runId"],
            "previousRun": None if previous is None else previous["meta"]["generatedFromRun"],
            "contract": "verification/card_discovery_adapters.json",
            "capabilityGraph": "verification/source_capability_graph.json",
            "identityGraph": "verification/print_identity_dryrun.json",
            "contractHash": manifest["contractHash"],
            "capabilityGraphHash": manifest["capabilityGraphHash"],
            "identityGraphHash": content_hash(identity),
            "sourceFirst": True,
            "verdictMutationAllowed": False,
            "counts": {
                "slices": len(slice_rows), "records": len(records),
                "matched": totals["matched"], "ambiguous": totals["ambiguous"],
                "newCandidate": totals["new-candidate"],
                "positivelyExcluded": totals["positively-excluded"],
                "needsEvidence": totals["needs-evidence"],
                "runErrors": len(run_errors), "gaps": len(contract["gaps"]),
            },
        },
        "slices": slice_rows,
        "runErrors": run_errors,
        "diff": diff_records(records, previous_records),
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
    contract: dict[str, Any], capability: dict[str, Any], identity: dict[str, Any]
) -> tuple[dict[str, Any], Path]:
    directories = run_directories()
    if not directories:
        raise DiscoveryError("no retained card-discovery run exists")
    previous = None
    for run_dir in directories:
        manifest = read_json(run_dir / "manifest.json")
        if manifest.get("runId") != run_dir.name:
            raise DiscoveryError(f"run directory and manifest id differ: {run_dir.name}")
        previous = build_projection(
            contract, capability, identity, manifest, run_dir, previous
        )
    return previous, directories[-1]


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "Snoredex-Data/1.0 source-first card discovery"}
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        if response.status != 200:
            raise DiscoveryError(f"HTTP {response.status}: {url}")
        return response.read()


def save_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    write_json(run_dir / "manifest.json", manifest)


def retain_response(run_dir: Path, relative: str, raw: bytes) -> str:
    path = checked_raw_path(run_dir, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        if existing != raw:
            raise DiscoveryError(f"resume would overwrite retained response: {relative}")
    else:
        path.write_bytes(raw)
    return content_hash(raw)


def new_manifest(
    contract: dict[str, Any], capability: dict[str, Any], run_id: str, timestamp: str
) -> dict[str, Any]:
    requests = []
    for adapter in contract["adapters"]:
        for slice_row in adapter["slices"]:
            requests.append({
                "runId": run_id,
                "adapterId": adapter["adapterId"],
                "adapterVersion": adapter["adapterVersion"],
                "sliceId": slice_row["sliceId"],
                "providerId": adapter["providerId"],
                "surfaceId": adapter["surfaceId"],
                "coverageEdgeId": slice_row["coverageEdgeId"],
                "rawLocale": slice_row["rawLocale"],
                "endpoint": adapter["listEndpointTemplate"].format(
                    rawLocale=slice_row["rawLocale"]
                ),
                "queryParameters": {
                    "nameQueries": slice_row["nameQueries"],
                    "cardType": "all", "regulation": "all",
                    "pageParameter": adapter["pageParameter"],
                },
                "retrievedAt": timestamp,
                "pages": [], "details": [], "assets": [],
                "checkpoint": {
                    "completedPages": [], "completedDetailIds": [],
                    "nextPage": 1, "complete": False,
                },
                "error": None,
            })
    return {
        "schema": "snoredex-card-discovery-run",
        "schemaVersion": "1.0.0",
        "runId": run_id,
        "coverageVersion": contract["meta"]["coverageVersion"],
        "startedAt": timestamp,
        "completedAt": None,
        "status": "incomplete",
        "contract": "verification/card_discovery_adapters.json",
        "contractHash": content_hash(contract),
        "capabilityGraph": "verification/source_capability_graph.json",
        "capabilityGraphHash": capability_pin(capability, surfaces_used(requests)),
        "capabilityGraphSurfaces": surfaces_used(requests),
        "requests": requests,
        "failures": [],
    }


def refresh(run_id: str, retrieved_at: str | None, resume: bool) -> None:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise DiscoveryError("--run-id must use YYYYMMDDTHHMMSSZ")
    contract, capability, identity = load_inputs()
    run_dir = RUNS_DIR / run_id
    timestamp = retrieved_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    if run_dir.exists():
        if not resume:
            raise DiscoveryError(f"run already exists; use --resume only for incomplete runs: {run_id}")
        manifest = read_json(run_dir / "manifest.json")
        if manifest.get("status") != "incomplete":
            raise DiscoveryError(f"immutable completed run cannot be resumed: {run_id}")
        if manifest.get("contractHash") != content_hash(contract) or manifest.get(
            "capabilityGraphHash"
        ) != content_hash(capability):
            raise DiscoveryError("resume inputs differ from the retained run")
    else:
        if resume:
            raise DiscoveryError(f"cannot resume missing run: {run_id}")
        run_dir.mkdir(parents=True)
        manifest = new_manifest(contract, capability, run_id, timestamp)
        save_manifest(run_dir, manifest)

    adapters = {row["adapterId"]: row for row in contract["adapters"]}
    slices = {
        row["sliceId"]: row
        for adapter in contract["adapters"] for row in adapter["slices"]
    }
    assertion_by_code = {
        (row["providerId"], row["surfaceId"], row["rawLocale"], row["rawSetCode"]): row
        for row in contract["setCodeAssertions"]
    }
    manifest["failures"] = []
    try:
        for request in manifest["requests"]:
            adapter = adapters[request["adapterId"]]
            slice_row = slices[request["sliceId"]]
            request["error"] = None
            pages_by_pair = {(row["query"], row["pageNo"]): row for row in request["pages"]}
            for query_index, query in enumerate(slice_row["nameQueries"], start=1):
                page_no = 1
                total_pages = None
                while total_pages is None or page_no <= total_pages:
                    pair = (query, page_no)
                    page = pages_by_pair.get(pair)
                    if page is None:
                        parameters = {
                            "pageNo": page_no, "keyword": query,
                            "cardType": "all", "regulation": "all",
                        }
                        url = request["endpoint"] + "?" + urllib.parse.urlencode(parameters)
                        raw = fetch_bytes(url)
                        parsed = parse_list(raw)
                        relative = (
                            f"raw/{request['sliceId']}/query-{query_index}/page-{page_no}.html"
                        )
                        page = {
                            "query": query, "pageNo": page_no, "url": url,
                            "rawPath": relative, "responseHash": retain_response(run_dir, relative, raw),
                            **parsed,
                        }
                        request["pages"].append(page)
                        pages_by_pair[pair] = page
                        request["checkpoint"]["completedPages"] = sorted(
                            f"{row['query']}:{row['pageNo']}" for row in request["pages"]
                        )
                        request["checkpoint"]["nextPage"] = page_no + 1
                        save_manifest(run_dir, manifest)
                    total_pages = page["totalPages"]
                    page_no += 1

            discovered_ids = sorted({
                raw_id for page in request["pages"] for raw_id in page["detailIds"]
            }, key=lambda value: int(value))
            details = {row["rawProviderId"]: row for row in request["details"]}
            for raw_provider_id in discovered_ids:
                if raw_provider_id not in details:
                    url = adapter["detailEndpointTemplate"].format(
                        rawLocale=slice_row["rawLocale"], rawProviderId=raw_provider_id
                    )
                    raw = fetch_bytes(url)
                    parsed = parse_detail(raw, raw_provider_id)
                    relative = f"raw/{request['sliceId']}/details/{raw_provider_id}.html"
                    detail = {
                        "rawProviderId": raw_provider_id, "url": url,
                        "rawPath": relative, "responseHash": retain_response(run_dir, relative, raw),
                        "parsedRecordHash": content_hash(parsed),
                    }
                    request["details"].append(detail)
                    details[raw_provider_id] = detail
                    request["checkpoint"]["completedDetailIds"] = sorted(
                        details, key=lambda value: int(value)
                    )
                    save_manifest(run_dir, manifest)

            assets = {row["rawSetCode"]: row for row in request["assets"]}
            for raw_provider_id in discovered_ids:
                detail = details[raw_provider_id]
                raw = checked_raw_path(run_dir, detail["rawPath"]).read_bytes()
                source_record = parse_detail(raw, raw_provider_id)
                assertion = assertion_by_code.get((
                    adapter["providerId"], adapter["surfaceId"], slice_row["rawLocale"],
                    source_record.get("rawSetCode"),
                ))
                if assertion is not None and assertion["rawSetCode"] not in assets:
                    asset_raw = fetch_bytes(assertion["assetUrl"])
                    extension = Path(urllib.parse.urlparse(assertion["assetUrl"]).path).suffix or ".bin"
                    relative = (
                        f"raw/{request['sliceId']}/assets/{assertion['rawSetCode']}{extension}"
                    )
                    asset = {
                        "rawSetCode": assertion["rawSetCode"], "url": assertion["assetUrl"],
                        "rawPath": relative,
                        "responseHash": retain_response(run_dir, relative, asset_raw),
                    }
                    request["assets"].append(asset)
                    assets[assertion["rawSetCode"]] = asset
                    save_manifest(run_dir, manifest)

            request["pages"].sort(key=lambda row: (row["query"], row["pageNo"]))
            request["details"].sort(key=lambda row: int(row["rawProviderId"]))
            request["assets"].sort(key=lambda row: row["rawSetCode"])
            request["checkpoint"] = {
                "completedPages": [
                    f"{row['query']}:{row['pageNo']}" for row in request["pages"]
                ],
                "completedDetailIds": [row["rawProviderId"] for row in request["details"]],
                "nextPage": None,
                "complete": True,
            }
            save_manifest(run_dir, manifest)
    except (DiscoveryError, urllib.error.URLError, TimeoutError, UnicodeError) as error:
        request["error"] = {"code": "fetch-or-parse-failure", "message": str(error)}
        manifest["failures"] = [{
            "code": "request-failure", "sliceId": request["sliceId"],
            "error": request["error"], "meaning": "source-failed; never negative evidence",
        }]
        save_manifest(run_dir, manifest)
        raise DiscoveryError(f"run retained incomplete for --resume: {error}") from error

    manifest["status"] = "complete"
    manifest["completedAt"] = timestamp
    save_manifest(run_dir, manifest)
    projection, _ = build_latest(contract, capability, identity)
    summary_text, records_text = render_projection(projection)
    OUTPUT_PATH.write_text(summary_text, encoding="utf-8")
    RECORDS_PATH.write_bytes(records_text.encode("utf-8"))
    counts = projection["meta"]["counts"]
    print(
        f"retained {run_id}: {counts['records']} card records, "
        f"{counts['newCandidate']} new candidates, {counts['runErrors']} run errors"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate immutable runs and projections")
    parser.add_argument("--refresh-asia", action="store_true", help="create or resume an official Asia run")
    parser.add_argument("--resume", action="store_true", help="resume the named incomplete run")
    parser.add_argument("--run-id", help="immutable run id in YYYYMMDDTHHMMSSZ form")
    parser.add_argument("--retrieved-at", help="explicit ISO-8601 retrieval timestamp for a run")
    args = parser.parse_args()
    try:
        if args.refresh_asia:
            if not args.run_id:
                raise DiscoveryError("--refresh-asia requires --run-id")
            refresh(args.run_id, args.retrieved_at, args.resume)
            return 0
        if args.resume:
            raise DiscoveryError("--resume requires --refresh-asia")
        contract, capability, identity = load_inputs()
        projection, run_dir = build_latest(contract, capability, identity)
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
                raise DiscoveryError("stale projection: " + ", ".join(stale))
            counts = projection["meta"]["counts"]
            if counts["runErrors"]:
                raise DiscoveryError(f"latest run has {counts['runErrors']} run error(s)")
            print(
                f"[ ok ] card discovery: {counts['records']} records across "
                f"{counts['slices']} accounted slices; {counts['gaps']} explicit gaps"
            )
            return 0
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
        RECORDS_PATH.write_bytes(records_rendered.encode("utf-8"))
        print(f"wrote {OUTPUT_PATH.relative_to(ROOT)} from immutable run {run_dir.name}")
        return 0
    except (DiscoveryError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        print(f"[FAIL] card discovery: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

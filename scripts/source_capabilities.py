#!/usr/bin/env python3
"""Validate and materialize the bounded source capability graph (#135).

``verification/source_capabilities.json`` is the reviewed manifest. This script validates it
against the versioned JSON Schema and the current source registry, resolves every verdict source
to a provider surface, checks every claimed coverage edge against a positive observation and
persists a SHA-256 for the exact retained fixture in the generated graph.

No network request is made here. A failed, blocked or empty source is graph state, never negative
evidence.

    python scripts/source_capabilities.py
    python scripts/source_capabilities.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "verification" / "source_capabilities.json"
SCHEMA_PATH = ROOT / "verification" / "source_capability_schema.json"
REGISTRY_PATH = ROOT / "verification" / "source_registry.json"
OUTPUT_PATH = ROOT / "verification" / "source_capability_graph.json"

ALLOWED_LOCALITIES = {
    "WEST", "LATAM", "JP", "KR", "TW", "CN", "ID", "TH", "SEA", "GLOBAL",
}
FAILURE_STATES = {
    "incomplete", "rate-limited", "blocked-by-browser", "unavailable", "needs-evidence",
}
SPECIMEN_ONLY_PROVIDERS = {
    "psa", "cgc", "snkrdunk", "ligapokemon", "retailer-listing",
    "owner-attestation", "inspected-specimen", "cardmarket-listing-photo",
    "seller-listing-photo",
}
DIMENSION_ALIASES = {"finish-override": "finish"}


class ContractError(ValueError):
    """The manifest violates its structural or semantic contract."""


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def record_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise ContractError(f"schema uses unsupported type {expected!r}")


def resolve_schema_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ContractError(f"only local JSON Schema references are supported: {reference}")
    node: Any = root_schema
    for part in reference[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def schema_errors(value: Any, schema: dict[str, Any], root_schema: dict[str, Any],
                  path: str = "$") -> list[str]:
    """Validate the JSON-Schema subset used by source_capability_schema.json."""
    if "$ref" in schema:
        return schema_errors(value, resolve_schema_ref(root_schema, schema["$ref"]),
                             root_schema, path)

    if "oneOf" in schema:
        variants = [schema_errors(value, item, root_schema, path)
                    for item in schema["oneOf"]]
        passed = sum(not errors for errors in variants)
        return [] if passed == 1 else [f"{path}: expected exactly one schema variant; got {passed}"]

    errors: list[str] = []
    expected_types = schema.get("type")
    if expected_types is not None:
        if isinstance(expected_types, str):
            expected_types = [expected_types]
        if not any(json_type_matches(value, item) for item in expected_types):
            return [f"{path}: expected {' or '.join(expected_types)}, got {type(value).__name__}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']!r}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        errors.extend(f"{path}: missing required property {name!r}"
                      for name in required if name not in value)
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            errors.extend(f"{path}: unexpected property {name!r}"
                          for name in value if name not in properties)
        for name, child in value.items():
            if name in properties:
                errors.extend(schema_errors(child, properties[name], root_schema,
                                            f"{path}.{name}"))

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if schema.get("uniqueItems") and len({canonical_json(item) for item in value}) != len(value):
            errors.append(f"{path}: array items must be unique")
        if "items" in schema:
            for index, child in enumerate(value):
                errors.extend(schema_errors(child, schema["items"], root_schema,
                                            f"{path}[{index}]"))

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than {schema['minLength']}")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: {value!r} does not match {schema['pattern']!r}")
        if schema.get("format") == "date":
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                errors.append(f"{path}: {value!r} is not an ISO date")

    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} is below {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} is above {schema['maximum']}")
    return errors


def require_unique(items: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    counts = Counter(item[key] for item in items)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    if duplicates:
        raise ContractError(f"duplicate {label}: {duplicates}")
    return {item[key]: item for item in items}


def resolve_fixture(observation: dict[str, Any], registry: dict[str, Any]) -> tuple[Any, str]:
    fixture = observation["fixtureRef"]
    if fixture["kind"] == "inline-record":
        return fixture["record"], "inline-record"

    matches = [
        row for row in registry["evidence"]
        if row["providerId"] == fixture["providerId"]
        and (row.get("canonicalUrl") or row.get("nonUrlEvidenceId")) == fixture["recordKey"]
    ]
    if len(matches) != 1:
        raise ContractError(
            f"{observation['observationId']}: fixture {fixture['providerId']} / "
            f"{fixture['recordKey']} resolves to {len(matches)} registry rows"
        )
    return matches[0], f"verification/source_registry.json:{fixture['recordKey']}"


def route_evidence(row: dict[str, Any], surfaces_by_provider: dict[str, list[dict[str, Any]]]
                   ) -> dict[str, Any]:
    candidates = surfaces_by_provider.get(row["providerId"], [])
    if len(candidates) == 1:
        return candidates[0]
    matched = []
    for surface in candidates:
        matcher = surface.get("match") or {}
        url = row.get("canonicalUrl") or ""
        evidence_id = row.get("nonUrlEvidenceId")
        if any(url.startswith(prefix) for prefix in matcher.get("urlPrefixes", [])):
            matched.append(surface)
        elif evidence_id in matcher.get("nonUrlEvidenceIds", []):
            matched.append(surface)
    if len(matched) != 1:
        source = row.get("canonicalUrl") or row.get("nonUrlEvidenceId")
        raise ContractError(
            f"registry source {source} resolves to {len(matched)} surfaces for {row['providerId']}"
        )
    return matched[0]


def validate_semantics(manifest: dict[str, Any], registry: dict[str, Any]
                       ) -> dict[str, Any]:
    providers = require_unique(manifest["providers"], "providerId", "provider ids")
    registry_providers = require_unique(registry["providers"], "providerId",
                                        "source-registry provider ids")
    if set(providers) != set(registry_providers):
        raise ContractError(
            "capability/registry provider mismatch: "
            f"only manifest={sorted(set(providers) - set(registry_providers))}; "
            f"only registry={sorted(set(registry_providers) - set(providers))}"
        )
    for provider_id, provider in providers.items():
        registered = registry_providers[provider_id]
        mismatches = []
        if registered["organization"] is not None \
                and provider["operator"] != registered["organization"]:
            mismatches.append("operator")
        if provider["authorityTier"] != registered["authorityTier"]:
            mismatches.append("authorityTier")
        if provider["licenseOrTerms"] != registered["licenseOrTerms"]:
            mismatches.append("licenseOrTerms")
        if mismatches:
            raise ContractError(f"{provider_id}: capability/registry drift in {mismatches}")

    surfaces = require_unique(manifest["surfaces"], "surfaceId", "surface ids")
    surfaces_by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)
    edges: dict[str, dict[str, Any]] = {}
    edge_surface: dict[str, str] = {}
    for surface in manifest["surfaces"]:
        if surface["providerId"] not in providers:
            raise ContractError(f"{surface['surfaceId']}: unknown provider {surface['providerId']}")
        surfaces_by_provider[surface["providerId"]].append(surface)
        if surface["state"] in FAILURE_STATES and not surface["failureState"]:
            raise ContractError(f"{surface['surfaceId']}: failure state must explain the failure")
        if surface["state"] not in FAILURE_STATES and surface["failureState"]:
            raise ContractError(f"{surface['surfaceId']}: healthy/non-URL state carries a failure")
        if surface["accessMode"] in {"scriptable", "direct-download", "browser", "manual"} \
                and not surface["query"]["endpoint"]:
            raise ContractError(f"{surface['surfaceId']}: accessible surface lacks an endpoint")
        if surface["adapterState"] == "active" and not surface["coverageEdges"]:
            raise ContractError(f"{surface['surfaceId']}: active adapter has no tested edge")
        for edge in surface["coverageEdges"]:
            edge_id = edge["edgeId"]
            if edge_id in edges:
                raise ContractError(f"duplicate coverage edge {edge_id}")
            edges[edge_id] = edge
            edge_surface[edge_id] = surface["surfaceId"]
            unknown_localities = set(edge["coverage"]["localities"]) - ALLOWED_LOCALITIES
            if unknown_localities:
                raise ContractError(f"{edge_id}: unknown localities {sorted(unknown_localities)}")
            finish_capable = "finish" in edge["positiveEvidenceCapabilities"]
            if finish_capable and surface["finishCapability"]["mode"] == "none":
                raise ContractError(f"{edge_id}: finish evidence has no independent finish capability")
            absence = edge["absenceCapability"]
            if absence["enabled"]:
                if not edge["exhaustive"] or not absence["dimensions"] or not absence["exactScopes"]:
                    raise ContractError(f"{edge_id}: absence requires an exhaustive exact scope")
                if edge["boundary"]["zeroResultMeans"] != "bounded-absence":
                    raise ContractError(f"{edge_id}: absence boundary is not explicitly bounded")
                if not edge.get("outOfScopeChallengeObservationId"):
                    raise ContractError(f"{edge_id}: absence edge lacks an out-of-scope challenge")
                if "finish" in absence["dimensions"] and not surface["finishCapability"]["closedWithinScope"]:
                    raise ContractError(f"{edge_id}: finish absence lacks a closed finish profile")
            else:
                if edge["exhaustive"] or absence["dimensions"] or absence["exactScopes"]:
                    raise ContractError(f"{edge_id}: non-absence edge carries exhaustive/absence fields")
                if edge["boundary"]["zeroResultMeans"] != "unknown":
                    raise ContractError(f"{edge_id}: zero result must remain unknown")
            if surface["providerId"] in SPECIMEN_ONLY_PROVIDERS and absence["enabled"]:
                raise ContractError(f"{edge_id}: specimen-only provider cannot establish absence")

    providers_without_surface = sorted(set(providers) - set(surfaces_by_provider))
    if providers_without_surface:
        raise ContractError(f"providers without a capability surface: {providers_without_surface}")

    observations = require_unique(manifest["observations"], "observationId", "observation ids")
    resolved_observations: list[dict[str, Any]] = []
    for observation in manifest["observations"]:
        if observation["surfaceId"] not in surfaces:
            raise ContractError(
                f"{observation['observationId']}: unknown surface {observation['surfaceId']}"
            )
        for edge_id in observation["validatesEdges"]:
            if edge_id not in edges:
                raise ContractError(f"{observation['observationId']}: unknown edge {edge_id}")
            if edge_surface[edge_id] != observation["surfaceId"]:
                raise ContractError(
                    f"{observation['observationId']}: edge {edge_id} belongs to another surface"
                )
        fixture = observation["fixtureRef"]
        surface_provider = surfaces[observation["surfaceId"]]["providerId"]
        if fixture["kind"] == "source-registry-evidence" \
                and fixture["providerId"] != surface_provider:
            raise ContractError(f"{observation['observationId']}: fixture/provider mismatch")
        raw_record, raw_ref = resolve_fixture(observation, registry)
        resolved_observations.append({
            **{key: value for key, value in observation.items() if key != "fixtureRef"},
            "rawRecordRef": raw_ref,
            "rawRecordHash": record_hash(raw_record),
            "rawRecord": raw_record,
        })

    for edge_id, edge in edges.items():
        positive = observations.get(edge["knownPositiveObservationId"])
        if not positive or positive["kind"] != "known-positive" \
                or edge_id not in positive["validatesEdges"]:
            raise ContractError(f"{edge_id}: known-positive observation is missing or mislinked")
        if edge["absenceCapability"]["enabled"]:
            challenge = observations.get(edge["outOfScopeChallengeObservationId"])
            if not challenge or challenge["kind"] != "out-of-scope-challenge" \
                    or edge_id not in challenge["validatesEdges"]:
                raise ContractError(f"{edge_id}: out-of-scope challenge is missing or mislinked")

    manifest_absence: dict[str, set[str]] = defaultdict(set)
    for edge_id, edge in edges.items():
        if edge["absenceCapability"]["enabled"]:
            provider_id = surfaces[edge_surface[edge_id]]["providerId"]
            manifest_absence[provider_id].update(edge["absenceCapability"]["exactScopes"])
    registry_absence = {
        provider_id: set(provider.get("absenceScopes") or [])
        for provider_id, provider in registry_providers.items()
        if provider.get("supportsAbsence")
    }
    if dict(manifest_absence) != registry_absence:
        raise ContractError(
            f"absence scopes differ from source registry: manifest={dict(manifest_absence)}, "
            f"registry={registry_absence}"
        )

    source_resolution = []
    for row in registry["evidence"]:
        surface = route_evidence(row, surfaces_by_provider)
        surface_edges = surface["coverageEdges"]
        if not surface_edges:
            source = row.get("canonicalUrl") or row.get("nonUrlEvidenceId")
            raise ContractError(f"used source {source} resolves to a surface with no capability edge")
        available = {
            capability for edge in surface_edges
            for capability in edge["positiveEvidenceCapabilities"]
        }
        required = {DIMENSION_ALIASES.get(item, item) for item in row["dimensions"]}
        missing = sorted(required - available)
        if missing:
            source = row.get("canonicalUrl") or row.get("nonUrlEvidenceId")
            raise ContractError(
                f"used source {source} requires undeclared capabilities {missing} on "
                f"{surface['surfaceId']}"
            )
        absence_edges = [
            edge["edgeId"] for edge in surface_edges
            if row.get("canonicalUrl") in edge["absenceCapability"]["exactScopes"]
        ]
        if row.get("supportsAbsence") and len(absence_edges) != 1:
            raise ContractError(
                f"absence-capable source {row['canonicalUrl']} resolves to {absence_edges}"
            )
        source_resolution.append({
            "sourceKey": row.get("canonicalUrl") or row.get("nonUrlEvidenceId"),
            "providerId": row["providerId"],
            "surfaceId": surface["surfaceId"],
            "capabilityEdgeIds": [edge["edgeId"] for edge in surface_edges],
            "absenceEdgeIds": absence_edges,
            "dimensions": row["dimensions"],
        })

    flattened_edges = []
    for surface in manifest["surfaces"]:
        for edge in surface["coverageEdges"]:
            flattened_edges.append({
                "edgeId": edge["edgeId"],
                "providerId": surface["providerId"],
                "surfaceId": surface["surfaceId"],
                **{key: value for key, value in edge.items() if key != "edgeId"},
            })
    return {
        "surfaces": surfaces,
        "edges": flattened_edges,
        "observations": resolved_observations,
        "sourceResolution": source_resolution,
    }


def build() -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    schema = read_json(SCHEMA_PATH)
    registry = read_json(REGISTRY_PATH)
    errors = schema_errors(manifest, schema, schema)
    if errors:
        preview = "\n  - ".join(errors[:20])
        raise ContractError(f"manifest violates source_capability_schema.json:\n  - {preview}")
    validated = validate_semantics(manifest, registry)

    surface_rows = []
    for surface in manifest["surfaces"]:
        surface_rows.append({
            **{key: value for key, value in surface.items() if key != "coverageEdges"},
            "coverageEdgeIds": [edge["edgeId"] for edge in surface["coverageEdges"]],
        })
    absence_edges = [
        edge["edgeId"] for edge in validated["edges"]
        if edge["absenceCapability"]["enabled"]
    ]
    states = Counter(surface["state"] for surface in manifest["surfaces"])
    return {
        "meta": {
            "schema": "snoredex-source-capability-graph",
            "schemaVersion": manifest["meta"]["schemaVersion"],
            "generated": datetime.now(timezone.utc).date().isoformat(),
            "manifest": "verification/source_capabilities.json",
            "manifestSchema": "verification/source_capability_schema.json",
            "sourceRegistry": "verification/source_registry.json",
            "policies": manifest["meta"]["policies"],
            "counts": {
                "providers": len(manifest["providers"]),
                "surfaces": len(surface_rows),
                "coverageEdges": len(validated["edges"]),
                "absenceEdges": len(absence_edges),
                "observations": len(validated["observations"]),
                "resolvedVerdictSources": len(validated["sourceResolution"]),
            },
            "surfaceStates": dict(sorted(states.items())),
        },
        "providers": manifest["providers"],
        "surfaces": surface_rows,
        "coverageEdges": validated["edges"],
        "observations": validated["observations"],
        "sourceResolution": validated["sourceResolution"],
    }


def render() -> str:
    return json.dumps(build(), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="validate and fail when the committed graph differs")
    args = parser.parse_args()
    try:
        rendered = render()
    except (ContractError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"[FAIL] source capability graph: {error}", file=sys.stderr)
        return 1

    if args.check:
        current = read_json(OUTPUT_PATH) if OUTPUT_PATH.exists() else {}
        expected = json.loads(rendered)
        # The write date is provenance, not input-derived graph content. Comparing it made every
        # unchanged checkout stale at midnight; source_registry.py applies the same boundary.
        current.get("meta", {}).pop("generated", None)
        expected.get("meta", {}).pop("generated", None)
        if current != expected:
            print(f"[FAIL] {OUTPUT_PATH.relative_to(ROOT)} is stale")
            return 1
        graph = expected
        counts = graph["meta"]["counts"]
        print(
            f"[ ok ] source capability graph: {counts['providers']} providers, "
            f"{counts['coverageEdges']} bounded edges, {counts['resolvedVerdictSources']} "
            "verdict sources resolved"
        )
        return 0

    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    graph = json.loads(rendered)
    counts = graph["meta"]["counts"]
    print(
        f"wrote {OUTPUT_PATH.relative_to(ROOT)}: {counts['providers']} providers -> "
        f"{counts['coverageEdges']} edges, {counts['absenceEdges']} exact absence edges, "
        f"{counts['observations']} hashed observations"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

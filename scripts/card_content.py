#!/usr/bin/env python3
"""Read reviewed card-content observations without changing evidence or identities.

This validates retained bytes, exact target joins and source capability boundaries.
It does not turn a well-formed observation into evidence: acceptance remains a
field-by-field review. Payload/profile validation belongs to the export consumer.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path, PurePosixPath

from collector_catalogue import entity_payloads
from source_capabilities import route_evidence
from source_registry import resolve_provider
from specimen_links import release_specimens, specimen_reference_index

ROOT = Path(__file__).resolve().parent.parent
STORE = "verification/card_content_observations.json"
FIELDS = {
    "/lang", "/card_type", "/subtype", "/name", "/subtitle", "/artists",
    "/regulation_mark", "/set_icon", "/collector_number", "/rarity",
    "/copyright", "/tags", "/size", "/back", "/foil", "/text", "/stage",
    "/stage_text", "/hp", "/types", "/weakness", "/resistance", "/retreat",
    "/flavor_text",
}
STATES = {"known", "not-applicable", "unknown", "blocked-by-source"}
METHODS = {"transcription", "structured-source assertion", "owner determination",
           "explicit reviewed transformation"}


def read(root: Path, relative: str):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def indexed(rows: list, key: str) -> dict:
    require(isinstance(rows, list), f"{key}: expected an array")
    result = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get(key), str) and bool(row[key]),
                f"missing {key}")
        require(row[key] not in result, f"duplicate {key}: {row[key]}")
        result[row[key]] = row
    return result


def strings(value, label: str) -> set[str]:
    require(isinstance(value, list) and bool(value)
            and all(isinstance(v, str) and v for v in value), f"{label}: expected nonempty string array")
    require(len(value) == len(set(value)), f"{label}: duplicate values")
    return set(value)


def dated(value, label: str) -> None:
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None,
            f"{label}: expected ISO date")
    date.fromisoformat(value)


def retained_path(root: Path, relative: str) -> Path:
    require(isinstance(relative, str) and bool(relative), "missing retained path")
    path = PurePosixPath(relative)
    require(not path.is_absolute() and ".." not in path.parts
            and "\\" not in relative and ":" not in relative, f"unsafe retained path: {relative}")
    resolved = (root / relative).resolve()
    require(resolved.is_relative_to(root.resolve()), f"retained path escapes repository: {relative}")
    return resolved


def context(root: Path) -> dict:
    graph = read(root, "verification/authoritative_graph.json")
    profile = read(root, "verification/malie_profile.json")
    specimens = indexed(read(root, "verification/specimens.json")["specimens"], "specimenId")
    surfaces = defaultdict(list)
    for surface in read(root, "verification/source_capabilities.json")["surfaces"]:
        surfaces[surface["providerId"]].append(surface)
    return {
        "releases": indexed(entity_payloads(graph, "card-release"), "cardReleaseId"),
        "printings": indexed(entity_payloads(graph, "physical-printing"), "physicalPrintingId"),
        "claims": indexed(entity_payloads(graph, "candidate-claim"), "claimId"),
        "specimens": specimens,
        "citations": specimen_reference_index(specimens.values(), read(root, "verification/units.json")),
        "records": indexed(read(root, "verification/source_first_prints.json")["prints"], "printId"),
        "surfaces": surfaces,
        "malieLanguages": {row["cardReleaseId"]: profile["languages"][row["localizationId"]]
                           for row in profile["pilot"] if row["localizationId"] in profile["languages"]},
    }


def validate_target(row: dict, ctx: dict, label: str) -> tuple[str, set[str]]:
    release = row.get("cardReleaseId")
    require(release in ctx["releases"], f"{label}: unknown card release")
    ids = strings(row.get("physicalPrintingIds"), label)
    require(all(pid in ctx["printings"] and ctx["printings"][pid]["cardReleaseId"] == release for pid in ids),
            f"{label}: printing does not belong to release")
    return release, ids


def validate_capability(source: dict, ctx: dict) -> None:
    sid, scope = source["sourceId"], source["scope"]
    fields = strings(scope.get("fields"), sid)
    require(fields <= FIELDS, f"{sid}: unsupported content field")
    surface = route_evidence({"providerId": source["providerId"], "canonicalUrl": source["url"]}, ctx["surfaces"])
    required = {{"/size": "size", "/back": "back", "/foil": "foil"}.get(f, "card-content") for f in fields}
    # One edge must cover the localized release, not a union of unrelated edges.
    release = ctx["releases"][scope["cardReleaseId"]]
    require(any(required <= set(edge["positiveEvidenceCapabilities"])
                and release["locality"] in edge["coverage"]["localities"]
                and release["language"] in edge["coverage"]["languages"]
                for edge in surface["coverageEdges"]), f"{sid}: unsupported source capability or locality")


def validate_specimen(source: dict, ctx: dict) -> None:
    sid, scope = source["sourceId"], source["scope"]
    specimen_id = scope.get("specimenId")
    if not specimen_id:
        return
    spec = ctx["specimens"].get(specimen_id, {})
    require(source["retainedPath"] == "verification/specimens/" + spec.get("photograph", "")
            and spec.get("photographSha256") == "sha256:" + source["sha256"]
            and spec.get("photographSource") == source["url"], f"{sid}: specimen provenance mismatch")
    linked = release_specimens(ctx["releases"][scope["cardReleaseId"]],
                               [ctx["printings"][p] for p in scope["physicalPrintingIds"]],
                               ctx["citations"], ctx["records"], ctx["claims"])
    require(specimen_id in linked, f"{sid}: specimen is not cited by this release/printing")


def validate_source(source: dict, root: Path, ctx: dict) -> None:
    sid = source["sourceId"]
    for key in ("providerId", "url", "retainedPath", "sha256"):
        require(isinstance(source.get(key), str) and bool(source[key]), f"{sid}: missing {key}")
    dated(source.get("retrievedAt"), sid)
    require(resolve_provider(source["url"], None) == source["providerId"], f"{sid}: provider mismatch")
    path = retained_path(root, source["retainedPath"])
    require(path.is_file(), f"{sid}: missing retained source")
    require(hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"], f"{sid}: source digest mismatch")
    scope = source.get("scope")
    require(isinstance(scope, dict) and bool(scope.get("limits")), f"{sid}: missing source limits")
    validate_target(scope, ctx, sid)
    validate_capability(source, ctx)
    validate_specimen(source, ctx)
    if source["providerId"] == "malie" and sid in ctx["acceptedSources"]:
        ctx.setdefault("malieRecords", {})[sid] = bound_malie_records(source, path, ctx)


def bound_malie_records(source: dict, path: Path, ctx: dict) -> dict:
    """Qualify the retained reference's exact named varieties, not neighbouring rows."""
    sid, scope = source["sourceId"], source["scope"]
    require(scope.get("language") == ctx["malieLanguages"].get(scope["cardReleaseId"]),
            f"{sid}: reference language does not match target profile")
    exports = [row for row in json.loads(path.read_text(encoding="utf-8"))["exports"]
               if row["url"] == source["url"] and row["language"] == scope["language"]]
    require(len(exports) == 1, f"{sid}: reference URL/language mismatch")
    records = {row["arrayIndex"]: row["record"] for row in exports[0]["records"]}
    bindings = indexed(scope.get("recordBindings"), "physicalPrintingId")
    require(set(bindings) == set(scope["physicalPrintingIds"]), f"{sid}: incomplete reference bindings")
    result = {}
    for pid, binding in bindings.items():
        require(binding.get("arrayIndex") in records, f"{sid}: unknown retained record")
        record = records[binding["arrayIndex"]]
        validate_malie_identity(record, ctx["releases"][scope["cardReleaseId"]], scope["language"], sid)
        validate_malie_binding(record, binding, ctx["printings"][pid], sid)
        result[pid] = record
    return result


def validate_malie_identity(record: dict, release: dict, language: str, label: str) -> None:
    require(record["lang"] == language
            and record["set_icon"].partition("_")[0] == release["localSetCode"]
            and record["collector_number"]["numerator"] == release["localNumber"],
            f"{label}: retained reference does not identify this localized card")


def validate_malie_binding(record: dict, binding: dict, printing: dict, label: str) -> None:
    native = record["ext"]["tcgl"]
    require(native["cardID"] == binding["tcglCardId"]
            and native["longFormID"] == binding["longFormID"], f"{label}: reference variant mismatch")
    # This is the reviewed finite source vocabulary, not an inference from a missing foil object.
    named_finish = {"NonFoil_None": "non-holo", "FlatSilver_Reverse": "reverse-holo"}
    suffix = "_".join(native["longFormID"].split("_")[-2:])
    require(suffix in named_finish and named_finish[suffix] == printing["finish"],
            f"{label}: named reference variant conflicts with physical finish")


def validate_malie_value(observation: dict, source_id: str, ctx: dict) -> None:
    field = observation["field"].removeprefix("/")
    for pid in observation["physicalPrintingIds"]:
        record = ctx["malieRecords"][source_id][pid]
        if observation["state"] == "known":
            require(field in record and record[field] == observation["value"],
                    f"{observation['observationId']}: value differs from bound reference")
        else:
            require(field == "foil" and record["ext"]["tcgl"]["longFormID"].endswith("_NonFoil_None"),
                    f"{observation['observationId']}: reference omission is not inapplicability")


def validate_assertion(observation: dict) -> list[str]:
    oid, state = observation["observationId"], observation.get("state")
    require(state in STATES and observation.get("field") in FIELDS, f"{oid}: invalid field/state")
    require(observation.get("method") in METHODS, f"{oid}: missing reviewed method")
    require(isinstance(observation.get("basis"), str) and bool(observation["basis"].strip()),
            f"{oid}: missing reviewed basis")
    dated(observation.get("observedAt"), oid)
    require(("value" in observation) == (state == "known"), f"{oid}: value/state mismatch")
    refs = observation.get("sourceIds")
    require(isinstance(refs, list), f"{oid}: invalid source references")
    if state in {"known", "not-applicable"}:
        strings(refs, oid)
    else:
        require(isinstance(observation.get("nextStep"), str) and bool(observation["nextStep"]),
                f"{oid}: unresolved observation needs a next step")
    return refs


def validate_observation(observation: dict, sources: dict, ctx: dict) -> None:
    oid = observation["observationId"]
    release, pids = validate_target(observation, ctx, oid)
    for sid in validate_assertion(observation):
        require(sid in sources, f"{oid}: unknown source {sid}")
        scope = sources[sid]["scope"]
        require(scope["cardReleaseId"] == release and pids <= set(scope["physicalPrintingIds"])
                and observation["field"] in scope["fields"], f"{oid}: source outside reviewed field/printing scope")
        if sources[sid]["providerId"] == "malie" and observation["state"] in {"known", "not-applicable"}:
            validate_malie_value(observation, sid, ctx)


def validate(document: dict, root: Path = ROOT) -> dict:
    require(isinstance(document, dict) and type(document.get("schemaVersion")) is int
            and document["schemaVersion"] == 1, "unsupported content schema")
    sources = indexed(document.get("sources"), "sourceId")
    observations = indexed(document.get("observations"), "observationId")
    ctx = context(root)
    ctx["acceptedSources"] = {sid for row in observations.values()
                              if row.get("state") in {"known", "not-applicable"}
                              for sid in row.get("sourceIds", [])}
    for source in sources.values():
        validate_source(source, root, ctx)
    for observation in observations.values():
        validate_observation(observation, sources, ctx)
    return document


def load(root: Path = ROOT) -> dict:
    return validate(read(root, STORE), root)


if __name__ == "__main__":
    data = load()
    print(f"Card content: {len(data['observations'])} observations, {len(data['sources'])} retained sources validated.")

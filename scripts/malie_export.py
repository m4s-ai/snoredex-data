#!/usr/bin/env python3
"""Deterministic Malie pilot export; authoritative identities remain in Snoredex.

The profile implements the reviewed contract in verification/MALIE-EXPORT.md.
This module uses the repository's existing stdlib JSON-schema validator.
"""
from __future__ import annotations

import json
import re
import copy
import hashlib
import argparse
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from source_capabilities import schema_errors

ROOT = Path(__file__).resolve().parent.parent
TEXT = {"type": "string", "minLength": 1, "pattern": r"\S"}
NATURAL = {"type": "integer", "minimum": 0}
STATUSES = ["outside-profile", "blocked-by-source", "needs-evidence", "needs-mapping", "exported"]
OPTIONAL_FIELDS = {"subtype", "subtitle", "artists", "rarity", "tags", "foil",
                   "weakness", "resistance", "flavor_text"}
IDENTITY_FIELDS = (
    "itemId", "cardReleaseId", "physicalPrintingId",
    "localizationId", "localSetId", "setEditionId", "edition", "editionAssignmentStatus",
    "finish", "finishVerificationStatus", "foilPattern", "markings", "distribution",
    "cardSize", "errorClass", "itemKind", "sourceClaimRefs", "completenessStatus", "progressClass",
    "sourcePrintingId", "finishUnitId",
)
INPUT_FILES = (
    "verification/malie_profile.json", "collector_catalogue.json",
    "verification/card_content_observations.json", "verification/authoritative_graph.json",
    "verification/specimens.json", "verification/units.json", "verification/source_first_prints.json",
    "verification/finish_units.json", "verification/source_registry.json", "verification/source_capabilities.json",
)


class ExportError(ValueError):
    """Malformed inputs or an inconsistent bundle; never a silently skipped card."""


def require(condition, message):
    if not condition:
        raise ExportError(message)


def unique(rows: list[dict], key: str) -> dict:
    require(isinstance(rows, list), f"{key}: expected an array")
    result = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get(key), str), f"missing {key}")
        require(row[key] not in result, f"duplicate {key}: {row[key]}")
        result[row[key]] = row
    return result


def object_schema(properties: dict, required=None) -> dict:
    return {"type": "object", "properties": properties, "additionalProperties": False,
            "required": list(properties) if required is None else list(required)}


def array_schema(items: dict) -> dict:
    return {"type": "array", "items": items, "minItems": 1}


def enum_schema(values: list[str]) -> dict:
    return {"type": "string", "enum": values}


def text_schema(vocabulary: dict) -> dict:
    damage = object_schema({"amount": NATURAL, "suffix": enum_schema(vocabulary["damage.suffix"])}, ["amount"])
    ability = object_schema({"kind": {"const": "ABILITY"}, "name": TEXT, "text": TEXT})
    attack = object_schema({
        "kind": {"const": "ATTACK"}, "name": TEXT, "text": TEXT,
        "cost": array_schema(enum_schema([*vocabulary["energyType"], "FREE"])), "damage": damage,
    }, ["kind", "name", "cost"])
    return array_schema({"oneOf": [ability, attack]})


def payload_schema(profile: dict) -> dict:
    vocab = profile["vocabulary"]
    energies = array_schema(enum_schema(vocab["energyType"]))
    properties = {
        "lang": enum_schema(sorted(set(profile["languages"].values()))),
        "card_type": enum_schema(vocab["card_type"]), "name": TEXT, "subtitle": TEXT,
        "artists": object_schema({"text": TEXT, "list": array_schema(TEXT)}),
        "regulation_mark": TEXT, "set_icon": TEXT,
        "collector_number": object_schema({"full": TEXT, "numerator": TEXT, "denominator": TEXT,
                                             "numeric": NATURAL}, ["full", "numerator", "numeric"]),
        "rarity": object_schema({"designation": enum_schema(vocab["rarity.designation"]),
                                   "icon": enum_schema(vocab["rarity.icon"])}),
        "copyright": object_schema({"text": TEXT, "year": NATURAL}),
        "tags": array_schema(enum_schema(vocab["tags"])),
        "size": enum_schema(vocab["size"]), "back": enum_schema(vocab["back"]),
        "foil": object_schema({"type": enum_schema(vocab["foil.type"]), "mask": enum_schema(vocab["foil.mask"])}),
        "text": text_schema(vocab), "stage": enum_schema(vocab["stage"]), "stage_text": TEXT,
        "hp": {"type": "integer", "minimum": 1}, "types": energies,
        "weakness": object_schema({"types": energies, "amount": NATURAL, "operator": {"const": "×"}}),
        "resistance": object_schema({"types": energies, "amount": NATURAL, "operator": {"const": "-"}}),
        "retreat": NATURAL, "flavor_text": TEXT,
    }
    required = ["lang", "card_type", "name", "regulation_mark", "set_icon", "collector_number",
                "copyright", "size", "back", "text", "stage", "stage_text", "hp", "types", "retreat"]
    return object_schema(properties, required)


def number_errors(number: dict, pattern: str) -> list[str]:
    errors = []
    parsed = re.fullmatch(pattern, number["numerator"])
    if parsed is None or int(parsed.group(1)) != number["numeric"]:
        errors.append("collector_number.numeric does not match the exact numerator")
    full = number["numerator"]
    if "denominator" in number:
        full += "/" + number["denominator"]
    if number["full"] != full:
        errors.append("collector_number.full does not preserve numerator/denominator")
    return errors


def payload_errors(payload: dict, profile: dict) -> list[str]:
    schema = payload_schema(profile)
    errors = schema_errors(payload, schema, schema)
    if errors:
        return errors
    errors.extend(number_errors(payload["collector_number"], profile["numberPattern"]))
    errors.extend(applicability_errors(payload, profile))
    return errors


def applicability_errors(payload: dict, profile: dict) -> list[str]:
    errors = copyright_errors(payload.get("copyright"))
    pairs = dict(zip(profile["vocabulary"]["rarity.designation"], profile["vocabulary"]["rarity.icon"]))
    if "rarity" in payload and pairs[payload["rarity"]["designation"]] != payload["rarity"]["icon"]:
        errors.append("rarity designation/icon mismatch")
    if "tags" in payload and payload["tags"] != sorted(set(payload["tags"])):
        errors.append("tags must be unique and sorted")
    for block in payload.get("text", []):
        if "FREE" in block.get("cost", []) and block["cost"] != ["FREE"]:
            errors.append("FREE must be the only attack-cost symbol")
    return errors


def copyright_errors(notice: dict | None) -> list[str]:
    if notice is None:
        return []
    years = re.findall(r"(?<!\d)\d{4}(?!\d)", notice["text"])
    if not years or max(map(int, years)) != notice["year"]:
        return ["copyright.year must be the largest explicit year in the printed notice"]
    return []


def canonical_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def selected_items(profile: dict, catalogue: dict) -> list[dict]:
    require(profile["statusPrecedence"] == STATUSES, "unsupported status precedence")
    selected = unique(profile["pilot"], "itemId")
    items = unique(catalogue["items"], "itemId")
    require(set(selected) <= items.keys(), "selected item does not exist")
    physical_ids = []
    for iid, target in selected.items():
        item = items[iid]
        require(all(target[key] == item[key] for key in
                    ("cardReleaseId", "physicalPrintingId", "localizationId")), f"selected identity mismatch: {iid}")
        if item["physicalPrintingId"] is not None:
            physical_ids.append(item["physicalPrintingId"])
    require(len(physical_ids) == len(set(physical_ids)), "selected physical identity collision")
    return [items[iid] for iid in sorted(selected)]


def reason(status: str, code: str, field: str, message: str) -> dict:
    return {"status": status, "code": code, "field": field, "message": message}


def leaf_paths(value, prefix: str) -> list[str]:
    if isinstance(value, dict):
        return [path for key, child in sorted(value.items())
                for path in leaf_paths(child, prefix + "/" + key.replace("~", "~0").replace("/", "~1"))]
    if isinstance(value, list):
        return [path for index, child in enumerate(value) for path in leaf_paths(child, prefix + "/" + str(index))]
    return [prefix]


def observation_provenance(row: dict) -> dict:
    result = {key: copy.deepcopy(row[key]) for key in
              ("observationId", "state", "sourceIds", "observedAt", "method", "basis", "nextStep") if key in row}
    result["sourceIds"] = sorted(row["sourceIds"])
    return result


def field_provenance(field: str, rows: list[dict], sources: dict, providers: dict) -> dict:
    refs = sorted({sid for row in rows for sid in row["sourceIds"]})
    qualified = []
    for sid in refs:
        require(sid in sources, f"unresolved field source: {sid}")
        source = sources[sid]
        require(source["providerId"] in providers, f"unregistered source provider: {sid}")
        provider = providers[source["providerId"]]
        qualified.append({**copy.deepcopy(source), "authorityTier": provider["authorityTier"],
                          "licenseOrTerms": provider["licenseOrTerms"]})
    return {"observations": [observation_provenance(row)
                             for row in sorted(rows, key=lambda r: r["observationId"])],
            "sources": qualified, "covers": sorted({p for row in rows if row["state"] == "known"
                                                      for p in leaf_paths(row["value"], field)})}


def choose_field(field: str, rows: list[dict]) -> tuple[str | None, object, list[dict]]:
    accepted = [normalized_observation(field, row) for row in rows if row["state"] in {"known", "not-applicable"}]
    signatures = {canonical_bytes([row["state"], row.get("value")]) for row in accepted}
    if len(signatures) > 1:
        return None, None, [reason("needs-mapping", "conflicting-observations", field,
                                  "Accepted observations disagree; no source is silently preferred.")]
    if accepted:
        return accepted[0]["state"], copy.deepcopy(accepted[0].get("value")), []
    if not rows:
        return None, None, [reason("needs-evidence", "unresolved-field", field,
                                  "No accepted field value or applicability observation.")]
    return None, None, [reason("blocked-by-source" if row["state"] == "blocked-by-source" else "needs-evidence",
                              "unresolved-field", field, row["basis"]) for row in rows]


def normalized_observation(field: str, row: dict) -> dict:
    result = copy.deepcopy(row)
    if field == "/tags" and result["state"] == "known":
        payload = {"tags": result["value"]}
        normalize_tags(payload)
        result["value"] = payload["tags"]
    return result


def content_fields(item: dict, content: dict, profile: dict, providers: dict) -> tuple[dict, dict, list]:
    sources = unique(content["sources"], "sourceId")
    observations = unique(content["observations"], "observationId")
    by_field = defaultdict(list)
    for row in observations.values():
        if row["cardReleaseId"] == item["cardReleaseId"] and item["physicalPrintingId"] in row["physicalPrintingIds"]:
            by_field[row["field"]].append(row)
    fields = set(payload_schema(profile)["properties"]) | {"subtype"}
    require(set(by_field) <= {"/" + f for f in fields}, "observation targets an unsupported payload field")
    payload, provenance, reasons = {}, {}, []
    for name in sorted(fields):
        field = "/" + name
        rows = by_field[field]
        state, value, problems = choose_field(field, rows)
        reasons.extend(problems)
        provenance[field] = field_provenance(field, rows, sources, providers)
        if state == "known":
            payload[name] = value
        elif state == "not-applicable" and name not in OPTIONAL_FIELDS:
            reasons.append(reason("needs-mapping", "required-field-inapplicable", field, "The profile requires this field."))
    return payload, provenance, reasons


def scope_reasons(item: dict, profile: dict) -> list[dict]:
    reasons = []
    if item["localizationId"] not in profile["languages"]:
        reasons.append(reason("outside-profile", "unsupported-localization", "/lang", item["localizationId"]))
    if item["localSetId"] not in profile["supportedLocalSetIds"]:
        reasons.append(reason("outside-profile", "unsupported-set-era", "/set_icon", item["localSetId"]))
    if item["itemKind"] != "verified-printing" or item["physicalPrintingId"] is None:
        reasons.append(reason("needs-evidence", "unresolved-physical-printing", "/identity", "No verified physical-printing identity."))
    if item.get("finishVerificationStatus") != "confirmed" or item.get("finish") in {None, "unknown"}:
        reasons.append(reason("needs-evidence", "unknown-finish", "/foil", "A language claim does not establish a physical finish."))
    return reasons


def identity_conflicts(item: dict, payload: dict, profile: dict) -> list[dict]:
    reasons = physical_scope_reasons(item, payload, profile)
    comparisons = {
        "lang": profile["languages"].get(item["localizationId"]),
        "name": item.get("localCardName"),
        "size": {"standard": "STANDARD"}.get(item.get("cardSize")),
    }
    for field, expected in comparisons.items():
        if expected is not None and field in payload and payload[field] != expected:
            reasons.append(reason("needs-mapping", "canonical-field-conflict", "/" + field,
                                  "The observed value conflicts with the existing localized identity/physical owner."))
    if "card_type" in payload and payload["card_type"] not in profile["vocabulary"]["card_type"]:
        reasons.append(reason("outside-profile", "unsupported-card-type", "/card_type", "Card type is outside this profile."))
    reasons.extend(finish_conflicts(item, payload))
    reasons.extend(printed_identity_conflicts(item, payload, profile))
    return reasons


def physical_scope_reasons(item: dict, payload: dict, profile: dict) -> list[dict]:
    reasons = []
    size = item.get("cardSize")
    if size != "standard":
        status = "needs-evidence" if size in {None, "unknown"} else "outside-profile"
        reasons.append(reason(status, "unsupported-physical-size", "/size",
                              "The physical owner must positively establish standard size."))
    for key in ("distribution", "markings", "edition", "errorClass"):
        if item.get(key):
            reasons.append(reason("needs-mapping", "unsupported-physical-dimension", "/identity/" + key,
                                  "Retained in the companion; this profile has no payload mapping for the physical distinction."))
    pattern = item.get("foilPattern")
    if pattern is not None and (pattern not in profile["foilPatternMappings"]
                                or profile["foilPatternMappings"][pattern] != payload.get("foil")):
        reasons.append(reason("needs-mapping", "unsupported-foil-pattern", "/identity/foilPattern",
                              "No reviewed pattern/layer/mask agreement in this profile."))
    return reasons


def printed_identity_conflicts(item: dict, payload: dict, profile: dict) -> list[dict]:
    reasons = []
    number = payload.get("collector_number")
    if isinstance(number, dict):
        for field, owner in (("numerator", "collectorNumber"), ("denominator", "collectorNumberDenominator")):
            if item.get(owner) is not None and number.get(field) != item[owner]:
                reasons.append(reason("needs-mapping", "printed-number-conflict", "/collector_number/" + field,
                                      "Printed numbering disagrees with the current localized owner."))
    suffix = profile["printedLanguageSuffixes"].get(item["localizationId"])
    if suffix and item.get("localSetCode") and "set_icon" in payload:
        expected = item["localSetCode"] + "_" + suffix
        if payload["set_icon"] != expected:
            reasons.append(reason("needs-mapping", "printed-set-conflict", "/set_icon", "Printed set/language marker disagrees with the selected local set."))
    reasons.extend(rarity_conflicts(item, payload, profile))
    return reasons


def rarity_conflicts(item: dict, payload: dict, profile: dict) -> list[dict]:
    owner, observed = item.get("rarity") or {}, payload.get("rarity")
    if owner.get("evidenceStatus") != "source-backed":
        return []
    mapped = profile["rarityOwnerIds"].get(observed.get("designation")) if isinstance(observed, dict) else None
    if mapped is None or mapped != owner.get("normalizedId"):
        return [reason("needs-mapping", "rarity-owner-conflict", "/rarity", "No agreeing mapping to the source-backed rarity owner.")]
    return []


def finish_conflicts(item: dict, payload: dict) -> list[dict]:
    foil = payload.get("foil")
    finish = item.get("finish")
    if finish == "non-holo" and "foil" in payload:
        return [reason("needs-mapping", "foil-conflicts-with-non-holo", "/foil", "The physical owner establishes non-holo.")]
    if finish in {"reverse-holo", "mirror-holo"} and isinstance(foil, dict) and foil.get("mask") != "REVERSE":
        return [reason("needs-mapping", "foil-mask-conflict", "/foil/mask", "The observed mask disagrees with the physical reverse finish.")]
    if finish == "holo" and isinstance(foil, dict) and foil.get("mask") == "REVERSE":
        return [reason("needs-mapping", "foil-mask-conflict", "/foil/mask", "A reverse mask disagrees with the physical holo finish.")]
    return []


def normalize_tags(payload: dict) -> None:
    tags = payload.get("tags")
    if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags):
        payload["tags"] = sorted(set(tags))


def observation_value_errors(payload: dict, profile: dict) -> list[str]:
    """Validate present observations even when another field still lacks evidence."""
    schema = payload_schema(profile)
    schema["required"] = []
    errors = schema_errors(payload, schema, schema)
    valid = {key: value for key, value in payload.items() if key in schema["properties"]
             and not schema_errors(value, schema["properties"][key], schema)}
    if "collector_number" in valid:
        errors.extend(number_errors(valid["collector_number"], profile["numberPattern"]))
    errors.extend(applicability_errors(valid, profile))
    return errors


def compile_entry(item: dict, profile: dict, content: dict, providers: dict, physical_sources: dict) -> tuple[dict, dict]:
    payload, field_sources, reasons = content_fields(item, content, profile, providers)
    reasons.extend(scope_reasons(item, profile))
    reasons.extend(identity_conflicts(item, payload, profile))
    reasons.extend(missing_foil_reasons(item, payload, field_sources))
    normalize_tags(payload)
    bind_leaf_paths(payload, field_sources)
    reasons.extend(reason("needs-mapping", "invalid-field-value", "/", message)
                   for message in observation_value_errors(payload, profile))
    reasons = sorted({canonical_bytes(row): row for row in reasons}.values(), key=canonical_bytes)
    present = {r["status"] for r in reasons}
    status = next((s for s in profile["statusPrecedence"] if s in present), "exported")
    identity = {key: copy.deepcopy(item.get(key)) for key in IDENTITY_FIELDS}
    identity["physicalSources"] = sorted(copy.deepcopy(physical_sources.get(item["physicalPrintingId"], [])), key=canonical_bytes)
    entry = {key: item[key] for key in ("itemId", "cardReleaseId", "physicalPrintingId")}
    entry.update(status=status, reasons=reasons, identity=identity, fieldSources=field_sources)
    return entry, payload


def missing_foil_reasons(item: dict, payload: dict, fields: dict) -> list[dict]:
    if item.get("finish") not in {"holo", "reverse-holo", "mirror-holo"} or "foil" in payload:
        return []
    accepted = any(row["state"] in {"known", "not-applicable"} for row in fields["/foil"]["observations"])
    if accepted:
        return [reason("needs-mapping", "foil-applicability-conflict", "/foil",
                       "Accepted foil observations do not agree with the established foiled printing.")]
    return [reason("needs-evidence", "missing-foil-mapping", "/foil", "A foiled printing needs an explicit layer and mask.")]


def bind_leaf_paths(payload: dict, field_sources: dict) -> None:
    for field, provenance in field_sources.items():
        name = field.removeprefix("/")
        provenance["covers"] = leaf_paths(payload[name], field) if name in payload else []


def build_bundle(profile: dict, catalogue: dict, content: dict, inputs: dict,
                 providers: dict, physical_sources: dict) -> dict[str, bytes]:
    profile = copy.deepcopy(profile)
    profile["pilot"] = sorted(profile["pilot"], key=lambda row: row["itemId"])
    profile["supportedLocalSetIds"] = sorted(profile["supportedLocalSetIds"])
    profile["payloadSchema"] = payload_schema(profile)
    profile["inputPaths"] = sorted(set(INPUT_FILES) | {source["retainedPath"] for source in content["sources"]})
    profile["inputsSha256"] = digest(inputs)
    targets = unique(profile["pilot"], "itemId")
    cards, entries = [], []
    for item in selected_items(profile, catalogue):
        entry, payload = compile_entry(item, profile, content, providers, physical_sources)
        if entry["status"] == "exported":
            entry.update(cardIndex=len(cards), cardSha256=digest(payload))
            cards.append(payload)  # Equal payloads still occupy distinct physical entries.
        targets[item["itemId"]]["entrySha256"] = digest(entry)
        entries.append(entry)
    profile_bytes = canonical_bytes(profile)
    cards_bytes = canonical_bytes(cards)
    counts = Counter(entry["status"] for entry in entries)
    report = {"schemaVersion": 1, "profileId": profile["profileId"], "upstream": profile["upstream"],
              "inputs": inputs, "cardsSha256": hashlib.sha256(cards_bytes).hexdigest(),
              "profileSha256": hashlib.sha256(profile_bytes).hexdigest(), "entries": entries,
              "summary": {"selected": len(entries), **{status: counts[status] for status in STATUSES}}}
    bundle = {"cards.json": cards_bytes, "report.json": canonical_bytes(report), "profile.json": profile_bytes}
    validate_bundle(bundle)
    return bundle


def validate_entry(entry: dict, target: dict, cards: list, profile: dict) -> int | None:
    require(all(entry[key] == target[key] for key in ("itemId", "cardReleaseId", "physicalPrintingId")),
            "report target identity mismatch")
    status = entry.get("status")
    require(status in STATUSES, "unknown report status")
    validate_companion(entry, target, profile)
    require(isinstance(entry.get("reasons"), list), "missing disposition reasons")
    statuses = {row.get("status") for row in entry["reasons"]}
    require(statuses <= set(STATUSES[:-1]), "invalid reason status")
    expected = next((value for value in STATUSES if value in statuses), "exported")
    require(status == expected, "disposition precedence mismatch")
    require(target.get("entrySha256") == digest(entry), "report entry digest differs from selected target")
    if status != "exported":
        require(bool(entry["reasons"]) and "cardIndex" not in entry and "cardSha256" not in entry,
                "unexported entry has a payload or lacks reasons")
        return None
    require(not entry["reasons"] and entry["physicalPrintingId"] is not None, "invalid exported disposition")
    index = entry.get("cardIndex")
    require(type(index) is int and 0 <= index < len(cards), "invalid card index")
    card = cards[index]
    require(entry.get("cardSha256") == digest(card), "card digest mismatch")
    require(not payload_errors(card, profile), "invalid card payload")
    require(card["lang"] == profile["languages"].get(target["localizationId"]), "exported language/identity mismatch")
    validate_exported_identity(entry, card, target, profile)
    validate_field_provenance(entry, card, profile)
    return index


def provenance_schema() -> dict:
    observation = object_schema({
        "observationId": TEXT, "state": enum_schema(["known", "not-applicable", "unknown", "blocked-by-source"]),
        "sourceIds": {"type": "array", "items": TEXT}, "observedAt": TEXT,
        "method": TEXT, "basis": TEXT, "nextStep": TEXT,
    }, ["observationId", "state", "sourceIds", "observedAt", "method", "basis"])
    source = object_schema({
        "sourceId": TEXT, "providerId": TEXT, "url": TEXT, "retrievedAt": TEXT,
        "retainedPath": TEXT, "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "scope": {"type": "object"}, "authorityTier": {"type": "integer", "enum": [1, 2, 3, 5]},
        "licenseOrTerms": TEXT,
    })
    source["additionalProperties"] = True
    return object_schema({"observations": {"type": "array", "items": observation},
                          "sources": {"type": "array", "items": source},
                          "covers": {"type": "array", "items": TEXT}})


def validate_companion(entry: dict, target: dict, profile: dict) -> None:
    identity = entry.get("identity")
    require(isinstance(identity, dict) and set(IDENTITY_FIELDS) <= identity.keys(), "incomplete companion identity")
    require(all(identity[key] == target[key] for key in
                ("itemId", "cardReleaseId", "physicalPrintingId", "localizationId")), "companion target identity mismatch")
    require(isinstance(identity.get("markings"), list) and isinstance(identity.get("physicalSources"), list),
            "missing physical companion arrays")
    reason_schema = object_schema({"status": enum_schema(STATUSES[:-1]), "code": TEXT, "field": TEXT, "message": TEXT})
    schema = {"type": "array", "items": reason_schema}
    require(not schema_errors(entry.get("reasons"), schema, schema), "invalid disposition reason structure")
    expected = {"/" + name for name in payload_schema(profile)["properties"]} | {"/subtype"}
    fields = entry.get("fieldSources")
    require(isinstance(fields, dict) and set(fields) == expected, "incomplete field companion")
    schema = provenance_schema()
    for field, provenance in fields.items():
        require(not schema_errors(provenance, schema, schema), f"invalid provenance structure: {field}")
        validate_companion_refs(field, provenance, entry)


def validate_companion_refs(field: str, provenance: dict, entry: dict) -> None:
    sources = unique(provenance["sources"], "sourceId")
    observations = unique(provenance["observations"], "observationId")
    for row in observations.values():
        require(set(row["sourceIds"]) <= sources.keys(), f"unresolved companion source: {field}")
        if row["state"] in {"known", "not-applicable"}:
            require(bool(row["sourceIds"]), f"unproven companion observation: {field}")
        else:
            require(bool(row.get("nextStep")), f"unresolved companion lacks next step: {field}")
    for source in sources.values():
        scope = source["scope"]
        require(scope.get("cardReleaseId") == entry["cardReleaseId"]
                and entry["physicalPrintingId"] in scope.get("physicalPrintingIds", [])
                and field in scope.get("fields", []), f"companion source outside target/field scope: {field}")
    require(all(path == field or path.startswith(field + "/") for path in provenance["covers"]),
            f"companion covers another field: {field}")


def validate_exported_identity(entry: dict, card: dict, target: dict, profile: dict) -> None:
    identity = entry.get("identity", {})
    require(set(IDENTITY_FIELDS) <= identity.keys(), "incomplete companion identity")
    require(identity["localizationId"] == target["localizationId"]
            and identity["localSetId"] in profile["supportedLocalSetIds"], "companion locality/profile mismatch")
    require(identity["itemKind"] == "verified-printing" and identity["finishVerificationStatus"] == "confirmed",
            "exported entry is not a verified printing")
    require(identity["finish"] in {"non-holo", "holo", "reverse-holo", "mirror-holo"}, "unknown exported finish")
    require((identity["finish"] == "non-holo") == ("foil" not in card), "foil applicability mismatch")
    require(not finish_conflicts(identity, card), "exported foil conflicts with physical identity")
    require(not physical_scope_reasons(identity, card, profile), "unsupported exported physical scope")


def validate_field_provenance(entry: dict, card: dict, profile: dict) -> None:
    fields = set(payload_schema(profile)["properties"]) | {"subtype"}
    for name in fields:
        field = "/" + name
        provenance = entry.get("fieldSources", {}).get(field, {})
        sources = unique(provenance.get("sources"), "sourceId")
        state = "known" if name in card else "not-applicable"
        accepted = [row for row in provenance.get("observations", []) if row.get("state") == state]
        require(any(row.get("sourceIds") and set(row["sourceIds"]) <= sources.keys() for row in accepted),
                f"unproven exported field/applicability: {field}")
        paths = leaf_paths(card[name], field) if name in card else []
        require(provenance.get("covers") == paths, f"incomplete field-leaf provenance: {field}")


def bundle_documents(bundle: dict[str, bytes]) -> dict:
    require(set(bundle) == {"cards.json", "report.json", "profile.json"}, "incomplete bundle")
    documents = {name: json.loads(raw) for name, raw in bundle.items()}
    require(all(canonical_bytes(documents[name]) == raw for name, raw in bundle.items()), "noncanonical bundle bytes")
    return documents


def validate_envelope(cards: list, report: dict, profile: dict, bundle: dict[str, bytes]) -> None:
    require(isinstance(cards, list) and isinstance(report, dict) and isinstance(profile, dict), "invalid bundle envelope")
    require(report.get("schemaVersion") == 1 and report.get("profileId") == profile["profileId"], "profile identity mismatch")
    require(report.get("upstream") == profile["upstream"], "upstream pin mismatch")
    require(profile.get("payloadSchema") == payload_schema(profile), "published payload schema mismatch")
    require(isinstance(report.get("inputs"), dict) and bool(report["inputs"]), "missing input digests")
    validate_input_bindings(report, profile)
    require(all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                for value in report["inputs"].values()), "invalid input digest")
    require(report.get("cardsSha256") == hashlib.sha256(bundle["cards.json"]).hexdigest(), "cards file digest mismatch")
    require(report.get("profileSha256") == hashlib.sha256(bundle["profile.json"]).hexdigest(), "profile file digest mismatch")


def validate_input_bindings(report: dict, profile: dict) -> None:
    paths = profile.get("inputPaths")
    require(isinstance(paths, list) and all(isinstance(path, str) for path in paths), "missing input path contract")
    require(paths == sorted(set(paths)) and set(INPUT_FILES) <= set(paths), "incomplete canonical input set")
    inputs = report["inputs"]
    require(set(inputs) == set(paths), "incomplete input digest set")
    require(profile.get("inputsSha256") == digest(inputs), "input digest binding mismatch")
    for entry in report["entries"]:
        for provenance in entry.get("fieldSources", {}).values():
            for source in provenance.get("sources", []):
                require(source.get("retainedPath") in inputs and
                        inputs[source["retainedPath"]] == source.get("sha256"), "retained source input mismatch")


def validate_bundle(bundle: dict[str, bytes]) -> None:
    documents = bundle_documents(bundle)
    cards, report, profile = (documents[name] for name in ("cards.json", "report.json", "profile.json"))
    validate_envelope(cards, report, profile, bundle)
    targets = unique(profile["pilot"], "itemId")
    entries = unique(report["entries"], "itemId")
    require(entries.keys() == targets.keys(), "selected-input accounting mismatch")
    require(list(entries) == sorted(entries), "report entries are not ordered by item identity")
    indices = [validate_entry(entry, targets[iid], cards, profile) for iid, entry in entries.items()]
    require([i for i in indices if i is not None] == list(range(len(cards))), "payload accounting mismatch")
    counts = Counter(entry["status"] for entry in entries.values())
    require(report["summary"] == {"selected": len(entries), **{status: counts[status] for status in STATUSES}},
            "disposition summary mismatch")


def read_inputs(root: Path = ROOT) -> tuple[dict, dict, dict, dict, dict, dict]:
    require((root / "verification/card_content_observations.json").is_file(),
            "Pilot field inputs from #386 are required before a real export can be built.")
    from card_content import load as load_content
    import collector_catalogue as collector
    raw = {path: (root / path).read_bytes() for path in INPUT_FILES}
    data = {path: json.loads(value) for path, value in raw.items()}
    content = load_content(root)
    require(content == data["verification/card_content_observations.json"], "content changed during validated read")
    catalogue = data["collector_catalogue.json"]
    graph = data["verification/authoritative_graph.json"]
    require(catalogue["meta"]["catalogueFingerprint"] == collector.semantic_fingerprint(catalogue),
            "collector catalogue fingerprint mismatch")
    require(catalogue["qualitySummary"]["authoritativeGraphFingerprint"] == collector.sha256_bytes(collector.canonical_bytes(graph)),
            "collector catalogue is not bound to the current authoritative graph")
    for source in content["sources"]:
        raw[source["retainedPath"]] = (root / source["retainedPath"]).read_bytes()
        require(hashlib.sha256(raw[source["retainedPath"]]).hexdigest() == source["sha256"], "retained source changed during read")
    inputs = {path: hashlib.sha256(value).hexdigest() for path, value in raw.items()}
    require(all((root / path).read_bytes() == value for path, value in raw.items()), "input changed during export read")
    providers = unique(data["verification/source_registry.json"]["providers"], "providerId")
    printing_sources = {printing["printingId"]: printing["sources"]
                        for unit in data["verification/finish_units.json"]["units"] for printing in unit["printings"]}
    physical_sources = {row["physicalPrintingId"]: printing_sources.get(row.get("sourcePrintingId"), [])
                        for row in collector.entity_payloads(graph, "physical-printing")}
    return data["verification/malie_profile.json"], catalogue, content, inputs, providers, physical_sources


def check_outputs(directory: Path, bundle: dict[str, bytes]) -> None:
    stale = [name for name, raw in bundle.items()
             if not (directory / name).is_file() or (directory / name).read_bytes() != raw]
    require(not stale, "missing or stale export artifacts: " + ", ".join(sorted(stale)))
    validate_bundle({name: (directory / name).read_bytes() for name in bundle})


def replace_file(path: Path, raw: bytes) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".malie-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(raw)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_outputs(directory: Path, bundle: dict[str, bytes]) -> None:
    validate_bundle(bundle)
    directory.mkdir(parents=True, exist_ok=True)
    # The report binds both other files and is replaced last. A partial replacement
    # cannot pass digest checks; individual files are never exposed half-written.
    for name in ("cards.json", "profile.json", "report.json"):
        replace_file(directory / name, bundle[name])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the validated offline export bundle")
    mode.add_argument("--check", action="store_true", help="observe current bundle without changing any files")
    args = parser.parse_args()
    try:
        bundle = build_bundle(*read_inputs())
        directory = ROOT / "exports/malie"
        if args.check:
            check_outputs(directory, bundle)
        else:
            write_outputs(directory, bundle)
        print("Malie pilot: " + json.dumps(json.loads(bundle["report.json"])["summary"], sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Malie export: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Standalone reader for snoredex-malie-sv-pilot/1; reads only three bundle files.

Usage: python malie_consumer.py PATH/TO/exports/malie
This checks bundle integrity and identity/accounting, not universal Malie compatibility.
No repository modules, graph files, network or third-party packages are used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

PROFILE = "snoredex-malie-sv-pilot/1"
PROFILE_CONTRACT_SHA256 = "2d91b30ef97256247d70976b6369be283156398b0ca9d228ec28ca4c7170b645"
PILOT_SEMANTICS_SHA256 = "e11d92f662d3cdf8a1cfd979076596ef6ded633b75746ee5e7d9b883c0a642e9"
SEMANTIC_FIELDS = ("itemId", "cardReleaseId", "physicalPrintingId", "localizationId", "localSetId",
                   "setEditionId", "edition", "finish", "foilPattern", "markings", "distribution",
                   "cardSize", "errorClass", "sourcePrintingId", "finishUnitId", "itemKind")
EVIDENCE_PROVIDERS = {"malie": (2, "cdn.malie.io"), "tcgdex": (2, "assets.tcgdex.net")}
INPUT_FILES = {
    "verification/malie_profile.json", "collector_catalogue.json",
    "verification/card_content_observations.json", "verification/authoritative_graph.json",
    "verification/specimens.json", "verification/units.json", "verification/source_first_prints.json",
    "verification/finish_units.json", "verification/source_registry.json", "verification/source_capabilities.json",
}
STATUSES = ["outside-profile", "blocked-by-source", "needs-evidence", "needs-mapping", "exported"]
FILES = ("cards.json", "report.json", "profile.json")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def indexed(rows, key):
    require(isinstance(rows, list), "expected array: " + key)
    result = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get(key), str), "missing identity: " + key)
        require(row[key] not in result, "duplicate identity: " + row[key])
        result[row[key]] = row
    return result


def load(directory):
    raw = {name: (directory / name).read_bytes() for name in FILES}
    data = {name: json.loads(value) for name, value in raw.items()}
    require(all(canonical(data[name]) == value for name, value in raw.items()), "noncanonical or duplicate-key JSON")
    report, profile = data["report.json"], data["profile.json"]
    require(report["schemaVersion"] == profile["schemaVersion"] == 1, "unsupported schema")
    require(report["profileId"] == profile["profileId"] == PROFILE, "unsupported or mixed profile")
    require(report["upstream"] == profile["upstream"], "mixed upstream pin")
    require(report["cardsSha256"] == sha(raw["cards.json"]), "cards digest mismatch")
    require(report["profileSha256"] == sha(raw["profile.json"]), "profile digest mismatch")
    validate_profile_contract(profile)
    input_bindings(report, profile)
    return data, {name: sha(value) for name, value in raw.items()}


def validate_profile_contract(profile):
    # Pin versioned semantics, while allowing evidence-dependent hashes to change.
    contract = {key: value for key, value in profile.items() if key not in {"inputPaths", "inputsSha256"}}
    contract["pilot"] = [{key: value for key, value in row.items() if key != "entrySha256"}
                         for row in profile["pilot"]]
    require(sha(canonical(contract)) == PROFILE_CONTRACT_SHA256, "declared profile contract mismatch")


def input_bindings(report, profile):
    paths = profile["inputPaths"]
    require(isinstance(paths, list) and all(isinstance(path, str) for path in paths), "missing input path contract")
    require(paths == sorted(set(paths)) and INPUT_FILES <= set(paths), "incomplete canonical input set")
    inputs = report["inputs"]
    require(isinstance(inputs, dict) and set(inputs) == set(paths), "incomplete input digest set")
    require(all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                for value in inputs.values()), "invalid input digest")
    require(sha(canonical(inputs)) == profile["inputsSha256"], "input digest binding mismatch")
    for entry in report["entries"]:
        for provenance in entry["fieldSources"].values():
            for source in provenance["sources"]:
                require(inputs.get(source["retainedPath"]) == source["sha256"], "retained source input mismatch")


def physical_card(entry, card, target, profile):
    identity = entry["identity"]
    require(entry["physicalPrintingId"] is not None, "research entry cannot carry a card")
    require(identity["localizationId"] == target["localizationId"], "companion locality mismatch")
    require(identity["localSetId"] in profile["supportedLocalSetIds"], "unsupported local set")
    require(card["lang"] == profile["languages"][target["localizationId"]], "card locality mismatch")
    require(identity["itemKind"] == "verified-printing" and identity["finishVerificationStatus"] == "confirmed",
            "unverified physical printing")
    require(identity["cardSize"] == "standard" and card["size"] == "STANDARD", "unsupported physical size")
    require(not any(identity.get(key) for key in ("distribution", "markings", "edition", "errorClass")),
            "unmapped physical distinction")
    finish = identity["finish"]
    require(finish in {"non-holo", "holo", "reverse-holo", "mirror-holo"}, "unknown finish")
    require((finish == "non-holo") == ("foil" not in card), "unknown or conflicting foil applicability")
    if finish in {"reverse-holo", "mirror-holo"}:
        require(card["foil"]["mask"] == "REVERSE", "reverse treatment mismatch")
    if finish == "holo":
        require(card["foil"]["mask"] != "REVERSE", "holo treatment mismatch")
    pattern = identity["foilPattern"]
    if pattern is not None:
        require(pattern in profile["foilPatternMappings"] and
                card.get("foil") == profile["foilPatternMappings"][pattern], "foil-pattern mapping mismatch")


def consume_entry(entry, target, cards, profile):
    for key in ("itemId", "cardReleaseId", "physicalPrintingId"):
        require(entry[key] == target[key], "selected identity mismatch: " + key)
    companion(entry, target, profile)
    reasons = entry["reasons"]
    require(isinstance(reasons, list), "missing reasons")
    statuses = {reason_status(reason) for reason in reasons}
    require(statuses <= set(STATUSES[:-1]), "unknown reason status")
    status = next((value for value in STATUSES if value in statuses), "exported")
    require(entry["status"] == status, "incorrect disposition precedence")
    result = {key: entry[key] for key in ("itemId", "cardReleaseId", "physicalPrintingId", "status", "identity", "reasons")}
    if status != "exported":
        require("cardIndex" not in entry and "cardSha256" not in entry, "withheld entry carries a card")
        return result, None
    position = entry["cardIndex"]
    require(type(position) is int and 0 <= position < len(cards), "invalid card position")
    card = cards[position]
    require(sha(canonical(card)) == entry["cardSha256"], "per-card digest mismatch")
    schema_check(card, profile["payloadSchema"])
    payload_rules(card, profile)
    physical_card(entry, card, target, profile)
    exported_evidence(entry, card)
    result["card"] = card
    return result, position


def reason_status(reason):
    require(isinstance(reason, dict) and set(reason) == {"status", "code", "field", "message"},
            "incomplete disposition reason")
    require(all(isinstance(value, str) and value.strip() for value in reason.values()), "empty reason")
    return reason["status"]


def companion(entry, target, profile):
    identity = entry["identity"]
    require(isinstance(identity, dict), "missing companion identity")
    require(sha(canonical(entry)) == target["entrySha256"], "complete report entry digest mismatch")
    require(all(identity[key] == target[key] for key in
                ("itemId", "cardReleaseId", "physicalPrintingId", "localizationId")), "companion target mismatch")
    required = {"localSetId", "setEditionId", "edition", "finish", "foilPattern", "distribution",
                "cardSize", "errorClass", "itemKind", "finishVerificationStatus", "markings", "physicalSources"}
    require(required <= identity.keys(), "incomplete physical companion")
    require(isinstance(identity["markings"], list) and isinstance(identity["physicalSources"], list),
            "missing physical companion arrays")
    fields = entry["fieldSources"]
    expected = {"/" + name for name in profile["payloadSchema"]["properties"]} | {"/subtype"}
    require(isinstance(fields, dict) and set(fields) == expected, "incomplete field provenance")
    for field, provenance in fields.items():
        require(field.startswith("/"), "invalid provenance field")
        require(isinstance(provenance, dict) and set(provenance) == {"observations", "sources", "covers"},
                "incomplete field provenance")
        require(all(isinstance(value, list) for value in provenance.values()), "invalid field provenance arrays")
        source_evidence(field, provenance, entry)


def schema_matches(value, schema):
    try:
        schema_check(value, schema)
        return True
    except ValueError:
        return False


def schema_check(value, schema):
    """Validate exactly the structural keywords emitted by this finite profile."""
    keywords = {"type", "properties", "required", "additionalProperties", "items", "minItems",
                "minLength", "pattern", "minimum", "const", "enum", "oneOf"}
    require(isinstance(schema, dict) and set(schema) <= keywords, "unsupported schema keyword")
    if "oneOf" in schema:
        require(sum(schema_matches(value, option) for option in schema["oneOf"]) == 1, "invalid union value")
    if "const" in schema:
        require(value == schema["const"], "invalid constant")
    if "enum" in schema:
        require(value in schema["enum"], "invalid enumeration")
    kind = schema.get("type")
    if kind is not None:
        types = {"object": dict, "array": list, "string": str, "integer": int}
        require(kind in types and type(value) is types[kind], "invalid field type")
        {"object": schema_object, "array": schema_array, "string": schema_string,
         "integer": schema_integer}[kind](value, schema)


def schema_object(value, schema):
    require(set(schema.get("required", [])) <= value.keys(), "missing required field")
    properties = schema.get("properties", {})
    for key, child in value.items():
        require(key in properties or schema.get("additionalProperties", True), "unknown field")
        if key in properties:
            schema_check(child, properties[key])


def schema_array(value, schema):
    require(len(value) >= schema.get("minItems", 0), "empty required array")
    for child in value:
        schema_check(child, schema["items"])


def schema_string(value, schema):
    require(len(value) >= schema.get("minLength", 0), "empty required text")
    if "pattern" in schema:
        require(re.search(schema["pattern"], value) is not None, "invalid text pattern")


def schema_integer(value, schema):
    require(value >= schema.get("minimum", value), "integer below minimum")


def payload_rules(card, profile):
    number = card["collector_number"]
    parsed = re.fullmatch(profile["numberPattern"], number["numerator"])
    require(parsed is not None and int(parsed.group(1)) == number["numeric"], "number component mismatch")
    full = number["numerator"] + ("/" + number["denominator"] if "denominator" in number else "")
    require(number["full"] == full, "printed number mismatch")
    years = re.findall(r"(?<!\d)\d{4}(?!\d)", card["copyright"]["text"])
    require(bool(years) and max(map(int, years)) == card["copyright"]["year"], "copyright year mismatch")
    vocabulary = profile["vocabulary"]
    if "rarity" in card:
        pairs = dict(zip(vocabulary["rarity.designation"], vocabulary["rarity.icon"]))
        require(pairs[card["rarity"]["designation"]] == card["rarity"]["icon"], "rarity pair mismatch")
    if "tags" in card:
        require(card["tags"] == sorted(set(card["tags"])), "tags must be unique and sorted")
    for block in card["text"]:
        if "FREE" in block.get("cost", []):
            require(block["cost"] == ["FREE"], "FREE cannot accompany other cost symbols")


def text_fields(record, names):
    for name in names:
        require(isinstance(record.get(name), str) and bool(record[name].strip()), "missing evidence text: " + name)


def source_evidence(field, provenance, entry):
    sources = indexed(provenance["sources"], "sourceId")
    observations = indexed(provenance["observations"], "observationId")
    for source in sources.values():
        text_fields(source, ("sourceId", "providerId", "url", "retrievedAt", "retainedPath", "sha256", "licenseOrTerms"))
        require(re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is not None, "invalid retained-source digest")
        require(type(source["authorityTier"]) is int and source["authorityTier"] in {1, 2, 3, 5}, "invalid source grade")
        source_scope(source["scope"], field, entry)
    for observation in observations.values():
        observation_refs(observation, sources, field)
    require(all(isinstance(path, str) and (path == field or path.startswith(field + "/"))
                for path in provenance["covers"]), "evidence covers unrelated field")


def source_scope(scope, field, entry):
    require(isinstance(scope, dict), "missing source scope")
    require(isinstance(scope.get("physicalPrintingIds"), list) and isinstance(scope.get("fields"), list),
            "missing source scope arrays")
    require(scope.get("cardReleaseId") == entry["cardReleaseId"], "source release mismatch")
    require(entry["physicalPrintingId"] in scope["physicalPrintingIds"], "source printing mismatch")
    require(field in scope["fields"], "source field mismatch")


def observation_refs(observation, sources, field):
    text_fields(observation, ("observationId", "state", "observedAt", "method", "basis"))
    state = observation["state"]
    require((state == "known") == ("value" in observation), "observation value/state mismatch")
    require(state in {"known", "not-applicable", "unknown", "blocked-by-source"}, "unknown evidence state")
    refs = observation["sourceIds"]
    require(isinstance(refs, list) and all(isinstance(ref, str) for ref in refs), "invalid observation references")
    require(set(refs) <= sources.keys(), "unresolved observation source")
    if state in {"known", "not-applicable"}:
        require(bool(refs), "accepted observation lacks a source")
        for reference in refs:
            eligible_evidence(sources[reference], field)
    else:
        text_fields(observation, ("nextStep",))


def eligible_evidence(source, field):
    provider = source["providerId"]
    require(provider in EVIDENCE_PROVIDERS, "provider is not qualified for this pilot")
    tier, host = EVIDENCE_PROVIDERS[provider]
    url = urlsplit(source["url"])
    require(source["authorityTier"] == tier and url.scheme == "https" and url.hostname == host,
            "source grade or origin is not qualified for this pilot")
    require(provider != "tcgdex" or field not in {"/size", "/back", "/foil"},
            "front image cannot establish this physical field")


def leaves(value, path):
    if isinstance(value, dict):
        return [leaf for key in sorted(value)
                for leaf in leaves(value[key], path + "/" + key.replace("~", "~0").replace("/", "~1"))]
    if isinstance(value, list):
        return [leaf for index, child in enumerate(value) for leaf in leaves(child, path + "/" + str(index))]
    return [path]


def exported_evidence(entry, card):
    for field, provenance in entry["fieldSources"].items():
        name = field[1:]
        state = "known" if name in card else "not-applicable"
        accepted = [row for row in provenance["observations"] if row["state"] in {"known", "not-applicable"}]
        require(bool(accepted), "missing accepted field evidence")
        for row in accepted:
            value = row.get("value")
            if name == "tags" and isinstance(value, list):
                value = sorted(set(value))
            require(row["state"] == state and (state != "known" or canonical(value) == canonical(card[name])),
                    "exported value disagrees with observation")
        paths = leaves(card[name], field) if name in card else []
        require(provenance["covers"] == paths, "incomplete field-leaf evidence coverage")


def consume(directory):
    documents, digests = load(directory)
    cards, report, profile = (documents[name] for name in FILES)
    require(isinstance(cards, list), "cards must be an array")
    targets = indexed(profile["pilot"], "itemId")
    entries = indexed(report["entries"], "itemId")
    require(entries.keys() == targets.keys(), "selected-input accounting mismatch")
    semantics = {iid: {key: entry["identity"][key] for key in SEMANTIC_FIELDS} for iid, entry in entries.items()}
    require(sha(canonical(semantics)) == PILOT_SEMANTICS_SHA256, "selected printing semantics mismatch")
    physical_ids = [target["physicalPrintingId"] for target in targets.values() if target["physicalPrintingId"] is not None]
    require(len(physical_ids) == len(set(physical_ids)), "duplicate physical printing")
    items, positions = [], []
    for iid in sorted(entries):
        item, position = consume_entry(entries[iid], targets[iid], cards, profile)
        items.append(item)
        if position is not None:
            positions.append(position)
    require(positions == list(range(len(cards))), "lost, duplicated or reordered card association")
    counts = Counter(item["status"] for item in items)
    expected = {"selected": len(items), **{status: counts[status] for status in STATUSES}}
    require(report["summary"] == expected, "incorrect summary")
    return {"profileId": PROFILE, "digests": digests, "summary": expected, "items": items}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    try:
        result = consume(args.bundle)
        # ASCII JSON escapes remain portable even under legacy Windows pipe encodings.
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Malie consumer: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

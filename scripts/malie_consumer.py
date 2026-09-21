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
import sys
from collections import Counter
from pathlib import Path

PROFILE = "snoredex-malie-sv-pilot/1"
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
    return data, {name: sha(value) for name, value in raw.items()}


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


def consume_entry(entry, target, cards, profile):
    for key in ("itemId", "cardReleaseId", "physicalPrintingId"):
        require(entry[key] == target[key], "selected identity mismatch: " + key)
    companion(entry, target)
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
    physical_card(entry, card, target, profile)
    result["card"] = card
    return result, position


def reason_status(reason):
    require(isinstance(reason, dict) and set(reason) == {"status", "code", "field", "message"},
            "incomplete disposition reason")
    require(all(isinstance(value, str) and value.strip() for value in reason.values()), "empty reason")
    return reason["status"]


def companion(entry, target):
    identity = entry["identity"]
    require(isinstance(identity, dict), "missing companion identity")
    require(sha(canonical(identity)) == target["identitySha256"], "companion identity digest mismatch")
    require(all(identity[key] == target[key] for key in
                ("itemId", "cardReleaseId", "physicalPrintingId", "localizationId")), "companion target mismatch")
    required = {"localSetId", "setEditionId", "edition", "finish", "foilPattern", "distribution",
                "cardSize", "errorClass", "itemKind", "finishVerificationStatus", "markings", "physicalSources"}
    require(required <= identity.keys(), "incomplete physical companion")
    require(isinstance(identity["markings"], list) and isinstance(identity["physicalSources"], list),
            "missing physical companion arrays")
    fields = entry["fieldSources"]
    require(isinstance(fields, dict) and bool(fields), "missing field provenance")
    for field, provenance in fields.items():
        require(field.startswith("/"), "invalid provenance field")
        require(isinstance(provenance, dict) and set(provenance) == {"observations", "sources", "covers"},
                "incomplete field provenance")
        require(all(isinstance(value, list) for value in provenance.values()), "invalid field provenance arrays")


def consume(directory):
    documents, digests = load(directory)
    cards, report, profile = (documents[name] for name in FILES)
    require(isinstance(cards, list), "cards must be an array")
    targets = indexed(profile["pilot"], "itemId")
    entries = indexed(report["entries"], "itemId")
    require(entries.keys() == targets.keys(), "selected-input accounting mismatch")
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

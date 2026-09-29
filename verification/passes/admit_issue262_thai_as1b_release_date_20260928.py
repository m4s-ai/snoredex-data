#!/usr/bin/env python3
"""Admit the locality-scoped Thai First Impact release date from Bulbapedia.

The First Impact article states Thailand's release date as 2019-02-01 and
describes Set A and Set B as the two components. This maps the launch only to
the Thai AS1b (Set B) edition. Indonesian AS1b has its own August 2019 date.

    python verification/passes/admit_issue262_thai_as1b_release_date_20260928.py
    python verification/passes/admit_issue262_thai_as1b_release_date_20260928.py --check
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "verification"
SOURCES_PATH = VERIFY / "set_catalogue_sources.json"
GRAPH_PATH = VERIFY / "authoritative_graph.json"
sys.path.insert(0, str(ROOT / "scripts"))

import authoritative_graph  # noqa: E402

SOURCE_ID = "SET-SRC-BP-DATE-TH-AS1B-FIRST-IMPACT"
EVENT_ID = "EVENT:TH:AS1b:First-Impact-launch-2019-02-01"
LOCAL_SET_ID = "LOCALSET:TH:AS1b"
EDITION_ID = "EDITION:TH:Thai:AS1b"
ORIGIN = "reviewed-evidence-issue-262"
URL = "https://bulbapedia.bulbagarden.net/wiki/AS1a"

SOURCE: dict[str, Any] = {
    "sourceRecordId": SOURCE_ID,
    "sourceKind": "release-date-record",
    "provider": "bulbapedia",
    "providerRecordKey": f"{URL}#release-date:TH:AS1b",
    "retrieved": "2026-09-28",
    "sourceUrl": URL,
    "raw": {
        "localCode": "AS1b",
        "page": "First Impact (ATCG)",
        "field": "Thai release date",
        "date": "2019-02-01",
        "datePrecision": "day",
        "approximate": False,
        "status": "released",
        "locality": "TH",
        "languageScope": "Thai",
        "marketScopes": ["TH"],
        "marketScopeBasis": (
            "The article explicitly states Thailand's First Impact release date and "
            "identifies Set A and Set B as the two components; this record maps the "
            "date only to the Thai AS1b Set B local set."
        ),
        "note": (
            "Bulbapedia reports First Impact and its GX Starter Deck released in "
            "Thailand on February 1, 2019. Indonesian AS1b is a separate locality "
            "and retains its separately sourced August 8, 2019 date."
        ),
    },
}

EVENT = {
    "entityType": "release-event",
    "entityId": EVENT_ID,
    "origin": ORIGIN,
    "payload": {
        "releaseEventId": EVENT_ID,
        "localSetId": LOCAL_SET_ID,
        "setEditionIds": [EDITION_ID],
        "eventKind": "launch",
        "dateValue": "2019-02-01",
        "datePrecision": "day",
        "approximate": False,
        "status": "released",
        "timezone": None,
        "marketScopes": ["TH"],
        "marketScopeBasis": SOURCE["raw"]["marketScopeBasis"],
        "sourceRecordId": SOURCE_ID,
        "linkBasis": (
            "The source identifies the Thai First Impact launch and names Set A and "
            "Set B as its components; AS1b is the established Thai Set B local set."
        ),
    },
}

DISPOSITION = {
    "entityType": "set-source-disposition",
    "entityId": SOURCE_ID,
    "origin": ORIGIN,
    "payload": {
        "sourceRecordId": SOURCE_ID,
        "disposition": "mapped",
        "targetRef": EVENT_ID,
        "reason": (
            "The source explicitly dates the Thai First Impact launch; its Set A/Set B "
            "description scopes the date to the Thai AS1b edition without transferring "
            "it to Indonesian AS1b."
        ),
    },
}

EDGES = [
    {"fromType": "release-event", "fromId": EVENT_ID, "relation": "belongs-to",
     "toType": "local-set", "toId": LOCAL_SET_ID, "provenance": {}},
    {"fromType": "release-event", "fromId": EVENT_ID, "relation": "supports",
     "toType": "set-edition", "toId": EDITION_ID, "provenance": {}},
    {"fromType": "set-source-record", "fromId": SOURCE_ID,
     "relation": "asserts-release-event", "toType": "release-event",
     "toId": EVENT_ID, "provenance": {}},
]

MIGRATION_DISPOSITION = {
    "sourceKind": "set-catalogue-source",
    "sourceId": SOURCE_ID,
    "disposition": "mapped",
    "targetRef": EVENT_ID,
    "reason": DISPOSITION["payload"]["reason"],
}


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def upsert(rows: list[dict[str, Any]], expected: dict[str, Any], key: str) -> None:
    matches = [row for row in rows if row.get(key) == expected[key]]
    if matches:
        if len(matches) != 1 or matches[0] != expected:
            raise ValueError(f"conflicting existing {key}: {expected[key]}")
        return
    rows.append(expected)


def upsert_entity(rows: list[dict[str, Any]], expected: dict[str, Any]) -> None:
    matches = [row for row in rows if (
        row.get("entityType"), row.get("entityId")
    ) == (expected["entityType"], expected["entityId"])]
    if matches:
        if len(matches) != 1 or matches[0] != expected:
            raise ValueError(
                f"conflicting existing entity: {expected['entityType']} {expected['entityId']}"
            )
        return
    rows.append(expected)


def apply(sources: dict[str, Any], graph: dict[str, Any]) -> None:
    upsert(sources["sourceRecords"], SOURCE, "sourceRecordId")
    sources["meta"]["counts"]["sourceRecords"] = len(sources["sourceRecords"])
    sources["meta"]["counts"]["releaseDateRecords"] = sum(
        row["sourceKind"] == "release-date-record" for row in sources["sourceRecords"]
    )
    sources["sourceRecords"].sort(key=lambda row: row["sourceRecordId"])

    source_entity = {
        "entityType": "set-source-record", "entityId": SOURCE_ID,
        "origin": ORIGIN, "payload": SOURCE,
    }
    for entity in (EVENT, DISPOSITION, source_entity):
        upsert_entity(graph["entities"], entity)
    for edge in EDGES:
        key = (edge["fromType"], edge["fromId"], edge["relation"], edge["toType"], edge["toId"])
        matches = [row for row in graph["edges"] if (
            row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"]
        ) == key]
        if matches:
            if len(matches) != 1 or matches[0] != edge:
                raise ValueError(f"conflicting graph edge: {key}")
        else:
            graph["edges"].append(edge)
    migration = graph["migrationDispositions"]
    migration_matches = [row for row in migration if (
        row.get("sourceKind"), row.get("sourceId")
    ) == (MIGRATION_DISPOSITION["sourceKind"], MIGRATION_DISPOSITION["sourceId"])]
    if migration_matches:
        if len(migration_matches) != 1 or migration_matches[0] != MIGRATION_DISPOSITION:
            raise ValueError(f"conflicting migration disposition for {SOURCE_ID}")
    else:
        migration.append(MIGRATION_DISPOSITION)
    migration.sort(key=lambda row: (row["sourceKind"], row["sourceId"]))
    graph["entities"].sort(key=lambda row: (row["entityType"], row["entityId"]))
    graph["edges"].sort(key=lambda row: (
        row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"]
    ))
    graph["meta"]["generated"] = "2026-09-28"
    graph["summary"]["entities"] = len(graph["entities"])
    graph["summary"]["edges"] = len(graph["edges"])
    graph["summary"]["migrationInputs"] = len(migration)
    graph["summary"]["migrationDispositions"] = dict(sorted(Counter(
        row["disposition"] for row in migration
    ).items()))
    graph["summary"]["setSourceRecords"] = sum(
        row["entityType"] == "set-source-record" for row in graph["entities"]
    )
    graph["summary"]["setSourceDispositions"] = sum(
        row["entityType"] == "set-source-disposition" for row in graph["entities"]
    )


def write_json(path: Path, document: dict[str, Any]) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = handle.name
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sources = read(SOURCES_PATH)
    graph = read(GRAPH_PATH)
    if args.check:
        expected_sources = read(SOURCES_PATH)
        expected_graph = read(GRAPH_PATH)
        apply(expected_sources, expected_graph)
        if expected_sources != sources or expected_graph != graph:
            print("Thai AS1b release date is not fully admitted")
            return 1
    else:
        apply(sources, graph)
        write_json(SOURCES_PATH, sources)
        write_json(GRAPH_PATH, graph)
    errors = authoritative_graph.validate(graph)
    if errors:
        print("\n".join(errors))
        return 1
    print("Thai AS1b launch date is admitted as a locality-scoped release event")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

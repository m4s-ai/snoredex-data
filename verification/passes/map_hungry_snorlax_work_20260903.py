#!/usr/bin/env python3
"""Map Hungry Snorlax to its own Work and record its first release date."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import authoritative_graph as graph_projection  # noqa: E402


GRAPH = ROOT / "verification" / "authoritative_graph.json"
CAPABILITIES = ROOT / "verification" / "source_capabilities.json"
UNITS = ROOT / "verification" / "units.json"
DATES = ROOT / "verification" / "bulbapedia_release_dates.json"
JOURNAL = ROOT / "verification" / "evidence.jsonl"
EVIDENCE = ROOT / "verification" / "evidence" / "issue-256-hungry-snorlax-work-release-20260903.json"
SNAPSHOT = "verification/evidence/issue-256-hungry-snorlax-work-release-20260903.json"
WORK = "Hungry-Snorlax-Lv50-Eat-Rollout"
WORK_ID = f"WORK:{WORK}"
RELEASE_ID = "RELEASE:JP:Japanese:UNP:unnumbered:None"
SOURCE_URL = (
    "https://bulbapedia.bulbagarden.net/w/index.php?oldid=4391521&"
    "title=Hungry_Snorlax_%28Nintendo_64_promo%29"
)
CURRENT_URL = "https://bulbapedia.bulbagarden.net/wiki/Hungry_Snorlax_(Nintendo_64_promo)"
REVIEWED_AT = "2026-09-03"
LEGACY_RETRIEVED_AT = "2026-07-31"
OBSERVED_AT = "2026-09-03T09:36:58+02:00"
EVIDENCE_TEXT = (
    "The pinned Bulbapedia card article identifies Hungry Snorlax LV.50 as its own "
    "unnumbered Japanese promotional card, illustrated by Sumiyoshi Kizuki with Eat and "
    "Rollout. Its Nintendo 64 Double Get Campaign distribution began on December 10, 1997; "
    "the January 1, 1999 Pokémon Song Best Collection copy is described as a reprint of the "
    "same card. The collection owner confirms that the reprint is not distinguishable and "
    "therefore needs no second collector entry."
)
JOURNAL_ROW = {
    "unitId": "U0504",
    "lang": "Japanese",
    "status": "confirmed",
    "source": SOURCE_URL,
    "evidence": EVIDENCE_TEXT,
    "at": OBSERVED_AT,
}


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def encoded(document: Any) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def encoded_dates(document: dict[str, Any]) -> str:
    lines = [
        "{",
        f'  "generated": {json.dumps(document["generated"], ensure_ascii=False)},',
        f'  "source": {json.dumps(document["source"], ensure_ascii=False)},',
        f'  "license": {json.dumps(document["license"], ensure_ascii=False)},',
        '  "records": [',
    ]
    for index, record in enumerate(document["records"]):
        suffix = "," if index + 1 < len(document["records"]) else ""
        lines.append("    " + json.dumps(record, ensure_ascii=False, separators=(", ", ": ")) + suffix)
    return "\n".join([*lines, "  ]", "}", ""])


def write(path: Path, document: Any) -> None:
    path.write_text(encoded(document), encoding="utf-8", newline="\n")


def validate_evidence() -> None:
    evidence = read(EVIDENCE)
    observation = evidence["observations"][0]
    decision = evidence["decision"]
    if observation["sourceUrl"] != SOURCE_URL:
        raise ValueError("Hungry Snorlax evidence source drifted")
    if decision != {
        "work": WORK,
        "workMappingState": "mapped",
        "releaseIds": [RELEASE_ID],
        "firstReleaseDate": "1997-12-10",
        "collectorEntryPolicy": "one indistinguishable printing across both documented distribution events",
        "basis": (
            "The pinned Bulbapedia card article identifies one Hungry Snorlax card with its "
            "own name, illustrator and attacks, dates its first distribution to December 10, "
            "1997, and calls the 1999 CD copy a reprint. The collection owner confirms that "
            "the reprint is not physically distinguishable and therefore remains the same "
            "collector entry."
        ),
    }:
        raise ValueError("Hungry Snorlax decision drifted")


def apply_capability(document: dict[str, Any]) -> None:
    surface = {
        "surfaceId": "bulbapedia-hungry-snorlax-card",
        "providerId": "bulbapedia",
        "label": "Bulbapedia exact Hungry Snorlax card and release history",
        "match": {
            "urlPrefixes": [CURRENT_URL, SOURCE_URL],
            "nonUrlEvidenceIds": [SNAPSHOT],
        },
        "state": "incomplete",
        "failureState": "Only the exact pinned Hungry Snorlax article and recorded facts are in scope.",
        "accessMode": "browser",
        "adapterState": "planned",
        "lastCheckedAt": REVIEWED_AT,
        "freshnessPolicy": "Re-check the pinned article; never infer undocumented printings, finish completeness or physical distribution differences.",
        "query": {
            "method": "GET",
            "endpoint": SOURCE_URL,
            "parameters": [],
            "pagination": "not paginated; one pinned card article",
            "expectedIdentifiers": [
                "Hungry Snorlax LV.50",
                "Unnumbered Promotional cards",
                "Sumiyoshi Kizuki",
                "Eat",
                "Rollout",
                "December 10, 1997",
                "January 1, 1999",
            ],
        },
        "finishCapability": {
            "mode": "none",
            "vocabulary": [],
            "publicationForm": "pinned card identity and release-history text, not a physical card photograph",
            "closedWithinScope": False,
        },
        "coverageEdges": [{
            "edgeId": "bulbapedia-hungry-snorlax-positive",
            "coverage": {
                "localities": ["JP"],
                "languages": ["Japanese"],
                "scripts": ["Jpan"],
                "productCategories": ["card"],
                "timeRange": {
                    "start": "1997-12-10",
                    "end": "1999-01-01",
                    "basis": "the two distribution dates stated in the exact pinned card article",
                },
            },
            "positiveEvidenceCapabilities": [
                "identity",
                "card-release",
                "set-membership",
                "artist",
                "card-text",
                "language",
                "date",
                "release-date",
                "distribution-history",
            ],
            "exhaustive": False,
            "absenceCapability": {
                "enabled": False,
                "dimensions": [],
                "exactScopes": [],
                "rationale": "The article positively identifies one card and two distributions; it is not used as a complete absence manifest.",
            },
            "knownPositiveObservationId": "obs-bulbapedia-hungry-snorlax-20260903",
            "boundary": {
                "outsideScope": [
                    "physical distinguishability of the two distributions",
                    "finish completeness",
                    "promotional-card catalogue completeness",
                ],
                "zeroResultMeans": "unknown",
                "challenge": "The one-entry collector treatment depends on the collection-owner decision, not on source silence.",
            },
        }],
    }
    observation = {
        "observationId": "obs-bulbapedia-hungry-snorlax-20260903",
        "surfaceId": surface["surfaceId"],
        "kind": "known-positive",
        "queryUrl": SOURCE_URL,
        "queryParameters": {},
        "retrievedAt": REVIEWED_AT,
        "fixtureRef": {
            "kind": "inline-record",
            "record": {
                "evidenceSnapshot": SNAPSHOT,
                "card": "Hungry Snorlax LV.50",
                "firstDistributionStart": "1997-12-10",
                "reprintDistributionDate": "1999-01-01",
                "work": WORK,
                "absenceCapability": False,
                "finishCapability": False,
            },
        },
        "expectedIdentifiers": [RELEASE_ID, WORK],
        "validatesEdges": ["bulbapedia-hungry-snorlax-positive"],
        "outcome": "The pinned article establishes the card identity, distinct card text and first distribution date; the owner decision keeps the indistinguishable reprint in the same collector entry.",
    }
    surfaces = {row["surfaceId"]: row for row in document["surfaces"]}
    surfaces[surface["surfaceId"]] = surface
    document["surfaces"] = list(surfaces.values())
    observations = {row["observationId"]: row for row in document["observations"]}
    observations[observation["observationId"]] = observation
    document["observations"] = list(observations.values())
    document["meta"]["reviewedAt"] = REVIEWED_AT


def apply_unit(document: list[dict[str, Any]]) -> None:
    row = next((item for item in document if item["unitId"] == "U0504"), None)
    if not row or (row.get("setCode"), row.get("number"), row.get("language")) != (
        "UNP", "", "Japanese",
    ):
        raise ValueError("Hungry Snorlax unit is missing or drifted")
    if row.get("cardKey") not in {None, WORK}:
        raise ValueError("Hungry Snorlax unit has another Work")
    row["cardKey"] = WORK
    row["artist"] = "Sumiyoshi Kizuki"
    row["evidence"] = EVIDENCE_TEXT
    row["checkedAt"] = OBSERVED_AT


def apply_dates(document: dict[str, Any]) -> None:
    record = {
        "setCode": "UNP",
        "date": "1997-12-10",
        "page": "Hungry Snorlax (Nintendo 64 promo)",
        "field": "release information: Nintendo 64 Double Get Campaign start",
        "note": "The later January 1, 1999 CD reprint is physically indistinguishable and remains the same collector entry by owner decision.",
        "retrievedAt": REVIEWED_AT,
    }
    records = []
    for row in document["records"]:
        if row["setCode"] == record["setCode"]:
            continue
        retained = dict(row)
        retained.setdefault("retrievedAt", LEGACY_RETRIEVED_AT)
        records.append(retained)
    insert_at = next(
        (index + 1 for index, row in enumerate(records) if row["setCode"] == "PJU"),
        len(records),
    )
    records.insert(insert_at, record)
    document["records"] = records
    document["generated"] = REVIEWED_AT
    document["source"] = (
        "Bulbapedia expansion/product release fields and exact card-article release statements, "
        "checked through the MediaWiki API or pinned page"
    )


def apply_graph(document: dict[str, Any]) -> None:
    work = next(
        (row for row in document["entities"] if row["entityType"] == "work" and row["entityId"] == WORK_ID),
        None,
    )
    if work is None:
        document["entities"].append({
            "entityType": "work",
            "entityId": WORK_ID,
            "origin": "reviewed-hungry-snorlax-work-decision",
            "payload": {"workId": WORK_ID, "cardKey": WORK},
        })
    elif work["payload"].get("cardKey") != WORK:
        raise ValueError("Hungry Snorlax Work drifted")
    release = next(
        (row for row in document["entities"] if row["entityType"] == "card-release" and row["entityId"] == RELEASE_ID),
        None,
    )
    if not release:
        raise ValueError("Hungry Snorlax release is missing")
    payload = release["payload"]
    current = (payload.get("workMappingState"), payload.get("work"))
    if current not in {("needs-explicit-equivalence", None), ("mapped", WORK)}:
        raise ValueError(f"Hungry Snorlax Work mapping drifted: {current}")
    payload["workMappingState"] = "mapped"
    payload["work"] = WORK
    payload["sourceRecords"] = sorted({*payload.get("sourceRecords", []), SOURCE_URL})
    document["edges"] = [
        edge for edge in document["edges"]
        if not (
            edge["fromType"] == "card-release"
            and edge["fromId"] == RELEASE_ID
            and edge["relation"] == "implements"
        )
    ]
    document["edges"].append({
        "fromType": "card-release",
        "fromId": RELEASE_ID,
        "relation": "implements",
        "toType": "work",
        "toId": WORK_ID,
        "provenance": {
            "state": "mapped",
            "evidenceSnapshot": SNAPSHOT,
            "sourceUrl": SOURCE_URL,
            "ownerDecisionAt": REVIEWED_AT,
        },
    })
    document["entities"].sort(key=lambda row: (row["entityType"], row["entityId"]))
    document["edges"].sort(key=lambda edge: (
        edge["fromType"], edge["fromId"], edge["relation"], edge["toType"], edge["toId"]
    ))
    document["meta"]["generated"] = REVIEWED_AT


def journal_is_current() -> bool:
    rows = [json.loads(line) for line in JOURNAL.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    matches = [row for row in rows if row.get("unitId") == "U0504" and row.get("at") == OBSERVED_AT]
    if len(matches) > 1:
        raise ValueError("duplicate Hungry Snorlax journal observation")
    return matches == [JOURNAL_ROW]


def append_journal() -> None:
    with JOURNAL.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(JOURNAL_ROW, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    validate_evidence()
    paths = {"capabilities": CAPABILITIES, "units": UNITS, "dates": DATES, "graph": GRAPH}
    documents = {label: read(path) for label, path in paths.items()}
    before = {
        label: paths[label].read_text(encoding="utf-8-sig") if label == "dates" else encoded(value)
        for label, value in documents.items()
    }
    apply_capability(documents["capabilities"])
    apply_unit(documents["units"])
    apply_dates(documents["dates"])
    apply_graph(documents["graph"])
    documents["graph"] = graph_projection.project_physical_evidence(documents["graph"])
    stale = [
        label for label, value in documents.items()
        if before[label] != (encoded_dates(value) if label == "dates" else encoded(value))
    ]
    journal_stale = not journal_is_current()
    if args.check:
        if stale or journal_stale:
            labels = stale + (["journal"] if journal_stale else [])
            raise SystemExit("Hungry Snorlax inputs are stale: " + ", ".join(labels))
        print(f"Hungry Snorlax mapping/date are current: {RELEASE_ID} -> {WORK}, 1997-12-10")
        return 0
    for label in stale:
        if label == "dates":
            paths[label].write_text(encoded_dates(documents[label]), encoding="utf-8", newline="\n")
        else:
            write(paths[label], documents[label])
    if journal_stale:
        append_journal()
    labels = stale + (["journal"] if journal_stale else [])
    print("updated Hungry Snorlax: " + (", ".join(labels) or "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

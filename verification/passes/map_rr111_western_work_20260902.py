#!/usr/bin/env python3
"""Map the four established Western RR 111 releases to their reviewed Work."""

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
EVIDENCE = ROOT / "verification" / "evidence" / "issue-267-rr111-work-equivalence-20260902.json"
SNAPSHOT = "verification/evidence/issue-267-rr111-work-equivalence-20260902.json"
WORK = "Snorlax-LvX-Big-Appetite-Exercise"
WORK_ID = f"WORK:{WORK}"
RELEASE_IDS = (
    "RELEASE:WEST:English:RR:111:None",
    "RELEASE:WEST:French:RR:111:None",
    "RELEASE:WEST:German:RR:111:None",
    "RELEASE:WEST:Italian:RR:111:None",
)
SOURCE_URL = (
    "https://bulbapedia.bulbagarden.net/w/index.php?"
    "title=Snorlax_LV.X_(Rising_Rivals_111)&oldid=4616809"
)
REVIEWED_AT = "2026-09-02"
UNIT_IDS = ("U0365", "U0366", "U0367", "U0368")


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def encoded(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def write(path: Path, document: dict[str, Any]) -> None:
    path.write_text(encoded(document), encoding="utf-8", newline="\n")


def validate_evidence() -> None:
    evidence = read(EVIDENCE)
    observation = evidence["observations"][0]
    decision = evidence["decision"]
    if observation["sourceUrl"] != SOURCE_URL:
        raise ValueError("RR 111 evidence source drifted")
    if decision["work"] != WORK or tuple(decision["releaseIds"]) != RELEASE_IDS:
        raise ValueError("RR 111 Work decision drifted")
    if decision["workMappingState"] != "mapped":
        raise ValueError("RR 111 Work mapping state drifted")


def apply_capability(document: dict[str, Any]) -> None:
    surface = {
        "surfaceId": "bulbapedia-rr111-card-equivalence",
        "providerId": "bulbapedia",
        "label": "Bulbapedia exact Rising Rivals 111 card equivalence",
        "match": {
            "urlPrefixes": [
                "https://bulbapedia.bulbagarden.net/wiki/Snorlax_LV.X_%28Rising_Rivals_111%29",
                "https://bulbapedia.bulbagarden.net/wiki/Snorlax_LV.X_%28DP-P_Promo_127%29",
                "https://bulbapedia.bulbagarden.net/w/index.php?title=Snorlax_LV.X_(Rising_Rivals_111)",
            ],
            "nonUrlEvidenceIds": [SNAPSHOT],
        },
        "state": "incomplete",
        "failureState": "Only the exact pinned card article and localized releases named in the reviewed snapshot are in scope.",
        "accessMode": "browser",
        "adapterState": "planned",
        "lastCheckedAt": REVIEWED_AT,
        "freshnessPolicy": "Re-check the pinned card article; never generalize this equivalence to another card or infer finish or absence.",
        "query": {
            "method": "GET",
            "endpoint": SOURCE_URL,
            "parameters": [],
            "pagination": "not paginated; one pinned card article",
            "expectedIdentifiers": [
                "Snorlax LV.X",
                "Rising Rivals 111/111",
                "DP-P Promotional cards 127/DP-P",
                "Big Appetite",
                "Exercise",
            ],
        },
        "finishCapability": {
            "mode": "none",
            "vocabulary": [],
            "publicationForm": "pinned card identity and release fields, not a physical card photograph",
            "closedWithinScope": False,
        },
        "coverageEdges": [{
            "edgeId": "bulbapedia-rr111-equivalence-positive",
            "coverage": {
                "localities": ["WEST", "JP"],
                "languages": ["English", "French", "German", "Italian", "Japanese"],
                "scripts": ["Latn", "Jpan"],
                "productCategories": ["card"],
                "timeRange": {
                    "start": None,
                    "end": None,
                    "basis": "the exact pinned Rising Rivals 111 card article only",
                },
            },
            "positiveEvidenceCapabilities": [
                "identity",
                "card-release",
                "collector-number",
                "set-membership",
                "artist",
                "cross-language-equivalence",
            ],
            "exhaustive": False,
            "absenceCapability": {
                "enabled": False,
                "dimensions": [],
                "exactScopes": [],
                "rationale": "The pinned article establishes one positive equivalence and no absence claim.",
            },
            "knownPositiveObservationId": "obs-bulbapedia-rr111-equivalence-20260902",
            "boundary": {
                "outsideScope": [
                    "other Rising Rivals cards",
                    "printed finish",
                    "rarity",
                    "catalogue completeness",
                ],
                "zeroResultMeans": "unknown",
                "challenge": "Shared character or artwork alone is insufficient; this edge depends on the exact card article and printed card facts.",
            },
        }],
    }
    observation = {
        "observationId": "obs-bulbapedia-rr111-equivalence-20260902",
        "surfaceId": surface["surfaceId"],
        "kind": "known-positive",
        "queryUrl": SOURCE_URL,
        "queryParameters": {},
        "retrievedAt": REVIEWED_AT,
        "fixtureRef": {
            "kind": "inline-record",
            "record": {
                "evidenceSnapshot": SNAPSHOT,
                "englishRelease": "Rising Rivals 111/111",
                "japaneseRelease": "DP-P Promotional cards 127/DP-P",
                "work": WORK,
                "absenceCapability": False,
                "finishCapability": False,
            },
        },
        "expectedIdentifiers": [*RELEASE_IDS, WORK],
        "validatesEdges": ["bulbapedia-rr111-equivalence-positive"],
        "outcome": "The pinned card article establishes the four localized Western RR 111 releases as implementations of the Big Appetite / Exercise Work while keeping release identity and finish separate.",
    }
    surfaces = {row["surfaceId"]: row for row in document["surfaces"]}
    surfaces[surface["surfaceId"]] = surface
    document["surfaces"] = list(surfaces.values())
    observations = {row["observationId"]: row for row in document["observations"]}
    observations[observation["observationId"]] = observation
    document["observations"] = list(observations.values())
    document["meta"]["reviewedAt"] = REVIEWED_AT


def apply_units(document: list[dict[str, Any]]) -> None:
    units = {row["unitId"]: row for row in document}
    for unit_id in UNIT_IDS:
        row = units.get(unit_id)
        if not row:
            raise ValueError(f"RR 111 identity unit is missing: {unit_id}")
        if (row.get("setCode"), row.get("number")) != ("RR", "111"):
            raise ValueError(f"RR 111 identity unit drifted: {unit_id}")
        if row.get("cardKey") not in {None, WORK}:
            raise ValueError(f"RR 111 identity unit has another Work: {unit_id}")
        if row.get("cardName") not in {"Snorlax LV.X", "Snorlax Lv.X"}:
            raise ValueError(f"RR 111 identity unit has another card name: {unit_id}")
        row["cardKey"] = WORK
        row["cardName"] = "Snorlax Lv.X"


def apply_graph(document: dict[str, Any]) -> None:
    work = next(
        (row for row in document["entities"] if row["entityType"] == "work" and row["entityId"] == WORK_ID),
        None,
    )
    if not work or work["payload"].get("cardKey") != WORK:
        raise ValueError(f"canonical Work is missing: {WORK_ID}")

    for release_id in RELEASE_IDS:
        release = next(
            (row for row in document["entities"] if row["entityType"] == "card-release" and row["entityId"] == release_id),
            None,
        )
        if not release:
            raise ValueError(f"RR 111 release is missing: {release_id}")
        payload = release["payload"]
        current = (payload.get("workMappingState"), payload.get("work"))
        if current not in {("needs-explicit-equivalence", None), ("mapped", WORK)}:
            raise ValueError(f"RR 111 release mapping drifted: {release_id}: {current}")
        payload["workMappingState"] = "mapped"
        payload["work"] = WORK
        payload["sourceRecords"] = sorted({*payload.get("sourceRecords", []), SOURCE_URL})
        document["edges"] = [
            edge for edge in document["edges"]
            if not (
                edge["fromType"] == "card-release"
                and edge["fromId"] == release_id
                and edge["relation"] == "implements"
            )
        ]
        document["edges"].append({
            "fromType": "card-release",
            "fromId": release_id,
            "relation": "implements",
            "toType": "work",
            "toId": WORK_ID,
            "provenance": {
                "state": "mapped",
                "evidenceSnapshot": SNAPSHOT,
                "sourceUrl": SOURCE_URL,
            },
        })

    document["edges"].sort(key=lambda edge: (
        edge["fromType"], edge["fromId"], edge["relation"], edge["toType"], edge["toId"]
    ))
    document["meta"]["generated"] = REVIEWED_AT


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    validate_evidence()
    paths = {"capabilities": CAPABILITIES, "units": UNITS, "graph": GRAPH}
    documents = {label: read(path) for label, path in paths.items()}
    before = {label: encoded(value) for label, value in documents.items()}

    apply_capability(documents["capabilities"])
    apply_units(documents["units"])
    apply_graph(documents["graph"])
    documents["graph"] = graph_projection.project_physical_evidence(documents["graph"])

    stale = [label for label, value in documents.items() if before[label] != encoded(value)]
    if args.check:
        if stale:
            raise SystemExit("RR 111 Work mapping inputs are stale: " + ", ".join(stale))
        print(f"RR 111 Western Work mapping is current: {len(RELEASE_IDS)} releases -> {WORK}")
        return 0
    for label in stale:
        write(paths[label], documents[label])
    print(f"mapped {len(RELEASE_IDS)} RR 111 releases to {WORK}; changed: {', '.join(stale) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

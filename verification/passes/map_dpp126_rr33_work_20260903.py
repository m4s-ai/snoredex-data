#!/usr/bin/env python3
"""Map Japanese DP-P 126 to its reviewed Rising Rivals 33 Work."""

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
EVIDENCE = ROOT / "verification" / "evidence" / "issue-256-dpp126-rr33-work-equivalence-20260903.json"
SNAPSHOT = "verification/evidence/issue-256-dpp126-rr33-work-equivalence-20260903.json"
WORK = "Snorlax-Lv37-Pick-and-Collect-Roll-Over"
WORK_ID = f"WORK:{WORK}"
RELEASE_ID = "RELEASE:JP:Japanese:DP-P:126:None"
REFERENCE_RELEASE_ID = "RELEASE:WEST:English:RR:33:Snorlax-Lv37-Pick-and-Collect-Roll-Over"
SOURCE_URL = (
    "https://bulbapedia.bulbagarden.net/w/index.php?"
    "title=Snorlax_(Rising_Rivals_33)&oldid=4616808"
)
REVIEWED_AT = "2026-09-03"


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def encoded(document: Any) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def write(path: Path, document: Any) -> None:
    path.write_text(encoded(document), encoding="utf-8", newline="\n")


def validate_evidence() -> None:
    evidence = read(EVIDENCE)
    observation = evidence["observations"][0]
    decision = evidence["decision"]
    if observation["sourceUrl"] != SOURCE_URL:
        raise ValueError("DP-P 126 evidence source drifted")
    if decision != {
        "work": WORK,
        "workMappingState": "mapped",
        "releaseIds": [RELEASE_ID],
        "referenceReleaseId": REFERENCE_RELEASE_ID,
        "basis": (
            "The pinned Bulbapedia card page redirects DP-P Promo 126 to Rising Rivals 33 "
            "and identifies English 33/111 and Japanese 126/DP-P as the same Snorlax Lv.37 "
            "with 100 HP, Kagemaru Himeno, Pick and Collect, and Roll Over. This decision "
            "adds only the shared Work relation."
        ),
    }:
        raise ValueError("DP-P 126 Work decision drifted")


def apply_capability(document: dict[str, Any]) -> None:
    surface = {
        "surfaceId": "bulbapedia-rr33-card-equivalence",
        "providerId": "bulbapedia",
        "label": "Bulbapedia exact Rising Rivals 33 card equivalence",
        "match": {
            "urlPrefixes": [
                "https://bulbapedia.bulbagarden.net/wiki/Snorlax_%28Rising_Rivals_33%29",
                "https://bulbapedia.bulbagarden.net/wiki/Snorlax_%28DP-P_Promo_126%29",
                "https://bulbapedia.bulbagarden.net/w/index.php?title=Snorlax_(Rising_Rivals_33)",
            ],
            "nonUrlEvidenceIds": [SNAPSHOT],
        },
        "state": "incomplete",
        "failureState": "Only the exact pinned card article and releases named in the reviewed snapshot are in scope.",
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
                "Snorlax Lv.37",
                "Rising Rivals 33/111",
                "DP-P Promotional cards 126/DP-P",
                "Pick and Collect",
                "Roll Over",
            ],
        },
        "finishCapability": {
            "mode": "none",
            "vocabulary": [],
            "publicationForm": "pinned card identity and release fields, not a physical card photograph",
            "closedWithinScope": False,
        },
        "coverageEdges": [{
            "edgeId": "bulbapedia-rr33-equivalence-positive",
            "coverage": {
                "localities": ["WEST", "JP"],
                "languages": ["English", "Japanese"],
                "scripts": ["Latn", "Jpan"],
                "productCategories": ["card"],
                "timeRange": {
                    "start": None,
                    "end": None,
                    "basis": "the exact pinned Rising Rivals 33 card article only",
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
            "knownPositiveObservationId": "obs-bulbapedia-rr33-equivalence-20260903",
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
        "observationId": "obs-bulbapedia-rr33-equivalence-20260903",
        "surfaceId": surface["surfaceId"],
        "kind": "known-positive",
        "queryUrl": SOURCE_URL,
        "queryParameters": {},
        "retrievedAt": REVIEWED_AT,
        "fixtureRef": {
            "kind": "inline-record",
            "record": {
                "evidenceSnapshot": SNAPSHOT,
                "englishRelease": "Rising Rivals 33/111",
                "japaneseRelease": "DP-P Promotional cards 126/DP-P",
                "work": WORK,
                "absenceCapability": False,
                "finishCapability": False,
            },
        },
        "expectedIdentifiers": [RELEASE_ID, REFERENCE_RELEASE_ID, WORK],
        "validatesEdges": ["bulbapedia-rr33-equivalence-positive"],
        "outcome": "The pinned card article establishes Japanese DP-P 126 as an implementation of the Pick and Collect / Roll Over Work while keeping release identity and finish separate.",
    }
    surfaces = {row["surfaceId"]: row for row in document["surfaces"]}
    surfaces[surface["surfaceId"]] = surface
    document["surfaces"] = list(surfaces.values())
    observations = {row["observationId"]: row for row in document["observations"]}
    observations[observation["observationId"]] = observation
    document["observations"] = list(observations.values())
    document["meta"]["reviewedAt"] = REVIEWED_AT


def apply_unit(document: list[dict[str, Any]]) -> None:
    row = next((item for item in document if item["unitId"] == "U0636"), None)
    if not row or (row.get("setCode"), row.get("number"), row.get("language")) != (
        "DP-P", "126", "Japanese",
    ):
        raise ValueError("DP-P 126 identity unit is missing or drifted")
    if row.get("cardKey") not in {None, WORK}:
        raise ValueError("DP-P 126 identity unit has another Work")
    row["cardKey"] = WORK


def apply_graph(document: dict[str, Any]) -> None:
    work = next(
        (row for row in document["entities"] if row["entityType"] == "work" and row["entityId"] == WORK_ID),
        None,
    )
    if not work or work["payload"].get("cardKey") != WORK:
        raise ValueError(f"canonical Work is missing: {WORK_ID}")
    release = next(
        (row for row in document["entities"] if row["entityType"] == "card-release" and row["entityId"] == RELEASE_ID),
        None,
    )
    if not release:
        raise ValueError(f"DP-P 126 release is missing: {RELEASE_ID}")
    payload = release["payload"]
    current = (payload.get("workMappingState"), payload.get("work"))
    if current not in {("needs-explicit-equivalence", None), ("mapped", WORK)}:
        raise ValueError(f"DP-P 126 Work mapping drifted: {current}")
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
    apply_unit(documents["units"])
    apply_graph(documents["graph"])
    documents["graph"] = graph_projection.project_physical_evidence(documents["graph"])
    stale = [label for label, value in documents.items() if before[label] != encoded(value)]
    if args.check:
        if stale:
            raise SystemExit("DP-P 126 Work mapping inputs are stale: " + ", ".join(stale))
        print(f"DP-P 126 Work mapping is current: {RELEASE_ID} -> {WORK}")
        return 0
    for label in stale:
        write(paths[label], documents[label])
    print(f"mapped DP-P 126 to {WORK}; changed: {', '.join(stale) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

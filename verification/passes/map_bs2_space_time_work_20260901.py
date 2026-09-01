#!/usr/bin/env python3
"""Map Korean BS2 30/40 to its positively identified Space-Time Creation Work."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import authoritative_graph as graph_projection  # noqa: E402
import admit_issue260_korean_20260828 as korean  # noqa: E402


PRINTS = ROOT / "verification" / "source_first_prints.json"
SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
CAPABILITIES = ROOT / "verification" / "source_capabilities.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
EVIDENCE = ROOT / "verification" / "evidence" / "issue-260-bs2-space-time-equivalence-20260901.json"

PRINT_ID = "KR:BS2:30/40:base"
WORK = "Snorlax-Lv35-Block-Ease-Up"
OLD_RELEASE_ID = "RELEASE:KR:Korean:BS2:30/40:unmapped-work:SPEC-0037"
RELEASE_ID = f"RELEASE:KR:Korean:BS2:30/40:{WORK}"
REDIRECT_URL = "https://bulbapedia.bulbagarden.net/wiki/Snorlax_%28Burning_Confrontation_30%29"
CANONICAL_URL = "https://bulbapedia.bulbagarden.net/wiki/Snorlax_%28Diamond_%26_Pearl_37%29"
SNAPSHOT = "verification/evidence/issue-260-bs2-space-time-equivalence-20260901.json"
REVIEWED_AT = "2026-09-01"
BASIS = (
    "Bulbapedia redirects Snorlax (Burning Confrontation 30) to Snorlax "
    "(Diamond & Pearl 37); that canonical card page lists the Japanese "
    "expansion Space-Time Creation and the same Snorlax Lv.35 card facts."
)


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload: dict[str, Any]) -> None:
    korean.write(path, payload)


def validate_evidence() -> None:
    evidence = read(EVIDENCE)
    if evidence["identity"]["printId"] != PRINT_ID:
        raise ValueError("BS2 evidence points to another print")
    if evidence["decision"] != {
        "work": WORK,
        "basis": BASIS,
        "releaseIdentityMerged": False,
        "finishEstablished": False,
        "rarityEstablished": False,
    }:
        raise ValueError("BS2 Work decision drifted")
    redirect = next(
        row for row in evidence["observations"]
        if row["observationId"] == "BULBAPEDIA-BURNING-CONFRONTATION-30-REDIRECT"
    )
    if (
        redirect["sourceUrl"] != REDIRECT_URL
        or redirect["canonicalUrl"] != CANONICAL_URL
        or redirect["observed"] != {
            "redirectedFrom": "Snorlax (Burning Confrontation 30)",
            "canonicalTitle": "Snorlax (Diamond & Pearl 37)",
            "japaneseExpansion": "Space-Time Creation",
            "cardName": "Snorlax",
            "level": 35,
            "hp": 100,
            "illustrator": "Ken Sugimori",
            "attacks": ["Block", "Ease Up"],
        }
        or redirect["establishes"] != [
            "Burning Confrontation 30 and Diamond & Pearl 37 are aliases for the same card",
            "the canonical card has a Japanese Space-Time Creation release",
            "KR:BS2:30/40:base maps to Work Snorlax-Lv35-Block-Ease-Up",
        ]
        or redirect["doesNotEstablish"] != [
            "identical local release identity",
            "printed finish",
            "rarity",
            "provider-wide catalogue completeness",
        ]
    ):
        raise ValueError("Bulbapedia redirect evidence drifted")


def apply_print(document: dict[str, Any]) -> dict[str, Any]:
    row = next(item for item in document["prints"] if item["printId"] == PRINT_ID)
    row["workEvidenceSnapshot"] = SNAPSHOT
    row["corroboratingSourceUrls"] = sorted({
        *row.get("corroboratingSourceUrls", []), REDIRECT_URL, CANONICAL_URL,
    })
    row["workEvidence"] = (
        "Bulbapedia redirects the exact Burning Confrontation 30 alias to Snorlax "
        "(Diamond & Pearl 37), whose canonical page lists the Japanese Space-Time "
        "Creation release; this establishes Work "
        f"{WORK}. The Korean release identity remains separate, and no finish is inferred."
    )
    return row


def apply_profile(document: dict[str, Any], source_row: dict[str, Any]) -> dict[str, Any]:
    profile = next(
        row for row in document["sourceRecords"]
        if row.get("raw", {}).get("printIds") == [PRINT_ID]
    )
    raw = profile["raw"]
    raw["providers"] = sorted({*raw.get("providers", []), "bulbapedia"})
    raw["sourceUrls"] = sorted({
        *raw.get("sourceUrls", []), source_row["sourceUrl"],
        *source_row["corroboratingSourceUrls"],
    })
    raw["workEvidenceSnapshot"] = SNAPSHOT
    return profile


def apply_capability(document: dict[str, Any]) -> None:
    surface = {
        "surfaceId": "bulbapedia-bs2-card-redirect",
        "providerId": "bulbapedia",
        "label": "Bulbapedia exact Burning Confrontation 30 card redirect",
        "match": {
            "urlPrefixes": [REDIRECT_URL, CANONICAL_URL],
            "nonUrlEvidenceIds": [SNAPSHOT],
        },
        "state": "incomplete",
        "failureState": "Only the exact rendered redirect and canonical card fields retained on 2026-09-01 are in scope.",
        "accessMode": "browser",
        "adapterState": "planned",
        "lastCheckedAt": REVIEWED_AT,
        "freshnessPolicy": "Re-check the exact redirect and canonical card page; never generalize this decision to another card or infer absence.",
        "query": {
            "method": "GET",
            "endpoint": REDIRECT_URL,
            "parameters": [],
            "pagination": "not paginated; one exact redirect and its canonical article",
            "expectedIdentifiers": [
                "Snorlax (Burning Confrontation 30)",
                "Snorlax (Diamond & Pearl 37)",
                "Space-Time Creation",
                "Block",
                "Ease Up",
            ],
        },
        "finishCapability": {
            "mode": "none",
            "vocabulary": [],
            "publicationForm": "rendered card identity fields, not a physical card photograph",
            "closedWithinScope": False,
        },
        "coverageEdges": [{
            "edgeId": "bulbapedia-bs2-card-redirect-positive",
            "coverage": {
                "localities": ["KR", "JP", "WEST"],
                "languages": ["Korean", "Japanese", "English"],
                "scripts": ["Hang", "Jpan", "Latn"],
                "productCategories": ["card"],
                "timeRange": {
                    "start": None,
                    "end": None,
                    "basis": "the exact retained Burning Confrontation 30 redirect only",
                },
            },
            "positiveEvidenceCapabilities": [
                "identity", "card-existence", "card-release", "collector-number",
                "set-membership", "artist", "cross-language-equivalence",
            ],
            "exhaustive": False,
            "absenceCapability": {
                "enabled": False,
                "dimensions": [],
                "exactScopes": [],
                "rationale": "The redirect establishes one positive equivalence and no absence claim.",
            },
            "knownPositiveObservationId": "obs-bulbapedia-bs2-card-redirect-20260901",
            "boundary": {
                "outsideScope": [
                    "other Burning Confrontation cards", "printed finish", "rarity",
                    "catalogue completeness",
                ],
                "zeroResultMeans": "unknown",
                "challenge": "Artwork similarity alone is insufficient; this edge depends on the exact redirect.",
            },
        }],
    }
    observation = {
        "observationId": "obs-bulbapedia-bs2-card-redirect-20260901",
        "surfaceId": surface["surfaceId"],
        "kind": "known-positive",
        "queryUrl": REDIRECT_URL,
        "queryParameters": {},
        "retrievedAt": REVIEWED_AT,
        "fixtureRef": {
            "kind": "inline-record",
            "record": {
                "evidenceSnapshot": SNAPSHOT,
                "redirectedFrom": "Snorlax (Burning Confrontation 30)",
                "canonicalTitle": "Snorlax (Diamond & Pearl 37)",
                "japaneseExpansion": "Space-Time Creation",
                "work": WORK,
                "absenceCapability": False,
                "finishCapability": False,
            },
        },
        "expectedIdentifiers": [PRINT_ID, WORK, "Space-Time Creation"],
        "validatesEdges": ["bulbapedia-bs2-card-redirect-positive"],
        "outcome": "The exact redirect establishes the BS2 card's cross-language Work mapping while keeping release identity and finish separate.",
    }
    surfaces = {row["surfaceId"]: row for row in document["surfaces"]}
    surfaces[surface["surfaceId"]] = surface
    document["surfaces"] = list(surfaces.values())
    observations = {row["observationId"]: row for row in document["observations"]}
    observations[observation["observationId"]] = observation
    document["observations"] = list(observations.values())


def apply_graph(document: dict[str, Any], profile: dict[str, Any], source_row: dict[str, Any]) -> None:
    row = {
        "printId": PRINT_ID,
        "localSetCode": "BS2",
        "localNumber": "30/40",
        "work": WORK,
        "workMappingState": "mapped",
        "workMappingBasis": BASIS,
        "legacy": [],
        "legacyVariants": [],
        "rarity": None,
        "specimenId": "SPEC-0037",
        "sourceUrl": source_row["sourceUrl"],
        "retrievedAt": source_row["retrievedAt"],
    }
    korean.apply_set_graph(
        document, profile, "BS2", [f"CLAIM:source-first:{PRINT_ID}"]
    )
    korean.apply_release_graph(document, profile, row)
    release = next(
        item for item in document["entities"]
        if item["entityType"] == "card-release" and item["entityId"] == RELEASE_ID
    )
    release["payload"]["sourceRecords"] = sorted({
        *release["payload"].get("sourceRecords", []),
        *source_row["corroboratingSourceUrls"],
    })
    document["meta"]["generated"] = REVIEWED_AT


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    validate_evidence()
    paths = {
        "prints": PRINTS,
        "sources": SOURCES,
        "capabilities": CAPABILITIES,
        "graph": GRAPH,
    }
    documents = {label: read(path) for label, path in paths.items()}
    before = {label: korean.encoded(value) for label, value in documents.items()}

    source_row = apply_print(documents["prints"])
    profile = apply_profile(documents["sources"], source_row)
    apply_capability(documents["capabilities"])
    # The shared graph re-key helper uses the first pass to remove the obsolete
    # identity and the second to stabilize the replacement's edge ordering.
    for _ in range(2):
        apply_graph(documents["graph"], profile, source_row)
    documents["graph"] = graph_projection.project_physical_evidence(
        documents["graph"]
    )

    stale = [
        label for label, value in documents.items()
        if before[label] != korean.encoded(value)
    ]
    if args.check:
        if stale:
            raise SystemExit("BS2 Work mapping inputs are stale: " + ", ".join(stale))
        print(f"BS2 Work mapping is current: {PRINT_ID} -> {WORK}")
        return 0
    for label in stale:
        write(paths[label], documents[label])
    print(f"mapped {PRINT_ID} to {WORK}; changed: {', '.join(stale) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

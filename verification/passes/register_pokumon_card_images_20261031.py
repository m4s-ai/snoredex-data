"""Register pokumon.com's retained card images as an identity surface (#436).

SPEC-0661 retains pokumon.com's image of the Japanese Expansion Sheet 1 vending Snorlax. The only
pokumon surface was its promo search, which supports card existence but not identity, so the
retained image could not carry the identity dimension every retained card image needs. This pass
adds one manual surface for the image CDN with a single positive edge for that exact card and an
out-of-scope challenge: an image establishes only the pictured card, never a finish, a complete set
or anything about cards it does not show.

Idempotent; `--check` reports pending entries without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPABILITIES = ROOT / "verification" / "source_capabilities.json"
SURFACE_ID = "pokumon-card-images"
IMAGE = "https://cdn6966.templcdn.com/wp-content/uploads/2021/03/JP_034Vending.jpg"
EDGE_ID = f"{SURFACE_ID}-exs-snorlax-positive"
CHALLENGE = ("A pokumon.com card image establishes only the pictured card's identity; finish, other "
             "cards, complete sets and missing images remain unknown.")
BASE = {"surfaceId": SURFACE_ID, "queryUrl": IMAGE, "retrievedAt": "2026-10-31",
        "fixtureRef": {"kind": "source-registry-evidence", "providerId": "pokumon", "recordKey": IMAGE}}
OBSERVATIONS = [
    {"observationId": f"obs-{SURFACE_ID}-exs-snorlax", **BASE, "kind": "known-positive",
     "queryParameters": {"asset": "JP_034Vending.jpg"},
     "expectedIdentifiers": ["カビゴン LV.35", "No. 143", "Uncommon rarity symbol"],
     "validatesEdges": [EDGE_ID],
     "outcome": "The retained image (SPEC-0661) visibly identifies the Japanese Expansion Sheet 1 vending Snorlax."},
    {"observationId": f"obs-{SURFACE_ID}-exs-snorlax-boundary", **BASE, "kind": "out-of-scope-challenge",
     "queryParameters": {"challenge": "unsupported finish, set or neighbouring-card transfer"},
     "expectedIdentifiers": ["カビゴン LV.35"], "validatesEdges": [EDGE_ID], "outcome": CHALLENGE},
]
SURFACE = {
    "surfaceId": SURFACE_ID, "providerId": "pokumon", "label": "pokumon.com retained card images",
    "match": {"urlPrefixes": ["https://cdn6966.templcdn.com/wp-content/uploads/"], "nonUrlEvidenceIds": []},
    "state": "active", "failureState": None, "accessMode": "manual", "adapterState": "not-applicable",
    "lastCheckedAt": "2026-10-31",
    "freshnessPolicy": "Retain the exact image bytes, URL and SHA-256 as a SPEC record; each image establishes only itself.",
    "query": {"method": "MANUAL", "endpoint": "exact pokumon.com card-image URL", "parameters": [],
              "pagination": "not paginated; each retained image establishes only itself",
              "expectedIdentifiers": ["printed card name", "collector number", "printed rarity symbol"]},
    "finishCapability": {"mode": "none", "vocabulary": [],
                         "publicationForm": "card image; no physical finish closure", "closedWithinScope": False},
    "coverageEdges": [{
        "edgeId": EDGE_ID,
        "coverage": {"localities": ["JP"], "languages": ["Japanese"], "scripts": ["Jpan"],
                     "productCategories": ["card"],
                     "timeRange": {"start": "1998-03", "end": "1998-03",
                                   "basis": "the retained Expansion Sheet 1 vending Snorlax image only"}},
        "positiveEvidenceCapabilities": ["identity", "card-existence"],
        "exhaustive": False,
        "absenceCapability": {"enabled": False, "dimensions": [], "exactScopes": [],
                              "rationale": "One retained image establishes the pictured card only; missing images and other cards remain unknown."},
        "knownPositiveObservationId": f"obs-{SURFACE_ID}-exs-snorlax",
        "outOfScopeChallengeObservationId": f"obs-{SURFACE_ID}-exs-snorlax-boundary",
        "boundary": {"outsideScope": ["finish/treatment", "other cards", "complete set or era"],
                     "zeroResultMeans": "unknown", "challenge": CHALLENGE},
    }],
}


def main(argv) -> int:
    document = json.loads(CAPABILITIES.read_text(encoding="utf-8"))
    surfaces = {row["surfaceId"] for row in document["surfaces"]}
    observations = {row["observationId"] for row in document["observations"]}
    pending = (SURFACE_ID not in surfaces) or any(row["observationId"] not in observations for row in OBSERVATIONS)
    if "--check" in argv:
        if pending:
            print("pending:", SURFACE_ID)
        return 1 if pending else 0
    if pending:
        if SURFACE_ID not in surfaces:
            document["surfaces"].append(SURFACE)
        document["observations"] += [row for row in OBSERVATIONS if row["observationId"] not in observations]
        CAPABILITIES.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

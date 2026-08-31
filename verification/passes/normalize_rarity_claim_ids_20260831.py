"""Drop unsupported rarity normalizations while retaining source-native values."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "verification" / "authoritative_graph.json"
EXPECTED = Counter({"triple-rare": 4, "super-rare": 4, "character-rare": 2})


def encoded(document: dict) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    claims = [
        row["payload"]
        for row in graph["entities"]
        if row["entityType"] == "rarity-claim"
        and row["payload"].get("normalizedRarityId") in EXPECTED
    ]
    counts = Counter(row["normalizedRarityId"] for row in claims)
    if counts and counts != EXPECTED:
        raise SystemExit(f"unexpected unsupported rarity claims: {dict(counts)}")
    for claim in claims:
        claim["normalizedRarityId"] = None

    rendered = encoded(graph)
    current = GRAPH.read_text(encoding="utf-8")
    if args.check:
        if current != rendered:
            raise SystemExit("unsupported rarity claim normalizations remain")
        print("rarity claim normalizations are catalogue-safe")
        return 0
    GRAPH.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"cleared {len(claims)} unsupported rarity claim normalization(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

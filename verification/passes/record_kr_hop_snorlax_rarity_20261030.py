"""Record the printed rarity of Korean Hop's Snorlax m2a 136/193 and its xm2a V2 mirror (#437).

Both items carried only the Cardmarket catalogue rarity "Fixed". Each claim rests on an image of
the exact card whose collector line is legible and shows no rarity symbol after 136/193:

* m2a 136/193: the official Pokémon Korea render, retained in
  `verification/evidence/kr-hop-snorlax-rarity-20261030/`. The claim concerns the release.
* xm2a 136/193 V2 (Poké Ball mirror): SPEC-0410. Its `sourceProductKey` is the V2 marketplace
  product, so the collector catalogue applies it to the V2 printing only, never to V1.

The value stays source-native (`no printed rarity symbol`, no normalized id): `fixed` is reserved
for fixed-deck contents. Idempotent; `--check` reports pending records without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from admit_issue257_simplified_chinese_20260827 import upsert_edge, upsert_entity  # noqa: E402

GRAPH = ROOT / "verification" / "authoritative_graph.json"
PRINTS = ROOT / "verification" / "source_first_prints.json"
ORIGIN = "reviewed-evidence-issue-437"
BUNDLE = "verification/evidence/kr-hop-snorlax-rarity-20261030"
RETRIEVED = "2026-10-30"
NATIVE = "no printed rarity symbol"
RENDER = "https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/M2a/M2a_136.png"
DETAIL = "https://pokemoncard.co.kr/cards/detail/BS2025015136"
V2_PRODUCT = ("https://www.cardmarket.com/en/Pokemon/Products/Singles/MEGA-Dream-ex-Additionals/"
              "Hops-Snorlax-V2-xm2a136")
WORK = "Hops-Snorlax-Extra-Helpings-Dynamic-Press"
CLAIMS = [
    {
        "rarityClaimId": f"RARITYCLAIM:issue437:m2a:136/193:{WORK}",
        "cardReleaseId": f"RELEASE:KR:Korean:m2a:136/193:{WORK}",
        "sourceRecordId": "SET-SRC-SF-EBC661CA979D",
        "sourceProductKey": RENDER,
        "supportingSourceUrls": [DETAIL],
        "evidence": ("The official Pokémon Korea render of 호브의 잠만보 m2a 136/193 shows the complete "
                     "collector line with no rarity symbol after the number. MEGA Dream ex is a "
                     "high-class pack; no fixed-deck normalization applies."),
    },
    {
        "rarityClaimId": f"RARITYCLAIM:issue437:xm2a:136/193-V2:{WORK}",
        "cardReleaseId": f"RELEASE:KR:Korean:xm2a:136/193:{WORK}",
        "sourceRecordId": "SET-SRC-SF-BE4749055DF1",
        "sourceProductKey": V2_PRODUCT,
        "specimenIds": ["SPEC-0410"],
        "evidence": ("SPEC-0410, a complete seller photograph of the Korean xm2a V2 Poké Ball mirror "
                     "product, shows the legible collector line 136/193 with no rarity symbol after "
                     "it. Scoped to the V2 product; the V1 Colorless Energy mirror is not covered."),
    },
]


def claim_payload(row: dict) -> dict:
    return {**row, "sourceProvider": "mixed-positive-evidence", "sourceVocabulary": "printed-Korean-card",
            "sourceNativeValue": NATIVE, "normalizedRarityId": None, "retrievedAt": RETRIEVED,
            "evidenceBundle": BUNDLE}


def pending_claims(graph: dict) -> list[dict]:
    present = {row["entityId"]: row["payload"] for row in graph["entities"]
               if row["entityType"] == "rarity-claim"}
    return [row for row in CLAIMS if present.get(row["rarityClaimId"]) != claim_payload(row)]


def pending_print(prints: dict) -> dict | None:
    row = next(row for row in prints["prints"] if row["printId"] == "KR:m2a:136/193:base")
    expected = {"raritySourceUrl": RENDER, "rarityProviderId": "pokemon-card-korea",
                "rarityRetrievedAt": RETRIEVED}
    return None if all(row.get(key) == value for key, value in expected.items()) else (row, expected)


def main(argv) -> int:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    prints = json.loads(PRINTS.read_text(encoding="utf-8"))
    claims, print_row = pending_claims(graph), pending_print(prints)
    if "--check" in argv:
        for row in claims:
            print("pending:", row["rarityClaimId"])
        if print_row:
            print("pending: rarity provenance on KR:m2a:136/193:base")
        return 1 if claims or print_row else 0
    for row in claims:
        upsert_entity(graph, "rarity-claim", row["rarityClaimId"], claim_payload(row), origin=ORIGIN)
        upsert_edge(graph, "rarity-claim", row["rarityClaimId"], "asserts-rarity-for", "card-release",
                    row["cardReleaseId"])
        upsert_edge(graph, "rarity-claim", row["rarityClaimId"], "observed-by", "set-source-record",
                    row["sourceRecordId"])
    if claims:
        GRAPH.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if print_row:
        print_row[0].update(print_row[1])
        PRINTS.write_text(json.dumps(prints, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

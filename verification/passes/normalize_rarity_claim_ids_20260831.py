"""Register reviewed rarity mappings and drop unsupported normalizations."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "verification" / "authoritative_graph.json"
CATALOGUE = ROOT / "verification" / "rarity_catalogue.json"
EXPECTED = Counter({
    "triple-rare": 4,
    "super-rare": 4,
    "character-rare": 2,
    "hyper-rare": 4,
})
EXPECTED_NATIVE = Counter({("printed-Korean-card", "UR", "ultra-rare"): 1})
SOURCE_NATIVE_MAPPINGS = [
    {
        "locality": "WEST",
        "sourceVocabulary": "cardmarket-2026-07-21",
        "basis": "Reviewed normalization of exact labels in the frozen Cardmarket-derived candidate universe.",
        "values": {
            "Common": "common", "Double Rare": "double-rare", "Holo Rare": "holofoil-rare",
            "Illustration Rare": "illustration-rare", "Promo": "promo", "Rare": "rare",
            "Secret Rare": "secret-rare", "Shiny Rare": "shiny-rare",
            "Ultra Rare": "ultra-rare", "Uncommon": "uncommon",
        },
    },
    {
        "locality": "JP",
        "sourceVocabulary": "cardmarket-2026-07-21",
        "basis": "Reviewed normalization of exact labels in the frozen Cardmarket-derived candidate universe.",
        "values": {
            "Common": "common", "Double Rare": "double-rare", "Holo Rare": "holofoil-rare",
            "Illustration Rare": "illustration-rare", "Promo": "promo", "Rare": "rare",
            "Secret Rare": "secret-rare", "Shiny Rare": "shiny-rare",
            "Ultra Rare": "ultra-rare", "Uncommon": "uncommon",
        },
    },
    {
        "locality": "CN",
        "sourceVocabulary": "cardmarket-2026-07-21",
        "basis": "Reviewed normalization of exact labels in the frozen Cardmarket-derived candidate universe.",
        "values": {
            "Double Rare": "double-rare", "Promo": "promo", "Rare": "rare",
            "Secret Rare": "secret-rare", "Shiny Rare": "shiny-rare",
            "Special Illustration Rare": "special-illustration-rare",
            "Ultra Rare": "ultra-rare", "Uncommon": "uncommon",
        },
    },
    {
        "locality": "TW",
        "sourceVocabulary": "cardmarket-2026-07-21",
        "basis": "Reviewed normalization of exact labels in the frozen Cardmarket-derived candidate universe.",
        "values": {"Promo": "promo"},
    },
    {
        "locality": "LATAM",
        "sourceVocabulary": "pokemon-official-la-card-database",
        "basis": "Reviewed exact rarity labels retained from the official Latin American card database.",
        "values": {"Common": "common", "Rare": "rare"},
    },
    {
        "locality": "LATAM",
        "sourceVocabulary": "pokemon-official-journey-together-prerelease-2025",
        "basis": "Reviewed promotional-card classification from the official prerelease product source.",
        "values": {"promo card": "promo"},
    },
    {
        "locality": "ID",
        "sourceVocabulary": "printed-Indonesian-card-render",
        "basis": "Reviewed official Indonesian card-render mappings admitted under issue #258.",
        "values": {
            "AR": "illustration-rare", "C": "common", "no printed rarity symbol": "fixed",
            "PROMO": "promo", "R": "rare", "RR": "double-rare", "S": "shiny-rare",
            "U": "uncommon",
        },
    },
    {
        "locality": "KR",
        "sourceVocabulary": "printed-Korean-card",
        "basis": (
            "Reviewed Korean card mappings admitted under issue #260. Historical HR and "
            "unqualified UR remain unmapped because their canonical meaning varies by era."
        ),
        "values": {
            "AR": "illustration-rare", "C": "common", "fixed product": "fixed",
            "no printed rarity symbol": "fixed", "PROMO": "promo",
            "R": "rare", "RR": "double-rare", "S": "shiny-rare", "U": "uncommon",
        },
    },
    {
        "locality": "TH",
        "sourceVocabulary": "printed-Thai-card",
        "basis": "Reviewed official Thai card mappings admitted under issue #262.",
        "values": {
            "AR": "illustration-rare", "C": "common", "no printed rarity symbol": "fixed",
            "PROMO": "promo", "R": "rare", "RR": "double-rare", "S": "shiny-rare",
            "U": "uncommon",
        },
    },
    {
        "locality": "TW",
        "sourceVocabulary": "printed-Traditional-Chinese-card",
        "basis": (
            "Reviewed official and retained Traditional Chinese card mappings admitted under issue #263. "
            "Historical HR remains unmapped because the catalogue's Hyper Rare id describes the later "
            "SV-era UR tier."
        ),
        "values": {
            "AR": "illustration-rare", "C": "common", "PROMO": "promo",
            "R": "rare", "RR": "double-rare", "S": "shiny-rare", "U": "uncommon",
        },
    },
]


def encoded(document: dict) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    claims = [
        row["payload"]
        for row in graph["entities"]
        if row["entityType"] == "rarity-claim"
        and row["payload"].get("normalizedRarityId") in EXPECTED
    ]
    counts = Counter(row["normalizedRarityId"] for row in claims)
    if any(count != EXPECTED[rarity_id] for rarity_id, count in counts.items()):
        raise SystemExit(f"unexpected unsupported rarity claims: {dict(counts)}")
    native_claims = [
        row["payload"]
        for row in graph["entities"]
        if row["entityType"] == "rarity-claim"
        and (
            row["payload"].get("sourceVocabulary"),
            row["payload"].get("sourceNativeValue"),
            row["payload"].get("normalizedRarityId"),
        ) in EXPECTED_NATIVE
    ]
    native_counts = Counter((
        row["sourceVocabulary"], row["sourceNativeValue"], row["normalizedRarityId"]
    ) for row in native_claims)
    if native_counts and native_counts != EXPECTED_NATIVE:
        raise SystemExit(f"unexpected unsupported native rarity claims: {dict(native_counts)}")
    claims.extend(native_claims)
    for claim in claims:
        claim["normalizedRarityId"] = None

    catalogue["meta"]["schemaVersion"] = "0.2.0"
    catalogue["meta"]["generated"] = "2026-09-01"
    catalogue["meta"]["description"] = (
        "One entry per rarity plus reviewed, locality-qualified mappings from exact source-native "
        "values to canonical rarity ids. Rarity remains a card-release claim, never a work claim."
    )
    catalogue = {
        "meta": catalogue["meta"],
        "localeVocabularies": catalogue["localeVocabularies"],
        "sourceNativeMappings": SOURCE_NATIVE_MAPPINGS,
        "rarities": catalogue["rarities"],
        "editionAvailability": catalogue["editionAvailability"],
    }

    rendered_graph = encoded(graph)
    rendered_catalogue = encoded(catalogue)
    current_graph = GRAPH.read_text(encoding="utf-8")
    current_catalogue = CATALOGUE.read_text(encoding="utf-8")
    if args.check:
        if current_graph != rendered_graph or current_catalogue != rendered_catalogue:
            raise SystemExit("rarity claim mappings are stale")
        print("rarity claim mappings are catalogue-safe")
        return 0
    GRAPH.write_text(rendered_graph, encoding="utf-8", newline="\n")
    CATALOGUE.write_text(rendered_catalogue, encoding="utf-8", newline="\n")
    print(
        f"registered {len(SOURCE_NATIVE_MAPPINGS)} rarity mapping scope(s); "
        f"cleared {len(claims)} unsupported normalization(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

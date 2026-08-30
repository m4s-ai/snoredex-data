"""Admit the researched Thai AS5a 142/184 release and its two owner specimens."""

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
from admit_issue257_simplified_chinese_20260827 import (  # noqa: E402
    append_unique,
    encoded,
    stable_profile_id,
    upsert_edge,
    upsert_entity,
    upsert_migration,
)
from admit_issue262_thai_20260828 import (  # noqa: E402
    apply_release_group,
    apply_set_graph,
    persisted_source_row,
)


PRINTS = ROOT / "verification" / "source_first_prints.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
SET_SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"

PRINT_ID = "TH:AS5a:142/184:base"
RELEASE_ID = "RELEASE:TH:Thai:AS5a:142/184:Snorlax-Lazy-Eating-Big-Counter"
PROFILE_ID = stable_profile_id("TH", "AS5a")
INDEX_ID = "SET-SRC-IDX-FF7AA1CC9DD8"
OFFICIAL_PRODUCT = "https://asia.pokemon-card.com/th/archive/card/sun_moon_series/booster_pack_5a.html"
OFFICIAL_LIST = "https://asia.pokemon-card.com/th/archive/card/pdf/AS5a.pdf"
BULBAPEDIA_SET = "https://bulbapedia.bulbagarden.net/wiki/AS5a"
BULBAPEDIA_CARD = "https://bulbapedia.bulbagarden.net/wiki/Snorlax_(Double_Burst_142)"
OJAMA_CARD = "https://ojamacard.com/product/21823/142-184-%E0%B8%84%E0%B8%B2%E0%B8%9A%E0%B8%B4%E0%B8%81%E0%B8%AD%E0%B8%99-r-as5a"
OJAMA_VARIANTS = "https://ojamacard.com/product/tag/as4a?tskp=12"
EBAY_REGULAR = "https://www.ebay.com/itm/127908236860"
EBAY_HOLO = "https://www.ebay.com/itm/127969187437"

ROW: dict[str, Any] = {
    "detail": "researched-thai-as5a-142",
    "specimenId": "SPEC-0427",
    "printId": PRINT_ID,
    "localSetCode": "AS5a",
    "localNumber": "142/184",
    "variant": "base",
    "cardName": "Snorlax",
    "locality": "TH",
    "language": "Thai",
    "script": "Thai",
    "name": "คาบิกอน",
    "catchUpOf": "the exact Thai counterpart established by its printed Thai attacks and card traits",
    "providerId": "bulbapedia",
    "sourceUrl": BULBAPEDIA_SET,
    "corroborated": True,
    "markAssetUrl": None,
    "cardImageUrl": None,
    "releaseDate": "2020-02-27",
    "releaseDatePrecision": "day",
    "releaseApproximate": False,
    "evidence": (
        "Bulbapedia's exact AS5a list identifies Thai Snorlax 142/184 as rarity R and dates "
        "Double Burst Set A to 2020-02-27. The official Thai product page and retained official "
        "card-list PDF establish the AS5a product. SPEC-0427 and SPEC-0428 positively show the "
        "Thai card face, collector number, 150 HP and kanahei credit; their owner attestations "
        "separately establish regular and holo physical copies. Ojama's exact R and R-Foil SKUs "
        "and the two exact seller-photo listings independently corroborate the two treatments. "
        "No completeness or unpictured variant is inferred."
    ),
    "corroboratingSourceUrls": [
        OFFICIAL_PRODUCT,
        OFFICIAL_LIST,
        BULBAPEDIA_CARD,
        OJAMA_CARD,
        OJAMA_VARIANTS,
        EBAY_REGULAR,
        EBAY_HOLO,
    ],
    "work": "Snorlax-Lazy-Eating-Big-Counter",
    "rarity": ("R", "rare"),
    "legacy": [],
}


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(encoded(payload), encoding="utf-8", newline="\n")


def apply_print(document: dict[str, Any]) -> None:
    rows = {row["printId"]: row for row in document["prints"]}
    rows[PRINT_ID] = persisted_source_row(ROW)
    document["prints"] = sorted(rows.values(), key=lambda row: row["printId"])
    document["meta"]["generated"] = "2026-08-30"
    document["meta"]["counts"]["admitted"] = len(document["prints"])


def apply_specimens(document: dict[str, Any]) -> None:
    rows = {row["specimenId"]: row for row in document["specimens"]}
    observations = {
        "SPEC-0427": (
            "The retained full-card photograph positively identifies Thai Snorlax AS5a 142/184, "
            "150 HP and Illus. kanahei. The collection-owner checklist identifies this physical "
            "copy as Non-Holo. The researched Thai source-first release is materialized separately "
            "from the T-Chinese AS5a 142 release."
        ),
        "SPEC-0428": (
            "The retained full-card photograph positively identifies Thai Snorlax AS5a 142/184, "
            "150 HP and Illus. kanahei. The collection-owner checklist identifies this physical "
            "copy as Holo. The researched Thai source-first release is materialized separately "
            "from the T-Chinese AS5a 142 release."
        ),
    }
    for specimen_id, observed in observations.items():
        row = rows[specimen_id]
        row["observed"] = observed
        row["citedBy"] = sorted(set(row.get("citedBy") or []) | {PRINT_ID})
        row.pop("allowUnprojected", None)
    document["specimens"] = sorted(
        rows.values(), key=lambda row: int(row["specimenId"].split("-")[1])
    )
    document["count"] = len(document["specimens"])


def profile() -> dict[str, Any]:
    return {
        "sourceRecordId": PROFILE_ID,
        "sourceKind": "source-first-local-set-profile",
        "provider": "mixed-positive-evidence",
        "providerRecordKey": "TH\x1fAS5a",
        "retrieved": "2026-08-30",
        "raw": {
            "localCode": "AS5a",
            "localName": "Double Burst Set A",
            "locality": "TH",
            "languages": ["Thai"],
            "scripts": ["Thai"],
            "printIds": [PRINT_ID],
            "providers": ["bulbapedia", "ojama-card", "pokemon-card-asia"],
            "sourceUrls": [
                OFFICIAL_PRODUCT,
                OFFICIAL_LIST,
                BULBAPEDIA_SET,
                BULBAPEDIA_CARD,
                OJAMA_CARD,
                OJAMA_VARIANTS,
            ],
            "printedSetSize": 184,
            "printedSetSizeBasis": "the denominator printed on both retained Thai cards",
            "localeSuffix": None,
            "observedCollectorNumbers": ["142/184"],
            "observedCoverage": "one exact positive Thai Snorlax card, not an enumeration of the set",
            "markAssetUrls": [],
            "cardImageUrls": [],
        },
    }


def apply_sources(document: dict[str, Any], source_profile: dict[str, Any]) -> dict[str, Any]:
    rows = {row["sourceRecordId"]: row for row in document["sourceRecords"]}
    rows[PROFILE_ID] = source_profile
    for row in rows.values():
        if row.get("sourceKind") != "locality-set-index-record":
            continue
        if row.get("providerRecordKey") != "TH\x1fAS5a":
            continue
        raw = row["raw"]
        raw["releaseDate"] = "February 27, 2020"
        raw["snorlaxExaminationState"] = "examined-snorlax-found"
        raw["snorlaxPrintIds"] = sorted(set(raw.get("snorlaxPrintIds") or []) | {PRINT_ID})
        raw["examinationBasis"] = (
            "the reviewed positive Thai AS5a card evidence establishes Snorlax 142/184; "
            "this is not an absence or complete-set claim"
        )
    document["sourceRecords"] = sorted(rows.values(), key=lambda row: row["sourceRecordId"])
    document["meta"]["counts"]["sourceRecords"] = len(document["sourceRecords"])
    document["meta"]["counts"]["sourceFirstLocalSets"] = sum(
        row["sourceKind"] == "source-first-local-set-profile"
        for row in document["sourceRecords"]
    )
    return rows[INDEX_ID]


def apply_index_graph(graph: dict[str, Any], index_source: dict[str, Any]) -> None:
    local_set_id = "LOCALSET:TH:AS5a"
    reason = "the reviewed Thai AS5a record and exact card evidence establish this local set"
    upsert_entity(
        graph,
        "set-source-record",
        INDEX_ID,
        index_source,
        origin="reviewed-evidence-thai-as5a-20260830",
    )
    upsert_entity(
        graph,
        "set-source-disposition",
        INDEX_ID,
        {
            "sourceRecordId": INDEX_ID,
            "disposition": "mapped",
            "targetRef": local_set_id,
            "reason": reason,
        },
        origin="reviewed-evidence-thai-as5a-20260830",
    )
    upsert_edge(graph, "set-source-disposition", INDEX_ID, "disposes", "set-source-record", INDEX_ID)
    upsert_migration(
        graph,
        {
            "sourceKind": "set-catalogue-source",
            "sourceId": INDEX_ID,
            "disposition": "mapped",
            "targetRef": local_set_id,
            "reason": reason,
        },
    )
    local_set = next(
        row for row in graph["entities"]
        if row.get("entityType") == "local-set" and row.get("entityId") == local_set_id
    )
    append_unique(local_set["payload"].setdefault("sourceRecordIds", []), INDEX_ID)
    upsert_edge(graph, "local-set", local_set_id, "observed-by", "set-source-record", INDEX_ID)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    prints = read(PRINTS)
    specimens = read(SPECIMENS)
    sources = read(SET_SOURCES)
    graph = read(GRAPH)
    before = {
        "prints": encoded(prints),
        "specimens": encoded(specimens),
        "sources": encoded(sources),
        "graph": encoded(graph),
    }

    apply_print(prints)
    apply_specimens(specimens)
    source_profile = profile()
    index_source = apply_sources(sources, source_profile)
    if not args.check:
        # The physical-evidence projection reads the canonical specimen file from disk.
        write(SPECIMENS, specimens)
    claim_id = f"CLAIM:source-first:{PRINT_ID}"
    apply_set_graph(graph, source_profile, "AS5a", [claim_id])
    apply_index_graph(graph, index_source)
    apply_release_group(graph, source_profile, [ROW], {})
    graph = graph_projection.project_physical_evidence(graph)

    current = {
        "prints": encoded(prints),
        "specimens": encoded(specimens),
        "sources": encoded(sources),
        "graph": encoded(graph),
    }
    stale = [name for name in before if before[name] != current[name]]
    if args.check:
        if stale:
            raise SystemExit("Thai AS5a 142/184 reviewed inputs are stale: " + ", ".join(stale))
        print("Thai AS5a 142/184 reviewed inputs are current")
        return 0

    for path, document in (
        (PRINTS, prints),
        (SPECIMENS, specimens),
        (SET_SOURCES, sources),
        (GRAPH, graph),
    ):
        write(path, document)
    print(f"admitted {PRINT_ID} as {RELEASE_ID} with two positive physical specimens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

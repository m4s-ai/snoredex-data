#!/usr/bin/env python3
"""Index Thailand's published product list, and say where the source stops (#138).

The Indonesian index gave that locality a denominator. This does the same for Thailand from
`Pokémon in Thailand`, and the interesting part is the difference between the two sources.

**The Thai table is tagged `{{outdated}}` by Bulbapedia itself**, "needs=updated list of booster
packs since SWSH". It lists 23 product rows and stops in the Sun & Moon era, while the Indonesian
article carries 78 rows through to 2026. So the Thai codes this repository already holds —
`sc1a T`, `sc1b T`, `sc1D T`, `sc3b T`, `scA T`, `scD T`, all Sword & Shield-era — are **not in the
index at all**, because the article never got that far.

That is why the record carries `indexCoverage` on every row and why the count is not presented as a
catalogue. An index that stopped six years ago, read as a denominator, would say Thailand released
23 products and make every later Thai set look like a discovery rather than a gap in one wiki table.

WHAT EACH ROW CARRIES

The mark code, the series, the English product name, the product kind — the Thai article splits a
release into `Booster Pack Set A` / `Set B` and `GX Starter Deck Set A` / `Set B` under one code,
which is the two-products-per-code trap the owner flagged — and `snorlaxExaminationState`, resolved
the same way as Indonesia: a source-first print or a confirmed Thai unit both count as examined.

    python verification/passes/seed_thailand_set_index_20260810.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT = ROOT / "verification" / ".th_catalogue_input.json"
PRINTS = ROOT / "verification" / "source_first_prints.json"
UNITS = ROOT / "verification" / "units.json"
SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
ARTICLE = "https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_in_Thailand"
RETRIEVED = "2026-08-10"
COVERAGE = (
    "Bulbapedia tags this table {{outdated}} — \"needs=updated list of booster packs since SWSH\" — "
    "so it stops in the Sun & Moon era. Thai Sword & Shield-era codes this repository already holds "
    "are absent from the index because the article never listed them, not because they do not "
    "exist. Never read this index as a catalogue of Thai releases."
)


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:12].upper()}"


def match_key(code: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"\s+T$", "", str(code).strip())).lower()


def main() -> int:
    rows: list[dict[str, Any]] = json.loads(INPUT.read_text(encoding="utf-8"))
    prints = json.loads(PRINTS.read_text(encoding="utf-8"))["prints"]
    document = json.loads(SOURCES.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = document["sourceRecords"]

    examined: dict[str, list[str]] = {}
    for entry in prints:
        if entry["locality"] == "TH":
            examined.setdefault(match_key(entry["localSetCode"]), []).append(entry["printId"])
    unit_evidence: dict[str, list[str]] = {}
    for unit in json.loads(UNITS.read_text(encoding="utf-8")):
        if unit["language"] == "Thai" and unit["status"] == "confirmed":
            unit_evidence.setdefault(match_key(unit["setCode"]), []).append(unit["unitId"])

    existing = {row["providerRecordKey"] for row in records
                if row["sourceKind"] == "locality-set-index-record"}
    added = 0
    for row in rows:
        code = row["markField"].strip()
        key = f"TH\x1f{code}"
        if key in existing:
            continue
        existing.add(key)
        found = examined.get(match_key(code), [])
        units_found = unit_evidence.get(match_key(code), [])
        records.append({
            "sourceRecordId": stable_id("SET-SRC-IDX", "TH", code),
            "sourceKind": "locality-set-index-record",
            "provider": "bulbapedia",
            "providerRecordKey": key,
            "retrieved": RETRIEVED,
            "sourceUrl": ARTICLE,
            "raw": {
                "locality": "TH",
                "localCode": code,
                "pairedCodes": [],
                "productKind": row["productKind"],
                "englishName": row["englishName"],
                "indonesianName": None,
                "series": row["series"],
                "releaseDate": row.get("releaseDate"),
                "indexCoverage": COVERAGE,
                "snorlaxExaminationState": (
                    "examined-snorlax-found" if (found or units_found) else "not-examined"),
                "snorlaxPrintIds": sorted(found),
                "snorlaxUnitIds": sorted(units_found),
                "examinationBasis": (
                    "a source-first print is admitted for this code" if found else
                    "a confirmed Thai language unit exists for the Japanese set this code "
                    "localizes" if units_found else
                    "no Snorlax has been established for this code. This source cannot "
                    "distinguish a set with no Snorlax from a set it does not list, and it is "
                    "explicitly outdated, so the state is 'not examined' and never an absence."
                ),
            },
        })
        added += 1

    records.sort(key=lambda item: item["sourceRecordId"])
    document["meta"]["counts"]["sourceRecords"] = len(records)
    document["meta"]["counts"]["localitySetIndexRecords"] = sum(
        1 for row in records if row["sourceKind"] == "locality-set-index-record")
    SOURCES.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    INPUT.unlink()

    thai = [r for r in records if r["sourceKind"] == "locality-set-index-record"
            and r["raw"]["locality"] == "TH"]
    found_n = sum(1 for r in thai if r["raw"]["snorlaxExaminationState"] == "examined-snorlax-found")
    print(f"added {added} Thai set-index record(s); {len(thai)} indexed, "
          f"{found_n} examined with a Snorlax found, {len(thai) - found_n} not examined")
    print("  the source is Bulbapedia-tagged outdated and stops at Sun & Moon; this is not a "
          "catalogue of Thai releases and every row says so")
    return 0


if __name__ == "__main__":
    sys.exit(main())

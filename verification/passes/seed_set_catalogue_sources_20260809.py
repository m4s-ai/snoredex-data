#!/usr/bin/env python3
"""Seed the independent set-catalogue source registry for #146.

This is a one-shot migration pass, not a recurring generator. It copies the set/product records
that were visible through the legacy Cardmarket harvest, the source-first local-set identifiers,
the reviewed Bulbapedia release-date records, and the two edition-availability records already
captured in the rarity catalogue into one source-record store. From that point forward the set
catalogue can accept provider records without asking whether ``snorlax_cards.json`` contains a
Snorlax from the set.

The output preserves raw provider values. Locality is recorded only where the input names it or
where the frozen legacy market context does; it is not an equivalence assertion across markets.

    python verification/passes/seed_set_catalogue_sources_20260809.py
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = ROOT / "verification" / "set_catalogue_sources.json"

MARKET_LOCALITY = {
    "Western": "WEST",
    "Japanese": "JP",
    "Simplified Chinese": "CN",
    "Traditional Chinese": "TW",
    "SEA promo": "SEA",
}

LOCALITY_LANGUAGE = {
    "WEST": "English",
    "JP": "Japanese",
    "KR": "Korean",
    "TW": "T-Chinese",
    "CN": "S-Chinese",
    "ID": "Indonesian",
    "TH": "Thai",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:12].upper()}"


def main() -> None:
    cards = read_json(ROOT / "snorlax_cards.json")["cards"]
    source_first = read_json(ROOT / "verification" / "source_first_prints.json")["prints"]
    release_dates = read_json(
        ROOT / "verification" / "bulbapedia_release_dates.json")["records"]
    availability = read_json(
        ROOT / "verification" / "rarity_catalogue.json")["editionAvailability"]

    records: list[dict[str, Any]] = []
    locality_by_code: dict[str, set[str]] = defaultdict(set)

    legacy_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for card in cards:
        locality = MARKET_LOCALITY[card["market"]]
        key = (locality, card["setCode"], card["setName"])
        legacy_groups[key].append(card)
        locality_by_code[card["setCode"]].add(locality)

    for (locality, code, name), group in sorted(legacy_groups.items()):
        source_id = stable_id("SET-SRC-CM", locality, code, name)
        products = []
        for card in sorted(group, key=lambda item: item["productUrl"]):
            products.append({
                "productUrl": card["productUrl"],
                "collectorNumber": str(card.get("number") or ""),
                "variantToken": card.get("variantToken") or "base",
                "rarity": card.get("rarity"),
                "market": card["market"],
                "isCodeCard": bool(card.get("isCodeCard")),
            })
        records.append({
            "sourceRecordId": source_id,
            "sourceKind": "legacy-cardmarket-set-profile",
            "provider": "cardmarket",
            "providerRecordKey": f"{locality}\x1f{code}\x1f{name}",
            "retrieved": "2026-07-21",
            "raw": {
                "localCode": code,
                "localName": name,
                "market": group[0]["market"],
                "locality": locality,
                "productKind": (
                    "code-card-product" if all(item.get("isCodeCard") for item in group)
                    else "physical-card-set-or-product"
                ),
                "products": products,
            },
        })

    source_first_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for entry in source_first:
        source_first_groups[(entry["locality"], entry["localSetCode"])].append(entry)
        locality_by_code[entry["localSetCode"]].add(entry["locality"])

    for (locality, code), group in sorted(source_first_groups.items()):
        source_id = stable_id("SET-SRC-SF", locality, code)
        records.append({
            "sourceRecordId": source_id,
            "sourceKind": "source-first-local-set-profile",
            "provider": "mixed-positive-evidence",
            "providerRecordKey": f"{locality}\x1f{code}",
            "retrieved": "2026-08-09",
            "raw": {
                "localCode": code,
                "localName": None,
                "locality": locality,
                "languages": sorted({entry["language"] for entry in group}),
                "scripts": sorted({entry["script"] for entry in group}),
                "printIds": sorted(entry["printId"] for entry in group),
                "providers": sorted({entry["providerId"] for entry in group}),
                "sourceUrls": sorted({entry["sourceUrl"] for entry in group}),
            },
        })

    for row in sorted(release_dates, key=lambda item: (item["setCode"], item["date"])):
        code = row["setCode"]
        field = row["field"]
        if field == "jarelease":
            locality = "JP"
            scope_basis = "provider field jarelease"
        elif field == "enrelease":
            locality = "WEST"
            scope_basis = "provider field enrelease"
        else:
            observed = locality_by_code.get(code, set())
            locality = next(iter(observed)) if len(observed) == 1 else None
            scope_basis = (
                "single frozen provider context for this raw code"
                if locality else "provider record does not identify one locality"
            )
        market_scopes = [locality] if locality else []
        if code == "BA20":
            market_scopes = ["US"]
            scope_basis = "source note says earliest US release"
        source_id = stable_id(
            "SET-SRC-BP-DATE", code, row["date"], row["page"], field)
        records.append({
            "sourceRecordId": source_id,
            "sourceKind": "release-date-record",
            "provider": "bulbapedia",
            "providerRecordKey": f"{row['page']}#{field}:{code}",
            "retrieved": "2026-07-31",
            "raw": {
                "localCode": code,
                "page": row["page"],
                "field": field,
                "date": row["date"],
                "datePrecision": "day",
                "approximate": False,
                "status": "released",
                "locality": locality,
                "languageScope": LOCALITY_LANGUAGE.get(locality),
                "marketScopes": market_scopes,
                "marketScopeBasis": scope_basis,
                "note": row.get("note"),
            },
        })

    for row in sorted(availability, key=lambda item: item["sourcePage"]):
        source_id = stable_id("SET-SRC-BP-AVAIL", row["sourcePage"])
        records.append({
            "sourceRecordId": source_id,
            "sourceKind": "edition-availability-record",
            "provider": "bulbapedia",
            "providerRecordKey": row["sourcePage"],
            "retrieved": "2026-08-09",
            "sourceUrl": row["sourceUrl"],
            "raw": {
                "localCode": row["legacySetCode"],
                "page": row["sourcePage"],
                "languages": row["languages"],
                "rarities": row["rarities"],
                "basis": row["basis"],
                "finishProfile": row["finishProfile"],
            },
        })

    records.sort(key=lambda item: item["sourceRecordId"])
    output = {
        "meta": {
            "schema": "snoredex-set-catalogue-sources",
            "schemaVersion": "0.1.0",
            "generated": date.today().isoformat(),
            "status": "authoritative immutable source-record registry; extend through reviewed passes",
            "decision": "ADR-0002 D1",
            "description": (
                "Provider records exist independently of Snorlax membership. Raw values are "
                "preserved here; mapping and disposition live in the authoritative locality graph."
            ),
            "counts": {
                "sourceRecords": len(records),
                "legacySetProfiles": len(legacy_groups),
                "sourceFirstLocalSets": len(source_first_groups),
                "releaseDateRecords": len(release_dates),
                "editionAvailabilityRecords": len(availability),
            },
        },
        "sourceRecords": records,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {OUTPUT.relative_to(ROOT)}: {len(records)} source records "
        f"({len(legacy_groups)} legacy profiles, {len(source_first_groups)} source-first, "
        f"{len(release_dates)} dates, {len(availability)} availability)"
    )


if __name__ == "__main__":
    main()

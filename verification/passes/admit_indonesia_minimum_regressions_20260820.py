#!/usr/bin/env python3
"""Admit the three Indonesian minimum regressions discovered by the #138 run.

Run 20260820T122400Z queried the publisher's Indonesian card search from an empty
staging slice and retained every returned detail. This pass promotes only the three
minimum-regression rows named by #138. Identity rests on the card-level publisher
detail; the retained Indonesian set index supplies the printed locality-bearing set
code. Finish and cross-language work equivalence remain unresolved.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from card_discovery import content_hash, parse_detail  # noqa: E402

PRINTS = ROOT / "verification" / "source_first_prints.json"
SETS = ROOT / "verification" / "set_catalogue_sources.json"
RUN_ID = "20260820T122400Z"
RUN_DIR = ROOT / "verification" / "runs" / "card-discovery" / RUN_ID

# detail id, raw code, printed ID code, number, local name, English work label
ROWS = [
    ("13757", "SV6s", "SV6s I", "136/167", "Snorlax", "Snorlax"),
    ("15784", "SV9s", "SV9s I", "109/139", "Snorlax <Hop>", "Hop's Snorlax"),
    ("9774", "SV4s", "SV4s I", "118/132", "Boneka Snorlax", "Snorlax Doll"),
]


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:12].upper()}"


def main() -> int:
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise SystemExit(f"immutable discovery run is not complete: {RUN_ID}")
    request = next(
        row for row in manifest["requests"]
        if row["sliceId"] == "pokemon-asia-id-snorlax"
    )
    if not request["checkpoint"].get("complete"):
        raise SystemExit("immutable Indonesian discovery checkpoint is incomplete")
    by_detail = {row["rawProviderId"]: row for row in request["details"]}
    set_document = json.loads(SETS.read_text(encoding="utf-8"))
    set_rows = set_document["sourceRecords"]
    indexed_codes = {
        row["raw"]["localCode"]
        for row in set_rows
        if row["sourceKind"] == "locality-set-index-record"
        and row["raw"].get("locality") == "ID"
    }
    print_document = json.loads(PRINTS.read_text(encoding="utf-8"))
    existing_prints = {}
    for row in print_document["prints"]:
        print_id = row["printId"]
        if print_id in existing_prints:
            raise SystemExit(f"duplicate source-first print: {print_id}")
        existing_prints[print_id] = row
    existing_profiles = {
        row["providerRecordKey"]
        for row in set_rows
        if row["sourceKind"] == "source-first-local-set-profile"
    }

    added_prints = 0
    added_profiles = 0
    for detail_id, raw_code, local_code, number, local_name, card_name in ROWS:
        detail = by_detail.get(detail_id)
        if detail is None:
            raise SystemExit(f"missing immutable Indonesian discovery detail {detail_id}")
        raw = (RUN_DIR / detail["rawPath"]).read_bytes()
        if content_hash(raw) != detail["responseHash"]:
            raise SystemExit(f"immutable Indonesian detail hash drift: {detail_id}")
        source = parse_detail(raw, detail_id, "pokemon-asia-html")
        expected = {
            "localName": local_name,
            "rawSetCode": raw_code,
            "localCollectorNumber": number,
        }
        if any(source.get(key) != value for key, value in expected.items()):
            raise SystemExit(f"Indonesian discovery detail drift: {detail_id}")
        if local_code not in indexed_codes:
            raise SystemExit(f"missing positive Indonesian set-index code: {local_code}")

        print_id = f"ID:{local_code}:{number}:base"
        source_url = f"https://asia.pokemon-card.com/id/card-search/detail/{detail_id}/"
        expected_print = {
            "printId": print_id,
            "locality": "ID",
            "localSetCode": local_code,
            "localNumber": number,
            "variant": "base",
            "language": "Indonesian",
            "script": "Latn",
            "name": local_name,
            "cardName": card_name,
            "catchUpOf": None,
            "specimenId": None,
            "providerId": "pokemon-card-asia",
            "sourceUrl": source_url,
            "corroborated": False,
            "markAssetUrl": source["setSymbolUrl"],
            "cardImageUrl": source["cardImageUrl"],
            "evidence": (
                f"Immutable card-discovery run {RUN_ID} retains the publisher's Indonesian "
                f"detail {detail_id}: {local_name}, collector number {number}, raw expansion "
                f"code {raw_code}, card image and set-mark asset. The independently retained "
                f"Indonesian locality set index names the physical product code {local_code}. "
                "Together they establish this Indonesian language-and-identity node under "
                "ADR-0001 D5. No finish or cross-language work equivalence is asserted. "
                "Retrieved 2026-08-20."
            ),
        }
        existing_print = existing_prints.get(print_id)
        if existing_print is None:
            print_document["prints"].append(expected_print)
            existing_prints[print_id] = expected_print
            added_prints += 1
        elif existing_print != expected_print:
            raise SystemExit(f"existing Indonesian source-first print drift: {print_id}")

        profile_key = f"ID\x1f{local_code}"
        if profile_key not in existing_profiles:
            _, _, denominator = number.partition("/")
            set_rows.append({
                "sourceRecordId": stable_id("SET-SRC-SF", "ID", local_code),
                "sourceKind": "source-first-local-set-profile",
                "provider": "mixed-positive-evidence",
                "providerRecordKey": profile_key,
                "retrieved": "2026-08-20",
                "raw": {
                    "localCode": local_code,
                    "localName": None,
                    "locality": "ID",
                    "languages": ["Indonesian"],
                    "scripts": ["Latn"],
                    "printIds": [print_id],
                    "providers": ["pokemon-card-asia"],
                    "sourceUrls": [source_url],
                    "printedSetSize": int(denominator),
                    "printedSetSizeBasis": "the denominator printed beside the observed card number",
                    "localeSuffix": "I",
                    "observedCollectorNumbers": [number],
                    "observedCoverage": "one official Indonesian Snorlax detail, not a set enumeration",
                    "markAssetUrls": [source["setSymbolUrl"]],
                    "cardImageUrls": [source["cardImageUrl"]],
                },
            })
            existing_profiles.add(profile_key)
            added_profiles += 1

    print_document["meta"]["counts"] = {
        "admitted": len(print_document["prints"]),
        "held": len(print_document.get("held", [])),
    }
    set_document["meta"]["counts"]["sourceRecords"] = len(set_rows)
    set_document["meta"]["counts"]["sourceFirstLocalSets"] = sum(
        row["sourceKind"] == "source-first-local-set-profile" for row in set_rows
    )
    PRINTS.write_text(json.dumps(print_document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SETS.write_text(json.dumps(set_document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"admitted {added_prints} Indonesian print(s), added {added_profiles} local-set profile(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

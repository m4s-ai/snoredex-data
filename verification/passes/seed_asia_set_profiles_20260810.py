#!/usr/bin/env python3
"""Give the Thai and Indonesian catch-up codes their set-source records (ADR-0002, #138).

`N8` requires the independent set registry to account for every source-first local set exactly
once: each `(locality, localSetCode)` in `source_first_prints.json` needs a
`source-first-local-set-profile` row in `set_catalogue_sources.json`. Admitting the Thai and
Indonesian catch-up prints introduced fifteen new pairs, so this adds their rows.

It is deliberately additive rather than a rerun of `seed_set_catalogue_sources_20260809.py`. That
pass rebuilds every record with its own retrieval date; re-running it would restamp 187 rows that
did not change, which is exactly the kind of churn an immutable source registry exists to prevent.
The id scheme and record shape are copied from it so the two agree.

    python verification/passes/seed_asia_set_profiles_20260810.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
PRINTS = ROOT / "verification" / "source_first_prints.json"
SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
RETRIEVED = "2026-08-10"


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:12].upper()}"


def main() -> int:
    prints = json.loads(PRINTS.read_text(encoding="utf-8"))["prints"]
    document = json.loads(SOURCES.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = document["sourceRecords"]

    existing = {
        row["providerRecordKey"]
        for row in records
        if row["sourceKind"] == "source-first-local-set-profile"
    }

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for entry in prints:
        groups[(entry["locality"], entry["localSetCode"])].append(entry)

    added = 0
    for (locality, code), group in sorted(groups.items()):
        key = f"{locality}\x1f{code}"
        if key in existing:
            continue
        records.append({
            "sourceRecordId": stable_id("SET-SRC-SF", locality, code),
            "sourceKind": "source-first-local-set-profile",
            "provider": "mixed-positive-evidence",
            "providerRecordKey": key,
            "retrieved": RETRIEVED,
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
        added += 1

    records.sort(key=lambda item: item["sourceRecordId"])
    document["meta"]["counts"]["sourceRecords"] = len(records)
    document["meta"]["counts"]["sourceFirstLocalSets"] = sum(
        1 for row in records if row["sourceKind"] == "source-first-local-set-profile"
    )
    SOURCES.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")

    print(f"added {added} source-first local-set profile(s); "
          f"{document['meta']['counts']['sourceFirstLocalSets']} total, "
          f"{len(records)} source records")
    if added == 0:
        print("  nothing to do — every source-first local set already has a record")
    return 0


if __name__ == "__main__":
    sys.exit(main())

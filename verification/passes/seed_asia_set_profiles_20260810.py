#!/usr/bin/env python3
"""Give the Thai and Indonesian catch-up codes their set-source records (ADR-0002, #138).

`N8` requires the independent set registry to account for every source-first local set exactly
once: each `(locality, localSetCode)` in `source_first_prints.json` needs a
`source-first-local-set-profile` row in `set_catalogue_sources.json`. Admitting the Thai and
Indonesian catch-up prints introduced sixteen new pairs, so this adds their rows.

IT ALSO RECORDS WHAT THE SCRAPE ALREADY KNEW

The first version stored only the identifiers and the URLs it came from, which left the set database
unable to answer anything the next person would have to re-scrape for. Three facts were sitting in
the harvested data and are now written down:

* **`printedSetSize`** — the denominator every card prints beside its collector number: `sc1b T` is
  `/153`, `scD T` is `/159`. This is exactly the field `evidence_semantics.py` reports
  `needs-set-size` for, filed as a #146 requirement on 2026-08-10, so recording it here is the first
  instalment rather than a nicety. It is asserted only when every observed card of the set agrees on
  the denominator; a disagreement stores `null` and the observed values.
* **`localeSuffix`** — the letter the set-mark badge carries: `T` for Thai, `I` for Indonesian, and
  `null` for the Sun & Moon-era codes that carry none. This is the rule that made every filename-
  derived code wrong before the badges were read.
* **`markAssetUrls`** and **`observedCollectorNumbers`** — the images the codes were read off, and
  which cards of the set have actually been seen, so coverage is visible rather than assumed.

None of this is a claim that a set is fully enumerated. `observedCollectorNumbers` is what a Snorlax
search returned, and the record says so.

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

# The badge suffix per locality, read off the rendered set-mark assets. Sun & Moon-era codes carry
# none — there the `A` prefix is the locale marker instead.
LOCALE_SUFFIX = {"TH": "T", "ID": "I", "TW": "F"}


def profile_facts(group: list[dict[str, Any]], locality: str,
                  set_code: str) -> dict[str, Any]:
    """Everything the harvest already knew, so nobody has to fetch it twice."""
    numbers, denominators = [], set()
    for entry in group:
        raw = str(entry.get("localNumber") or "")
        head, _, tail = raw.partition("/")
        numbers.append(raw)
        if tail.isdigit():
            denominators.add(int(tail))
    suffix = LOCALE_SUFFIX.get(locality)
    if suffix and not set_code.endswith(f" {suffix}"):
        suffix = None
    return {
        # Asserted only when every observed card agrees. One disagreement means the denominator is
        # not a property of the set as observed, and guessing which value wins is how a set size
        # becomes fiction.
        "printedSetSize": next(iter(denominators)) if len(denominators) == 1 else None,
        "printedSetSizeBasis": (
            "the denominator printed beside the collector number on every observed card"
            if len(denominators) == 1
            else f"observed denominators disagree: {sorted(denominators)}"
        ),
        "localeSuffix": suffix,
        "observedCollectorNumbers": sorted(numbers),
        "observedCoverage": "cards returned by a Snorlax search, not an enumeration of the set",
        "markAssetUrls": sorted(
            {entry["markAssetUrl"] for entry in group if entry.get("markAssetUrl")}),
        "cardImageUrls": sorted(
            {entry["cardImageUrl"] for entry in group if entry.get("cardImageUrl")}),
    }


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
                **profile_facts(group, locality, code),
            },
        })
        added += 1

    # Existing rows predate the facts above; fill them in without touching identity or provenance.
    by_key = {row["providerRecordKey"]: row for row in records
              if row["sourceKind"] == "source-first-local-set-profile"}
    enriched = 0
    for (locality, code), group in sorted(groups.items()):
        row = by_key.get(f"{locality}\x1f{code}")
        if row is None or "markAssetUrls" in row["raw"]:
            continue
        row["raw"].update(profile_facts(group, locality, code))
        enriched += 1

    records.sort(key=lambda item: item["sourceRecordId"])
    document["meta"]["counts"]["sourceRecords"] = len(records)
    document["meta"]["counts"]["sourceFirstLocalSets"] = sum(
        1 for row in records if row["sourceKind"] == "source-first-local-set-profile"
    )
    SOURCES.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")

    sized = sum(
        1 for row in records
        if row["sourceKind"] == "source-first-local-set-profile"
        and row["raw"].get("printedSetSize") is not None
    )
    print(f"added {added} source-first local-set profile(s), enriched {enriched}; "
          f"{sized} now carry a printed set size")
    print(f"total: "
          f"{document['meta']['counts']['sourceFirstLocalSets']} total, "
          f"{len(records)} source records")
    if added == 0:
        print("  nothing to do — every source-first local set already has a record")
    return 0


if __name__ == "__main__":
    sys.exit(main())

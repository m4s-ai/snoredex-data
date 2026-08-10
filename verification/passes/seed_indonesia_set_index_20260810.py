#!/usr/bin/env python3
"""Record Indonesia's whole published product list, and what of it has been examined (#138).

The owner asked what is still missing on the Indonesian side, and the honest answer needed a
denominator this project did not have. `Pokémon in Indonesia` publishes one: 78 products across
booster packs and starter decks, each with its Indonesian name, its series, its set-mark code and a
release date. Ninety-one codes in total, because a product often ships as a paired `a`/`b` or
`D`-suffixed release under two marks.

Against that list, the publisher's Asia card database returned a Snorlax for **21** codes. The
other **70 have never been examined** — and the distinction this record exists to preserve is that
"not examined" is not "no Snorlax". Rule 3 applies with full force: a keyword search that returned
nothing for `S11 I` has a gap, not a proof, and nothing here may be read as an absence.

WHY THE INDEX BELONGS IN THE SET DATABASE

Because the alternative is doing this again. Everything below was scraped once; storing only the
answers and not the catalogue would leave the next question — "what about `SV1a I`?" — needing a
fresh fetch, a wiki-table parse and a locale-code reconciliation. The set database now answers it.

WHAT EACH RECORD CARRIES

`localCode` per mark, with `pairedCodes` naming the sibling half when a product ships as two, the
product's English and Indonesian names, its series, its release date, and `snorlaxExaminationState`:

* `examined-snorlax-found` — the Asia database returned a Snorlax and the print is recorded;
* `not-examined` — no query has been run against this code, or a Snorlax keyword search returned
  nothing, which are deliberately the same state because this source cannot tell them apart.

TWO LIMITS THIS INDEX HAS, STATED RATHER THAN DISCOVERED LATER

**Promotional cards are not in it.** The article's `Promotional cards` subsection is prose, not a
table with mark codes, so the 78 products indexed here are boosters and starter decks only. The
Asia database returned four Indonesian `S-P` promo Snorlax cards (`030`, `052`, `100`, `356`) that
consequently match no indexed code. They are not lost — they are outside this index's scope, and
that scope is stated so nobody reads the index as the whole Indonesian catalogue.

**`examined-snorlax-found` says a Snorlax is known, not how well.** Seven codes reach that state
through a confirmed language unit rather than a source-first print, and two of those units —
`S10a I` and `S5a I` — are themselves on #137's set-level queue: the claim is confirmed, the
evidence is about the set. `snorlaxUnitIds` is stored so a consumer can look the granularity up in
`evidence_semantics.json` rather than inferring card-level evidence from this field.

The `AC3a` case is why the owner asked. It is Indonesian-only — Thailand's table has no counterpart
— and it does carry a Snorlax, `145/205`, now admitted as `ID:AC3a:145/205:base`. Its sibling
`AC3b` sits in `not-examined`, which is exactly the shape of the remaining work.

    python verification/passes/seed_indonesia_set_index_20260810.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT = ROOT / "verification" / ".id_catalogue_input.json"
PRINTS = ROOT / "verification" / "source_first_prints.json"
UNITS = ROOT / "verification" / "units.json"
SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
ARTICLE = "https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_in_Indonesia"
RETRIEVED = "2026-08-10"


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:12].upper()}"


def match_key(code: str) -> str:
    """Compare codes across sources that write the locale suffix differently.

    The article writes `SC1a I`; the set-mark badge renders `sc1a I`; a mark asset filename says
    `S_mark_Indonesia_SC1a`. Case and spacing vary, the suffix is sometimes absent from a filename,
    and none of that is a difference in the set.
    """
    return re.sub(r"\s+", "", re.sub(r"\s+I$", "", code.strip())).lower()


def main() -> int:
    rows: list[dict[str, Any]] = json.loads(INPUT.read_text(encoding="utf-8"))
    prints = json.loads(PRINTS.read_text(encoding="utf-8"))["prints"]
    document = json.loads(SOURCES.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = document["sourceRecords"]

    # Two ways an Indonesian code can already be examined, and both count. A catch-up code carries
    # its own source-first print; an ordinary localized edition of a Japanese set carries a
    # confirmed unit under the Japanese set code instead — `S8b I` against `s8b`. Counting only the
    # first would put eleven examined sets back on the queue and invent work that is already done.
    examined: dict[str, list[str]] = {}
    for entry in prints:
        if entry["locality"] != "ID":
            continue
        examined.setdefault(match_key(entry["localSetCode"]), []).append(entry["printId"])
    unit_evidence: dict[str, list[str]] = {}
    for unit in json.loads(UNITS.read_text(encoding="utf-8")):
        if unit["language"] != "Indonesian" or unit["status"] != "confirmed":
            continue
        unit_evidence.setdefault(match_key(unit["setCode"]), []).append(unit["unitId"])

    existing = {
        row["providerRecordKey"] for row in records
        if row["sourceKind"] == "locality-set-index-record"
    }

    added = 0
    for row in rows:
        codes = [c.strip() for c in re.split(r"\s*/\s*", row["markField"]) if c.strip()]
        for code in codes:
            key = f"ID\x1f{code}"
            if key in existing:
                continue
            found = examined.get(match_key(code), [])
            units_found = unit_evidence.get(match_key(code), [])
            records.append({
                "sourceRecordId": stable_id("SET-SRC-IDX", "ID", code),
                "sourceKind": "locality-set-index-record",
                "provider": "bulbapedia",
                "providerRecordKey": key,
                "retrieved": RETRIEVED,
                "sourceUrl": ARTICLE,
                "raw": {
                    "locality": "ID",
                    "localCode": code,
                    "pairedCodes": [c for c in codes if c != code],
                    "productKind": row["kind"],
                    "englishName": row["englishName"],
                    "indonesianName": row["indonesianName"],
                    "series": row["series"],
                    "releaseDate": row["releaseDate"],
                    "snorlaxExaminationState": (
                        "examined-snorlax-found" if (found or units_found) else "not-examined"),
                    "snorlaxPrintIds": sorted(found),
                    "snorlaxUnitIds": sorted(units_found),
                    "examinationBasis": (
                        "a source-first print is admitted for this code"
                        if found else
                        "a confirmed Indonesian language unit exists for the Japanese set this "
                        "code localizes; the Snorlax is recorded there rather than as a "
                        "source-first print"
                        if units_found else
                        "no Snorlax has been established for this code. This source cannot "
                        "distinguish a set with no Snorlax from a set it does not index, so the "
                        "state is 'not examined' and never an absence — rule 3."
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

    index_rows = [r for r in records if r["sourceKind"] == "locality-set-index-record"]
    found_n = sum(1 for r in index_rows
                  if r["raw"]["snorlaxExaminationState"] == "examined-snorlax-found")
    via_print = sum(1 for r in index_rows if r["raw"]["snorlaxPrintIds"])
    via_unit = sum(1 for r in index_rows
                   if r["raw"]["snorlaxUnitIds"] and not r["raw"]["snorlaxPrintIds"])
    print(f"added {added} locality set-index record(s) from {len(rows)} published products")
    print(f"  {len(index_rows)} Indonesian codes indexed: "
          f"{found_n} examined with a Snorlax found ({via_print} via a source-first print, "
          f"{via_unit} via a confirmed unit), {len(index_rows) - found_n} not examined")
    print("  'not examined' is not an absence: this source cannot tell a set with no Snorlax "
          "from a set it does not index")
    return 0


if __name__ == "__main__":
    sys.exit(main())

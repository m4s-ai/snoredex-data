#!/usr/bin/env python3
"""Regenerate the language-verification exports and report coverage (#50, Wave 2).

Ported from `report.ps1`. Projects `units.json` into the three exports readers actually consume —
what is confirmed, what an outside source contradicts, and what is still open — then prints where
the verification stands.

    python verification/report.py

Run it after any write pass. The exports are committed, so a run that changes nothing should
leave `git status` clean; if it does not, the store moved and the diff is the news.

One deliberate difference from the PowerShell. Its two diagnostic tables were rendered with
`Format-Table`, which emits nothing at all when output is not a terminal — so in every redirected
run, every CI log and every captured session, the "CONTRADICTED (highlight)" and "open units by
language" headings were followed by blank lines. The tables are printed here unconditionally.
This script is not part of the release gate, so the only readers affected are people running it
by hand, who saw the tables at an interactive console and now see them everywhere.
"""

from __future__ import annotations

import json
import sys
from collections import Counter

from checks import VERIFICATION, format_table, read_json, write_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RESOLVED = ("confirmed", "contradicted")
SETTLED = ("confirmed", "contradicted", "needs-manual-review")

CONFIRMED_FIELDS = ["unitId", "cardName", "setCode", "setName", "number", "variant", "language",
                    "sourceType", "sourceUrl", "evidence", "checkedAt"]
CONTRADICTED_FIELDS = ["unitId", "cardName", "setCode", "setName", "number", "variant", "language",
                       "sourceType", "sourceUrl", "evidence", "cmUrl"]
OPEN_FIELDS = ["card", "setName", "variant", "market", "rarity", "cmUrl", "image",
               "openLanguages", "confirmedLanguages"]


def project(units: list[dict], fields: list[str]) -> list[dict]:
    """`Select-Object`: named properties in order, absent ones as null."""
    return [{field: unit.get(field) for field in fields} for unit in units]


def write_or_check(outputs: dict) -> None:
    if "--check" in sys.argv:
        stale = [
            path.name
            for path, payload in outputs.items()
            if not path.exists()
            or path.read_text(encoding="utf-8")
            != json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        ]
        if stale:
            raise ValueError(f"stale: {', '.join(stale)}")
        print("language-verification exports are current")
        return
    for path, payload in outputs.items():
        write_json(path, payload)


def main() -> int:
    units = read_json(VERIFICATION / "units.json")

    confirmed = [u for u in units if u.get("status") == "confirmed"]
    contradicted = [u for u in units if u.get("status") == "contradicted"]
    manual = [u for u in units if u.get("status") == "needs-manual-review"]
    unresolved = [u for u in units if u.get("status") not in SETTLED]

    confirmed_rows = project(confirmed, CONFIRMED_FIELDS)
    contradicted_rows = project(contradicted, CONTRADICTED_FIELDS)

    # OPEN: still no external source either way. Grouped by card-variant, because a reader decides
    # per card, not per language. Group-Object orders groups by name; the later sort is stable, so
    # cards with equally many open languages keep that order.
    groups: dict[str, list[dict]] = {}
    for unit in unresolved:
        key = f"{unit.get('cardName')}|{unit.get('setCode')} {unit.get('number')}|{unit.get('variant')}"
        groups.setdefault(key, []).append(unit)

    # Case-insensitively, because PowerShell's Group-Object and Sort-Object compare that way:
    # "sA 10" sorts before "WCD23", which a codepoint sort gets backwards and which shows up as
    # reordered entries in the committed export.
    open_rows = []
    for key in sorted(groups, key=str.casefold):
        members = groups[key]
        first = members[0]
        open_rows.append({
            "card": f"{first.get('cardName')} ({first.get('setCode')} {first.get('number')})",
            "setName": first.get("setName"),
            "variant": first.get("variant"),
            "market": first.get("market"),
            "rarity": first.get("rarity"),
            "cmUrl": first.get("cmUrl"),
            "image": first.get("image"),
            "openLanguages": sorted(m.get("language") for m in members),
            "confirmedLanguages": sorted(
                u.get("language") for u in units
                if u.get("setCode") == first.get("setCode")
                and u.get("number") == first.get("number")
                and u.get("variant") == first.get("variant")
                and u.get("status") == "confirmed"),
        })
    open_rows.sort(key=lambda row: len(row["openLanguages"]), reverse=True)
    outputs = {
        VERIFICATION / "confirmed_sources.json": confirmed_rows,
        VERIFICATION / "CONTRADICTED.json": contradicted_rows,
        VERIFICATION / "UNCONFIRMED.json": open_rows,
    }
    write_or_check(outputs)

    fully_resolved = 0
    card_variants: dict[str, list[dict]] = {}
    for unit in units:
        key = f"{unit.get('setCode')}|{unit.get('number')}|{unit.get('variant')}"
        card_variants.setdefault(key, []).append(unit)
    for members in card_variants.values():
        if all(m.get("status") in RESOLVED for m in members):
            fully_resolved += 1

    resolvable = len(units) - len(manual)
    print("=== COVERAGE ===")
    print(f"total units          : {len(units)}")
    print(f"confirmed            : {len(confirmed)}  "
          f"({100 * len(confirmed) / len(units):,.1f}% of all, "
          f"{100 * len(confirmed) / resolvable:,.1f}% of resolvable)")
    print(f"contradicted         : {len(contradicted)}   "
          "<- Cardmarket claims it, external source says no")
    print(f"needs manual review  : {len(manual)}   "
          "<- structurally undocumentable, see MANUAL_REVIEW.csv")
    print(f"still open           : {len(unresolved)}")
    print(f"card-variants fully resolved: {fully_resolved} / {len(card_variants)}")
    print()
    print("=== CONTRADICTED (highlight) ===")
    for line in format_table([{
        "card": f"{u.get('cardName')} ({u.get('setCode')} {u.get('number')}) {u.get('variant')}",
        "language": u.get("language"),
        "why": u.get("evidence"),
    } for u in contradicted]):
        print(line)
    print("=== open units by language ===")
    counts = Counter(u.get("language") for u in unresolved)
    for line in format_table(
            [{"Count": count, "Name": name}
             for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))],
            ["Count", "Name"]):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""(Re)tag the units no card database can ever evidence (#50, Wave 2).

Ported from `classify_manual.ps1`. Some units are structurally undocumentable: Cardmarket's
"Additionals" groupings are not publisher products and appear in no card database, and Play!
Pokemon Prize Packs are documented as products while no source records which languages were
distributed. They stay in the dataset but leave the "open" pool, so the open count reflects real
remaining work rather than work nobody can do.

    python verification/classify_manual.py

Writes `units.json`, `MANUAL_REVIEW.json` and `MANUAL_REVIEW.csv`.

**This script is not idempotent, and the port keeps it that way.** It skips only `confirmed` and
`contradicted`, so a unit already sitting in `needs-manual-review` is matched again and re-stamped
with a fresh `checkedAt` — rewriting `units.json` on every run even when nothing has changed. That
behaviour predates the port; reproducing it is deliberate, so that this commit is a translation
and not a translation plus a silent fix. Making it idempotent is #29, and belongs in its own diff.
"""

from __future__ import annotations

import csv
import io
import re
import sys
from collections import Counter
from datetime import datetime

from checks import VERIFICATION, format_table, read_json, write_json

RESOLVED = ("confirmed", "contradicted")

CSV_FIELDS = ["unitId", "cardName", "setCode", "number", "variant", "language", "setName",
              "rarity", "cmUrl", "manualReason", "verdict", "yourSource"]

# Case-sensitive, deliberately. PowerShell's -match is case-insensitive, so an earlier pass using
# it matched '^x' against XY-P, XY2, XY10 and XYPR too, parking twelve ordinary units in manual
# review where every later evidence pass then skipped them. The original used -cmatch after that
# was found; `re.match` is case-sensitive by default, which is the same contract.
ADDITIONALS = re.compile(r"^x")
PRIZE_PACK = re.compile(r"^PPS\d")

ADDITIONALS_REASON = ('Cardmarket "Additionals" grouping - not a publisher product, absent from '
                      "every card database")
PRIZE_PACK_REASON = ("Play! Pokemon Prize Pack - the card is documented, but no source records "
                     "distribution languages")


def reason_for(unit: dict) -> str | None:
    set_code = str(unit.get("setCode") or "")
    if ADDITIONALS.match(set_code):
        return ADDITIONALS_REASON
    if PRIZE_PACK.match(set_code):
        return PRIZE_PACK_REASON
    return None


def write_csv(path, rows: list[dict]) -> None:
    """`Export-Csv -NoTypeInformation -Encoding utf8NoBOM`: every field quoted, LF line endings."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, quoting=csv.QUOTE_ALL,
                            lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: "" if row.get(field) is None else row.get(field)
                         for field in CSV_FIELDS})
    path.write_text(buffer.getvalue(), encoding="utf-8")


def main() -> int:
    units = read_json(VERIFICATION / "units.json")

    moved = 0
    for unit in units:
        if unit.get("status") in RESOLVED:
            continue
        reason = reason_for(unit)
        if not reason:
            continue
        # English prize-pack units are already confirmed; only the undocumented languages land here
        unit["status"] = "needs-manual-review"
        unit["manualReason"] = reason
        unit["checkedAt"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        moved += 1
    write_json(VERIFICATION / "units.json", units)

    manual = [u for u in units if u.get("status") == "needs-manual-review"]

    # grouped, decision-ready export
    groups: dict[str, list[dict]] = {}
    for unit in manual:
        key = f"{unit.get('cardName')}|{unit.get('setCode')} {unit.get('number')}|{unit.get('variant')}"
        groups.setdefault(key, []).append(unit)

    rows = []
    for key in sorted(groups, key=str.casefold):
        members = groups[key]
        first = members[0]
        rows.append({
            "card": f"{first.get('cardName')} ({first.get('setCode')} {first.get('number')})",
            "variant": first.get("variant"),
            "setName": first.get("setName"),
            "rarity": first.get("rarity"),
            "languagesToDecide": sorted(m.get("language") for m in members),
            "alreadyConfirmed": sorted(
                u.get("language") for u in units
                if u.get("setCode") == first.get("setCode")
                and u.get("number") == first.get("number")
                and u.get("variant") == first.get("variant")
                and u.get("status") == "confirmed"),
            "reason": first.get("manualReason"),
            "cardmarketUrl": first.get("cmUrl"),
            "image": first.get("image"),
            "verdict": "",      # <- fill in: confirmed | false
            "yourSource": "",   # <- fill in
        })
    rows.sort(key=lambda row: str(row["card"]).casefold())
    write_json(VERIFICATION / "MANUAL_REVIEW.json", rows)

    # flat CSV for quick editing
    write_csv(VERIFICATION / "MANUAL_REVIEW.csv",
              [{**unit, "verdict": "", "yourSource": ""} for unit in manual])

    print(f"moved to manual review: {moved} units, {len(rows)} card-variants")
    # Printed unconditionally. The PowerShell used Format-Table, which renders nothing when output
    # is not a terminal, so these two summaries were blank in every redirected run.
    statuses = Counter(u.get("status") for u in units)
    for line in format_table(
            [{"Count": count, "Name": name}
             for name, count in sorted(statuses.items(), key=lambda item: (-item[1], item[0]))],
            ["Count", "Name"]):
        print(line)
    reasons = Counter(u.get("manualReason") for u in manual)
    for line in format_table([{"Count": count, "Name": name} for name, count in reasons.items()],
                             ["Count", "Name"]):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

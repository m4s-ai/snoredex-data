#!/usr/bin/env python3
"""Independent database review harness.

Complements `verification/review_integrity.ps1`. That script validates invariants
*within* each store; this one validates consistency *between* the state stores and
the derived artifacts that consumers and the future public site actually read.

Every check corresponds to a finding in `verification/REVIEW-2026-07-25.md`. Run it
after any write pass, and re-run it to confirm a fix:

    python verification/review_findings.py

Exit code 0 when no FAIL-severity check fires, 1 otherwise. Checks marked INFO
report drift without failing, so legitimate progress does not turn the suite red.

Runs on Python 3.9+ with no third-party dependencies and no network access.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

FINISHES = ("non-holo", "holo", "reverse-holo", "mirror-holo")
STRENGTH = {"pending": 0, "marketplace-claimed": 1, "owner-attested": 2, "confirmed": 3}

results: list[tuple[str, str, str, bool, str]] = []


def load(rel: str) -> Any:
    with open(ROOT / rel, encoding="utf-8") as handle:
        return json.load(handle)


def check(check_id: str, title: str, severity: str, ok: bool, detail: str = "") -> None:
    results.append((check_id, title, severity, ok, detail))


def norm_number(value: Any) -> str:
    """Canonical collector number. Unnumbered cards are null in some stores and "" in others."""
    return str(value or "")


# --------------------------------------------------------------------------- #
# Load stores and derived artifacts
# --------------------------------------------------------------------------- #

units = load("verification/units.json")
finish_doc = load("verification/finish_units.json")
finish_units = finish_doc["units"]
dataset = load("snorlax_cards.json")
cards = dataset["cards"]
releases = load("analysis_confirmed_releases.json")["variants"]
finish_analysis = load("analysis_finishes.json")

finish_by_id = {unit["finishUnitId"]: unit for unit in finish_units}
finish_by_key = {
    (unit["setCode"], norm_number(unit["number"]), unit["language"]): unit
    for unit in finish_units
}


# --------------------------------------------------------------------------- #
# F1 — confirmed printings must stay reachable from a product view
# --------------------------------------------------------------------------- #

reachable_printings = {
    printing["printingId"]
    for card in cards
    for row in (card.get("finishAvailability") or {}).get("byLanguage", [])
    for printing in row.get("printings", [])
}
confirmed_printings = {
    printing["printingId"]: (unit["setCode"], norm_number(unit["number"]), unit["language"],
                             printing["finish"])
    for unit in finish_units
    for printing in unit["printings"]
    if printing["verificationStatus"] == "confirmed"
}
unreachable = sorted(set(confirmed_printings) - reachable_printings)
check(
    "F1.1",
    "Every externally confirmed printing is reachable from at least one product view",
    "FAIL",
    not unreachable,
    f"{len(unreachable)} confirmed printings appear in no card view, no chronological row, and no "
    f"generated page. e.g. "
    f"{', '.join(f'{pid} {confirmed_printings[pid]}' for pid in unreachable[:3])}",
)

# The projected per-product view may hold less evidence than the store only where it says so.
# "unmapped" and "other-product" are the two legitimate reasons; anything else is silent loss.
projection_gaps: list[tuple[str, ...]] = []
for card in cards:
    for row in (card.get("finishAvailability") or {}).get("byLanguage", []):
        unit = finish_by_id.get(row.get("finishUnitId"))
        if unit is None:
            continue
        if row.get("unitFinishStatus") != unit["finishStatus"]:
            projection_gaps.append(
                (card["setCode"], norm_number(card.get("number")),
                 str(card.get("variantToken")), row["language"],
                 str(row.get("unitFinishStatus")), str(unit["finishStatus"]))
            )
check(
    "F1.2",
    "Projected rows carry unit-level finish status verbatim, so projection loses no evidence",
    "FAIL",
    not projection_gaps,
    f"{len(projection_gaps)} projected rows do not reproduce the store's finishStatus. Product "
    f"attribution is necessarily weaker than unit knowledge, so the unit view must travel with it. "
    f"e.g. {projection_gaps[:2]}",
)

blind_cells = []
for row in releases:
    for cell in row.get("finishByLanguage") or []:
        unit = finish_by_key.get(
            (row["setCode"], norm_number(row.get("number")), cell.get("language"))
        )
        if unit is None or not unit["availableFinishes"]:
            continue
        if not cell.get("availableFinishes") and not cell.get("unitAvailableFinishes"):
            blind_cells.append(
                (row["setCode"], norm_number(row.get("number")), row["variant"],
                 cell["language"], unit["availableFinishes"])
            )
check(
    "F1.3",
    "Published table never renders a blind cell where the store holds evidence",
    "FAIL",
    not blind_cells,
    f"{len(blind_cells)} published cells expose neither product-attributed nor unit-level finishes "
    f"while finish_units.json holds positive evidence. e.g. {blind_cells[:3]}",
)


# --------------------------------------------------------------------------- #
# F2 — `pending` must not conflate "no evidence" with "not attributable"
# --------------------------------------------------------------------------- #

missing_marker = [
    card["setCode"]
    for card in cards
    for row in (card.get("finishAvailability") or {}).get("byLanguage", [])
    if "productMappingStatus" not in row
]
check(
    "F2.1",
    "Projected finish rows carry productMappingStatus so `pending` is unambiguous",
    "FAIL",
    not missing_marker,
    f"{len(missing_marker)} projected rows omit productMappingStatus. A consumer cannot distinguish "
    f"'no finish evidence exists' from 'evidence exists but is not attributable to this product', "
    f"though README directs consumers to use this view.",
)


# --------------------------------------------------------------------------- #
# F3 — public prose must match generated facts
# --------------------------------------------------------------------------- #

readme = (ROOT / "README.md").read_text(encoding="utf-8")
counts = finish_analysis["counts"]
prose_errors = []
for label, key in (
    ("Non-holo", "withNonHolo"),
    ("Holo", "withHolo"),
    ("Reverse holo", "withReverseHolo"),
    ("Mirror holo", "withMirrorHolo"),
    ("Both non-holo and holo", "withBothNonHoloAndHolo"),
):
    for line in readme.splitlines():
        if line.startswith(f"| {label} |"):
            stated = line.rstrip("| ").split("|")[-1].strip()
            if stated != str(counts[key]):
                prose_errors.append(f"README '{label}' says {stated}, generated data says {counts[key]}")
check(
    "F3.1",
    "README finish table matches analysis_finishes.json",
    "FAIL",
    not prose_errors,
    "; ".join(prose_errors),
)

jtg_english = finish_by_key.get(("JTG", "117", "English"))
jtg_finishes = sorted(jtg_english["availableFinishes"]) if jtg_english else []
jtg_prose_wrong = "JTG 117` now explicitly\nshows non-holo, holo," in readme or (
    "shows non-holo, holo, and intricate-tile reverse-holo" in readme.replace("\n", " ")
)
check(
    "F3.2",
    "README describes regular JTG 117 as holo + reverse holo only",
    "FAIL",
    not jtg_prose_wrong,
    f"README describes regular JTG 117 as non-holo + holo + reverse holo; the verified model and "
    f"review_integrity.ps1 check 'regular JTG 117 discloses holo + reverse only' both say "
    f"{jtg_finishes}. The non-holo printing belongs to the Prize Pack product, not the regular card.",
)


# --------------------------------------------------------------------------- #
# F4 — refuted language claims must be marked in the main dataset
# --------------------------------------------------------------------------- #

contradicted: dict[tuple[str, str, str], set[str]] = {}
for unit in units:
    if unit["status"] == "contradicted":
        key = (unit["setCode"], norm_number(unit["number"]), unit["variant"])
        contradicted.setdefault(key, set()).add(unit["language"])

unflagged = []
for card in cards:
    if card.get("isCodeCard"):
        continue
    key = (card["setCode"], norm_number(card.get("number")), card.get("variantToken") or "base")
    refuted = contradicted.get(key, set()) & set(card.get("languages") or [])
    if refuted and not (set(card.keys()) & {"languagesContradicted", "languagesConfirmed"}):
        unflagged.append((card["setCode"], norm_number(card.get("number")), sorted(refuted)))
check(
    "F4.1",
    "Cards carrying refuted language claims expose a confirmed/contradicted breakdown",
    "FAIL",
    not unflagged,
    f"{len(unflagged)} of {sum(1 for c in cards if not c.get('isCodeCard'))} non-code-card products "
    f"still list languages this project has itself refuted, with no field separating confirmed from "
    f"contradicted. e.g. {unflagged[:4]}",
)


# --------------------------------------------------------------------------- #
# F5/F6/F7 — canonical identity and typed fields
# --------------------------------------------------------------------------- #

release_keys = [
    (row["setCode"], norm_number(row.get("number")), row["variant"], row.get("edition"))
    for row in releases
]
duplicate_keys = [key for key, count in Counter(release_keys).items() if count > 1]
has_stable_id = all(row.get("rowId") for row in releases)
check(
    "F5.1",
    "Every chronological row carries a stable identity independent of sort order",
    "FAIL",
    has_stable_id,
    f"No row in analysis_confirmed_releases.json has a rowId; correction links embed the generated "
    f"row number instead, so sorting or filtering (#10) would retarget them. The natural key "
    f"(setCode, number, variant, edition) is already unique across all {len(releases)} rows "
    f"({len(duplicate_keys)} collisions), so a stable ID is derivable today.",
)

null_number_stores = []
for label, rows, field in (
    ("snorlax_cards.json", cards, "number"),
    ("verification/units.json", units, "number"),
    ("verification/finish_units.json", finish_units, "number"),
):
    kinds = {repr(row.get(field)) for row in rows if not row.get(field)}
    if kinds:
        null_number_stores.append(f"{label}={sorted(kinds)}")
check(
    "F6.1",
    "Unnumbered cards use one canonical representation across every store",
    "FAIL",
    len({s.split("=")[1] for s in null_number_stores}) <= 1,
    f"Unnumbered products are represented inconsistently: {'; '.join(null_number_stores)}. "
    f"Consumers must coerce with `str(x or '')` before any join, and a null number cannot take part "
    f"in a stable checklist ID (#8) or natural-number sort (#10).",
)


def precision(value: Any) -> str:
    """Classify by validating, not by measuring length: "2025-26" is a year range, not a month."""
    text = str(value)
    if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", text):
        return "day"
    if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", text):
        return "month"
    return "year"


# The defect was one boolean carrying two independent facts: how precise the value is, and
# whether it is trusted at that precision. The fix is that precision is *derived*, so it can
# never contradict the value it describes, and confidence stands alone.
precision_conflicts = [
    (row["setCode"], norm_number(row.get("number")), row["date"], row.get("datePrecision"))
    for row in releases
    if row.get("datePrecision") != precision(row.get("date"))
]
missing_confidence = [
    row["setCode"] for row in releases if not isinstance(row.get("dateApproximate"), bool)
]
check(
    "F7.1",
    "Date precision is derived from the value, and confidence is a separate field",
    "FAIL",
    not precision_conflicts and not missing_confidence,
    f"{len(precision_conflicts)} rows carry a datePrecision that contradicts their date value; "
    f"{len(missing_confidence)} rows lack a boolean dateApproximate. e.g. {precision_conflicts[:3]}",
)

bad_sort = [
    (row["setCode"], row.get("date"), row.get("dateSort"))
    for row in releases
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row.get("dateSort") or ""))
]
check(
    "F7.3",
    "Every normalized sort date is a valid full ISO date",
    "FAIL",
    not bad_sort,
    f"{len(bad_sort)} rows have a malformed dateSort. e.g. {bad_sort[:4]}",
)

has_sort_key = all(row.get("dateSort") for row in releases)
check(
    "F7.2",
    "Rows expose a normalized sortable date alongside the display date",
    "FAIL",
    has_sort_key,
    f"`date` mixes YYYY, YYYY-MM and YYYY-MM-DD in one string field "
    f"({dict(Counter(precision(r.get('date')) for r in releases))}). #10 requires typed release "
    f"sorting that retains approximate-date display; no normalized sort key exists.",
)


# --------------------------------------------------------------------------- #
# Regression guards for invariants that currently hold — keep them holding
# --------------------------------------------------------------------------- #

check(
    "R1",
    "finishUnitId, unitId and printingId are unique",
    "FAIL",
    len({u["unitId"] for u in units}) == len(units)
    and len(finish_by_id) == len(finish_units)
    and len({p["printingId"] for u in finish_units for p in u["printings"]})
    == sum(len(u["printings"]) for u in finish_units),
    "",
)

check(
    "R2",
    "availableFinishes agrees with finishStatus in every finish unit",
    "FAIL",
    not [
        u["finishUnitId"]
        for u in finish_units
        if set(u["availableFinishes"])
        != {f for f in FINISHES if u["finishStatus"].get(f) in
            ("confirmed", "owner-attested", "marketplace-claimed")}
    ],
    "",
)

check(
    "R3",
    "Every resolved language unit has a non-trivial evidence string and a sourceType",
    "FAIL",
    not [
        u["unitId"]
        for u in units
        if u["status"] in ("confirmed", "contradicted")
        and (len(u.get("evidence") or "") < 12 or not u.get("sourceType"))
    ],
    "",
)

check(
    "R4",
    "Every confirmed printing cites at least one source",
    "FAIL",
    not [
        p["printingId"]
        for u in finish_units
        for p in u["printings"]
        if p["verificationStatus"] == "confirmed" and not p.get("sources")
    ],
    "",
)

referenced = {c["imageFile"].split("/")[-1] for c in cards if c.get("imageFile")}
on_disk = {p.name for p in (ROOT / "images").iterdir() if p.is_file()}
check(
    "R5",
    "Image references and files on disk agree exactly",
    "FAIL",
    referenced == on_disk,
    f"missing={sorted(referenced - on_disk)[:5]} orphaned={sorted(on_disk - referenced)[:5]}",
)

check(
    "R6",
    "meta.verification matches the language state store",
    "FAIL",
    dataset["meta"]["verification"]["totalUnits"] == len(units)
    and dataset["meta"]["verification"]["confirmed"]
    == sum(1 for u in units if u["status"] == "confirmed"),
    "",
)

# Reported, never failed: these move whenever real verification work lands.
status_counts = Counter(u["status"] for u in units)
check(
    "I1",
    "Language verification progress",
    "INFO",
    True,
    f"{status_counts['confirmed']} confirmed, {status_counts['contradicted']} contradicted, "
    f"{status_counts['needs-manual-review']} manual review, {status_counts['pending']} open "
    f"of {len(units)} units",
)
check(
    "I2",
    "Finish verification progress",
    "INFO",
    True,
    f"{counts['withConfirmedFinish']} confirmed, {counts['withOnlyMarketplaceClaim']} marketplace-only, "
    f"{counts['pendingFinish']} pending, {counts['notApplicableFinish']} not-applicable of "
    f"{counts['totalFinishUnits']} finish units; {counts['withUnresolvedProductMapping']} with "
    f"unresolved product mapping",
)


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #

def main() -> int:
    failures = 0
    for check_id, title, severity, ok, detail in results:
        if severity == "INFO":
            print(f"[info] {check_id} {title}: {detail}")
            continue
        if ok:
            print(f"[ ok ] {check_id} {title}")
        else:
            failures += 1
            print(f"[FAIL] {check_id} {title}")
            if detail:
                print(f"       {detail}")
    total = sum(1 for r in results if r[2] != "INFO")
    print(f"\n{total - failures}/{total} checks passed, {failures} failing.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

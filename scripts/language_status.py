#!/usr/bin/env python3
"""Attach the language verification verdict to every card in the main dataset.

`cards[].languages` is what Cardmarket claims. That claim is the project's central finding
*because it is often wrong*: 85 of 719 unit claims are refuted by an outside source, and
`KSS 26` advertises 17 languages for an expansion printed in 7.

Until now the refutation lived only in `verification/units.json` and `CONTRADICTED.json`, so
anyone loading the main dataset got the unfiltered marketplace claim. The caveat was documented
in prose, and prose does not survive a `json.load`.

`languages` is deliberately left untouched — it is a faithful record of the Cardmarket claim,
and that record is itself evidence. The verdict travels beside it instead:

    languagesRepositoryConfirmed  preserved raw confirmed verdicts
    languagesConfirmed     printings whose evidence may establish the exact card
    languagesContradicted  claims an outside source refutes
    languagesNeedsEvidence confirmed claims whose evidence cannot reach the exact card
    languagesUnresolved    the needs-evidence subset plus pending/manual-review claims

A refutation is not automatically a settled absence, and the two used to be indistinguishable
here (#66). `languagesContradicted` stays as it was — the union, so existing consumers are
unaffected — and the split travels beside it:

    languagesNotPrinted    an owner adjudication or a complete official manifest settled it
    languagesDisputed      a source disagrees and nothing has settled it

The application status is read from `verification/evidence_semantics.json`, the one generated
classification of evidence granularity. This keeps the JSON, chronological export, checklist and
database from each independently deciding whether a set-level observation reaches the card.

Run after any verification write pass, before regenerating the chronological exports:

    python scripts/language_status.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CARDS_PATH = ROOT / "snorlax_cards.json"
UNITS_PATH = ROOT / "verification" / "units.json"
SEMANTICS_PATH = ROOT / "verification" / "evidence_semantics.json"

LANG_ORDER = (
    "English", "French", "German", "Italian", "Spanish", "Portuguese", "Dutch", "Polish",
    "Russian", "Japanese", "Korean", "T-Chinese", "S-Chinese", "Indonesian", "Thai",
    "Czech", "Hungarian",
)
LANG_RANK = {language: index for index, language in enumerate(LANG_ORDER)}

APPLICATION_FIELD = {
    "exists": "languagesConfirmed",
    "not-printed": "languagesNotPrinted",
    "disputed": "languagesDisputed",
    "needs-evidence": "languagesNeedsEvidence",
    "unresolved": "languagesUnresolved",
}


def read_json(path: Path) -> Any:
    # Tolerate historical PowerShell 5.1 BOM output; all active writers now emit UTF-8 no-BOM.
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def ordered(languages: set[str]) -> list[str]:
    return sorted(languages, key=lambda language: (LANG_RANK.get(language, 999), language))


def main() -> None:
    cards_document = read_json(CARDS_PATH)
    units = read_json(UNITS_PATH)
    semantics = {
        row["unitId"]: row for row in read_json(SEMANTICS_PATH)["units"]
    }
    unit_ids = {unit["unitId"] for unit in units}
    if set(semantics) != unit_ids:
        raise ValueError("evidence semantics must classify every language unit exactly once")

    verdicts: dict[tuple[str, str, str], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for unit in units:
        key = (
            str(unit.get("setCode") or ""),
            str(unit.get("number") or ""),
            str(unit.get("variant") or "base"),
        )
        status = unit["status"]
        app_status = semantics[unit["unitId"]]["applicationStatus"]
        if status == "confirmed":
            verdicts[key]["languagesRepositoryConfirmed"].add(unit["language"])
        elif status == "contradicted":
            verdicts[key]["languagesContradicted"].add(unit["language"])
        if app_status in APPLICATION_FIELD:
            verdicts[key][APPLICATION_FIELD[app_status]].add(unit["language"])
        if app_status == "needs-evidence":
            # Backward-compatible union: every needs-evidence row is unresolved, while the named
            # subset lets consumers distinguish it from an untouched pending/manual queue.
            verdicts[key]["languagesUnresolved"].add(unit["language"])

    annotated = 0
    for card in cards_document["cards"]:
        if card.get("isCodeCard"):
            # Code cards are excluded from verification entirely; say so rather than
            # leaving empty lists that read as "everything refuted".
            card["languageVerification"] = {
                "status": "not-applicable",
                "reason": "Online/live code cards are excluded from language verification.",
            }
            card.pop("languagesConfirmed", None)
            card.pop("languagesRepositoryConfirmed", None)
            card.pop("languagesContradicted", None)
            card.pop("languagesNotPrinted", None)
            card.pop("languagesDisputed", None)
            card.pop("languagesNeedsEvidence", None)
            card.pop("languagesUnresolved", None)
            continue
        key = (
            str(card.get("setCode") or ""),
            str(card.get("number") or ""),
            str(card.get("variantToken") or "base"),
        )
        verdict = verdicts.get(key, {})
        repository_confirmed = ordered(verdict.get("languagesRepositoryConfirmed", set()))
        confirmed = ordered(verdict.get("languagesConfirmed", set()))
        contradicted = ordered(verdict.get("languagesContradicted", set()))
        needs_evidence = ordered(verdict.get("languagesNeedsEvidence", set()))
        unresolved = ordered(verdict.get("languagesUnresolved", set()))
        not_printed = ordered(verdict.get("languagesNotPrinted", set()))
        disputed = ordered(verdict.get("languagesDisputed", set()))
        card["languagesRepositoryConfirmed"] = repository_confirmed
        card["languagesConfirmed"] = confirmed
        card["languagesContradicted"] = contradicted
        card["languagesNotPrinted"] = not_printed
        card["languagesDisputed"] = disputed
        card["languagesNeedsEvidence"] = needs_evidence
        card["languagesUnresolved"] = unresolved
        card["languageVerification"] = {
            "status": "resolved" if not unresolved else "partial",
            "claimed": len(card.get("languages") or []),
            "repositoryConfirmed": len(repository_confirmed),
            "confirmed": len(confirmed),
            "contradicted": len(contradicted),
            "notPrinted": len(not_printed),
            "disputed": len(disputed),
            "needsEvidence": len(needs_evidence),
            "unresolved": len(unresolved),
            "note": (
                "languages is the raw Cardmarket claim and is not a print manifest. Use "
                "languagesConfirmed for exact printings established within the permitted evidence "
                "granularity. languagesRepositoryConfirmed preserves the raw verdict; its "
                "languagesNeedsEvidence subset cannot yet establish the exact card and is also in "
                "languagesUnresolved. languagesContradicted splits into languagesNotPrinted, where "
                "an owner adjudication settled the question, and languagesDisputed, where a source "
                "disagrees and nothing has settled it. Unresolved and disputed never mean absent."
            ),
        }
        annotated += 1

    notes = [
        note
        for note in cards_document["meta"].get("notes", [])
        if not str(note).startswith(("languagesConfirmed", "languagesRepositoryConfirmed"))
    ]
    notes.append(
        "languagesRepositoryConfirmed / languagesContradicted preserve the external repository "
        "verdict. languagesConfirmed contains only claims whose evidence may establish the exact "
        "card; languagesNeedsEvidence is the unsupported subset and is also unresolved. languages "
        "itself remains the raw marketplace claim: see verification/evidence_semantics.json."
    )
    cards_document["meta"]["notes"] = notes

    with CARDS_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(cards_document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    refuted_products = sum(
        1
        for card in cards_document["cards"]
        if card.get("languagesContradicted")
    )
    print(f"annotated {annotated} cards; {refuted_products} carry at least one refuted language")


if __name__ == "__main__":
    main()

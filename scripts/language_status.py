#!/usr/bin/env python3
"""Attach the language verification verdict to every card in the main dataset.

`cards[].languages` is what Cardmarket claims. That claim is the project's central finding
*because it is often wrong*: 71 of 719 unit claims are refuted by an outside source, and
`KSS 26` advertises 17 languages for an expansion printed in 7.

Until now the refutation lived only in `verification/units.json` and `CONTRADICTED.json`, so
anyone loading the main dataset got the unfiltered marketplace claim. The caveat was documented
in prose, and prose does not survive a `json.load`.

`languages` is deliberately left untouched — it is a faithful record of the Cardmarket claim,
and that record is itself evidence. The verdict travels beside it instead:

    languagesConfirmed     externally verified printings
    languagesContradicted  claims an outside source refutes
    languagesUnresolved    pending or awaiting manual review

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

LANG_ORDER = (
    "English", "French", "German", "Italian", "Spanish", "Portuguese", "Dutch", "Polish",
    "Russian", "Japanese", "Korean", "T-Chinese", "S-Chinese", "Indonesian", "Thai",
    "Czech", "Hungarian",
)
LANG_RANK = {language: index for index, language in enumerate(LANG_ORDER)}

STATUS_FIELD = {
    "confirmed": "languagesConfirmed",
    "contradicted": "languagesContradicted",
    "pending": "languagesUnresolved",
    "needs-manual-review": "languagesUnresolved",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def ordered(languages: set[str]) -> list[str]:
    return sorted(languages, key=lambda language: (LANG_RANK.get(language, 999), language))


def main() -> None:
    cards_document = read_json(CARDS_PATH)
    units = read_json(UNITS_PATH)

    verdicts: dict[tuple[str, str, str], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for unit in units:
        key = (
            str(unit.get("setCode") or ""),
            str(unit.get("number") or ""),
            str(unit.get("variant") or "base"),
        )
        field = STATUS_FIELD.get(unit["status"])
        if field:
            verdicts[key][field].add(unit["language"])

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
            card.pop("languagesContradicted", None)
            card.pop("languagesUnresolved", None)
            continue
        key = (
            str(card.get("setCode") or ""),
            str(card.get("number") or ""),
            str(card.get("variantToken") or "base"),
        )
        verdict = verdicts.get(key, {})
        confirmed = ordered(verdict.get("languagesConfirmed", set()))
        contradicted = ordered(verdict.get("languagesContradicted", set()))
        unresolved = ordered(verdict.get("languagesUnresolved", set()))
        card["languagesConfirmed"] = confirmed
        card["languagesContradicted"] = contradicted
        card["languagesUnresolved"] = unresolved
        card["languageVerification"] = {
            "status": "resolved" if not unresolved else "partial",
            "claimed": len(card.get("languages") or []),
            "confirmed": len(confirmed),
            "contradicted": len(contradicted),
            "unresolved": len(unresolved),
            "note": (
                "languages is the raw Cardmarket claim and is not a print manifest. Use "
                "languagesConfirmed for printings backed by an outside source. A contradicted "
                "language is refuted; an unresolved one is not yet established, never proven absent."
            ),
        }
        annotated += 1

    notes = [
        note
        for note in cards_document["meta"].get("notes", [])
        if not str(note).startswith("languagesConfirmed")
    ]
    notes.append(
        "languagesConfirmed / languagesContradicted / languagesUnresolved carry the external "
        "verification verdict for each Cardmarket language claim. languages itself is left as the "
        "raw marketplace claim, which over-claims: see verification/CONTRADICTED.json."
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

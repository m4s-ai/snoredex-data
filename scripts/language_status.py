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

    languagesConfirmed     externally verified printings
    languagesContradicted  claims an outside source refutes
    languagesUnresolved    pending or awaiting manual review

A refutation is not automatically a settled absence, and the two used to be indistinguishable
here (#66). `languagesContradicted` stays as it was — the union, so existing consumers are
unaffected — and the split travels beside it:

    languagesNotPrinted    an owner adjudication or a complete official manifest settled it
    languagesDisputed      a source disagrees and nothing has settled it

73 of the 85 are `disputed`. `scripts/database.py` has drawn that line since the clean handoff and
`DATABASE.md` tells applications not to read `disputed` as "does not exist"; the line simply never
reached the artifacts above the database. Both generators now derive it from
`scripts/absence_model.py` so there is one rule rather than two implementations.

Run after any verification write pass, before regenerating the chronological exports:

    python scripts/language_status.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from absence_model import absence_decision, absence_scope_urls  # noqa: E402
# Imported from the generator rather than read from verification/source_registry.json: this script
# runs *before* source_registry.py in the documented order, so reading the generated file would
# take provider config one run out of date every time that config changed. PROVIDERS is the
# definition; the JSON is a projection of it.
from source_registry import PROVIDERS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CARDS_PATH = ROOT / "snorlax_cards.json"
UNITS_PATH = ROOT / "verification" / "units.json"
ADJUDICATIONS_PATH = ROOT / "verification" / "owner_adjudications.json"

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

# The split inside languagesContradicted. Kept separate from STATUS_FIELD because these are not a
# fourth status: every language here is also in languagesContradicted, and consumers that only
# understand the three original lists keep working unchanged.
ABSENCE_FIELD = {
    "not-printed": "languagesNotPrinted",
    "disputed": "languagesDisputed",
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
    scope_urls = absence_scope_urls(PROVIDERS)
    adjudicated = {
        decision["unitId"] for decision in read_json(ADJUDICATIONS_PATH)["decisions"]
    }

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
        decision = absence_decision(
            unit["status"], unit.get("sourceUrl"), scope_urls,
            unit["unitId"] in adjudicated,
        )
        if decision in ("not-printed", "disputed"):
            verdicts[key][ABSENCE_FIELD[decision]].add(unit["language"])

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
            card.pop("languagesNotPrinted", None)
            card.pop("languagesDisputed", None)
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
        not_printed = ordered(verdict.get("languagesNotPrinted", set()))
        disputed = ordered(verdict.get("languagesDisputed", set()))
        card["languagesConfirmed"] = confirmed
        card["languagesContradicted"] = contradicted
        card["languagesNotPrinted"] = not_printed
        card["languagesDisputed"] = disputed
        card["languagesUnresolved"] = unresolved
        card["languageVerification"] = {
            "status": "resolved" if not unresolved else "partial",
            "claimed": len(card.get("languages") or []),
            "confirmed": len(confirmed),
            "contradicted": len(contradicted),
            "notPrinted": len(not_printed),
            "disputed": len(disputed),
            "unresolved": len(unresolved),
            "note": (
                "languages is the raw Cardmarket claim and is not a print manifest. Use "
                "languagesConfirmed for printings backed by an outside source. An unresolved "
                "language is not yet established, never proven absent. languagesContradicted "
                "splits into languagesNotPrinted, where an owner adjudication or a complete "
                "official manifest settled the question, and languagesDisputed, where a source "
                "disagrees and nothing has settled it — do not read disputed as 'does not exist'."
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

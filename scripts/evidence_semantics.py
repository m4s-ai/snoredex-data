#!/usr/bin/env python3
"""Classify what each verdict actually rests on, and which inferences carry (#137).

#137's first two work items are an inventory: "Classify every evidence record by granularity"
and "Inventory all current verdicts derived from set-level or absence-based logic". This produces
that inventory and changes no verdict. Downgrading a row is an owner-facing decision and belongs
to #140's migration, not to a report.

FOUR GRANULARITIES, FROM THE ISSUE

``specimen-or-card``   a record about this exact card in this exact language — a card database
                      entry, a set list row, a photographed specimen
``product-or-set``     a statement about the set or product, not the card row — a cross-language
                      expansion index, an "In other languages" table, a release field
``market-or-era``      market-history reasoning — "the Traditional Chinese market opened in 2019"
``sibling-derived``    the evidence of a neighbouring unit rather than this one

WHY SET-LEVEL IS NOT AUTOMATICALLY WRONG

The tempting summary is "142 confirmations rest on a set release, all of them unsound". That is
false and worth resisting. A normally numbered expansion is printed as a whole: if the set was
released in German, card 118/162 exists in German, and inferring that is sound. What does not
follow is a card that is not part of that numbered run — a promo, a deck-fixed card, or a
secret-numbered card above the set size. Bulbapedia's own Rarity article is explicit that these
vary by locale: "Full Art cards were notably only considered 'secret' in Japan", and "the rarity
of a card may vary between Japanese and other-language releases".

So the inventory splits set-level confirmations by whether the step from the source to the card
holds, and only the remainder is a finding. Two things make it hold:

* the card sits inside the set's **numbered run**, which is printed as a whole per language; or
* the cited source carries a **closed card list** containing this card, beside its statement about
  which languages the product exists in.

The second was missed on the first pass, and the miss is instructive. A rarity-only rule flagged
the fifteen Play! Pokémon Prize Pack rows as unsound because "Prize Pack Series" is not an
expansion rarity. But the Prize Pack Series article carries the card row — `Snorlax 131/185` — next
to a language table naming the French, German, Italian and Spanish products. A Prize Pack is a
closed list distributed as a whole, structurally the same as an expansion, so the inference carries
for the same reason. Rarity was a poor proxy; what matters is whether the source lists the card.

WHERE THE RARITY PROXY LEAKS, AND WHAT IT IS NOW ALLOWED TO SAY

Rarity remained the proxy for run membership, and it has since been wrong twice more. Both are
recorded here because the queue this report produces is read as a work list, and a row on it for a
bad reason costs someone the same time as a real one.

* **A rarity belongs to a card, not to a collector number.** The lookup was keyed by
  `(setCode, number)` while a unit is keyed by variant as well. Seventeen pairs carry more than one
  card and eight differ in rarity — always a base printing beside a promo variant sharing a number —
  so `RR 33 V1`, a Rare inside the numbered run, read as the `V2` Promo next to it.
* **"Ultra Rare" is era-dependent and cannot answer alone.** It covers the modern Full Art, which is
  secret in some locales, and the EX-era `ex` and DP-era LV.X cards, which were numbered inside the
  set. The fact that decides between them is the set's printed size, and this project records it
  nowhere. Those rows now report `needs-set-size` rather than an answer; the fix belongs in the set
  database (#146), not in another rarity special case.

A third state is therefore deliberate. `carries` and `does-not-carry` are claims about the
inference; `needs-set-size` is the report declining to make one, and it is not a quieter way of
saying the inference fails.

    python scripts/evidence_semantics.py
    python scripts/evidence_semantics.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "verification" / "evidence_semantics.json"
SCHEMA_VERSION = "0.1.0"

# Matched against `sourceType`, most specific first. A market-history article and a sibling
# inference both mention things the card-level pattern would otherwise catch.
MARKET_ERA = re.compile(r"Pok[eé]mon in |market-history", re.IGNORECASE)
SIBLING = re.compile(r"units of the same product|set release schedule", re.IGNORECASE)
CARD_LEVEL = re.compile(
    r"card database|TCGdex|photographed|specimen|set list|card article|card page|"
    r"locale card archive|promo search|"
    r"promo series article|card list|deck list|"
    # An owner speaking about a card, a collector community naming its languages, and a listing
    # of the card itself are all statements about this card rather than about its set.
    r"Owner attestation|Marketplace listing|retail listings|Elite Fourum|collector guide|"
    r"collector-group|card release history", re.IGNORECASE)
SET_LEVEL = re.compile(
    r"expansion index|expansion article|set article|In other languages|release. field|"
    r"Prize Pack Series article|Languages this set|product article|set-code note", re.IGNORECASE)

# Sources whose page carries a closed card list containing the card, not merely a statement about
# the container. A list plus a language statement reaches the card the same way an expansion's
# numbered run does.
CLOSED_LIST_SOURCE = re.compile(r"set list|deck list|card list|Prize Pack Series article",
                                re.IGNORECASE)

# Does a card of this harvest rarity sit inside the set's numbered run? Only then does "the set
# was released in language L" reach the card. The vocabulary is Cardmarket's, because that is what
# the harvest stores; the reasons cite the rarity catalogue where it speaks.
RUN_MEMBERSHIP = {
    "Common": (True, "part of the numbered run"),
    "Uncommon": (True, "part of the numbered run"),
    "Rare": (True, "part of the numbered run"),
    "Holo Rare": (True, "a rare printed in the run, in its holofoil version"),
    "Double Rare": (True, "Scarlet & Violet run rarity, inside the printed set size"),
    "Promo": (False, "a promo is distributed outside the expansion's numbered run"),
    "Fixed": (False, "deck, kit and half-deck cards carry no set rarity and are not in the run"),
    "Prize Pack Series": (False, "distribution promo, released per market on its own schedule"),
    "Secret Rare": (False, "numbered above the printed set size; presence varies by locale"),
    "Rainbow Rare": (False, "secret-numbered class; presence varies by locale"),
    "Shiny Rare": (False, "subset rarity, not a guaranteed part of every locale's run"),
    "Character Rare": (False, "secret-numbered class; presence varies by locale"),
    "Illustration Rare": (False, "presence and rarity assignment differ between locales"),
    "Special Illustration Rare": (False, "presence and rarity assignment differ between locales"),
    "Triple Rare": (False, "secret-numbered class; presence varies by locale"),
    # Era-dependent, and the only rarity in this table that is. Cardmarket's "Ultra Rare" covers
    # both the modern Full Art — secret in some locales and not others — and the EX-era `ex` and
    # DP-era LV.X cards, which were numbered inside the set (`TRR 104` of 109, `RR 111` of 111).
    # One word, two opposite answers, and the deciding fact is the set's printed size, which this
    # project does not yet record anywhere. Asserting "does not carry" from the word alone was
    # wrong; `None` reports the gap instead of guessing past it. Set size belongs in the set
    # database — filed on #146.
    "Ultra Rare": (None, "run membership depends on the set's printed size, which is not recorded"),
    "Oversized": (False, "jumbo product insert, not part of any numbered run"),
    "World Championship Deck": (False, "event product, not an expansion run"),
    "Online Code Card": (False, "not a physical collectible card"),
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def granularity(unit: dict[str, Any]) -> str:
    source_type = unit.get("sourceType") or ""
    if MARKET_ERA.search(source_type):
        return "market-or-era"
    if SIBLING.search(source_type):
        return "sibling-derived"
    if CARD_LEVEL.search(source_type):
        return "specimen-or-card"
    if SET_LEVEL.search(source_type):
        return "product-or-set"
    return "unclassified"


def build(units: list[dict], cards: list[dict], registry: dict,
          capabilities: dict, adjudications: dict) -> dict[str, Any]:
    # Keyed by the variant token too, not just set and number. Seventeen (setCode, number) pairs
    # carry more than one card and eight of those differ in rarity, always the same way: a base
    # printing and a promo variant sharing a collector number. Keying without the token kept
    # whichever card came last, so `RR 33 V1` — a Rare, inside the numbered run — read as the
    # `V2` Promo beside it and was reported as an unsound inference. That is the neighbour's
    # evidence problem in a new place: judge a row by its own record.
    by_key = {(c["setCode"], str(c.get("number") or ""), c.get("variantToken") or "base"): c
              for c in cards}

    # Which providers may carry absence at all. Both stores are consulted and must agree; they do
    # today, and a disagreement is worth seeing rather than silently preferring one.
    registry_absence = {p["providerId"] for p in registry["providers"] if p.get("supportsAbsence")}
    graph_absence = {
        surface["providerId"]
        for surface in capabilities["surfaces"]
        for edge in surface.get("coverageEdges", [])
        if edge.get("exhaustive") and (edge.get("absenceCapability") or {}).get("enabled")
    }
    settled_units = set()
    for decision in adjudications["decisions"]:
        for key in ("unitId", "unitIds"):
            value = decision.get(key)
            if isinstance(value, str):
                settled_units.add(value)
            elif isinstance(value, list):
                settled_units.update(value)

    rows: list[dict[str, Any]] = []
    for unit in units:
        grain = granularity(unit)
        card = by_key.get((unit["setCode"], str(unit.get("number") or ""),
                           unit.get("variant") or "base"))
        rarity = card["rarity"] if card else None
        inside_run, run_reason = RUN_MEMBERSHIP.get(rarity, (None, "rarity not classified"))

        closed_list = bool(CLOSED_LIST_SOURCE.search(unit.get("sourceType") or ""))
        inference = None
        if unit["status"] == "confirmed" and grain == "product-or-set":
            if inside_run or closed_list:
                inference = "carries"
            elif inside_run is False:
                inference = "does-not-carry"
            elif rarity in RUN_MEMBERSHIP:
                # The rarity is known and the table declines to answer: the fact that would decide
                # it is missing, not the classification. Kept apart from `unknown-rarity` so the
                # queue says which of the two a reader is looking at.
                inference = "needs-set-size"
            else:
                inference = "unknown-rarity"
        if unit["status"] == "contradicted":
            if unit["unitId"] in settled_units:
                inference = "owner-adjudicated"
            elif unit["providerId"] in (registry_absence & graph_absence):
                inference = "provider-holds-an-absence-edge"
            else:
                inference = "unscoped-absence"

        rows.append({
            "unitId": unit["unitId"],
            "setCode": unit["setCode"],
            "number": str(unit.get("number") or ""),
            "variant": unit.get("variant") or "base",
            "language": unit["language"],
            "status": unit["status"],
            "providerId": unit["providerId"],
            "granularity": grain,
            "rarity": rarity,
            "insideNumberedRun": inside_run,
            "runMembershipReason": run_reason,
            "sourceCarriesCardList": closed_list,
            "inference": inference,
        })

    by_grain: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        by_grain[row["granularity"]][row["status"]] += 1

    unsound = [r for r in rows if r["inference"] == "does-not-carry"]
    unscoped = [r for r in rows if r["inference"] == "unscoped-absence"]
    needs_size = [r for r in rows if r["inference"] == "needs-set-size"]

    return {
        "meta": {
            "schema": "snoredex-evidence-semantics",
            "schemaVersion": SCHEMA_VERSION,
            "generated": date.today().isoformat(),
            "issue": "https://github.com/m4s-ai/snoredex-data/issues/137",
            "status": "inventory only — no verdict is changed by this report",
            "description": (
                "Every unit classified by the granularity of the evidence it rests on, and, for "
                "set-level confirmations, whether the inference from set to card carries."
            ),
            "absenceCapableProviders": {
                "sourceRegistry": sorted(registry_absence),
                "capabilityGraph": sorted(graph_absence),
                "agree": sorted(registry_absence) == sorted(graph_absence),
            },
        },
        "runMembershipRules": {
            rarity: {"insideNumberedRun": inside, "reason": reason}
            for rarity, (inside, reason) in sorted(RUN_MEMBERSHIP.items())
        },
        "counts": {
            "units": len(rows),
            "byGranularity": {k: dict(v) for k, v in sorted(by_grain.items())},
            "setLevelConfirmations": sum(
                1 for r in rows if r["status"] == "confirmed" and r["granularity"] == "product-or-set"),
            "setLevelConfirmationsThatCarry": sum(1 for r in rows if r["inference"] == "carries"),
            "setLevelConfirmationsThatDoNotCarry": len(unsound),
            "setLevelConfirmationsNeedingSetSize": len(needs_size),
            "contradictionsByBacking": dict(Counter(
                r["inference"] for r in rows if r["status"] == "contradicted")),
            "unsoundByRarity": dict(Counter(r["rarity"] for r in unsound).most_common()),
        },
        "setLevelConfirmationsThatDoNotCarry": sorted(unsound, key=lambda r: r["unitId"]),
        "setLevelConfirmationsNeedingSetSize": sorted(needs_size, key=lambda r: r["unitId"]),
        "unscopedAbsenceContradictions": sorted(unscoped, key=lambda r: r["unitId"]),
        "units": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the report is stale")
    args = parser.parse_args()

    document = build(
        read_json(ROOT / "verification" / "units.json"),
        read_json(ROOT / "snorlax_cards.json")["cards"],
        read_json(ROOT / "verification" / "source_registry.json"),
        read_json(ROOT / "verification" / "source_capabilities.json"),
        read_json(ROOT / "verification" / "owner_adjudications.json"),
    )

    if args.check:
        if not OUTPUT_PATH.is_file():
            print("evidence_semantics.json missing; run python scripts/evidence_semantics.py")
            return 1
        existing = read_json(OUTPUT_PATH)
        if {k: v for k, v in existing.items() if k != "meta"} != \
                {k: v for k, v in document.items() if k != "meta"}:
            print("evidence_semantics.json is stale; run python scripts/evidence_semantics.py")
            return 1
        print(f"evidence semantics current ({document['counts']['units']} units classified)")
        return 0

    OUTPUT_PATH.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    counts = document["counts"]
    print(f"{OUTPUT_PATH.relative_to(ROOT)}: {counts['units']} units classified")
    for grain, statuses in counts["byGranularity"].items():
        print(f"  {grain:18} {statuses}")
    print(f"  set-level confirmations: {counts['setLevelConfirmations']} "
          f"({counts['setLevelConfirmationsThatCarry']} carry, "
          f"{counts['setLevelConfirmationsThatDoNotCarry']} do not, "
          f"{counts['setLevelConfirmationsNeedingSetSize']} undecidable without a set size)")
    print(f"  contradictions by backing: {counts['contradictionsByBacking']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

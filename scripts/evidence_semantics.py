#!/usr/bin/env python3
"""Classify what each verdict actually rests on, and which inferences carry (#137).

#137 first inventories what every verdict rests on, then derives the conservative application
status from that inventory. The raw verdict and observation never change: an unsupported
confirmation becomes ``needs-evidence`` only on consumer projections, and an unsupported
contradiction becomes ``disputed``.

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
SCHEMA_VERSION = "0.2.0"

# Matched against `sourceType`, most specific first. A market-history article and a sibling
# inference both mention things the card-level pattern would otherwise catch.
MARKET_ERA = re.compile(r"Pok[eé]mon in |market-history", re.IGNORECASE)
# A sibling-derived row rests on **another unit's record**. That is what makes it unable to support
# a confirmation: the neighbour's evidence is not this unit's evidence.
#
# `set release schedule` was in this pattern and is not a sibling. It is a fact about the set, and
# it sat in `sourceType` after an owner attestation naming this exact card in this exact language —
# "Owner (domain expert) confirms the MEGA Dream ex mirror-holo Hop's Snorlax variants exist in
# Korean". Because this pattern is tested before `CARD_LEVEL`, the trailing context decided the
# granularity and eight `xm2a 136` rows were filed as though a neighbour carried them.
#
# The fourteen Prize Pack rows that remain here are *correctly* classified, and the distinction is
# worth keeping in view: their own evidence says the unit "rests on the owner attestation plus the
# uniform per-region Prize Pack distribution the corroborated languages demonstrate". That names
# other units as part of the basis. A release schedule names nobody.
SIBLING = re.compile(r"units of the same product", re.IGNORECASE)
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

# Rarities that name how a card was *distributed*, not where it sits in a set. A recorded set size
# outranks the rarity word — but not these, and the difference is not a nicety.
#
# A promo's collector number is the number of the run card it reprints. `RR 33 V2` is the Rival
# Season promo printing of `RR 33 V1`, an ordinary Rare; `CL 33 V2` and `FLF 80 V2` are the same
# shape. Comparing 33 against a 111-card run therefore answers a question nobody asked: it says the
# *number* is inside the run, which was never in doubt, and concludes that a language release of the
# set reaches a promo distributed separately from it.
#
# This is not hypothetical. When `RR` gained a size and `CL`/`FLF` had not yet, `RR 33 V2` moved to
# `carries` while its two identical siblings stayed on the queue — one promo judged sound and two
# unsound, by nothing but which set had been measured first. So the exclusion is checked before the
# size, and a distribution rarity is outside every numbered run whatever its number says.
DISTRIBUTION_RARITIES = {
    "Promo",
    "Prize Pack Series",
    "Oversized",
    "World Championship Deck",
    "Online Code Card",
}


# WHICH VERDICT EACH GRANULARITY MAY SUPPORT
#
# #137's second work item, and the one #140 needs before it can downgrade anything: the rules were
# implicit in this file's branching, so a reader could see what the report concluded but not what it
# was entitled to conclude. Declaring them makes the residue one queue under one rule instead of
# three ad-hoc counters.
#
# `alone` is the operative word throughout. Every row here asks what a granularity establishes **by
# itself**; corroboration and owner adjudication are separate mechanisms layered on top, and the
# owner adjudication in particular settles a contradiction whatever the evidence's granularity,
# because rule 4 makes it the only thing that can.
VERDICT_TRANSITIONS: dict[str, dict[str, dict[str, str]]] = {
    "specimen-or-card": {
        "confirmed": {
            "support": "always",
            "rule": "A record of this exact card in this exact language establishes the printing. "
                    "This is the granularity every other one is trying to reach.",
        },
        "contradicted": {
            "support": "only-within-an-exhaustive-absence-edge",
            "rule": "A card-level source may deny a printing only where #135 proves it exhaustive "
                    "for that locality, category and period. Otherwise its silence is a gap.",
        },
    },
    "product-or-set": {
        "confirmed": {
            "support": "only-when-the-step-to-the-card-holds",
            "rule": "A statement about the product reaches the card when the card sits inside the "
                    "set's numbered run, or when the cited page carries a closed card list "
                    "containing it — and never when the row is a distribution printing.",
        },
        "contradicted": {
            "support": "never",
            "rule": "A product-level source that does not list a card has a gap, not a finding. "
                    "This is #137's named failure: contradicting a card because a cross-language "
                    "expansion index has no entry for it.",
        },
    },
    "market-or-era": {
        "confirmed": {
            "support": "never",
            "rule": "That a market existed, or received a set, never establishes a particular "
                    "card in a particular language.",
        },
        "contradicted": {
            "support": "never",
            "rule": "An era argument is Indizien: it is the material the owner weighs, not a "
                    "verdict a page can assert. Only an owner adjudication settles it.",
        },
    },
    "sibling-derived": {
        "confirmed": {
            "support": "never",
            "rule": "The neighbour's evidence is not this unit's evidence. A row whose only basis "
                    "is a sibling's record establishes nothing about itself.",
        },
        "contradicted": {
            "support": "never",
            "rule": "Same reason, in the other direction.",
        },
    },
}

# An owner adjudication settles a contradiction whatever the granularity beneath it, because rule 4
# makes it the only mechanism that can settle an absence at all. It is recorded separately in
# owner_adjudications.json and never attributed to a provider, so it is a layer over this table
# rather than a row in it.
ADJUDICATED = "owner-adjudicated"
SCOPED_ABSENCE = "provider-holds-an-absence-edge"


def transition_support(grain: str, status: str, inference: str | None) -> tuple[bool, str]:
    """Does this unit's verdict sit within what its evidence's granularity may support?

    Returns (within, the rule that decided it). A verdict outside its granularity is not a damaged
    observation: the raw row stays exactly as recorded while its application status becomes
    needs-evidence or disputed.
    """
    if status not in ("confirmed", "contradicted"):
        return True, "not-an-existence-verdict"
    if status == "contradicted":
        if inference == ADJUDICATED:
            return True, "owner-adjudication"
        if inference == SCOPED_ABSENCE:
            allowed = VERDICT_TRANSITIONS.get(grain, {}).get("contradicted", {}).get("support")
            return allowed == "only-within-an-exhaustive-absence-edge", "exhaustive-absence-edge"
        return False, "unscoped-absence"
    if grain == "specimen-or-card":
        return True, "card-level-record"
    if grain == "product-or-set":
        return inference == "carries", "step-from-product-to-card"
    return False, "granularity-cannot-support-a-confirmation"


def application_status(status: str, within: bool, inference: str | None) -> str:
    """Project a raw repository verdict without overstating what its evidence establishes."""
    if status == "confirmed":
        return "exists" if within else "needs-evidence"
    if status == "contradicted":
        # The collection owner's explicit decision is the only mechanism that publishes a hard
        # absence. An exact exhaustive source edge permits the raw contradiction, but remains
        # disputed at the application boundary until the owner adjudicates it.
        return "not-printed" if inference == ADJUDICATED else "disputed"
    return "unresolved"


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


def printed_set_sizes(set_sources: dict) -> dict[str, int]:
    """The denominator printed beside the collector number, per set, from the set database.

    This is what separates the two things Cardmarket's `Ultra Rare` means. A card is inside the
    numbered run when its number is within the set's printed size, and once that number is
    recorded, run membership is computed from data rather than inferred from a rarity word — which
    is the requirement filed on #146 and the reason the `needs-set-size` state existed.
    """
    return {
        row["raw"]["legacySetCode"]: row["raw"]["printedSetSize"]
        for row in set_sources["sourceRecords"]
        if row["sourceKind"] == "printed-set-size-record"
    }


def build(units: list[dict], cards: list[dict], registry: dict,
          capabilities: dict, adjudications: dict, set_sources: dict) -> dict[str, Any]:
    # Keyed by the variant token too, not just set and number. Seventeen (setCode, number) pairs
    # carry more than one card and eight of those differ in rarity, always the same way: a base
    # printing and a promo variant sharing a collector number. Keying without the token kept
    # whichever card came last, so `RR 33 V1` — a Rare, inside the numbered run — read as the
    # `V2` Promo beside it and was reported as an unsound inference. That is the neighbour's
    # evidence problem in a new place: judge a row by its own record.
    by_key = {(c["setCode"], str(c.get("number") or ""), c.get("variantToken") or "base"): c
              for c in cards}
    sizes = printed_set_sizes(set_sources)

    # Which providers may carry absence at all. Both stores are consulted and must agree; they do
    # today, and a disagreement is worth seeing rather than silently preferring one.
    registry_absence = {p["providerId"] for p in registry["providers"] if p.get("supportsAbsence")}
    graph_absence = {
        surface["providerId"]
        for surface in capabilities["surfaces"]
        for edge in surface.get("coverageEdges", [])
        if edge.get("exhaustive") and (edge.get("absenceCapability") or {}).get("enabled")
    }
    registry_absence_scopes = {
        (provider["providerId"], url.rstrip("/"))
        for provider in registry["providers"]
        if provider.get("supportsAbsence")
        for url in provider.get("absenceScopes") or []
    }
    graph_language_absence_scopes = {
        (surface["providerId"], url.rstrip("/"))
        for surface in capabilities["surfaces"]
        for edge in surface.get("coverageEdges", [])
        if edge.get("exhaustive")
        for absence in [edge.get("absenceCapability") or {}]
        if absence.get("enabled") and "language" in (absence.get("dimensions") or [])
        for url in absence.get("exactScopes") or []
    }
    bounded_language_absence_scopes = (
        registry_absence_scopes & graph_language_absence_scopes
    )
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
        run_basis = "rarity-table"
        # A recorded set size outranks the rarity word in both directions. It is the fact the word
        # was standing in for, so it settles the era-dependent rarities and corrects any other
        # classification that disagrees with the printed denominator.
        #
        # A distribution rarity is the exception, and it is checked first: that row is a promo,
        # prize-pack, jumbo, Worlds-deck or code-card printing, whose collector number belongs to
        # the run card it reprints rather than to itself. See DISTRIBUTION_RARITIES.
        size = sizes.get(unit["setCode"])
        number_text = str(unit.get("number") or "")
        if rarity in DISTRIBUTION_RARITIES:
            run_basis = "distribution-rarity"
        elif size is not None and number_text.isdigit():
            inside_run = int(number_text) <= size
            run_basis = "printed-set-size"
            run_reason = (
                f"collector number {int(number_text)} against the set's printed size {size}, "
                f"recorded in the set database: "
                + ("inside the numbered run" if inside_run else "numbered above the printed size")
            )

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
            elif (
                unit["providerId"], str(unit.get("sourceUrl") or "").rstrip("/")
            ) in bounded_language_absence_scopes:
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
            "runMembershipBasis": run_basis,
            "runMembershipReason": run_reason,
            "sourceCarriesCardList": closed_list,
            "inference": inference,
        })
        within, rule = transition_support(grain, unit["status"], inference)
        rows[-1]["verdictWithinGranularity"] = within
        rows[-1]["verdictTransitionRule"] = rule
        rows[-1]["applicationStatus"] = application_status(unit["status"], within, inference)

    by_grain: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        by_grain[row["granularity"]][row["status"]] += 1

    unsound = [r for r in rows if r["inference"] == "does-not-carry"]
    unscoped = [r for r in rows if r["inference"] == "unscoped-absence"]
    needs_size = [r for r in rows if r["inference"] == "needs-set-size"]
    beyond = [r for r in rows if not r["verdictWithinGranularity"]]

    return {
        "meta": {
            "schema": "snoredex-evidence-semantics",
            "schemaVersion": SCHEMA_VERSION,
            "generated": date.today().isoformat(),
            "issue": "https://github.com/m4s-ai/snoredex-data/issues/137",
            "status": "active application policy — raw verdicts remain unchanged",
            "description": (
                "Every unit classified by the granularity of the evidence it rests on, and, for "
                "set-level confirmations, whether the inference from set to card carries. "
                "applicationStatus is the conservative consumer projection."
            ),
            "absenceCapableProviders": {
                "sourceRegistry": sorted(registry_absence),
                "capabilityGraph": sorted(graph_absence),
                "agree": sorted(registry_absence) == sorted(graph_absence),
            },
            "boundedLanguageAbsenceScopes": [
                {"providerId": provider, "url": url}
                for provider, url in sorted(bounded_language_absence_scopes)
            ],
        },
        "runMembershipRules": {
            rarity: {"insideNumberedRun": inside, "reason": reason}
            for rarity, (inside, reason) in sorted(RUN_MEMBERSHIP.items())
        },
        "verdictTransitions": {
            "description": (
                "Which verdict each granularity may support on its own. An owner adjudication "
                "settles a contradiction whatever the granularity beneath it, because it is the "
                "only mechanism that can settle an absence at all."
            ),
            "byGranularity": VERDICT_TRANSITIONS,
        },
        "counts": {
            "units": len(rows),
            "byGranularity": {k: dict(v) for k, v in sorted(by_grain.items())},
            "setLevelConfirmations": sum(
                1 for r in rows if r["status"] == "confirmed" and r["granularity"] == "product-or-set"),
            "setLevelConfirmationsThatCarry": sum(1 for r in rows if r["inference"] == "carries"),
            "setLevelConfirmationsThatDoNotCarry": len(unsound),
            "setLevelConfirmationsNeedingSetSize": len(needs_size),
            # One queue, reported as one number. Splitting "the inference fails" from "this report
            # cannot say" is useful to a reader and misleading to a gate: resolving an undecidable
            # row into a failing one moves both counters and reads as a regression on either half.
            "setLevelConfirmationsNotReachingTheCard": len(unsound) + len(needs_size),
            "contradictionsByBacking": dict(Counter(
                r["inference"] for r in rows if r["status"] == "contradicted")),
            "setLevelConfirmationsByRunBasis": dict(Counter(
                r["runMembershipBasis"] for r in rows
                if r["status"] == "confirmed" and r["granularity"] == "product-or-set")),
            "unsoundByRarity": dict(Counter(r["rarity"] for r in unsound).most_common()),
            # The same residue the three queues above describe, counted once under one rule. It is
            # what #140 has to disposition, and it is deliberately a superset: a row can fail the
            # transition test without appearing on any single one of them.
            "verdictsBeyondTheirGranularity": len(beyond),
            "verdictsBeyondTheirGranularityByRule": dict(Counter(
                r["verdictTransitionRule"] for r in beyond).most_common()),
            "applicationStatuses": dict(Counter(
                r["applicationStatus"] for r in rows).most_common()),
        },
        "verdictsBeyondTheirGranularity": sorted(beyond, key=lambda r: r["unitId"]),
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
        read_json(ROOT / "verification" / "set_catalogue_sources.json"),
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
    print(f"  verdicts beyond their granularity: {counts['verdictsBeyondTheirGranularity']} "
          f"{counts['verdictsBeyondTheirGranularityByRule']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Classify evidence granularity and derive conservative application states.

Raw verdicts remain unchanged. Confirmations can become ``needs-evidence`` in projections.
Contradictions remain disputed unless the collection owner adjudicates them.

    python scripts/evidence_semantics.py
    python scripts/evidence_semantics.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "verification" / "evidence_semantics.json"
SCHEMA_VERSION = "1.0.0"

MARKET_ERA = re.compile(r"Pok[eé]mon in |market-history", re.IGNORECASE)
SIBLING = re.compile(r"units of the same product", re.IGNORECASE)
DIRECT_OWNER_ATTESTATION = re.compile(r"^Owner attestation", re.IGNORECASE)
CARD_LEVEL = re.compile(
    r"card database|card catalogue detail|TCGdex|photographed|specimen|set list|card article|card page|"
    r"locale card archive|promo search|"
    r"promo series article|card list|deck list|"
    r"Owner attestation|Marketplace listing|retail listings|Elite Fourum|collector guide|"
    r"collector-group|card release history", re.IGNORECASE)
SET_LEVEL = re.compile(
    r"expansion index|expansion article|set article|In other languages|release. field|"
    r"Prize Pack Series article|Languages this set|product article|set-code note", re.IGNORECASE)

CLOSED_LIST_SOURCE = re.compile(r"set list|deck list|card list|Prize Pack Series article",
                                re.IGNORECASE)

RUN_MEMBERSHIP = {
    "Common": (True, "part of the numbered run"),
    "Uncommon": (True, "part of the numbered run"),
    "Rare": (True, "part of the numbered run"),
    "Holo Rare": (True, "a rare printed in the run, in its holofoil version"),
    "Double Rare": (True, "Scarlet & Violet run rarity, inside the printed set size"),
    "Promo": (False, "a promo is distributed outside the expansion's numbered run"),
    "Fixed": (False, "deck, kit and half-deck cards carry no set rarity and are not in the run"),
    "Prize Pack Series": (False, "distribution promo, released per market on its own schedule"),
    "Secret Rare": (False, "numbered above the printed set size, with presence varying by locale"),
    "Rainbow Rare": (False, "secret-numbered class with presence varying by locale"),
    "Shiny Rare": (False, "subset rarity, not a guaranteed part of every locale's run"),
    "Character Rare": (False, "secret-numbered class with presence varying by locale"),
    "Illustration Rare": (False, "presence and rarity assignment differ between locales"),
    "Special Illustration Rare": (False, "presence and rarity assignment differ between locales"),
    "Triple Rare": (False, "secret-numbered class with presence varying by locale"),
    "Ultra Rare": (None, "run membership depends on the set's printed size, which is not recorded"),
    "Oversized": (False, "jumbo product insert, not part of any numbered run"),
    "World Championship Deck": (False, "event product, not an expansion run"),
    "Online Code Card": (False, "not a physical collectible card"),
}

DISTRIBUTION_RARITIES = {
    "Promo",
    "Prize Pack Series",
    "Oversized",
    "World Championship Deck",
    "Online Code Card",
}


VERDICT_TRANSITIONS: dict[str, dict[str, dict[str, str]]] = {
    "specimen-or-card": {
        "confirmed": {
            "support": "always",
            "rule": "A record of this exact card in this exact language establishes the printing. "
                    "This is the granularity every other one is trying to reach.",
        },
        "contradicted": {
            "support": "raw-disagreement-only",
            "rule": "A contradiction retains source disagreement. It does not establish absence "
                    "without owner adjudication.",
        },
    },
    "product-or-set": {
        "confirmed": {
            "support": "only-when-the-step-to-the-card-holds",
            "rule": "A statement about the product reaches the card when the card sits inside the "
                    "set's numbered run, or when the cited page carries a closed card list "
                    "containing it. A distribution printing remains separate.",
        },
        "contradicted": {
            "support": "raw-disagreement-only",
            "rule": "A contradiction retains source disagreement. Product omission alone remains unknown.",
        },
    },
    "market-or-era": {
        "confirmed": {
            "support": "never",
            "rule": "That a market existed, or received a set, never establishes a particular "
                    "card in a particular language.",
        },
        "contradicted": {
            "support": "raw-disagreement-only",
            "rule": "An era argument may be retained as disagreement. It does not establish absence.",
        },
    },
    "sibling-derived": {
        "confirmed": {
            "support": "never",
            "rule": "The neighbour's evidence is not this unit's evidence. A row whose only basis "
                    "is a sibling's record establishes nothing about itself.",
        },
        "contradicted": {
            "support": "raw-disagreement-only",
            "rule": "A sibling record may be retained as disagreement but cannot settle absence.",
        },
    },
}

ADJUDICATED = "owner-adjudicated"


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
        return False, "source-disagreement-does-not-establish-absence"
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
        return "not-printed" if inference == ADJUDICATED else "disputed"
    return "unresolved"


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def granularity(unit: dict[str, Any]) -> str:
    source_type = unit.get("sourceType") or ""
    if MARKET_ERA.search(source_type):
        return "market-or-era"
    if unit.get("providerId") == "owner-attestation" and DIRECT_OWNER_ATTESTATION.match(source_type):
        return "specimen-or-card"
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
    recorded, run membership is computed from data rather than inferred from a rarity word. This
    is the requirement filed on #146 and the reason the `needs-set-size` state existed.
    """
    return {
        row["raw"]["legacySetCode"]: row["raw"]["printedSetSize"]
        for row in set_sources["sourceRecords"]
        if row["sourceKind"] == "printed-set-size-record"
    }


def build(units: list[dict], cards: list[dict],
          adjudications: dict, set_sources: dict) -> dict[str, Any]:
    by_key = {(c["setCode"], str(c.get("number") or ""), c.get("variantToken") or "base"): c
              for c in cards}
    sizes = printed_set_sizes(set_sources)

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
                inference = "needs-set-size"
            else:
                inference = "unknown-rarity"
        if unit["status"] == "contradicted":
            if unit["unitId"] in settled_units:
                inference = "owner-adjudicated"
            else:
                inference = "source-disagreement"

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
    needs_size = [r for r in rows if r["inference"] == "needs-set-size"]
    beyond = [r for r in rows if not r["verdictWithinGranularity"]]
    generated = max(
        [str(unit.get("checkedAt") or "")[:10] for unit in units]
        + [str(adjudications.get("meta", {}).get("generated") or "")[:10]]
        + [str(set_sources.get("meta", {}).get("generated") or "")[:10]]
    )

    return {
        "meta": {
            "schema": "snoredex-evidence-semantics",
            "schemaVersion": SCHEMA_VERSION,
            "generated": generated,
            "issue": "https://github.com/m4s-ai/snoredex-data/issues/137",
            "status": "active application policy. Raw verdicts remain unchanged",
            "description": (
                "Every unit classified by the granularity of the evidence it rests on, and, for "
                "set-level confirmations, whether the inference from set to card carries. "
                "applicationStatus is the conservative consumer projection."
            ),
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
            "setLevelConfirmationsNotReachingTheCard": len(unsound) + len(needs_size),
            "contradictionsByBacking": dict(Counter(
                r["inference"] for r in rows if r["status"] == "contradicted")),
            "setLevelConfirmationsByRunBasis": dict(Counter(
                r["runMembershipBasis"] for r in rows
                if r["status"] == "confirmed" and r["granularity"] == "product-or-set")),
            "unsoundByRarity": dict(Counter(r["rarity"] for r in unsound).most_common()),
            "verdictsBeyondTheirGranularity": len(beyond),
            "verdictsBeyondTheirGranularityByRule": dict(Counter(
                r["verdictTransitionRule"] for r in beyond).most_common()),
            "applicationStatuses": dict(Counter(
                r["applicationStatus"] for r in rows).most_common()),
        },
        "verdictsBeyondTheirGranularity": sorted(beyond, key=lambda r: r["unitId"]),
        "setLevelConfirmationsThatDoNotCarry": sorted(unsound, key=lambda r: r["unitId"]),
        "setLevelConfirmationsNeedingSetSize": sorted(needs_size, key=lambda r: r["unitId"]),
        "units": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the report is stale")
    args = parser.parse_args()

    document = build(
        read_json(ROOT / "verification" / "units.json"),
        read_json(ROOT / "snorlax_cards.json")["cards"],
        read_json(ROOT / "verification" / "owner_adjudications.json"),
        read_json(ROOT / "verification" / "set_catalogue_sources.json"),
    )

    if args.check:
        if not OUTPUT_PATH.is_file():
            print("evidence_semantics.json missing. Run python scripts/evidence_semantics.py")
            return 1
        existing = read_json(OUTPUT_PATH)
        if {k: v for k, v in existing.items() if k != "meta"} != \
                {k: v for k, v in document.items() if k != "meta"}:
            print("evidence_semantics.json is stale. Run python scripts/evidence_semantics.py")
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

#!/usr/bin/env python3
"""Generate the canonical checklist-item export (#8).

A checklist item is one **documented physical thing a collector can own**. The hard part is not
producing rows, it is refusing to produce rows that were never printed. A naive expansion of
card x language x edition x finish invents combinations, and this project's whole discipline is
that an unlisted finish is *unknown*, not *absent*.

Rules, in the order they bite:

1. Start from confirmed language claims only. Contradicted languages, unresolved languages, and
   code cards never enter.
2. Iterate the finish store's logical `printings[]`, never the group-level finish booleans. The
   store already dedupes printings by physical signature, so two Cardmarket products sharing one
   physical printing yield one item, not two.
3. Expand by edition only where that edition is supported for that language, taken from the
   edition model rather than assumed.
4. Never apply edition-agnostic finish evidence to both First Edition and Unlimited. When more
   than one edition is supported, a concrete printing is emitted only if the printing explicitly
   identifies its edition. Otherwise each confirmed edition receives one unresolved placeholder.
5. Where a confirmed card-language-edition has no printing detail at all, emit exactly one
   `finish: "unresolved"` placeholder rather than inventing a finish.
6. Keep markings, patterns, distribution channels, release dates and card sizes attached to each
   physical item even when their collector-facing finish family matches. `mirror-holo` remains an
   auditable technical finish, but is presented to collectors under the `reverse-holo` family.

    python scripts/checklist.py
    python scripts/checklist.py --check    # fail if regeneration would change the output
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "analysis_checklist.json"

FINISHES = ("non-holo", "holo", "reverse-holo", "mirror-holo")
FINISH_FAMILY = {
    "non-holo": "non-holo",
    "holo": "holo",
    "reverse-holo": "reverse-holo",
    "mirror-holo": "reverse-holo",
    "unresolved": "unresolved",
}
SCHEMA_VERSION = "1.3.0"


def read_json(path: Path) -> Any:
    # Tolerate historical PowerShell 5.1 BOM output; all active writers now emit UTF-8 no-BOM.
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def slug(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "")).strip("-").lower()
    return text or "x"


def marking_slug(markings: Any) -> str:
    """Identify a stamp by what is physically printed on the card.

    `text` is the distinguishing part: xJTG 117 carries three Cosmos-holo printings that differ
    only by their retailer/set-logo stamp ("EB Games", "GameStop", "Journey Together"). Keying on
    `role` alone collapses all three into one item, which is exactly the regression #8 guards
    against.
    """
    if not markings:
        return ""
    parts = []
    for marking in markings:
        if isinstance(marking, dict):
            parts.append(slug("-".join(
                str(marking.get(field)) for field in ("kind", "text") if marking.get(field)
            ) or marking.get("role")))
        else:
            parts.append(slug(marking))
    return "-".join(p for p in parts if p)


def distribution_slug(distribution: Any) -> str:
    """Distribution channel plus region: the same promotion ran in different territories."""
    if not distribution:
        return ""
    return slug("-".join(
        str(distribution.get(field)) for field in ("kind", "name", "region")
        if distribution.get(field)
    ))


def release_precision(value: Any) -> str:
    text = str(value or "")
    if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", text):
        return "day"
    if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", text):
        return "month"
    return "year"


def release_sort(value: Any) -> str:
    text = str(value or "9999")
    precision = release_precision(text)
    if precision == "day":
        return text
    if precision == "month":
        return f"{text}-01"
    return f"{text[:4]}-01-01"


def printing_editions(printing: dict[str, Any]) -> set[str]:
    """Return editions explicitly attributed to a logical printing.

    The current finish store is edition-agnostic, so this normally returns an empty set. Keeping
    the reader here gives future evidence passes a narrow, machine-checked way to make a concrete
    First Edition or Unlimited assertion without reintroducing cross multiplication.
    """
    editions = printing.get("editions")
    if isinstance(editions, list):
        return {str(value) for value in editions if value}
    edition = printing.get("edition")
    return {str(edition)} if edition else set()


def main() -> int:
    cards = read_json(ROOT / "snorlax_cards.json")["cards"]
    finish_units = read_json(ROOT / "verification" / "finish_units.json")["units"]
    releases = read_json(ROOT / "analysis_confirmed_releases.json")["variants"]

    # Products keyed by (setCode, number) so a finish unit can find its edition model, imagery
    # and Cardmarket URLs. A finish unit is language-scoped; products are variant-scoped.
    products_by_group: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for card in cards:
        if card.get("isCodeCard"):
            continue
        products_by_group[(card["setCode"], str(card.get("number") or ""))].append(card)

    release_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {
        (row["setCode"], str(row.get("number") or ""), row["variant"], row["edition"]): row
        for row in releases
    }

    items: list[dict[str, Any]] = []
    warnings: list[str] = []

    for unit in finish_units:
        if unit["applicabilityStatus"] != "applicable":
            continue
        group = (unit["setCode"], str(unit["number"] or ""))
        products = products_by_group.get(group, [])
        if not products:
            continue
        language = unit["language"]

        # Rule 1: only confirmed language claims. The card carries the verdict; a product whose
        # claim for this language is contradicted or unresolved contributes nothing.
        confirming = [
            product for product in products
            if language in (product.get("languagesConfirmed") or [])
        ]
        if not confirming:
            continue

        # Rule 3: editions supported for THIS language, from the edition model.
        #
        # This mirrors scripts/confirmed_releases.py exactly. `unlimitedLanguages` is populated
        # even for cards to which no edition system applies, so membership alone would label
        # every modern card "Unlimited" here while the chronological table calls it "—", and the
        # two artifacts would disagree about the same card.
        editions: list[tuple[str, str]] = []
        for product in confirming:
            model = product.get("editions") or {}
            source = model.get("source") or ""
            if model.get("hasFirstEdition"):
                if language in (model.get("firstEditionLanguages") or []):
                    editions.append(("1st Edition", source))
                if language in (model.get("unlimitedLanguages") or []):
                    editions.append(("Unlimited", source))
            elif model.get("system") in ("WOTC-unlimited-only", "JP-unlimited-only"):
                editions.append(("Unlimited", source))
            else:
                editions.append(("—", source or "No edition system applies to this card."))
        if not editions:
            editions = [("—", "No edition system applies to this card.")]
        seen_editions: dict[str, str] = {}
        for name, source in editions:
            seen_editions.setdefault(name, source)

        reference = confirming[0]
        # Rule 2: logical printings, already deduped by physical signature in the store.
        printings = [p for p in unit["printings"] if p["finish"] in FINISHES]

        multiple_editions = len(seen_editions) > 1
        for edition, edition_source in seen_editions.items():
            if multiple_editions:
                edition_printings = [p for p in printings if edition in printing_editions(p)]
                edition_scope = (
                    "explicit-printing-mapping" if edition_printings else "unresolved"
                )
                if printings and not edition_printings:
                    warnings.append(
                        f"{unit['finishUnitId']} {language} {edition}: finish evidence exists but "
                        "does not identify an edition; emitted an unresolved placeholder"
                    )
            else:
                edition_printings = printings
                edition_scope = (
                    "no-edition-system" if edition == "—" else "only-supported-edition"
                )

            if not edition_printings:
                # Rule 5: one honest placeholder, never an invented finish.
                items.append(
                    build_item(unit, reference, confirming, edition, edition_source,
                               printing=None, edition_scope=edition_scope, release=release_by_key)
                )
                continue
            for printing in edition_printings:
                items.append(
                    build_item(unit, reference, confirming, edition, edition_source,
                               printing=printing, edition_scope=edition_scope,
                               release=release_by_key)
                )

    # Rule 6 relies on the ID carrying every physical dimension; a collision means two genuinely
    # different physical things were about to be merged, so fail rather than silently dedupe.
    duplicates = [cid for cid, count in Counter(item["checklistId"] for item in items).items() if count > 1]
    if duplicates:
        print(f"ERROR: {len(duplicates)} duplicate checklist IDs: {duplicates[:10]}", file=sys.stderr)
        return 1

    items.sort(key=lambda item: (item["releaseSort"], item["setCode"], item["number"],
                                 item["language"], item["edition"], item["checklistId"]))

    resolved = [item for item in items if item["finish"] != "unresolved"]
    unresolved_items = [item for item in items if item["finish"] == "unresolved"]
    first_edition = [item for item in items if item["edition"] == "1st Edition"]
    agnostic = [item for item in first_edition if item["editionScope"] == "edition-agnostic-evidence"]
    finish_groups = {item["finishGroupId"] for item in items}
    reverse_family = [item for item in resolved if item["finishFamily"] == "reverse-holo"]
    reverse_family_groups = {item["finishGroupId"] for item in reverse_family}

    document = {
        "meta": {
            "schema": "snoredex-checklist",
            "schemaVersion": SCHEMA_VERSION,
            "generated": date.today().isoformat(),
            "description": (
                "One record per documented physical collectible item, or per explicitly unresolved "
                "one. Collector-facing finishFamily groups technical reverse-holo and mirror-holo "
                "treatments without collapsing their physical printing records."
            ),
            "rules": [
                "Only confirmed language claims enter; contradicted and unresolved languages and code cards are excluded.",
                "Expansion follows logical printings[], never group-level finish booleans.",
                "Editions expand only where the edition model supports that edition for that language.",
                "When multiple editions are supported, concrete finishes require an explicit edition mapping; otherwise each edition receives one unresolved placeholder.",
                "A confirmed card-language-edition with no printing detail yields exactly one finish:unresolved placeholder.",
                "Markings, foil patterns, distribution channels, release dates and card sizes remain attached to each physical item even when the finish family matches.",
                "Technical mirror-holo printings use finishFamily:reverse-holo for collector-facing grouping while retaining finish:mirror-holo.",
                "Positive evidence is not proof of completeness: only completenessStatus=complete-manifest asserts that an unlisted alternative is absent.",
            ],
            "warning": (
                "This checklist lists what is DOCUMENTED, not what exists. An item's absence means "
                "no evidence has been established, never that the printing does not exist."
            ),
            "counts": {
                "items": len(items),
                "documentedPrintings": len(resolved),
                "unresolvedPlaceholders": len(unresolved_items),
                "firstEditionItems": len(first_edition),
                "firstEditionWithEditionAgnosticEvidence": len(agnostic),
                "completeManifestItems": sum(
                    1 for item in items if item["completenessStatus"] == "complete-manifest"
                ),
                "finishFamilyGroups": len(finish_groups),
                "reverseHoloFamilyItems": len(reverse_family),
                "reverseHoloFamilyGroups": len(reverse_family_groups),
                "languages": len({item["language"] for item in items}),
                "cards": len({(item["setCode"], item["number"]) for item in items}),
            },
        },
        "items": items,
    }

    if warnings:
        for warning in warnings[:10]:
            print(f"warning: {warning}", file=sys.stderr)

    if "--check" in sys.argv:
        if not OUTPUT_PATH.exists():
            print("analysis_checklist.json missing; run python scripts/checklist.py")
            return 1
        existing = read_json(OUTPUT_PATH)
        if existing["items"] != items:
            print("analysis_checklist.json is stale; run python scripts/checklist.py")
            return 1
        print(f"checklist is current ({len(items)} items)")
        return 0

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=1)
        handle.write("\n")

    counts = document["meta"]["counts"]
    print(f"checklist items: {counts['items']} "
          f"({counts['documentedPrintings']} documented printings + "
          f"{counts['unresolvedPlaceholders']} unresolved placeholders)")
    print(f"first edition: {counts['firstEditionItems']} items, "
          f"{counts['firstEditionWithEditionAgnosticEvidence']} resting on edition-agnostic evidence")
    print(f"complete-manifest items: {counts['completeManifestItems']}")
    return 0


def build_item(unit, reference, confirming, edition, edition_source, printing, edition_scope, release):
    """Build one checklist record. `printing=None` yields the unresolved placeholder."""
    set_code = unit["setCode"]
    number = str(unit["number"] or "")
    language = unit["language"]

    variants = sorted({v for p in ([printing] if printing else []) for v in (p.get("mappedVariants") or [])})
    product = next(
        (c for c in confirming if (c.get("variantToken") or "base") in variants),
        reference,
    )
    row = release.get(
        (set_code, number, product.get("variantToken") or "base", edition)
    ) or release.get((set_code, number, product.get("variantToken") or "base", "—"))

    printing_release = printing.get("releaseDate") if printing else None
    if printing_release:
        release_date = printing_release
        release_date_precision = release_precision(printing_release)
        release_approximate = bool(printing.get("releaseApproximate", False))
        release_sort_value = release_sort(printing_release)
    else:
        release_date = (row or {}).get("date")
        release_date_precision = (row or {}).get("datePrecision")
        release_approximate = (row or {}).get("dateApproximate")
        release_sort_value = (row or {}).get("dateSort") or "9999-01-01"

    finish = printing["finish"] if printing else "unresolved"
    finish_family = FINISH_FAMILY[finish]
    pattern = printing.get("foilPattern") if printing else None
    markings = printing.get("markings") if printing else None
    distribution = printing.get("distribution") if printing else None
    card_size = (printing.get("cardSize") if printing else None) or "unknown"

    # Every physical dimension participates in the ID, so two items differing only by stamp,
    # pattern, channel or size cannot collide.
    id_parts = [
        slug(set_code), slug(number or "no-number"), slug(language),
        {"1st Edition": "1e", "Unlimited": "unl", "—": "none"}.get(edition, slug(edition)),
        slug(finish),
    ]
    for extra in (slug(pattern) if pattern else "", marking_slug(markings), distribution_slug(distribution)):
        if extra:
            id_parts.append(extra)
    if card_size and card_size != "standard":
        id_parts.append(slug(card_size))
    checklist_id = "-".join(id_parts)

    # The family ID intentionally excludes the technical finish, foil pattern and Cardmarket
    # V-token. It lets the collector UI place reverse-holo and mirror-holo treatments under one
    # Reverse Holo heading without losing any of the physical checklist items above. Dimensions
    # that represent a genuinely different product context remain in the group identity.
    group_parts = [
        "fg", slug(set_code), slug(number or "no-number"), slug(language),
        {"1st Edition": "1e", "Unlimited": "unl", "—": "none"}.get(edition, slug(edition)),
        slug(finish_family),
    ]
    for extra in (marking_slug(markings), distribution_slug(distribution)):
        if extra:
            group_parts.append(extra)
    if card_size and card_size != "standard":
        group_parts.append(slug(card_size))
    finish_group_id = "-".join(group_parts)

    return {
        "checklistId": checklist_id,
        "cardName": unit["cardName"],
        "setCode": set_code,
        "setName": unit["setName"],
        "number": number,
        "language": language,
        "edition": edition,
        "editionScope": edition_scope,
        "editionSource": edition_source or None,
        "finish": finish,
        "finishFamily": finish_family,
        "finishGroupId": finish_group_id,
        "finishVerificationStatus": printing["verificationStatus"] if printing else "pending",
        "foilPattern": pattern,
        "markings": markings,
        "markingRoles": sorted({m.get("role") for m in (markings or []) if isinstance(m, dict) and m.get("role")}),
        "distribution": distribution,
        "cardSize": card_size,
        "cardmarketVariant": product.get("variantToken") or "base",
        "cardmarketVariantName": product.get("variantName"),
        "mappedVariants": variants,
        "productMapping": "mapped" if variants else ("unresolved" if printing else "not-applicable"),
        "rarity": product.get("rarity"),
        "artist": product.get("artist"),
        "releaseDate": release_date,
        "releaseDatePrecision": release_date_precision,
        "releaseApproximate": release_approximate,
        "releaseSort": release_sort_value,
        "rowId": (row or {}).get("rowId"),
        "finishUnitId": unit["finishUnitId"],
        "printingId": printing["printingId"] if printing else None,
        "completenessStatus": unit["completenessStatus"],
        "sourceIds": sorted({
            s.get("url") or s.get("sourceType")
            for s in ((printing or {}).get("sources") or [])
            if s.get("url") or s.get("sourceType")
        }),
        "image": (
            printing["image"]
            if printing is not None and "image" in printing
            else product.get("imageFile")
        ),
        "cardmarketUrl": product.get("productUrl"),
    }


if __name__ == "__main__":
    sys.exit(main())

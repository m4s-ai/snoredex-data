# -*- coding: utf-8 -*-
"""Build the finish-verification layer and attach product summaries to the main data.

The authoritative finish unit is (set code, collector number, language), because
TCGdex normal/holo/reverse flags describe the card rather than Cardmarket's opaque
V1/V2/V3 product split. Curated overrides map special printings to those products.

Only positive availability is asserted. A false or missing upstream flag becomes
``pending`` here, never proof that a printing does not exist.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CARDS_PATH = ROOT / "snorlax_cards.json"
UNITS_PATH = ROOT / "verification" / "units.json"
OVERRIDES_PATH = ROOT / "verification" / "finish_overrides.json"
OUTPUT_PATH = ROOT / "verification" / "finish_units.json"
REVIEW_JSON_PATH = ROOT / "verification" / "FINISH_REVIEW.json"
REVIEW_CSV_PATH = ROOT / "verification" / "FINISH_REVIEW.csv"
ANALYSIS_PATH = ROOT / "analysis_finishes.json"
CACHE_DIR = ROOT / "verification" / "cache" / "finish-tcgdex"

FINISHES = ("non-holo", "holo", "reverse-holo", "mirror-holo")
STATUS_RANK = {"pending": 0, "marketplace-claimed": 1, "owner-attested": 2, "confirmed": 3}
LANG_ORDER = (
    "English",
    "French",
    "German",
    "Italian",
    "Spanish",
    "Portuguese",
    "Dutch",
    "Polish",
    "Russian",
    "Japanese",
    "Korean",
    "T-Chinese",
    "S-Chinese",
    "Indonesian",
    "Thai",
    "Czech",
    "Hungarian",
)
LANG_RANK = {language: index for index, language in enumerate(LANG_ORDER)}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def variant_token(value: dict[str, Any]) -> str:
    return str(value.get("variantToken") or value.get("variant") or "base")


def group_key(value: dict[str, Any]) -> tuple[str, str, str]:
    return (str(value.get("setCode") or ""), str(value.get("number") or ""), str(value["language"]))


def group_sort_key(key: tuple[str, str, str]) -> tuple[Any, ...]:
    set_code, number, language = key
    number_parts = tuple(int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", number))
    return (set_code.casefold(), number_parts, LANG_RANK.get(language, 999), language.casefold())


def cache_path(url: str) -> Path:
    return CACHE_DIR / f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"


def fetch_tcgdex(url: str) -> tuple[str, dict[str, Any] | None, str | None]:
    cached = cache_path(url)
    if cached.exists():
        try:
            return url, read_json(cached), None
        except (OSError, json.JSONDecodeError):
            pass

    request = urllib.request.Request(url, headers={"User-Agent": "snoredex-data/finish-verification"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.load(response)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        write_json(cached, payload)
        return url, payload, None
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        return url, None, str(error)


def reverse_pattern(card_url: str | None) -> str | None:
    """Return a sourced era pattern only where the TCGdex set id is unambiguous."""
    if not card_url or "/cards/" not in card_url:
        return None
    card_id = card_url.rsplit("/cards/", 1)[1]
    if card_id.startswith(("base6-", "lc-")):
        return "fireworks"
    if re.match(r"ecard[123]-", card_id):
        return "flat-foil-card-body"
    match = re.match(r"ex(\d+)-", card_id)
    if match:
        ex_number = int(match.group(1))
        return {
            5: "energy-symbol-artwork",
            6: "energy-symbol-artwork-poke-ball",
            7: "energy-symbol-artwork-poke-ball",
            8: "pinwheel-artwork",
            9: "poke-ball-and-stars-artwork",
            10: "three-dimensional-poke-ball-artwork",
            11: "plain-foil-artwork-background",
            12: "plain-foil-artwork-background",
            13: "plain-foil-artwork-background",
            14: "plain-foil-artwork-background",
            15: "plain-foil-on-pokemon",
            16: "plain-foil-artwork-background",
        }.get(ex_number)
    if re.match(r"(?:dp\d+|pl\d+|hgss\d*|col1|bw1)-", card_id):
        return "plain-foil-background"
    match = re.match(r"bw(\d+)-", card_id)
    if match and int(match.group(1)) >= 2:
        return "type-symbol-background"
    match = re.match(r"xy(\d+)-", card_id)
    if match:
        return "plain-foil-background" if int(match.group(1)) == 12 else "type-symbol-background"
    if card_id.startswith("g1-"):
        return "type-symbol-background"
    if re.match(r"sm\d", card_id):
        return "large-type-symbol-left"
    if card_id.startswith("swsh"):
        return "tiled-type-symbol"
    if re.match(r"sv\d", card_id):
        return "intricate-tiled-type-symbol"
    if card_id.startswith("me"):
        return "plain-foil-background"
    return None


def source_signature(source: dict[str, Any]) -> str:
    return json.dumps(source, ensure_ascii=False, sort_keys=True)


def printing_signature(printing: dict[str, Any]) -> str:
    identity = {
        "finish": printing["finish"],
        "foilPattern": printing.get("foilPattern"),
        "markings": printing.get("markings"),
        "distribution": printing.get("distribution"),
        "cardSize": printing.get("cardSize"),
    }
    return json.dumps(identity, ensure_ascii=False, sort_keys=True)


def add_printing(printings: list[dict[str, Any]], candidate: dict[str, Any]) -> None:
    candidate.setdefault("foilPattern", None)
    candidate.setdefault("markings", None)
    candidate.setdefault("distribution", None)
    candidate.setdefault("cardSize", "unknown")
    candidate.setdefault("mappedVariants", [])
    candidate.setdefault("verificationStatus", "pending")
    candidate.setdefault("sources", [])
    signature = printing_signature(candidate)
    existing = next((item for item in printings if printing_signature(item) == signature), None)
    if existing is None:
        candidate["mappedVariants"] = sorted(set(candidate["mappedVariants"]))
        candidate["_origin"] = candidate.get("_origin", "auto")
        printings.append(candidate)
        return
    existing["mappedVariants"] = sorted(set(existing["mappedVariants"] + candidate["mappedVariants"]))
    if STATUS_RANK[candidate["verificationStatus"]] > STATUS_RANK[existing["verificationStatus"]]:
        existing["verificationStatus"] = candidate["verificationStatus"]
    seen_sources = {source_signature(source) for source in existing["sources"]}
    for source in candidate["sources"]:
        if source_signature(source) not in seen_sources:
            existing["sources"].append(source)
            seen_sources.add(source_signature(source))


def exact_source(url: str, source_type: str, evidence: str) -> dict[str, Any]:
    return {"url": url, "sourceType": source_type, "evidence": evidence}


def resolve_override_sources(
    source_refs: list[str],
    registry: dict[str, dict[str, Any]],
    products: list[dict[str, Any]],
    mapped_variants: list[str],
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for source_ref in source_refs:
        source = dict(registry[source_ref])
        if source_ref == "cardmarket-stock-image":
            product = next((item for item in products if item["variant"] in mapped_variants), None)
            if product:
                source["url"] = product["cardmarketUrl"]
                source["image"] = product["image"]
        if source.get("url") is None:
            source.pop("url", None)
        resolved.append(source)
    return resolved


def strongest_status(printings: list[dict[str, Any]], finish: str | None = None) -> str:
    statuses = [item["verificationStatus"] for item in printings if finish is None or item["finish"] == finish]
    return max(statuses, key=lambda status: STATUS_RANK[status]) if statuses else "pending"


def has_complete_manifest(printings: list[dict[str, Any]], language: str) -> bool:
    """Return true only for a complete source whose declared language covers this unit."""
    return any(
        source.get("supportsAbsence") is True
        and source.get("coverage") == "complete-manifest"
        and (not source.get("languages") or language in source["languages"])
        for printing in printings
        for source in printing.get("sources") or []
    )


def compact_printing(printing: dict[str, Any]) -> dict[str, Any]:
    return {
        "printingId": printing["printingId"],
        "finish": printing["finish"],
        "foilPattern": printing.get("foilPattern"),
        "markings": printing.get("markings"),
        "distribution": printing.get("distribution"),
        "cardSize": printing.get("cardSize"),
        "verificationStatus": printing["verificationStatus"],
    }


def main() -> None:
    cards_document = read_json(CARDS_PATH)
    cards = cards_document["cards"]
    units = read_json(UNITS_PATH)
    overrides_document = read_json(OVERRIDES_PATH)
    source_registry = overrides_document["sources"]

    cards_by_product: dict[tuple[str, str, str], dict[str, Any]] = {}
    for card in cards:
        if card.get("isCodeCard"):
            continue
        key = (str(card.get("setCode") or ""), str(card.get("number") or ""), variant_token(card))
        if key in cards_by_product:
            raise ValueError(f"Duplicate non-code product key: {key}")
        cards_by_product[key] = card

    grouped_units: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        grouped_units[group_key(unit)].append(unit)

    tcgdex_urls = sorted(
        {
            unit["sourceUrl"]
            for unit in units
            if unit.get("status") == "confirmed"
            and str(unit.get("sourceUrl") or "").startswith("https://api.tcgdex.net/")
        }
    )
    tcgdex_data: dict[str, dict[str, Any]] = {}
    fetch_errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch_tcgdex, url): url for url in tcgdex_urls}
        for future in as_completed(futures):
            url, payload, error = future.result()
            if payload is not None:
                tcgdex_data[url] = payload
            else:
                fetch_errors[url] = error or "unknown error"

    tcgdex_sibling_url: dict[tuple[str, str], str] = {}
    for unit in units:
        url = str(unit.get("sourceUrl") or "")
        if url.startswith("https://api.tcgdex.net/"):
            sibling_key = (str(unit.get("setCode") or ""), str(unit.get("number") or ""))
            if unit.get("language") == "English" or sibling_key not in tcgdex_sibling_url:
                tcgdex_sibling_url[sibling_key] = url

    overrides_by_group: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for override in overrides_document["overrides"]:
        overrides_by_group[(str(override["setCode"]), str(override.get("number") or ""))].append(override)

    finish_units: list[dict[str, Any]] = []
    for finish_index, key in enumerate(sorted(grouped_units, key=group_sort_key)):
        set_code, number, language = key
        member_units = grouped_units[key]
        products: list[dict[str, Any]] = []
        for unit in sorted(member_units, key=lambda item: variant_token(item)):
            product_key = (set_code, number, variant_token(unit))
            card = cards_by_product.get(product_key)
            if card is None:
                raise ValueError(f"Finish unit has no card product: {product_key}")
            products.append(
                {
                    "variant": variant_token(unit),
                    "claimStatus": unit["status"],
                    "rarity": card.get("rarity"),
                    "variantName": card.get("variantName"),
                    "variantNameSource": card.get("variantNameSource"),
                    "cardmarketHints": {
                        "reverseHoloAxis": "Reverse Holo" in (card.get("variantAxes") or []),
                        "firstEditionAxis": "First Edition?" in (card.get("variantAxes") or []),
                    },
                    "cardmarketUrl": card["productUrl"],
                    "image": card.get("imageFile"),
                }
            )
        present_variants = {product["variant"] for product in products}
        active_variants = {
            product["variant"] for product in products if product["claimStatus"] != "contradicted"
        }
        all_claims_contradicted = bool(products) and not active_variants
        card_name = member_units[0]["cardName"]
        set_name = member_units[0]["setName"]
        printings: list[dict[str, Any]] = []

        exact_urls = sorted(
            {
                str(unit.get("sourceUrl") or "")
                for unit in member_units
                if unit.get("status") == "confirmed"
                and str(unit.get("sourceUrl") or "").startswith("https://api.tcgdex.net/")
            }
        )
        pattern_url = exact_urls[0] if exact_urls else tcgdex_sibling_url.get((set_code, number))
        inferred_reverse_pattern = reverse_pattern(pattern_url)
        auto_mapping = sorted(active_variants) if len(active_variants) == 1 else []
        auto_product = (
            next((product for product in products if product["variant"] in active_variants), None)
            if len(active_variants) == 1
            else None
        )
        auto_card_size = (
            "jumbo" if auto_product and auto_product.get("rarity") == "Oversized" else "standard"
        ) if auto_product else "unknown"

        for url in exact_urls:
            payload = tcgdex_data.get(url)
            if payload is None:
                continue
            upstream_variants = payload.get("variants") or {}
            upstream_source = exact_source(
                url,
                "TCGdex API card variants",
                f"{payload.get('id')} variants=true is positive evidence that the printing exists; false values are not used as contradiction.",
            )
            for field, finish in (("normal", "non-holo"), ("holo", "holo"), ("reverse", "reverse-holo")):
                if upstream_variants.get(field) is not True:
                    continue
                sources = [upstream_source]
                pattern = inferred_reverse_pattern if finish == "reverse-holo" else None
                if pattern:
                    sources.append(dict(source_registry["holofoil-patterns"]))
                add_printing(
                    printings,
                    {
                        "finish": finish,
                        "foilPattern": pattern,
                        "markings": None,
                        "distribution": None,
                        "cardSize": auto_card_size,
                        "mappedVariants": auto_mapping,
                        "verificationStatus": "confirmed",
                        "sources": sources,
                        "_origin": "auto",
                    },
                )

        for product in products:
            if product["claimStatus"] == "contradicted":
                continue
            product_source = exact_source(
                product["cardmarketUrl"],
                "Cardmarket catalogue hint (not external verification)",
                "This is a positive marketplace catalogue claim only; it is not treated as proof or as a complete finish manifest.",
            )
            rarity = str(product.get("rarity") or "")
            product_card_size = "jumbo" if rarity == "Oversized" else "standard"
            if product["cardmarketHints"]["reverseHoloAxis"]:
                sources = [product_source]
                if inferred_reverse_pattern:
                    sources.append(dict(source_registry["holofoil-patterns"]))
                add_printing(
                    printings,
                    {
                        "finish": "reverse-holo",
                        "foilPattern": inferred_reverse_pattern,
                        "markings": None,
                        "distribution": None,
                        "cardSize": product_card_size,
                        "mappedVariants": [product["variant"]],
                        "verificationStatus": "marketplace-claimed",
                        "sources": sources,
                        "_origin": "auto",
                    },
                )
            if rarity in {"Common", "Uncommon", "Rare"}:
                add_printing(
                    printings,
                        {
                            "finish": "non-holo",
                            "cardSize": product_card_size,
                        "mappedVariants": [product["variant"]],
                        "verificationStatus": "marketplace-claimed",
                        "sources": [product_source],
                        "_origin": "auto",
                    },
                )
            elif "Holo" in rarity:
                add_printing(
                    printings,
                        {
                            "finish": "holo",
                            "cardSize": product_card_size,
                        "mappedVariants": [product["variant"]],
                        "verificationStatus": "marketplace-claimed",
                        "sources": [product_source],
                        "_origin": "auto",
                    },
                )

            variant_name = str(product.get("variantName") or "")
            if variant_name:
                normalized_name = variant_name.casefold()
                named_finish = None
                named_pattern = None
                if "non-holo" in normalized_name:
                    named_finish = "non-holo"
                elif "mirror holo" in normalized_name:
                    named_finish = "mirror-holo"
                elif "holo" in normalized_name:
                    named_finish = "holo"
                if "master ball" in normalized_name:
                    named_pattern = "master-ball"
                elif "poké ball" in normalized_name or "poke ball" in normalized_name:
                    named_pattern = "poke-ball"
                elif "cosmos" in normalized_name:
                    named_pattern = "cosmos"
                elif "colourless-energy star" in normalized_name:
                    named_pattern = "colorless-energy-star"
                if named_finish:
                    add_printing(
                        printings,
                        {
                            "finish": named_finish,
                            "foilPattern": named_pattern,
                            "markings": None,
                            "distribution": None,
                            "cardSize": product_card_size,
                            "mappedVariants": [product["variant"]],
                            "verificationStatus": "confirmed",
                            "sources": [
                                exact_source(
                                    product["cardmarketUrl"],
                                    product.get("variantNameSource") or "Curated variant identification",
                                    f"Curated variant name: {variant_name}",
                                )
                            ],
                            "_origin": "auto",
                        },
                    )

        applicable_overrides = [
            override
            for override in overrides_by_group.get((set_code, number), [])
            if not override.get("languages") or language in override["languages"]
        ]
        for override in applicable_overrides:
            suppressed = set(override.get("suppressAutoFinishes") or [])
            if suppressed:
                printings = [
                    printing
                    for printing in printings
                    if not (printing.get("_origin") == "auto" and printing["finish"] in suppressed)
                ]
            for finish, mapped_variants in (override.get("mapAutoFinishes") or {}).items():
                usable = sorted(set(mapped_variants) & present_variants)
                mapped_sizes = {
                    "jumbo" if product.get("rarity") == "Oversized" else "standard"
                    for product in products
                    if product["variant"] in usable
                }
                for printing in printings:
                    if printing["finish"] == finish and printing.get("_origin") == "auto":
                        printing["mappedVariants"] = usable
                        if printing.get("cardSize") == "unknown" and len(mapped_sizes) == 1:
                            printing["cardSize"] = next(iter(mapped_sizes))
            for manual in override.get("printings") or []:
                requested_variants = list(manual.get("mappedVariants") or [])
                mapped_variants = sorted(set(requested_variants) & present_variants)
                if requested_variants and not mapped_variants:
                    continue
                candidate = {
                    "finish": manual["finish"],
                    "foilPattern": manual.get("foilPattern"),
                    "markings": manual.get("markings"),
                    "distribution": manual.get("distribution"),
                    "cardSize": manual.get("cardSize", "unknown"),
                    "mappedVariants": mapped_variants,
                    "verificationStatus": manual["verificationStatus"],
                    "sources": resolve_override_sources(
                        manual.get("sourceRefs") or [], source_registry, products, mapped_variants
                    ),
                    "_origin": "manual",
                }
                add_printing(printings, candidate)

        deduplicated_printings: list[dict[str, Any]] = []
        for printing in printings:
            add_printing(deduplicated_printings, printing)
        # A finish cannot be attached to a product-language claim that the language
        # verification layer has already disproved. These units remain in the state
        # store for exact key coverage, but they are not finish-research work.
        printings = [] if all_claims_contradicted else deduplicated_printings

        printings.sort(
            key=lambda item: (
                FINISHES.index(item["finish"]) if item["finish"] in FINISHES else 99,
                str(item.get("foilPattern") or ""),
                json.dumps(item.get("markings"), ensure_ascii=False, sort_keys=True),
                item.get("cardSize") or "",
            )
        )
        finish_unit_id = f"F{finish_index:04d}"
        for printing_index, printing in enumerate(printings, 1):
            printing["printingId"] = f"{finish_unit_id}-P{printing_index:02d}"
            printing.pop("_origin", None)

        available_finishes = [finish for finish in FINISHES if any(p["finish"] == finish for p in printings)]
        finish_status = {
            finish: "not-applicable" if all_claims_contradicted else strongest_status(printings, finish)
            for finish in FINISHES
        }
        mapped_variants = {variant for printing in printings for variant in printing["mappedVariants"]}
        required_variants = active_variants
        if not required_variants:
            product_mapping_status = "not-applicable"
        elif required_variants <= mapped_variants:
            product_mapping_status = "confirmed"
        elif required_variants & mapped_variants:
            product_mapping_status = "partial"
        else:
            product_mapping_status = "pending"

        known_printings = [printing for printing in printings if printing["finish"] in FINISHES]
        complete_manifest = has_complete_manifest(known_printings, language)
        pattern_target_printings = [
            printing for printing in printings if printing["finish"] in {"reverse-holo", "mirror-holo"}
        ]
        patterned = [printing for printing in pattern_target_printings if printing.get("foilPattern")]
        if not pattern_target_printings:
            pattern_status = "not-applicable"
        elif len(patterned) == len(pattern_target_printings):
            pattern_status = "confirmed"
        elif patterned:
            pattern_status = "partial"
        else:
            pattern_status = "pending"

        unresolved: list[str] = []
        if not all_claims_contradicted and not known_printings:
            unresolved.append("No positive finish evidence has been recorded for this set-number-language unit.")
        if product_mapping_status in {"partial", "pending"}:
            unresolved.append(
                "One or more Cardmarket product variants are not mapped to a logical printing: "
                + ", ".join(sorted(required_variants - mapped_variants))
            )
        if pattern_status in {"partial", "pending"}:
            unresolved.append("The exact reverse- or mirror-holo pattern is not identified for every known printing of those types.")
        if not all_claims_contradicted and any(
            product["claimStatus"] == "contradicted" for product in products
        ):
            unresolved.append("The underlying Cardmarket language claim is contradicted for at least one product variant.")

        if all_claims_contradicted:
            completeness_status = "not-applicable"
        elif complete_manifest:
            completeness_status = "complete-manifest"
        elif known_printings:
            completeness_status = "positive-evidence-only"
        else:
            completeness_status = "pending"

        finish_units.append(
            {
                "finishUnitId": finish_unit_id,
                "cardName": card_name,
                "setCode": set_code,
                "setName": set_name,
                "number": number,
                "language": language,
                "products": products,
                "availableFinishes": available_finishes,
                "finishStatus": finish_status,
                "applicabilityStatus": "not-applicable" if all_claims_contradicted else "applicable",
                "availabilityStatus": (
                    "not-applicable" if all_claims_contradicted else strongest_status(known_printings)
                ),
                "completenessStatus": completeness_status,
                "productMappingStatus": product_mapping_status,
                "patternStatus": pattern_status,
                "printings": printings,
                "unresolved": unresolved,
            }
        )

    finish_lookup = {
        (unit["setCode"], unit["number"], unit["language"]): unit for unit in finish_units
    }
    for card in cards:
        if card.get("isCodeCard"):
            card["finishAvailability"] = {
                "scope": "not-applicable",
                "status": "not-applicable",
                "reason": "Online/live code cards do not have physical card finishes.",
            }
            continue
        token = variant_token(card)
        by_language: list[dict[str, Any]] = []
        for language in card.get("languages") or []:
            unit = finish_lookup[(str(card.get("setCode") or ""), str(card.get("number") or ""), language)]
            product = next((item for item in unit["products"] if item["variant"] == token), None)
            mapped = [printing for printing in unit["printings"] if token in printing["mappedVariants"]]
            mapped_known = [printing for printing in mapped if printing["finish"] in FINISHES]
            not_applicable = bool(product and product["claimStatus"] == "contradicted")
            finish_status = {
                finish: "not-applicable" if not_applicable else strongest_status(mapped_known, finish)
                for finish in FINISHES
            }
            by_language.append(
                {
                    "language": language,
                    "claimStatus": product["claimStatus"] if product else "pending",
                    "availableFinishes": [finish for finish in FINISHES if any(p["finish"] == finish for p in mapped)],
                    "finishStatus": finish_status,
                    "status": "not-applicable" if not_applicable else strongest_status(mapped_known),
                    "finishUnitId": unit["finishUnitId"],
                    "printings": [compact_printing(printing) for printing in mapped],
                }
            )
        union_finishes = [
            finish
            for finish in FINISHES
            if any(finish in row["availableFinishes"] for row in by_language)
        ]
        language_statuses = [row["status"] for row in by_language]
        applicable_statuses = [status for status in language_statuses if status != "not-applicable"]
        if language_statuses and not applicable_statuses:
            overall_status = "not-applicable"
        elif applicable_statuses and all(status == "confirmed" for status in applicable_statuses):
            overall_status = "confirmed"
        elif any(status != "pending" for status in applicable_statuses):
            overall_status = "partial"
        else:
            overall_status = "pending"
        card["finishAvailability"] = {
            "scope": "this Cardmarket product variant, by listed language; full evidence is in verification/finish_units.json",
            "status": overall_status,
            "availableFinishes": union_finishes,
            "byLanguage": by_language,
        }

    counts = {
        "totalFinishUnits": len(finish_units),
        "withConfirmedFinish": sum(unit["availabilityStatus"] == "confirmed" for unit in finish_units),
        "withOnlyMarketplaceClaim": sum(unit["availabilityStatus"] == "marketplace-claimed" for unit in finish_units),
        "pendingFinish": sum(unit["availabilityStatus"] == "pending" for unit in finish_units),
        "notApplicableFinish": sum(unit["availabilityStatus"] == "not-applicable" for unit in finish_units),
        "withCompleteManifest": sum(unit["completenessStatus"] == "complete-manifest" for unit in finish_units),
        "withNonHolo": sum("non-holo" in unit["availableFinishes"] for unit in finish_units),
        "withHolo": sum("holo" in unit["availableFinishes"] for unit in finish_units),
        "withReverseHolo": sum("reverse-holo" in unit["availableFinishes"] for unit in finish_units),
        "withMirrorHolo": sum("mirror-holo" in unit["availableFinishes"] for unit in finish_units),
        "withBothNonHoloAndHolo": sum(
            {"non-holo", "holo"} <= set(unit["availableFinishes"]) for unit in finish_units
        ),
        "withUnresolvedProductMapping": sum(
            unit["productMappingStatus"] in {"partial", "pending"} for unit in finish_units
        ),
        "withAnyUnresolvedDetail": sum(bool(unit["unresolved"]) for unit in finish_units),
        "tcgdexUrlsRequested": len(tcgdex_urls),
        "tcgdexFetchErrors": len(fetch_errors),
    }
    cards_document["meta"]["finishVerification"] = {
        "description": "Positive finish availability by set number, language, and mapped Cardmarket product. See verification/finish_units.json.",
        "lastUpdated": date.today().isoformat(),
        **counts,
    }
    notes = cards_document["meta"].setdefault("notes", [])
    generated_note_prefixes = (
        "variantAxes =",
        "variantAxes and hasReverseHolo are",
        "markings.role distinguishes EX-era",
    )
    notes = [
        note for note in notes if not any(str(note).startswith(prefix) for prefix in generated_note_prefixes)
    ]
    notes.append(
        "variantAxes and hasReverseHolo are Cardmarket catalogue hints only. finishAvailability is the positive-evidence finish layer; pending never means a finish is proven not to exist."
    )
    notes.append(
        "markings.role distinguishes EX-era reverse-holo-treatment set logos from later distribution-promo stamps such as prerelease, Staff, retailer, and Pokemon Center marks."
    )
    cards_document["meta"]["notes"] = notes

    finish_document = {
        "meta": {
            "description": "One row per set code x collector number x language, with logical physical printings and Cardmarket product mappings.",
            "generated": date.today().isoformat(),
            "scope": "Physical cards only; online/live code cards are excluded.",
            "sourcePolicy": [
                "Only positive availability is asserted. pending means not yet established, never proven absent.",
                "A unit whose underlying product-language claims are all contradicted is not-applicable and is excluded from the finish-review queue.",
                "Only a language-scoped source marked supportsAbsence=true and coverage=complete-manifest can set completenessStatus=complete-manifest.",
                "TCGdex variants=true is confirmation; false is ignored because upstream variant coverage is incomplete.",
                "TCGdex finish flags are set-number-language level and are not mapped to a Cardmarket V token without independent evidence or an unambiguous single product.",
                "Cardmarket Reverse Holo axes and rarity labels are retained as marketplace-claimed hints, not external confirmation.",
                "EX-era set-logo stamps intrinsic to reverse holo use markings.role=reverse-holo-treatment; later promotional stamps use markings.role=distribution-promo.",
            ],
            "taxonomy": {
                "finish": list(FINISHES) + ["unknown"],
                "verificationStatus": ["confirmed", "owner-attested", "marketplace-claimed", "pending"],
                "availabilityStatus": ["confirmed", "owner-attested", "marketplace-claimed", "pending", "not-applicable"],
                "cardSize": ["standard", "jumbo", "unknown"],
                "markingRoles": ["reverse-holo-treatment", "distribution-promo"],
                "completenessStatus": ["complete-manifest", "positive-evidence-only", "pending", "not-applicable"],
            },
            "counts": counts,
            "fetchErrors": fetch_errors,
        },
        "units": finish_units,
    }

    review_rows = [
        {
            "finishUnitId": unit["finishUnitId"],
            "cardName": unit["cardName"],
            "setCode": unit["setCode"],
            "number": unit["number"],
            "language": unit["language"],
            "availabilityStatus": unit["availabilityStatus"],
            "availableFinishes": unit["availableFinishes"],
            "productMappingStatus": unit["productMappingStatus"],
            "patternStatus": unit["patternStatus"],
            "unmappedVariants": sorted(
                {
                    product["variant"]
                    for product in unit["products"]
                    if product["claimStatus"] != "contradicted"
                }
                - {
                    variant
                    for printing in unit["printings"]
                    for variant in printing["mappedVariants"]
                }
            ),
            "unresolved": unit["unresolved"],
        }
        for unit in finish_units
        if unit["unresolved"]
    ]
    review_document = {
        "meta": {
            "description": "Finish units that still need finish, pattern, marking, size, or Cardmarket-product mapping evidence.",
            "generated": date.today().isoformat(),
            "count": len(review_rows),
        },
        "units": review_rows,
    }

    combination_counts = Counter(" + ".join(unit["availableFinishes"]) or "pending" for unit in finish_units)
    pattern_counts = Counter(
        printing["foilPattern"] or "unidentified"
        for unit in finish_units
        for printing in unit["printings"]
        if printing["finish"] in {"holo", "reverse-holo", "mirror-holo"}
    )
    marking_role_counts = Counter(
        marking["role"]
        for unit in finish_units
        for printing in unit["printings"]
        for marking in (printing.get("markings") or [])
    )
    analysis = {
        "generated": date.today().isoformat(),
        "note": "Counts are set-number-language finish units. Availability is positive-evidence-only and is not a proof of completeness.",
        "counts": counts,
        "finishCombinations": dict(sorted(combination_counts.items())),
        "foilPatterns": dict(sorted(pattern_counts.items())),
        "markingRoles": dict(sorted(marking_role_counts.items())),
        "bothNonHoloAndHolo": [
            {
                "finishUnitId": unit["finishUnitId"],
                "card": f"{unit['cardName']} ({unit['setCode']} {unit['number']})",
                "language": unit["language"],
            }
            for unit in finish_units
            if {"non-holo", "holo"} <= set(unit["availableFinishes"])
        ],
    }

    write_json(OUTPUT_PATH, finish_document)
    write_json(REVIEW_JSON_PATH, review_document)
    write_json(ANALYSIS_PATH, analysis)
    write_json(CARDS_PATH, cards_document)
    with REVIEW_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "finishUnitId",
                "cardName",
                "setCode",
                "number",
                "language",
                "availabilityStatus",
                "availableFinishes",
                "productMappingStatus",
                "patternStatus",
                "unmappedVariants",
                "unresolved",
            ]
        )
        for row in review_rows:
            writer.writerow(
                [
                    row["finishUnitId"],
                    row["cardName"],
                    row["setCode"],
                    row["number"],
                    row["language"],
                    row["availabilityStatus"],
                    "; ".join(row["availableFinishes"]),
                    row["productMappingStatus"],
                    row["patternStatus"],
                    "; ".join(row["unmappedVariants"]),
                    " | ".join(row["unresolved"]),
                ]
            )

    print(f"finish units: {counts['totalFinishUnits']}")
    print(
        "availability: "
        f"confirmed={counts['withConfirmedFinish']} "
        f"marketplace-only={counts['withOnlyMarketplaceClaim']} "
        f"pending={counts['pendingFinish']} "
        f"not-applicable={counts['notApplicableFinish']}"
    )
    print(
        "finishes: "
        f"non-holo={counts['withNonHolo']} holo={counts['withHolo']} "
        f"reverse={counts['withReverseHolo']} mirror={counts['withMirrorHolo']} "
        f"both-base+holo={counts['withBothNonHoloAndHolo']}"
    )
    print(
        f"review units: {len(review_rows)}; unresolved product mappings: "
        f"{counts['withUnresolvedProductMapping']}"
    )
    print(f"TCGdex: {len(tcgdex_data)}/{len(tcgdex_urls)} fetched; errors={len(fetch_errors)}")


if __name__ == "__main__":
    main()

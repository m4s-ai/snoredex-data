#!/usr/bin/env python3
"""Dry-run the locality-aware print identity against the legacy rows (#134).

`ADR-0001` proposes replacing the Cardmarket product identity — `(setCode, number, variantToken)`
with language as an attribute — with a graph where a **print** is one physical localized printing
keyed by `(locality, localSetCode, localNumber, variant)`. This script is the dry run the ADR is
not allowed to skip: it maps every legacy row onto that model and reports what happens, without
touching a single store.

It writes `verification/print_identity_dryrun.json` and changes nothing else. Migration is #140.

The finding it exists to make measurable: a language claim on a Japanese product is very often not
a language of that product at all. A Korean Snorlax in `sv2a 181` is its own printing, with a
Korean set code and a Korean collector number that this repository has never recorded — because
the model had nowhere to put them. Those become print nodes with `localIdentifier: null` and a
`needs-local-identifier` state, which is the honest representation and doubles as the discovery
queue for #138.

    python scripts/print_identity_dryrun.py
    python scripts/print_identity_dryrun.py --check    # fail if the report is stale

Every legacy member gets exactly one disposition — `carried`, `split`, `aliased` or `queued` — and
check `N1` fails if any member has none. "The script ran" is not the exit condition; accounting for
every row is.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "verification" / "print_identity_dryrun.json"
SCHEMA_VERSION = "0.1.0"

# Locality is a market/distribution territory. It is deliberately not a language: European and
# Latin-American Spanish are one language across two of these, which is the case `SVP 184` makes.
LOCALITIES = {
    "WEST": "Western distribution (EU/NA)",
    "LATAM": "Latin-American distribution",
    "JP": "Japan",
    "KR": "South Korea",
    "TW": "Taiwan / Traditional-Chinese distribution",
    "CN": "Mainland China / Simplified-Chinese distribution",
    "ID": "Indonesia",
    "TH": "Thailand",
    "SEA": "South-East Asian regional promo distribution",
}

# The locality a Cardmarket market label implies for the product's own identifiers. A product's set
# code and collector number are the *local* identifiers of exactly this locality and no other.
MARKET_LOCALITY = {
    "Western": "WEST",
    "Japanese": "JP",
    "Simplified Chinese": "CN",
    "Traditional Chinese": "TW",
    "SEA promo": "SEA",
}

# Languages that name their locality on their own.
LANGUAGE_LOCALITY = {
    "Japanese": "JP",
    "Korean": "KR",
    "T-Chinese": "TW",
    "S-Chinese": "CN",
    "Thai": "TH",
    "Indonesian": "ID",
}

# Languages printed for Western distribution. "Spanish" is European Spanish here, per the project's
# standing scope rule; LATAM-ES is a distinct locality and out of the legacy universe entirely.
WESTERN_LANGUAGES = {
    "English", "French", "German", "Italian", "Spanish", "Portuguese",
    "Russian", "Dutch", "Polish", "Czech", "Hungarian",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def resolve_locality(language: str, market: str) -> tuple[str | None, str]:
    """Which locality does a printing in this language, sold under this market, belong to?

    Returns the locality and the rule that produced it, because a mapping nobody can audit is how
    a language label quietly becomes a locality again.
    """
    if language in LANGUAGE_LOCALITY:
        return LANGUAGE_LOCALITY[language], "language names its locality"
    if language in WESTERN_LANGUAGES:
        # English is the ambiguous one: the same language is printed for Western distribution and
        # for SEA regional promos. The market disambiguates it today, and the model must keep
        # asking rather than assume, because a SEA English promo is a different physical print.
        if market == "SEA promo":
            return "SEA", "Western language under SEA regional distribution"
        return "WEST", "Western language under Western distribution"
    return None, "no locality rule for this language"


def print_key(locality: str, set_code: str, number: str, variant: str,
              identifier_known: bool) -> str:
    """The proposed print id.

    While the local identifier is unknown the key is anchored to the legacy slot it was found on,
    marked so that nobody mistakes it for a real local code. #138 replaces the anchor with the
    printing's own set code and number; the alias edge back to this key is what makes that
    replacement traceable rather than a new row appearing from nowhere.
    """
    if identifier_known:
        return f"{locality}:{set_code}:{number}:{variant}"
    return f"{locality}:via-{set_code}:{number}:{variant}:unknown-local-id"


def build(cards: list[dict], units: list[dict], excluded: list[dict],
          specimens: list[dict], baseline: dict) -> dict[str, Any]:
    by_key = {(c["setCode"], str(c.get("number") or ""), c.get("variantToken") or "base"): c
              for c in cards}

    prints: dict[str, dict[str, Any]] = {}
    unit_disposition: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []

    for unit in units:
        key = (unit["setCode"], str(unit.get("number") or ""), unit.get("variant") or "base")
        card = by_key.get(key)
        market = card["market"] if card else None
        locality, rule = resolve_locality(unit["language"], market or "")

        if card is None or locality is None:
            unresolved.append({
                "unitId": unit["unitId"], "language": unit["language"],
                "reason": "no product node for the unit" if card is None else rule,
            })
            unit_disposition[unit["unitId"]] = {"disposition": "queued", "printId": None,
                                                "reason": rule if card else "orphan unit"}
            continue

        product_locality = MARKET_LOCALITY.get(market)
        identifier_known = locality == product_locality
        pid = print_key(locality, key[0], key[1], key[2], identifier_known)

        record = prints.setdefault(pid, {
            "printId": pid,
            "locality": locality,
            "localityRule": rule,
            "localSetCode": key[0] if identifier_known else None,
            "localNumber": key[1] if identifier_known else None,
            "variant": key[2],
            "localIdentifierKnown": identifier_known,
            "state": "identified" if identifier_known else "needs-local-identifier",
            "work": card["cardKey"],
            "languages": [],
            "legacyProduct": {"setCode": key[0], "number": key[1], "variant": key[2],
                              "market": market, "sourceRecord": card["productUrl"]},
            "unitIds": [],
        })
        if unit["language"] not in record["languages"]:
            record["languages"].append(unit["language"])
        record["unitIds"].append(unit["unitId"])
        unit_disposition[unit["unitId"]] = {"disposition": "carried", "printId": pid,
                                            "reason": rule}

    # A legacy product carries one print if all its claims land in one locality, several if not.
    prints_per_product: dict[tuple, list[str]] = defaultdict(list)
    for pid, record in prints.items():
        legacy = record["legacyProduct"]
        prints_per_product[(legacy["setCode"], legacy["number"], legacy["variant"])].append(pid)

    # Keyed by productUrl, which is unique, rather than by the identity tuple, which is not: three
    # PKM code-card products share ('PKM', '', 'base') because they are unnumbered. Keying the
    # disposition table by the tuple silently dropped two of the 198 rows — the first collision the
    # new model has to answer for, and a good argument for it.
    identity_collisions = defaultdict(list)
    for card in cards:
        key = (card["setCode"], str(card.get("number") or ""), card.get("variantToken") or "base")
        identity_collisions[key].append(card["productUrl"])

    card_disposition = {}
    for card in cards:
        key = (card["setCode"], str(card.get("number") or ""), card.get("variantToken") or "base")
        produced = sorted(prints_per_product.get(key, []))
        shared = len(identity_collisions[key]) > 1
        if shared:
            card_disposition[card["productUrl"]] = {
                "disposition": "queued", "printIds": produced,
                "reason": (f"identity tuple {key} is shared by "
                           f"{len(identity_collisions[key])} products; needs a distinguishing "
                           f"local identifier before it can become a print"),
            }
        elif not produced:
            card_disposition[card["productUrl"]] = {
                "disposition": "queued", "printIds": [],
                "reason": "no language claim in the legacy store, so no print can be derived yet",
            }
        else:
            card_disposition[card["productUrl"]] = {
                "disposition": "split" if len(produced) > 1 else "carried",
                "printIds": produced,
                "reason": f"{len(produced)} locality track(s) on one product",
            }

    # Code-card claims stay excluded and keep their identifiers; they are aliased, never dropped.
    excluded_disposition = {
        unit["unitId"]: {"disposition": "aliased", "printId": None,
                         "reason": "code card, excluded from the physical catalogue"}
        for unit in excluded
    }

    # Evidence that has nowhere to live: a specimen the owner holds whose set code and number match
    # no product node. SPEC-0024 (AS5a 142, T-Chinese) is the worked case and the reason
    # CATCHUP-SETS.md exists.
    product_codes = {(c["setCode"], str(c.get("number") or "")) for c in cards}
    orphan_specimens = []
    for spec in specimens:
        code = str(spec.get("setCode") or "")
        # Specimen set codes carry the locality inline for regional promos ("SV-P/ID 117").
        base_code = code.split("/")[0].strip()
        number = str(spec.get("number") or "")
        if (code, number) not in product_codes and (base_code, number) not in product_codes:
            orphan_specimens.append({
                "specimenId": spec.get("specimenId"), "setCode": code, "number": number,
                "language": spec.get("language"),
                "reason": "no product node carries this set code and number",
            })

    split_products = {k: v for k, v in prints_per_product.items() if len(v) > 1}
    needs_identifier = [p for p in prints.values() if not p["localIdentifierKnown"]]

    by_locality = Counter(p["locality"] for p in prints.values())
    unknown_by_locality = Counter(p["locality"] for p in needs_identifier)

    return {
        "meta": {
            "schema": "snoredex-print-identity-dryrun",
            "schemaVersion": SCHEMA_VERSION,
            "generated": date.today().isoformat(),
            "adr": "verification/ADR-0001-locality-aware-print-identity.md",
            "status": "dry-run — proposes nothing to the stores, migrates nothing",
            "baselineId": baseline["meta"]["baselineId"],
            "description": (
                "Maps every legacy row onto the proposed locality-aware print model and reports "
                "what the migration would have to account for. A print with "
                "localIdentifierKnown=false is a printing this repository has evidence for and no "
                "local set code or collector number to name it by."
            ),
        },
        "localities": LOCALITIES,
        "counts": {
            "legacyProducts": len(by_key),
            "legacyLanguageUnits": len(units),
            "legacyExcludedCodeCardUnits": len(excluded),
            "printNodes": len(prints),
            "printNodesIdentified": len(prints) - len(needs_identifier),
            "printNodesNeedingLocalIdentifier": len(needs_identifier),
            "productsSplitAcrossLocalities": len(split_products),
            "identityCollisions": sum(1 for v in identity_collisions.values() if len(v) > 1),
            "unresolvedUnits": len(unresolved),
            "orphanSpecimens": len(orphan_specimens),
            "printNodesByLocality": dict(sorted(by_locality.items(), key=lambda kv: -kv[1])),
            "needsLocalIdentifierByLocality": dict(
                sorted(unknown_by_locality.items(), key=lambda kv: -kv[1])),
        },
        "dispositions": {
            "cards": dict(sorted(card_disposition.items())),
            "languageUnits": dict(sorted(unit_disposition.items())),
            "excludedCodeCardUnits": dict(sorted(excluded_disposition.items())),
        },
        "reports": {
            "splitProducts": [
                {"setCode": k[0], "number": k[1], "variant": k[2], "printIds": sorted(v)}
                for k, v in sorted(split_products.items())
            ],
            "needsLocalIdentifier": sorted(
                ({"printId": p["printId"], "locality": p["locality"],
                  "languages": sorted(p["languages"]), "viaProduct": p["legacyProduct"]["setCode"]
                  + " " + p["legacyProduct"]["number"], "unitIds": sorted(p["unitIds"])}
                 for p in needs_identifier),
                key=lambda item: (item["locality"], item["viaProduct"]),
            ),
            "identityCollisions": [
                {"setCode": k[0], "number": k[1], "variant": k[2], "sourceRecords": sorted(v)}
                for k, v in sorted(identity_collisions.items()) if len(v) > 1
            ],
            "unresolvedUnits": sorted(unresolved, key=lambda item: item["unitId"]),
            "orphanSpecimens": sorted(orphan_specimens, key=lambda item: str(item["specimenId"])),
        },
        "prints": [prints[pid] for pid in sorted(prints)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the report is stale")
    args = parser.parse_args()

    cards = read_json(ROOT / "snorlax_cards.json")["cards"]
    units = read_json(ROOT / "verification" / "units.json")
    excluded = read_json(ROOT / "verification" / "excluded_codecards.json")
    specimen_doc = read_json(ROOT / "verification" / "specimens.json")
    specimens = specimen_doc["specimens"] if isinstance(specimen_doc, dict) else specimen_doc
    baseline = read_json(ROOT / "legacy-cardmarket-baseline.json")

    document = build(cards, units, excluded, specimens, baseline)

    if args.check:
        if not OUTPUT_PATH.is_file():
            print("print_identity_dryrun.json missing; run python scripts/print_identity_dryrun.py")
            return 1
        existing = read_json(OUTPUT_PATH)
        comparable = {k: v for k, v in document.items() if k != "meta"}
        if {k: v for k, v in existing.items() if k != "meta"} != comparable:
            print("print_identity_dryrun.json is stale; run python scripts/print_identity_dryrun.py")
            return 1
        print(f"print identity dry run is current "
              f"({document['counts']['printNodes']} print nodes)")
        return 0

    body = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    OUTPUT_PATH.write_text(body, encoding="utf-8")
    counts = document["counts"]
    print(f"{OUTPUT_PATH.relative_to(ROOT)}: {counts['legacyProducts']} legacy products -> "
          f"{counts['printNodes']} print nodes "
          f"({counts['printNodesNeedingLocalIdentifier']} need a local identifier)")
    print(f"  {counts['productsSplitAcrossLocalities']} products split across localities; "
          f"{counts['identityCollisions']} identity collision(s); "
          f"{counts['orphanSpecimens']} orphan specimen(s); "
          f"{counts['unresolvedUnits']} unresolved unit(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

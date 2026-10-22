"""Apply the retained 2026-10-22 data-gap research through the existing field owners.

Bulk research integration only. Every applied value is a positive observation retained in
verification/evidence/data-gaps-20261022 (finding row, source URL, retrieval time, excerpt and
sha256 of the retained bytes or of the cited repository file). Nothing is inferred from absence.

- Local set names: the source-first local-set profile keeps the source-native name in
  `raw.localName` with its provenance; the graph mirrors that record byte-for-byte and the local
  set gains it as `observedNames`.
- Illustrators: source-first prints gain `illustrator` plus provenance fields; legacy releases gain
  the Cardmarket product `artist`/`artistSource` read by checklist.py. Per the owner rule of
  2026-10-22 an illustrator belongs to the artwork, so a credit may be carried along a visually
  confirmed identical artwork (`artwork-propagation`). Recolours awaiting the owner decision are
  held back, and existing credits are never overwritten.

    python verification/passes/integrate_data_gap_research_20261022.py --check   # report only
    python verification/passes/integrate_data_gap_research_20261022.py           # write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from atomic_write import atomic_write  # noqa: E402

BUNDLE = "verification/evidence/data-gaps-20261022"
ORIGIN = "reviewed-evidence-data-gaps-20261022"
SET_NAME_STREAMS = ("id-th-sets", "korea", "chinese")
ILLUSTRATOR_STREAMS = ("korea", "chinese", "asia-artists", "jp-west-artists")

# Owner decision 2026-10-22: a rainbow/hyper-rare recolour of the same composition is the same
# artwork (the base illustration and its illustrator are unchanged), so no propagation is held.
HELD_FOR_OWNER: set[str] = set()
# The official TW database text names Masakazu Fukuda, but the card image on the same official
# page prints "Illus.aky CG Works", as does the identical-artwork CN print (SPEC-0098). The printed
# credit is the card's own statement and wins over the database text field.
PRINTED_CREDIT = {
    "RELEASE:TW:T-Chinese:sc1b F:165/153:Snorlax-V-Swallow-Falling-Down": (
        "aky CG Works",
        "Printed credit read on the official card image of this database page and on the identical "
        "CN CS1aC 188 artwork (SPEC-0098); the page's text field names Masakazu Fukuda.",
    ),
}
# The credit prints as "0313" on the card; two Asian database pages render it "313".
DISPLAY_CREDIT = {"313": "0313"}

HOST_PROVIDERS = (
    ("asia.pokemon-card.com", "pokemon-card-asia"),
    ("pokemoncard.co.kr", "pokemon-card-korea"),
    ("pokemonkorea.co.kr", "pokemon-card-korea"),
    ("pokemon.cn", "pokemon-cn-official"),
    ("pokemon-card.com", "pokemon-card-jp"),
    ("tcgdex.net", "tcgdex"),
    ("52poke.com", "52poke"),
    ("pokewiki.de", "pokewiki"),
    ("pokepedia.fr", "pokepedia"),
    ("wikidex.net", "wikidex"),
    ("pokecottage", "pokecottage"),
    ("gamespress.com", "pokemon-official"),
    ("pokemon.com", "pokemon-official"),
    ("pokemon.co.jp", "pokemon-official"),
    ("portal-pokemon.com", "pokemon-official"),
    ("bulbagarden.net", "bulbapedia"),
    ("pkparaiso.com", "pkparaiso"),
    ("cardmarket.com", "cardmarket-product-image"),
    ("ebay", "seller-listing-photo"),
    ("bunjang", "seller-listing-photo"),
    ("karousell", "seller-listing-photo"),
    ("tradera", "seller-listing-photo"),
    ("susercontent.com", "seller-listing-photo"),
    ("collectorworth", "retailer-listing"),
    ("tcgbox.co.kr", "retailer-listing"),
)


def read(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def render(document) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def provider_for(finding: dict) -> str:
    retained = finding.get("retainedPath")
    retained = retained[0] if isinstance(retained, list) else retained or ""
    url = finding.get("sourceUrl") or ""
    if retained.startswith("verification/specimens/") or "/verification/specimens/" in url:
        return "inspected-specimen"
    if retained.startswith("images/") or "/snoredex-data/images/" in url:
        return "cardmarket-product-image"
    host = urlsplit(url).hostname or ""
    for needle, provider in HOST_PROVIDERS:
        if needle in host:
            return provider
    raise ValueError(f"no registered provider for {url!r}")


def is_url(value: str) -> bool:
    return value.startswith(("https://", "http://"))


def provenance(stream: str, finding: dict) -> dict:
    # A repository photograph or product image is cited by path, never given a hyperlink (S3).
    source = finding["sourceUrl"]
    if is_url(source) and "/snoredex-data/" not in source:
        locator = {"sourceUrl": source}
    else:
        retained = finding["retainedPath"]
        locator = {"sourceRef": retained[0] if isinstance(retained, list) else retained}
    row = {
        **locator,
        "providerId": provider_for(finding),
        "retrievedAt": finding["retrievedAt"],
        "excerpt": finding["excerpt"],
        "evidencePath": finding["retainedPath"],
        "sha256": finding["sha256"],
        "confidence": finding["confidence"],
        "evidenceBundle": f"{BUNDLE}/{stream}/findings.json",
    }
    for key in ("method", "anchorCardReleaseId", "anchorSourceUrl", "comparison"):
        if finding.get(key):
            row[key] = finding[key]
    if finding.get("valueEnglish"):
        row["translation"] = finding["valueEnglish"]
    return row


def findings(field: str, streams: tuple[str, ...]):
    for stream in streams:
        document = read(f"{BUNDLE}/{stream}/findings.json")
        for finding in document["findings"]:
            if finding["field"] == field:
                yield stream, finding


def upsert(rows: list, key: str, value: dict, match) -> None:
    found = [row for row in rows if match(row)]
    if len(found) > 1:
        raise ValueError(f"ambiguous {key}")
    if found:
        found[0].clear()
        found[0].update(value)
    else:
        rows.append(value)


def apply_set_names(graph: dict, catalogue: dict, report: dict) -> None:
    """Append one name record per local set; existing provider records stay untouched.

    The registry is append-only and older admission passes rebuild their own profile records on
    replay, so a researched name lives in its own `local-set-name-record`, mapped to the local set.
    """
    entities = graph["entities"]
    local_sets = {row["entityId"]: row["payload"] for row in entities if row["entityType"] == "local-set"}
    added = 0
    for stream, finding in findings("localSetName", SET_NAME_STREAMS):
        for local_set_id in finding["targetIds"]:
            local_set = local_sets[local_set_id]
            evidence = provenance(stream, finding)
            digest = hashlib.sha256(f"{local_set_id}\x1f{finding['value']}".encode()).hexdigest()[:12].upper()
            sid = f"SET-SRC-NAME-{digest}"
            record = {
                "sourceRecordId": sid,
                "sourceKind": "local-set-name-record",
                "provider": evidence["providerId"],
                "providerRecordKey": f"{local_set['locality']}\x1f{local_set['localCode']}\x1fname",
                "retrieved": evidence["retrievedAt"][:10],
                **({"sourceUrl": evidence["sourceUrl"]} if "sourceUrl" in evidence else {}),
                "raw": {"localCode": local_set["localCode"], "locality": local_set["locality"],
                        "localName": finding["value"], **{k: v for k, v in evidence.items()
                                                          if k not in ("sourceUrl", "providerId", "retrievedAt")}},
            }
            reason = "Researched official local set name for this exact local set; name only, no membership."
            upsert(catalogue["sourceRecords"], sid, record, lambda row: row["sourceRecordId"] == sid)
            for entity_type, payload in (
                ("set-source-record", record),
                ("set-source-disposition", {"sourceRecordId": sid, "disposition": "mapped",
                                            "targetRef": local_set_id, "reason": reason}),
            ):
                upsert(entities, sid, {"entityType": entity_type, "entityId": sid, "origin": ORIGIN,
                                       "payload": payload},
                       lambda row, t=entity_type: (row["entityType"], row["entityId"]) == (t, sid))
            for edge in (("set-source-disposition", sid, "disposes", "set-source-record", sid),
                         ("local-set", local_set_id, "observed-by", "set-source-record", sid)):
                upsert(graph["edges"], sid, dict(zip(("fromType", "fromId", "relation", "toType", "toId"), edge),
                                                 provenance={}),
                       lambda row, e=edge: tuple(row[k] for k in ("fromType", "fromId", "relation", "toType", "toId")) == e)
            upsert(graph["migrationDispositions"], sid,
                   {"sourceKind": "set-catalogue-source", "sourceId": sid, "disposition": "mapped",
                    "targetRef": local_set_id, "reason": reason},
                   lambda row: (row.get("sourceKind"), row.get("sourceId")) == ("set-catalogue-source", sid))
            if sid not in local_set["sourceRecordIds"]:
                local_set["sourceRecordIds"] = sorted(local_set["sourceRecordIds"] + [sid])
                added += 1
                report["applied"].append({"target": local_set_id, "field": "localSetName",
                                          "value": finding["value"], "confidence": finding["confidence"]})
            names = local_set.get("observedNames") or []
            local_set["observedNames"] = [finding["value"], *[name for name in names if name != finding["value"]]]
    counts = catalogue["meta"]["counts"]
    counts["sourceRecords"] = len(catalogue["sourceRecords"])
    counts["localSetNameRecords"] = sum(row["sourceKind"] == "local-set-name-record"
                                        for row in catalogue["sourceRecords"])


# Wording source_registry.resolve_provider maps back to the same provider (checked at runtime).
ARTIST_SOURCE_WORDING = {
    "pokemon-card-jp": "Official Pokemon Japan card database (pokemon-card.com)",
    "inspected-specimen": "Inspected physical specimen photograph",
    "cardmarket-product-image": "Cardmarket exact product image",
    "tcgdex": "TCGdex",
    "pokemon-card-asia": "Official Pokemon Asia card database (asia.pokemon-card.com)",
}


def artist_source(evidence: dict, release_id: str, stream: str) -> str:
    from source_registry import resolve_provider

    if evidence.get("method") == "artwork-propagation":
        # Carried along an identical artwork: graded as this project's derivation, never as the
        # anchor's own source (the anchor print keeps that grade).
        provider = "internal-derivation"
        text = (f"sibling print of the same artwork as {evidence['anchorCardReleaseId']} "
                f"(artwork-propagation, owner rule 2026-10-22); anchor credit from "
                f"{ARTIST_SOURCE_WORDING[evidence['providerId']]}; target {release_id} "
                f"({BUNDLE}/{stream}/findings.json)")
    else:
        provider = evidence["providerId"]
        text = (f"{ARTIST_SOURCE_WORDING[provider]}: {evidence.get('method', 'database-credit')}, exact print "
                f"{release_id} ({BUNDLE}/{stream}/findings.json)")
    if resolve_provider(None, text) != provider:
        raise ValueError(f"artistSource wording does not resolve to {provider}: {text}")
    return text


def legacy_products(catalogue_items: dict, checklist: dict, cards: list) -> dict:
    """Map each legacy card release to its Cardmarket products through exact checklist rows."""
    rows = {row["checklistId"]: row for row in checklist["items"]}
    products = {(card["setCode"], str(card["number"]), card.get("variantToken") or "base"): card
                for card in cards}
    by_release = defaultdict(list)
    for item in catalogue_items.values():
        for legacy_id in item["legacyChecklistIds"]:
            row = rows.get(legacy_id)
            if not row:
                continue
            key = (row["setCode"], str(row["number"]), row.get("cardmarketVariant") or "base")
            if key in products and products[key] not in by_release[item["cardReleaseId"]]:
                by_release[item["cardReleaseId"]].append(products[key])
    return by_release


def apply_illustrators(graph, prints, cards, checklist, catalogue, units, report) -> None:
    releases = {row["entityId"]: row["payload"] for row in graph["entities"]
                if row["entityType"] == "card-release"}
    items = {row["itemId"]: row for row in catalogue["items"]}
    print_rows = {row["printId"]: row for row in prints["prints"]}
    products = legacy_products(items, checklist, cards)
    unit_artists = {row["unitId"]: row.get("artist") for row in units}
    claims = {row["entityId"]: row["payload"] for row in graph["entities"]
              if row["entityType"] == "candidate-claim"}
    pending_product = {}
    for stream, finding in findings("illustrator", ILLUSTRATOR_STREAMS):
        release_ids = {target if target.startswith("RELEASE:") else items[target]["cardReleaseId"]
                       for target in finding["targetIds"] if target.startswith("RELEASE:") or target in items}
        for release_id in sorted(release_ids):
            value = DISPLAY_CREDIT.get(finding["value"], finding["value"])
            evidence = provenance(stream, finding)
            if finding["value"] != value:
                evidence["sourceNativeValue"] = finding["value"]
            if release_id in PRINTED_CREDIT:
                value, basis = PRINTED_CREDIT[release_id]
                evidence.update(sourceNativeValue=finding["value"], method="image-transcription",
                                printedCreditBasis=basis)
            if release_id in HELD_FOR_OWNER:
                report["held"].append({"target": release_id, "field": "illustrator", "value": value,
                                       "reason": "recolour propagation awaits the owner's same-artwork decision"})
                continue
            release = releases.get(release_id)
            if release is None:
                report["skipped"].append({"target": release_id, "field": "illustrator",
                                          "reason": "card release not in the graph"})
                continue
            sf_ids = [pid for pid in release.get("sourceFirstRecordIds") or [] if pid in print_rows]
            if sf_ids:
                for print_id in sf_ids:
                    row = print_rows[print_id]
                    if row.get("illustrator") == value and row.get("illustratorEvidence") == evidence:
                        continue  # already applied by an earlier run
                    if row.get("illustrator") not in (None, "", value):
                        report["skipped"].append({"target": print_id, "field": "illustrator",
                                                  "reason": f"existing credit {row['illustrator']!r} kept"})
                        continue
                    row["illustrator"] = value
                    row["illustratorEvidence"] = evidence
                    report["applied"].append({"target": print_id, "field": "illustrator", "value": value,
                                              "method": evidence.get("method"), "confidence": finding["confidence"]})
                continue
            targets = products.get(release_id) or []
            if not targets:
                report["skipped"].append({"target": release_id, "field": "illustrator",
                                          "reason": "no exact Cardmarket product row for this legacy release"})
                continue
            legacy_units = [claims[ref]["sourceId"] for item in items.values()
                            if item["cardReleaseId"] == release_id for ref in item["sourceClaimRefs"]
                            if claims.get(ref, {}).get("sourceKind") == "legacy-language-unit"]
            conflicting = {unit_artists.get(unit) for unit in legacy_units} - {None, "", value}
            if conflicting:
                report["skipped"].append({"target": release_id, "field": "illustrator",
                                          "reason": f"legacy unit credit {sorted(conflicting)} differs"})
                continue
            for product in targets:
                key = product["imageFile"]
                if product.get("artist") not in (None, "", value) or pending_product.get(key, value) != value:
                    report["skipped"].append({"target": key, "field": "illustrator",
                                              "reason": f"product credit conflict ({product.get('artist') or pending_product.get(key)!r} vs {value!r})"})
                    continue
                pending_product[key] = value
                if product.get("artist") == value:
                    if BUNDLE in (product.get("artistSource") or ""):
                        product["artistSource"] = artist_source(evidence, release_id, stream)
                    continue
                product["artist"] = value
                product["artistSource"] = artist_source(evidence, release_id, stream)
                report["applied"].append({"target": key, "field": "illustrator", "value": value,
                                          "release": release_id, "method": evidence.get("method"),
                                          "confidence": finding["confidence"]})


# Owner decision 2026-10-22: SWSH068 is the Vivid Voltage prerelease promo sold in the Build &
# Battle Box, which the official press releases date 2020-10-31. These four items are its ordinary
# unmarked print. The gold "Staff" stamp is a variant of the same prerelease promo distributed in
# the Prerelease Program, and the Cosmos-holo store giveaway is a separate printing; neither is
# dated here.
HELD_DATE_ITEMS: set[str] = set()


def apply_reviewed_dates(overrides: dict, catalogue: dict, report: dict) -> None:
    """Append exact item-scoped date observations to the existing reviewed-date owner."""
    items = {row["itemId"]: row for row in catalogue["items"]}
    reviewed = overrides["releaseDates"]["reviewedItems"]
    existing = {row["itemId"] for row in reviewed}
    for _stream, finding in findings("releaseDate", ("dates",)):
        for item_id in finding["targetIds"]:
            if item_id in HELD_DATE_ITEMS:
                report["held"].append({"target": item_id, "field": "releaseDate", "value": finding["value"],
                                       "reason": "owner confirms Build & Battle promo vs Cosmos giveaway"})
                continue
            if item_id in existing:
                continue
            item = items[item_id]
            reviewed.append({
                "itemId": item_id,
                "cardReleaseId": item["cardReleaseId"],
                "physicalPrintingId": item["physicalPrintingId"],
                "localizationId": item["localizationId"],
                "sourcePrintingId": item["sourcePrintingId"],
                "legacyChecklistIds": item["legacyChecklistIds"],
                "releaseDate": finding["value"],
                "releaseDatePrecision": finding["precision"],
                "releaseApproximate": False,
                "basis": finding["identityMatch"],
                "sources": [{
                    "providerId": provider_for(finding),
                    "url": finding["sourceUrl"],
                    "retrievedAt": finding["retrievedAt"],
                    "evidencePath": f"{BUNDLE}/dates/findings.json",
                    "sourceRef": finding["retainedPath"],
                }],
            })
            report["applied"].append({"target": item_id, "field": "releaseDate", "value": finding["value"],
                                      "confidence": finding["confidence"]})


VIVID_SURFACE = "tpci-vivid-voltage-build-battle-dates"
VIVID_LANGUAGES = {"/fr/": "French", "/de/": "German", "/it/": "Italian", "/es/": "Spanish"}
VIVID_IDENTIFIERS = {
    "French": ["Boîtier Stratégies et Combats", "31 octobre"],
    "German": ["Build & Battle-Box", "31. Oktober"],
    "Italian": ["kit Sfida Strategica", "31 ottobre"],
    "Spanish": ["caja de Combina y Combate", "31 de octubre"],
}


def register_vivid_voltage_surface(capabilities: dict) -> None:
    """Declare the four localized Build & Battle press releases for their date field only."""
    edges, observations = [], []
    for _stream, finding in findings("releaseDate", ("dates",)):
        url = finding["sourceUrl"]
        if "gamespress.com" not in url:
            continue
        language = next(name for marker, name in VIVID_LANGUAGES.items() if marker in url)
        slug = language.lower()
        edge_id = f"{VIVID_SURFACE}-{slug}-swsh068-positive"
        scope = (f"Only the native {language} Vivid Voltage Build & Battle Box availability from "
                 "2020-10-31, applied to the ordinary unmarked SWSH068 prerelease promo the owner "
                 "identified as that box's promo (2026-10-22).")
        record = {
            "sourceId": f"official-vivid-voltage-build-battle-{slug}",
            "sourceUrl": url,
            "retrievedAt": finding["retrievedAt"],
            "captureMethod": "Public official localized press release over the inherited HTTPS proxy; exact visible text excerpt",
            "responseSha256": (finding.get("originalSha256") or [finding["sha256"]])[0],
            "responseHashScope": "original acquired HTTP response bytes, not excerpt",
            "excerpt": finding["excerpt"],
            "excerptSha256": hashlib.sha256(finding["excerpt"].encode("utf-8")).hexdigest(),
            "excerptHashScope": "UTF-8 bytes of the excerpt",
            "fieldLimits": "date only",
            "nativeQualifier": f"{language}-language Build & Battle Box availability",
            "date": finding["value"], "precision": finding["precision"], "approximate": False,
            "field": "source-native availability date", "scope": scope,
            "limits": "Staff-stamped prerelease variant, Cosmos-holo giveaway, other languages and finishes are outside scope.",
            "retainedContext": finding["retainedPath"],
        }
        base = {"surfaceId": VIVID_SURFACE, "queryUrl": url, "retrievedAt": finding["retrievedAt"][:10],
                "fixtureRef": {"kind": "inline-record", "record": record}}
        observations += [
            {"observationId": f"obs-{VIVID_SURFACE}-{slug}", **base, "kind": "known-positive",
             "queryParameters": {"field": "source-native availability date",
                                 "nativeQualifier": record["nativeQualifier"]},
             "expectedIdentifiers": VIVID_IDENTIFIERS[language], "validatesEdges": [edge_id], "outcome": scope},
            {"observationId": f"obs-{VIVID_SURFACE}-{slug}-boundary", **base, "kind": "out-of-scope-challenge",
             "queryParameters": {"challenge": "unsupported date/precision/locality transfer"},
             "expectedIdentifiers": VIVID_IDENTIFIERS[language], "validatesEdges": [edge_id],
             "outcome": ("The release dates the Build & Battle Box only; it neither names Snorlax nor dates "
                         "the Staff-stamped prerelease variant or the separate Cosmos-holo store giveaway.")},
        ]
        edges.append({
            "edgeId": edge_id,
            "coverage": {"localities": ["WEST"], "languages": [language], "scripts": ["Latn"],
                         "productCategories": ["product"],
                         "timeRange": {"start": finding["value"], "end": finding["value"],
                                       "basis": "Only the exact retained source-native date at its stated precision: " + scope}},
            "positiveEvidenceCapabilities": ["date", "release-date"],
            "exhaustive": False,
            "absenceCapability": {"enabled": False, "dimensions": [], "exactScopes": [],
                                  "rationale": "An explicit retained native date establishes only its matching already-known release scope. Missing rows, fields, markets and finer precision remain unknown."},
            "knownPositiveObservationId": f"obs-{VIVID_SURFACE}-{slug}",
            "outOfScopeChallengeObservationId": f"obs-{VIVID_SURFACE}-{slug}-boundary",
            "boundary": {
                "outsideScope": ["other pages, products or campaigns", "other markets or languages",
                                 "unsupported finer precision or other shipment/reprint waves",
                                 "card existence, identity or membership", "rarity or physical finish",
                                 "absence or completeness"],
                "zeroResultMeans": "unknown",
                "challenge": "The release dates the Build & Battle Box only; it neither names Snorlax nor dates the Staff-stamped prerelease variant or the separate Cosmos-holo store giveaway.",
            },
        })
    surface = {
        "surfaceId": VIVID_SURFACE, "providerId": "pokemon-official",
        "label": "Official French, German, Italian and Spanish Vivid Voltage Build & Battle Box dates",
        "match": {"urlPrefixes": sorted(edge["knownPositiveObservationId"] and
                                        next(o["queryUrl"] for o in observations if o["observationId"] == edge["knownPositiveObservationId"])
                                        for edge in edges),
                  "nonUrlEvidenceIds": []},
        "state": "active", "failureState": None, "accessMode": "manual", "adapterState": "not-applicable",
        "lastCheckedAt": "2026-10-22",
        "freshnessPolicy": "Only individually retained native date fields, original acquisition metadata and separate response/excerpt hashes. Re-review changed sources or expanded scope. No automatic acquisition adapter, completeness or finer precision is inferred.",
        "query": {"method": "MANUAL", "endpoint": observations[0]["queryUrl"], "parameters": [],
                  "pagination": "not paginated; individually reviewed source fields only",
                  "expectedIdentifiers": ["exact named product or campaign",
                                          "source-native locality/language qualifier",
                                          "source-native availability field"]},
        "finishCapability": {"mode": "none", "vocabulary": [],
                             "publicationForm": "date excerpt only; adjacent card or finish vocabulary confers no capability",
                             "closedWithinScope": False},
        "coverageEdges": edges,
    }
    upsert(capabilities["surfaces"], VIVID_SURFACE, surface, lambda row: row["surfaceId"] == VIVID_SURFACE)
    for observation in observations:
        upsert(capabilities["observations"], observation["observationId"], observation,
               lambda row, oid=observation["observationId"]: row.get("observationId") == oid)


SPECIES_KEYS = {
    "English": ("English", "WEST"), "German": ("German", "WEST"), "French": ("French", "WEST"),
    "Italian": ("Italian", "WEST"), "Spanish (Europe)": ("Spanish", "WEST"),
    "Spanish (Latin America)": ("Spanish", "LATAM"), "Portuguese": ("Portuguese", "WEST"),
    "Dutch": ("Dutch", "WEST"), "Polish": ("Polish", "WEST"), "Russian": ("Russian", "WEST"),
    "Japanese": ("Japanese", "JP"), "Korean": ("Korean", "KR"),
    "Traditional Chinese": ("T-Chinese", "TW"), "Simplified Chinese": ("S-Chinese", "CN"),
    "Thai": ("Thai", "TH"), "Indonesian": ("Indonesian", "ID"),
}
# Card names that print only the species name; the level is printed apart from the name.
SPECIES_ONLY_CARD_NAMES = ["Snorlax", "Snorlax Lv.35", "Snorlax Lv.37", "Snorlax Lv.40"]
# Owner decision 2026-10-22: these mechanic/trainer names may take their evidenced per-localization
# pattern when no exact-print name exists.
DERIVED_PATTERN_CARD_NAMES = {"Hop's Snorlax": "owner decision 2026-10-22"}


def build_local_names(catalogue: dict) -> dict:
    """Assemble the reviewed localized card-name registry from the local-names workstream."""
    localization = {(row["language"], row["locality"]): row["localizationId"]
                    for row in catalogue["localizations"]}
    items = {row["itemId"]: row for row in catalogue["items"]}
    species, patterns, releases = {}, defaultdict(dict), {}
    for _stream, finding in findings("localCardName", ("local-names",)):
        target = finding["targetIds"][0]
        evidence = provenance("local-names", finding)
        if target.startswith("species:"):
            species[localization[SPECIES_KEYS[target.split(":", 1)[1]]]] = {
                "value": finding["value"], "evidence": evidence}
        elif target.startswith("pattern:"):
            _, english, language = target.split(":", 2)
            key = localization.get(SPECIES_KEYS.get(language, (None, None)))
            patterns[english][key or language] = {"value": finding["value"], "evidence": evidence}
        for item_id in (t for t in finding["targetIds"] if t in items):
            release_id = items[item_id]["cardReleaseId"]
            entry = releases.setdefault(release_id, {"value": finding["value"], "evidence": []})
            if entry["value"] != finding["value"]:
                raise ValueError(f"conflicting exact-print names for {release_id}")
            if evidence not in entry["evidence"]:
                entry["evidence"].append(evidence)
    return {
        "schemaVersion": "1.0.0",
        "meta": {
            "description": (
                "Reviewed localized printed card names. An exact-print observation of a card "
                "release wins; otherwise a card whose English name is only the species takes the "
                "localization's official species name. A pattern listed in derivedPatternCardNames "
                "is applied per localization by owner decision; every other mechanic or "
                "trainer-owned name (ex, GX, V, VMAX, LV.X, Team Rocket's, Eevee & Snorlax, Doll) is "
                "never derived and its pattern is retained as reference only."),
            "evidenceBundle": f"{BUNDLE}/local-names/findings.json",
            "speciesOnlyCardNames": SPECIES_ONLY_CARD_NAMES,
            "derivedPatternCardNames": DERIVED_PATTERN_CARD_NAMES,
        },
        "speciesNames": dict(sorted(species.items())),
        "releases": dict(sorted(releases.items())),
        "patterns": {name: dict(sorted(rows.items())) for name, rows in sorted(patterns.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report only; write nothing")
    args = parser.parse_args(argv)

    paths = {
        "graph": "verification/authoritative_graph.json",
        "catalogue": "verification/set_catalogue_sources.json",
        "prints": "verification/source_first_prints.json",
        "cards": "snorlax_cards.json",
        "overrides": "verification/confirmed_release_overrides.json",
        "capabilities": "verification/source_capabilities.json",
    }
    documents = {name: read(path) for name, path in paths.items()}
    before = {name: render(document) for name, document in documents.items()}
    report = {"applied": [], "skipped": [], "held": []}
    apply_set_names(documents["graph"], documents["catalogue"], report)
    apply_illustrators(documents["graph"], documents["prints"], documents["cards"]["cards"],
                       read("analysis_checklist.json"), read("collector_catalogue.json"),
                       read("verification/units.json"), report)
    apply_reviewed_dates(documents["overrides"], read("collector_catalogue.json"), report)
    register_vivid_voltage_surface(documents["capabilities"])
    paths["names"] = "verification/local_card_names.json"
    names_path = ROOT / paths["names"]
    before["names"] = names_path.read_text(encoding="utf-8") if names_path.exists() else ""
    documents["names"] = build_local_names(read("collector_catalogue.json"))
    changed = [name for name, document in documents.items() if render(document) != before[name]]
    summary = defaultdict(int)
    for row in report["applied"]:
        summary[row["field"]] += 1
    print(f"applied {dict(summary)}; skipped {len(report['skipped'])}; held {len(report['held'])}; "
          f"stores changed: {changed}")
    if args.check:
        return 0
    for name in changed:
        atomic_write(ROOT / paths[name], render(documents[name]))
    atomic_write(ROOT / BUNDLE / "integration-report.json", render(state_report(documents, report)))
    return 0


def state_report(documents: dict, run: dict) -> dict:
    """Account for everything this bundle established in the stores, independent of run order."""
    marker = BUNDLE + "/"
    name_records = [row for row in documents["catalogue"]["sourceRecords"]
                    if row["sourceKind"] == "local-set-name-record"
                    and marker in (row["raw"].get("evidenceBundle") or "")]
    prints = [row for row in documents["prints"]["prints"]
              if marker in json.dumps(row.get("illustratorEvidence") or {})]
    products = [row for row in documents["cards"]["cards"] if marker in (row.get("artistSource") or "")]
    dates = [row for row in documents["overrides"]["releaseDates"]["reviewedItems"]
             if any(marker in source.get("evidencePath", "") for source in row["sources"])]
    names = documents["names"]
    return {
        "bundle": BUNDLE,
        "established": {
            "localSetNameRecords": sorted(row["sourceRecordId"] for row in name_records),
            "sourceFirstIllustrators": sorted(row["printId"] for row in prints),
            "legacyProductArtists": sorted(row["imageFile"] for row in products),
            "reviewedReleaseDates": sorted(row["itemId"] for row in dates),
            "localCardNameReleases": len(names["releases"]),
            "speciesNames": sorted(names["speciesNames"]),
        },
        "held": run["held"],
        "skipped": run["skipped"],
    }


if __name__ == "__main__":
    raise SystemExit(main())

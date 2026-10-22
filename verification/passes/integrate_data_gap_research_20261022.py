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

# Rainbow/hyper-rare recolours of an SR composition: whether a recolour counts as the same
# artwork is an open owner decision, so these propagations are not applied yet.
HELD_FOR_OWNER = {
    "RELEASE:KR:Korean:sm9:115/095:Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX",
    "RELEASE:TW:T-Chinese:AS5a:222/184:Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX",
}
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


def apply_set_names(graph: dict, catalogue: dict, report: dict) -> None:
    records = {row["sourceRecordId"]: row for row in catalogue["sourceRecords"]}
    entities = {(row["entityType"], row["entityId"]): row for row in graph["entities"]}
    for stream, finding in findings("localSetName", SET_NAME_STREAMS):
        for local_set_id in finding["targetIds"]:
            local_set = entities[("local-set", local_set_id)]["payload"]
            if local_set.get("observedNames"):
                report["skipped"].append({"target": local_set_id, "field": "localSetName",
                                          "reason": "local set already has an observed name"})
                continue
            profiles = [records[sid] for sid in local_set["sourceRecordIds"]
                        if records[sid]["sourceKind"] == "source-first-local-set-profile"]
            if not profiles:
                report["skipped"].append({"target": local_set_id, "field": "localSetName",
                                          "reason": "no source-first profile owns this local set"})
                continue
            evidence = provenance(stream, finding)
            retained_names = []
            for profile in profiles:
                raw = profile["raw"]
                if raw.get("localName") not in (None, finding["value"]):
                    # Keep an earlier retained rendering; the source-native name is added beside it.
                    retained_names.append(raw["localName"])
                    raw["nativeLocalName"] = finding["value"]
                else:
                    raw["localName"] = finding["value"]
                raw["localNameEvidence"] = evidence
                if "sourceUrl" in evidence:
                    raw["sourceUrls"] = sorted(set(raw.get("sourceUrls") or []) | {evidence["sourceUrl"]})
                raw["providers"] = sorted(set(raw.get("providers") or []) | {evidence["providerId"]})
                entities[("set-source-record", profile["sourceRecordId"])]["payload"] = profile
            local_set["observedNames"] = [finding["value"], *dict.fromkeys(retained_names)]
            report["applied"].append({"target": local_set_id, "field": "localSetName",
                                      "value": finding["value"], "confidence": finding["confidence"]})


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
                    continue
                product["artist"] = value
                product["artistSource"] = (f"{evidence['providerId']} ({evidence.get('method', 'database-credit')}, "
                                           f"exact print {release_id}; {BUNDLE}/{stream}/findings.json)")
                report["applied"].append({"target": key, "field": "illustrator", "value": value,
                                          "release": release_id, "method": evidence.get("method"),
                                          "confidence": finding["confidence"]})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report only; write nothing")
    args = parser.parse_args(argv)

    paths = {
        "graph": "verification/authoritative_graph.json",
        "catalogue": "verification/set_catalogue_sources.json",
        "prints": "verification/source_first_prints.json",
        "cards": "snorlax_cards.json",
    }
    documents = {name: read(path) for name, path in paths.items()}
    before = {name: render(document) for name, document in documents.items()}
    report = {"applied": [], "skipped": [], "held": []}
    apply_set_names(documents["graph"], documents["catalogue"], report)
    apply_illustrators(documents["graph"], documents["prints"], documents["cards"]["cards"],
                       read("analysis_checklist.json"), read("collector_catalogue.json"),
                       read("verification/units.json"), report)
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
    atomic_write(ROOT / BUNDLE / "integration-report.json", render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

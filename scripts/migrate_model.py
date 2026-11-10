#!/usr/bin/env python3
"""Write the canonical item-centric model in data/ from the committed end product.

Refactor-time migration. It reads `collector_catalogue.json` and the JSON blocks of `index.html`
and `gallery.html`, the evidence layer from the committed `snoredex.sqlite` (the normalized frozen
end product: language claims, finish units and printings, sources, providers, languages), and of the
curated stores only `site/gallery-review.json` (the card release a gallery research placeholder
varies) and the source registry's frozen page counts. Everything `scripts/build.py` can derive is
left out. Deterministic and re-runnable while main moves on.

    python scripts/migrate_model.py
    python scripts/migrate_model.py --check     # exit 1 if a fresh run would change data/
    python scripts/migrate_model.py --coverage  # reproduce every kept table of snoredex.sqlite
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

import build

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPO_BLOB = "https://github.com/m4s-ai/snoredex-data/blob/main/"
SPECIMEN_DIR = "verification/specimens/"
DATE_FIELDS = ("releaseDate", "releaseDatePrecision", "releaseApproximate")
# Item fields that are facts about one printing; every other catalogue item field is derived.
PRINTING_FIELDS = (
    "itemId", "legacyChecklistIds", "active", "itemKind", "progressClass", "workId",
    "workMappingState", "setEditionId", "cardReleaseId", "physicalPrintingId", "sourcePrintingId",
    "finishUnitId", "sourceClaimRefs", "cardName", "localCardName", "collectorNumber",
    "collectorNumberDenominator", "edition", "editionAssignmentStatus", "finishVerificationStatus",
    "finish", "finishGroupId", "foilPattern", "markings", "distribution", "cardSize", "errorClass",
    "rarity", "completenessStatus", "completenessEvidence", "imageAssetId",
)
LEGACY_QUALITY = ("authoritativeGraphFingerprint", "authoritativeGraphSchemaVersion",
                  "discoveryTerminalState", "setDiscoveryRun", "cardDiscoveryRun", "predecessor")
IMAGE_FIELDS = ("thumbnail", "preview", "imageSource", "imageScope")
DB = ROOT / "snoredex.sqlite"
FLAGS = {"corroborated", "is_code_card", "date_approximate"}
DISTRIBUTION = ("kind", "name", "region", "date")
# Dropped on purpose: dated marketplace context (owner decision for the re-cut database).
PRODUCT_DROPPED = ("marketplace_reverse_holo_hint", "marketplace_first_edition_hint")
# Every language unit descends from the marketplace candidate universe, and no external source
# supports absence: both product_languages columns are the same value on every row.
CLAIM_CONSTANTS = {"marketplace_claimed": 1, "absence_supported": 0}
# Old-database metadata kept as recorded; the other keys are derived (see coverage) or dropped.
STORED_META = ("application_status_policy", "generated", "graph_edge_count", "graph_entity_count",
               "graph_generated", "graph_migration_input_count", "graph_source", "graph_status",
               "history_included", "schema", "schema_version", "scope")
DROPPED_META = ("generator_sha256", "source_fingerprint_sha256")  # and every input_sha256:* key
REGISTRY_COUNTS = ("claimsAttributed", "evidenceRecords", "uniqueUrls", "nonUrlEvidenceClasses")


def dump(document: dict) -> str:
    """The data/ format: top-level keys in order, one record (or header object) per line."""
    line = lambda value: json.dumps(value, ensure_ascii=False)
    parts = []
    for key, value in document.items():
        if isinstance(value, list) and value:
            parts.append(f"{line(key)}: [\n" + ",\n".join(map(line, value)) + "\n]")
        else:
            parts.append(f"{line(key)}: {line(value)}")
    return "{\n" + ",\n".join(parts) + "\n}\n"


def html_block(name: str, element_id: str):
    text = (ROOT / name).read_text(encoding="utf-8")
    match = re.search(rf'<script type="application/json" id="{element_id}">(.*?)</script>', text, re.S)
    return json.loads(match.group(1))


def unpublished(link: str | None) -> str | None:
    """Undo site.py's published_link: a specimen original is stored as its repository path."""
    return link.removeprefix(REPO_BLOB) if link and link.startswith(REPO_BLOB + SPECIMEN_DIR) else link


def printing_record(item: dict, edition: dict, row: dict | None) -> tuple[dict, dict]:
    """The stored facts of one item, and its evidence record."""
    record = {key: item[key] for key in PRINTING_FIELDS if key in item}
    record["identityAnchor"] = item["releaseSortKey"].split("|", 4)[4]
    if any(item[key] != edition[key] for key in DATE_FIELDS):  # only a real override of the edition date
        record.update({key: item[key] for key in DATE_FIELDS})
    assert item["evidenceLinks"] == item["sourceLinks"], item["itemId"]
    links = {"itemId": item["itemId"], "sourceLinks": item["sourceLinks"]}
    if row is None:
        return record, links
    assert (row["sourceRowId"], row["splitPhysicalPrinting"]) == (row["rowId"], False), row["rowId"]
    if row["artist"]:
        record["artist"] = row["artist"]
    (grade,) = row["langEvidence"].values()
    links["languageEvidence"] = {key: grade[key] for key in ("provider", "corroborated", "checkable")}
    links["dateSource"] = row["dateSource"]
    return record, links


def asset_records(catalogue: dict, rows: dict, items: dict) -> list[dict]:
    """Assets; a specimen original also records the preview derivative the table shows."""
    previews = {}
    for row in filter(lambda row: row["image"] and items[row["rowId"]]["imageAssetId"], rows.values()):
        previews.setdefault(items[row["rowId"]]["imageAssetId"], row["image"])
    assets = []
    for asset in catalogue["assets"]:
        record = {key: asset[key] for key in ("assetId", "path", "sha256", "imageScope", "altTextBasis")}
        if asset["path"].startswith(SPECIMEN_DIR) and asset["assetId"] in previews:
            record["preview"] = previews[asset["assetId"]]
        assets.append(record)
    return sorted(assets, key=lambda row: row["assetId"])


def placeholder_record(card: dict, items: dict, research: dict) -> dict:
    release = research[card["id"]]["release"]
    base = min(i for i, row in items.items() if row["cardReleaseId"] == release and row["finish"] == "non-holo")
    assert all(card[key] is None for key in IMAGE_FIELDS), card["id"]
    return {"id": card["id"], "baseItemId": base, "finish": card["finish"], "foilPattern": card["foilPattern"],
            "distribution": card["distribution"], "status": card["status"], "note": card["note"],
            "sources": card["sources"]}


def gallery_image(card: dict) -> dict | None:
    """The prepared image of one card; a card without a recipe shows none."""
    if not card.get("imageRecipe"):
        assert all(card[key] is None for key in IMAGE_FIELDS), card["id"]
        return None
    sizes = card["imageSizes"]
    assert (card["thumbnail"], card["preview"], card["imageWidth"], card["imageHeight"]) == (
        sizes[0]["path"], sizes[-1]["path"], sizes[-1]["width"], sizes[-1]["height"]), card["id"]
    return {"itemId": card["id"], "recipe": card["imageRecipe"], "mediaKind": card["mediaKind"],
            "scope": card["imageScope"], "source": unpublished(card["imageSource"]), "images": sizes}


def images_document(catalogue: dict, rows: dict, items: dict, cards: list) -> dict:
    research = {row["id"]: row for row in json.loads(
        (ROOT / "site/gallery-review.json").read_text(encoding="utf-8"))["research"]}
    placeholders = [placeholder_record(card, items, research) for card in cards if card["id"] not in items]
    cards = [card for card in cards if card["id"] in items]
    groups = {}
    for card in cards:
        release = items[card["id"]]["cardReleaseId"]
        assert groups.setdefault(release, card["group"]) == card["group"], release
    return {
        "assets": asset_records(catalogue, rows, items),
        "galleryImages": sorted(filter(None, map(gallery_image, cards)), key=lambda row: row["itemId"]),
        "artworkGroups": [{"cardReleaseId": k, "group": v} for k, v in sorted(groups.items()) if k != v],
        "placeholders": sorted(placeholders, key=lambda row: row["id"]),
    }


def without(rows: list, key: str, *drop: str) -> list:
    return sorted(({k: v for k, v in row.items() if k not in drop} for row in rows), key=lambda row: row[key])


def read_store(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))


def registry_counts() -> dict:
    """Frozen page copy: counts over the source registry's evidence index, which is not migrated."""
    counts = read_store("verification/source_registry.json")["meta"]["counts"]
    return {key: counts[key] for key in REGISTRY_COUNTS}


# --- the evidence layer, from the committed snoredex.sqlite (the normalized frozen end product) ---

def camel(column: str) -> str:
    head, *rest = column.removesuffix("_json").split("_")
    return head + "".join(word.title() for word in rest)


def field(column: str, value):
    if column.endswith("_json") and value is not None:
        return json.loads(value)
    return bool(value) if column in FLAGS and value is not None else value


def record(row: dict, drop=()) -> dict:
    """A database row as a model record: camelCase names, JSON columns parsed, flags as booleans."""
    return {camel(key): field(key, value) for key, value in row.items() if key not in drop}


def query(db, sql: str) -> list[dict]:
    return [dict(row) for row in db.execute(sql)]


def grouped(rows: list, key) -> defaultdict:
    groups = defaultdict(list)
    for row in rows:
        groups[key(row)].append(row)
    return groups


def open_db():
    db = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def verdict(claim: dict) -> dict:
    """The unit's own status is the repository verdict, beside the derived application status."""
    return {("repositoryVerdict" if key == "verificationStatus" else key): value for key, value in claim.items()}


def language_claims(db) -> list[dict]:
    """One record per language unit, its Cardmarket product identity and product facts inline."""
    products = {row["product_id"]: record(row, ("product_id", *PRODUCT_DROPPED))
                for row in query(db, "SELECT * FROM products")}
    axes = grouped(query(db, "SELECT * FROM product_axes ORDER BY product_id, axis"), lambda row: row["product_id"])
    editions = grouped(query(db, "SELECT * FROM product_editions ORDER BY product_id, language_code, edition"),
                       lambda row: (row["product_id"], row["language_code"]))
    claims = []
    for row in query(db, "SELECT * FROM product_languages ORDER BY unit_id"):
        pid, code = row["product_id"], row["language_code"]
        assert {key: row[key] for key in CLAIM_CONSTANTS} == CLAIM_CONSTANTS, row["unit_id"]
        claims.append({"unitId": row["unit_id"], "productId": pid, "languageCode": code, **products[pid],
                       "axes": [axis["axis"] for axis in axes[pid]],
                       **verdict(record(row, ("product_id", "language_code", "unit_id", *CLAIM_CONSTANTS))),
                       "editions": [record(e, ("product_id", "language_code")) for e in editions[(pid, code)]]})
    return claims


def finish_units(db) -> list[dict]:
    products = grouped(query(db, "SELECT * FROM finish_unit_products ORDER BY finish_unit_id, product_id"),
                       lambda row: row["finish_unit_id"])
    return [dict(record(row), products=[record(p, ("finish_unit_id",)) for p in products[row["finish_unit_id"]]])
            for row in query(db, "SELECT * FROM finish_units ORDER BY finish_unit_id")]


def orphan_printing(row: dict, marks: list) -> dict:
    """A finish printing no catalogue item carries: its facts are stored here, once."""
    distribution = {key: row["distribution_" + key] for key in DISTRIBUTION if row["distribution_" + key]}
    return {"finishUnitId": row["finish_unit_id"], "finish": row["finish"], "foilPattern": row["foil_pattern"],
            "cardSize": row["card_size"], "verificationStatus": row["verification_status"],
            "distribution": distribution or None, "markings": marks}


def finish_printing(row: dict, item: dict | None, assets: dict, links: dict) -> dict:
    """The finish-store facts of one printing that are not already on its item."""
    rec = {"printingId": row["printing_id"]}
    if item is None:
        rec.update(orphan_printing(row, links["markings"]))
    if links["product"]:
        rec["productId"] = links["product"]
    if row["release_date"]:
        rec["releaseDate"] = row["release_date"]
    if row["image_path"] != assets.get((item or {}).get("imageAssetId")):
        rec["image"] = row["image_path"]
    rec["sources"] = [{"providerId": s["provider_id"], "source": json.loads(s["source_json"])}
                      for s in links["sources"]]
    return rec


def finish_printings(db, printings: list, assets: dict) -> list[dict]:
    items = {row["sourcePrintingId"]: row for row in printings if row["sourcePrintingId"]}
    marks = grouped(query(db, "SELECT * FROM printing_markings ORDER BY printing_id, marking_order"),
                    lambda row: row["printing_id"])
    products = {row["printing_id"]: row["product_id"] for row in query(db, "SELECT * FROM printing_product_map")}
    sources = grouped(query(db, "SELECT * FROM printing_sources ORDER BY printing_id, source_order"),
                      lambda row: row["printing_id"])
    return [finish_printing(row, items.get(row["printing_id"]), assets, {
        "markings": [record(m, ("printing_id", "marking_order")) for m in marks[row["printing_id"]]],
        "product": products.get(row["printing_id"]), "sources": sources[row["printing_id"]]})
        for row in query(db, "SELECT * FROM printings ORDER BY printing_id")]


def providers(db) -> list[dict]:
    rows = query(db, "SELECT * FROM providers ORDER BY provider_id")
    assert all(row["supports_absence"] == 0 for row in rows)  # external providers never support absence (E9)
    return [record(row, ("supports_absence",)) for row in rows]


def claims_document(db, printings: list, assets: dict) -> dict:
    meta = {row["key"]: row["value"] for row in query(db, "SELECT * FROM metadata")}
    return {
        "meta": {"legacyDatabase": {key: meta[key] for key in STORED_META}},
        "languageClaims": language_claims(db),
        "releaseRows": [record(row, ("date_sort",)) for row in query(db, "SELECT * FROM release_rows ORDER BY row_id")],
        "finishUnits": finish_units(db),
        "finishPrintings": finish_printings(db, printings, assets),
    }


def provider_ids(evidence: list, records: list) -> list:
    """Reference each item's language-evidence provider by id; the display name is derived."""
    by_name = {row["displayName"]: row["providerId"] for row in records}
    assert len(by_name) == len(records), "provider display names are not unique"
    for row in filter(lambda row: "languageEvidence" in row, evidence):
        grade = row["languageEvidence"]
        row["languageEvidence"] = {"providerId": by_name[grade.pop("provider")], **grade}
    return evidence


def printings_meta(catalogue: dict) -> dict:
    quality = catalogue["qualitySummary"]
    return {"dataAsOf": catalogue["meta"]["dataAsOf"],
            "siteGenerated": html_block("index.html", "data-meta")["generated"],
            "previousFingerprint": catalogue["meta"]["previousFingerprint"],
            "legacyQuality": {key: quality[key] for key in LEGACY_QUALITY}}


def sets_document(catalogue: dict, db) -> dict:
    return {
        "localizations": without(catalogue["localizations"], "localizationId"),
        "languages": [record(row) for row in query(db, "SELECT * FROM languages ORDER BY display_order")],
        "localSets": without(catalogue["localSets"], "localSetId", "sortKey"),
        "setEditions": without(catalogue["setEditions"], "setEditionId", "localSetCode", "localSetName", "sortKey"),
        "works": without(catalogue["works"], "workId", "displayName")}


def model() -> dict[str, str]:
    catalogue = json.loads((ROOT / "collector_catalogue.json").read_text(encoding="utf-8"))
    rows = {row["rowId"]: row for row in html_block("index.html", "data-rows")}
    editions = {row["setEditionId"]: row for row in catalogue["setEditions"]}
    items = {row["itemId"]: row for row in catalogue["items"]}
    assert len(rows) == sum(row["itemKind"] == "verified-printing" for row in items.values() if row["active"])
    records = [printing_record(items[i], editions[items[i]["setEditionId"]], rows.get(i)) for i in sorted(items)]
    printings = [printing for printing, _ in records]
    db = open_db()
    provider_rows = providers(db)
    return {
        "printings.json": dump({"meta": printings_meta(catalogue), "printings": printings}),
        "sets.json": dump(sets_document(catalogue, db)),
        "images.json": dump(images_document(catalogue, rows, items, html_block("gallery.html", "gallery-data"))),
        "evidence.json": dump({"meta": {"frozenRegistryCounts": registry_counts()}, "providers": provider_rows,
                               "printings": provider_ids([links for _, links in records], provider_rows)}),
        "claims.json": dump(claims_document(db, printings,
                                            {row["assetId"]: row["path"] for row in catalogue["assets"]})),
    }


# --- --coverage: every kept table of the old database, reproduced from data/ and the owner files ---

def canonical(columns: list, values) -> str:
    """One row, comparable across the database and the model (JSON parsed, booleans as integers)."""
    row = [json.loads(v) if c.endswith("_json") and isinstance(v, str) else v for c, v in zip(columns, values)]
    return json.dumps([int(v) if isinstance(v, bool) else v for v in row], ensure_ascii=False, sort_keys=True)


def compare(db, table: str, columns: list, rows, where: str = "") -> bool:
    old = Counter(canonical(columns, row) for row in db.execute(f"SELECT {', '.join(columns)} FROM {table} {where}"))
    new = Counter(canonical(columns, row) for row in rows)
    ok = old == new
    missing, extra = sum((old - new).values()), sum((new - old).values())
    verdict = "reproduced" if ok else f"NOT reproduced: {missing} missing, {extra} extra"
    print(f"{table}: {sum(old.values())} rows, {len(columns)} kept columns, {verdict}")
    return ok


def table_columns(db, table: str, dropped=()) -> list:
    return [row[1] for row in db.execute(f"PRAGMA table_info({table})") if row[1] not in dropped]


def values(records, columns: list, **fixed) -> list:
    """The `columns` of each model record, by the record() naming rule; `fixed` fills derived ones."""
    return [tuple(fixed[c] if c in fixed else rec.get(camel(c)) for c in columns) for rec in records]


def printing_rows(model: dict) -> list[dict]:
    """The finish printings as the old `printings` table held them, items supplying the shared facts."""
    items = {row["sourcePrintingId"]: row for row in model["printings"] if row["sourcePrintingId"]}
    assets = {row["assetId"]: row["path"] for row in model["assets"]}
    rows = []
    for rec in model["finishPrintings"]:
        item = items.get(rec["printingId"])
        base = rec if item is None else {
            "finishUnitId": item["finishUnitId"], "finish": item["finish"], "foilPattern": item["foilPattern"],
            "cardSize": item["cardSize"], "verificationStatus": item["finishVerificationStatus"],
            "distribution": item["distribution"], "markings": item["markings"]}
        rows.append(dict(base, printingId=rec["printingId"], releaseDate=rec.get("releaseDate"),
                         imagePath=rec.get("image", assets.get((item or {}).get("imageAssetId"))),
                         finishFamily=build.CATALOGUE_FAMILY.get(base["finish"]),
                         **{"distribution" + k.title(): (base["distribution"] or {}).get(k) for k in DISTRIBUTION}))
    return rows


def source_rows(model: dict) -> list:
    return [(rec["printingId"], order, s["providerId"], src.get("url"), src.get("identityUrl"), src["sourceType"],
             src["evidence"], src.get("authorityTier"), src.get("coverage"),
             0 if "supportsAbsence" in src else None, src.get("retrievedAt"), src)
            for rec in model["finishPrintings"] for order, s in enumerate(rec["sources"]) for src in [s["source"]]]


def metadata_rows(model: dict) -> list:
    quality = model["meta"]["legacyQuality"]
    owner = read_store("verification/owner_adjudications.json")
    document = build.catalogue(model["printingsDoc"], model["sets"], model["images"], model["evidence"])
    derived = {
        **{"candidate_universe_" + camel_key: build.COVERAGE[key] for camel_key, key in (
            ("id", "candidateUniverseId"), ("manifest", "manifest"), ("scope_status", "scopeStatus"),
            ("type", "candidateUniverseType"))},
        "legacy_source_commit": build.COVERAGE["sourceCommit"],
        "checklist_schema_version": quality["predecessor"]["schemaVersion"],
        "graph_schema_version": quality["authoritativeGraphSchemaVersion"],
        "collector_catalogue_fingerprint": document["meta"]["catalogueFingerprint"],
        "collector_catalogue_schema_version": build.CATALOGUE_META["schemaVersion"],
        "collector_compatibility_schema_version": build.LEGACY_COMPATIBILITY["schemaVersion"],
        "owner_adjudications_schema_version": owner["meta"]["schemaVersion"],
    }
    return list({**model["claimsMeta"]["legacyDatabase"], **derived}.items())


def claim_tables(db, claims: list) -> list[bool]:
    products = {rec["productId"]: rec for rec in claims}
    product_columns = table_columns(db, "products", PRODUCT_DROPPED)
    return [
        compare(db, "products", product_columns, set(values(claims, product_columns))),
        compare(db, "product_languages", table_columns(db, "product_languages"),
                values([dict(rec, verificationStatus=rec["repositoryVerdict"]) for rec in claims],
                       table_columns(db, "product_languages"), **CLAIM_CONSTANTS)),
        compare(db, "product_axes", ["product_id", "axis"],
                [(pid, axis) for pid, rec in products.items() for axis in rec["axes"]]),
        compare(db, "product_editions", table_columns(db, "product_editions"),
                [(rec["productId"], rec["languageCode"], e["edition"], e["editionSystem"], e["source"])
                 for rec in claims for e in rec["editions"]]),
    ]


def finish_tables(db, model: dict) -> list[bool]:
    printings = printing_rows(model)
    return [
        compare(db, "finish_units", table_columns(db, "finish_units"), values(model["finishUnits"],
                table_columns(db, "finish_units"))),
        compare(db, "finish_unit_products", table_columns(db, "finish_unit_products"),
                [(u["finishUnitId"], p["productId"], p["claimStatus"]) for u in model["finishUnits"]
                 for p in u["products"]]),
        compare(db, "printings", table_columns(db, "printings"), values(printings, table_columns(db, "printings"))),
        compare(db, "printing_markings", table_columns(db, "printing_markings"),
                [(p["printingId"], n, m["kind"], m["text"], m["role"]) for p in printings
                 for n, m in enumerate(p["markings"])]),
        compare(db, "printing_product_map", ["printing_id", "product_id"],
                [(p["printingId"], p["productId"]) for p in model["finishPrintings"] if "productId" in p]),
        compare(db, "printing_sources", table_columns(db, "printing_sources"), source_rows(model)),
    ]


def owner_tables(db) -> list[bool]:
    decisions = read_store("verification/owner_adjudications.json")["decisions"]
    specimens = read_store("verification/specimens.json")["specimens"]
    return [
        compare(db, "owner_adjudications", table_columns(db, "owner_adjudications"),
                [(d["adjudicationId"], d["unitId"], d["decision"], d["authority"], d["basis"], d["decidedAt"],
                  d["rationale"], d["evidenceRefs"]) for d in decisions]),
        compare(db, "specimens", ["specimen_id", "specimen_json"], [(s["specimenId"], s) for s in specimens]),
    ]


def unreachable_refs(db, model: dict) -> Counter:
    """Checklist evidence refs (dropped table) that the item's sourceLinks and sources do not reach."""
    items = {row["itemId"]: row for row in model["printings"]}
    links = {row["itemId"]: set(row["sourceLinks"]) for row in model["evidence"]["printings"]}
    # A checklist ref is a source's URL, or its source type where it has none (collector_catalogue.py).
    sources = {rec["printingId"]: {s["source"].get(k) for s in rec["sources"]
                                   for k in ("url", "identityUrl", "sourceType")}
               for rec in model["finishPrintings"]}
    missing = Counter()
    for item_id, ref in db.execute("SELECT i.collector_item_id, r.evidence_ref FROM checklist_evidence_refs r "
                                   "JOIN checklist_items i USING (checklist_id)"):
        reach = links[item_id] | sources.get(items[item_id]["sourcePrintingId"], set())
        if ref not in reach:
            missing[re.sub(r"^(\w+:|https?://([^/]+)).*", r"\1\2", ref)] += 1
    return missing


def coverage() -> int:
    model = {name: json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
             for name in ("printings", "sets", "images", "evidence", "claims")}
    flat = {"printings": model["printings"]["printings"], "meta": model["printings"]["meta"],
            "assets": model["images"]["assets"], "printingsDoc": model["printings"], "sets": model["sets"],
            "images": model["images"], "evidence": model["evidence"], "claimsMeta": model["claims"]["meta"],
            **{key: model["claims"][key] for key in ("finishUnits", "finishPrintings")}}
    db = open_db()
    release_rows = [dict(row, dateSort=build.release_sort(row["releaseDate"]))
                    for row in model["claims"]["releaseRows"]]
    results = [
        compare(db, "languages", table_columns(db, "languages"), values(model["sets"]["languages"],
                table_columns(db, "languages"))),
        compare(db, "providers", table_columns(db, "providers"), values(model["evidence"]["providers"],
                table_columns(db, "providers"), supports_absence=0)),
        *claim_tables(db, model["claims"]["languageClaims"]),
        compare(db, "release_rows", table_columns(db, "release_rows"), values(release_rows,
                table_columns(db, "release_rows"))),
        *finish_tables(db, flat), *owner_tables(db),
        compare(db, "metadata", ["key", "value"], metadata_rows(flat), f"WHERE key NOT LIKE 'input_sha256:%' "
                f"AND key NOT IN ({', '.join(repr(k) for k in DROPPED_META)})"),
    ]
    missing = unreachable_refs(db, flat)
    print(f"checklist_evidence_refs (dropped): {sum(missing.values())} refs not reachable from the item "
          f"{dict(missing) if missing else ''}")
    print(f"coverage: {sum(results)} of {len(results)} kept tables reproduced")
    return 0 if all(results) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if data/ is stale; write nothing")
    parser.add_argument("--coverage", action="store_true",
                        help="reproduce every kept table of snoredex.sqlite from data/; write nothing")
    args = parser.parse_args()
    if args.coverage:
        return coverage()
    files = model()
    stale = [name for name, text in files.items()
             if not (DATA / name).is_file() or (DATA / name).read_text(encoding="utf-8") != text]
    if args.check:
        print(f"stale: {', '.join(stale)}; run python scripts/migrate_model.py" if stale else "data/ is current")
        return 1 if stale else 0
    DATA.mkdir(exist_ok=True)
    for name in stale:
        (DATA / name).write_text(files[name], encoding="utf-8", newline="\n")
    print(f"data/: {len(files) - len(stale)} current, {len(stale)} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())

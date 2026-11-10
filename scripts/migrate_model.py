#!/usr/bin/env python3
"""Write the canonical item-centric model in data/ from the committed end product.

Refactor-time migration (Phase 1a). It reads `collector_catalogue.json` and the JSON blocks of
`index.html` and `gallery.html`; the only curated store it reads is `site/gallery-review.json`, for
the card release a gallery research placeholder varies. Everything `scripts/build.py` can derive
is left out. Deterministic and re-runnable while main moves on.

    python scripts/migrate_model.py
    python scripts/migrate_model.py --check    # exit 1 if a fresh run would change data/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

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


def provider_tiers(rows: dict) -> list[dict]:
    grades = {(g["provider"], g["tier"]) for row in rows.values() for g in row["langEvidence"].values()}
    tiers = dict(grades)
    assert len(tiers) == len(grades), "a provider has two tiers"
    return [{"provider": k, "authorityTier": v} for k, v in sorted(tiers.items())]


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


def model() -> dict[str, str]:
    catalogue = json.loads((ROOT / "collector_catalogue.json").read_text(encoding="utf-8"))
    rows = {row["rowId"]: row for row in html_block("index.html", "data-rows")}
    editions = {row["setEditionId"]: row for row in catalogue["setEditions"]}
    items = {row["itemId"]: row for row in catalogue["items"]}
    assert len(rows) == sum(row["itemKind"] == "verified-printing" for row in items.values() if row["active"])
    records = [printing_record(items[i], editions[items[i]["setEditionId"]], rows.get(i)) for i in sorted(items)]
    quality = catalogue["qualitySummary"]
    return {
        "printings.json": dump({
            "meta": {"dataAsOf": catalogue["meta"]["dataAsOf"],
                     "siteGenerated": html_block("index.html", "data-meta")["generated"],
                     "previousFingerprint": catalogue["meta"]["previousFingerprint"],
                     "legacyQuality": {key: quality[key] for key in LEGACY_QUALITY}},
            "printings": [record for record, _ in records]}),
        "sets.json": dump({
            "localizations": without(catalogue["localizations"], "localizationId"),
            "localSets": without(catalogue["localSets"], "localSetId", "sortKey"),
            "setEditions": without(catalogue["setEditions"], "setEditionId", "localSetCode", "localSetName", "sortKey"),
            "works": without(catalogue["works"], "workId", "displayName")}),
        "images.json": dump(images_document(catalogue, rows, items, html_block("gallery.html", "gallery-data"))),
        "evidence.json": dump({"providers": provider_tiers(rows), "printings": [links for _, links in records]}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if data/ is stale; write nothing")
    args = parser.parse_args()
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

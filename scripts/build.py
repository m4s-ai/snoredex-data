#!/usr/bin/env python3
"""Build the end product from the canonical model in data/.

Reads data/, the page templates (templates/index.html, and site/gallery.html in place) and the
owner's publication-decisions.json, owner adjudications and specimens, and writes into --out:
collector_catalogue.json, index.html, gallery.html, snoredex.sqlite (its contract is
templates/schema.sql) and snoredex-tracker-template.sqlite. It never reads the committed outputs.

    python scripts/build.py --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote, urlencode

import collection

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

REPOSITORY = "https://github.com/m4s-ai/snoredex-data"
ASSET_BASE_URL = "https://m4s-ai.github.io/snoredex-data/"
SPECIMEN_ASSET_BASE_URL = "https://raw.githubusercontent.com/m4s-ai/snoredex-data/main/"
REPO_BLOB = REPOSITORY + "/blob/main/"
SPECIMEN_DIR = "verification/specimens/"
DATE_FIELDS = ("releaseDate", "releaseDatePrecision", "releaseApproximate")
UNDATED = "9999-99-99"
MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
ATTRIBUTION = {"rightsStatus": "third-party-rights-excluded-from-project-grants",
               "licenceRef": "LICENSE.md", "noticeRef": "THIRD_PARTY_NOTICES.md"}
# Catalogue contract 1.0.0 constants.
CATALOGUE_META = {"schema": "snoredex-collector-catalogue", "schemaVersion": "1.0.0",
                  "datasetId": "snoredex-data/snorlax-current-known", "sourceRepository": REPOSITORY}
CATALOGUE_SCOPE = {"policy": "positive-evidence/current-known", "allLocalitiesComplete": False,
                   "absenceIsNotEvidence": True}
CANDIDATE_PROGRESS_POLICY = {
    "progressClass": "research", "status": "owner-decision-accepted",
    "basis": "positive-printing-evidence-or-later-dated-explicit-owner-decision-required-for-promotion",
    "decisionRef": "https://github.com/m4s-ai/snoredex-checklist/issues/5#issuecomment-5407399741"}
LEGACY_COMPATIBILITY = {
    "schema": "snoredex-legacy-collector-compatibility", "schemaVersion": "1.0.0",
    "legacyStableId": "checklistId", "collectorStableId": "itemId",
    "stateFields": ["itemKind", "progressClass", "finishVerificationStatus"],
    "collectionProjection": {"current-known": "need", "research": "research"}}
# The frozen legacy Cardmarket baseline (legacy-cardmarket-baseline.json is immutable).
COVERAGE = {"candidateUniverseId": "cardmarket-search-2026-07-21",
            "candidateUniverseType": "historical-marketplace-search",
            "manifest": "legacy-cardmarket-baseline.json",
            "scopeStatus": "legacy-not-all-locality-complete",
            "sourceCommit": "32d43304a9b87ceacd73f08119d312ae3003580c"}
CORRECTION_URL_MAX_LENGTH = 6000

ITEM_FIELDS = (
    "itemId", "legacyChecklistIds", "active", "itemKind", "progressClass", "workId", "workMappingState",
    "setEditionId", "localSetId", "cardReleaseId", "physicalPrintingId", "sourcePrintingId", "finishUnitId",
    "sourceClaimRefs", "localizationId", "cardName", "localCardName", "localSetCode", "localSetName",
    "collectorNumber", "collectorNumberDenominator", "collectorNumberSortKey", "edition",
    "editionAssignmentStatus", "finishVerificationStatus", "finish", "finishFamily", "finishGroupId",
    "foilPattern", "markings", "distribution", "cardSize", "errorClass", "rarity", "completenessStatus",
    "completenessEvidence", *DATE_FIELDS, "releaseSortKey", "imageAssetId", "imageScope", "sourceLinks",
    "evidenceLinks", "correctionLink",
)
CATALOGUE_FAMILY = {"non-holo": "non-holo", "holo": "holo", "reverse-holo": "reverse-holo",
                    "mirror-holo": "reverse-holo", "unknown": "unknown"}
TABLE_FAMILY = {key: value for key, value in CATALOGUE_FAMILY.items() if key != "unknown"}
FINISH_LABEL = {"non-holo": "Non-Holo", "holo": "Holo", "reverse-holo": "Reverse Holo"}
STATUS_RANK = {"pending": 0, "other-product": 1, "unmapped": 2, "marketplace-claimed": 3,
               "owner-attested": 4, "observed": 5, "confirmed": 5}
LANG_CODE = {
    "English": "EN", "French": "FR", "German": "DE", "Italian": "IT", "Spanish": "ES",
    "Portuguese": "PT", "Dutch": "NL", "Polish": "PL", "Russian": "RU", "Japanese": "JA",
    "Korean": "KO", "T-Chinese": "ZH-T", "S-Chinese": "ZH-S", "Indonesian": "ID", "Thai": "TH",
    "Spanish (Latin America)": "ES-LA",
}


def read(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def natural_key(value) -> str:
    return re.sub(r"\d+", lambda match: match.group(0).zfill(12), str(value or "").casefold())


def release_sort(value: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return value + "-01"
    return value[:4] + "-01-01"


def number_key(number: str):
    match = re.match(r"\D*(\d+)", number or "")
    return int(match.group(1)) if match else float("inf")


def printed_number(item: dict) -> str:
    number = item["collectorNumber"] or ""
    return number + "/" + item["collectorNumberDenominator"] if number and item["collectorNumberDenominator"] else number


def published_link(path):
    return REPO_BLOB + path if path and path.startswith(SPECIMEN_DIR) else path


# --- correction link: the producer-owned prefilled issue form (contract 1.0.0) ---

def public_text(value, limit: int = 180) -> str:
    text = " ".join(str(value).split()) if value is not None else ""
    if not text:
        return "unknown"
    return text if len(text) <= limit else text[: max(1, limit - 1)] + "…"


def public_markings(markings) -> str:
    values = ["/".join(public_text(mark.get(key), 80) for key in ("kind", "role", "text")) for mark in markings]
    return public_text("; ".join(sorted(values)) if values else None)


def public_distribution(distribution) -> str:
    if not isinstance(distribution, dict):
        return "unknown"
    values = [f"{key}={public_text(distribution.get(key), 80)}" for key in ("kind", "name", "region", "date", "text")
              if distribution.get(key) is not None and str(distribution.get(key)).strip()]
    return public_text(", ".join(values) if values else None)


def correction_link(item: dict) -> str:
    state = "\n".join([
        f"Item kind: {public_text(item['itemKind'])}", f"Progress: {public_text(item['progressClass'])}",
        f"Evidence state: {public_text(item['finishVerificationStatus'])}",
        f"Completeness: {public_text(item['completenessStatus'])}",
        f"Edition status: {public_text(item['editionAssignmentStatus'])}",
        f"Edition: {public_text(item['edition'])}", f"Finish: {public_text(item['finish'])}",
        f"Finish family: {public_text(item['finishFamily'])}", f"Foil pattern: {public_text(item['foilPattern'])}",
        f"Markings: {public_markings(item['markings'])}",
        f"Distribution: {public_distribution(item['distribution'])}", f"Card size: {public_text(item['cardSize'])}",
    ])
    name, code, set_name = (public_text(item[key]) for key in ("cardName", "localSetCode", "localSetName"))
    context = code if set_name == "unknown" else f"{code} — {set_name}"
    number = public_text(item["collectorNumber"])
    params = {"template": "printing-correction.yml",
              "title": public_text(f"[Correction] {name} — {context} {number} ({public_text(item['itemKind'])})"),
              "row-id": item["itemId"], "card-name": name, "set-code": public_text(context),
              "card-number": number, "current-state": public_text(state, 1200)}
    link = REPOSITORY + "/issues/new?" + urlencode(params)
    shrinkable = ("current-state", "title", "card-name", "set-code", "card-number")
    while len(link) > CORRECTION_URL_MAX_LENGTH:  # shrink display context, never the item id
        key = max(shrinkable, key=lambda k: (len(params[k]), -shrinkable.index(k)))
        value = params[key]
        shorter = "unknown" if value == "unknown" or len(value) <= 8 else value[: max(7, len(value) // 2 - 1)] + "…"
        if shorter == value:
            raise ValueError(f"correction link too long: {item['itemId']}")
        params[key] = shorter
        link = REPOSITORY + "/issues/new?" + urlencode(params)
    return link


# --- collector_catalogue.json ---

def set_tables(sets: dict) -> tuple[dict, dict]:
    local_sets = {row["localSetId"]: dict(row, sortKey="|".join((
        row["locality"], natural_key(row["localSetCode"]), natural_key(row["localSetName"]), row["localSetId"])))
        for row in sets["localSets"]}
    editions = {}
    for row in sets["setEditions"]:
        local_set = local_sets[row["localSetId"]]
        editions[row["setEditionId"]] = {
            "setEditionId": row["setEditionId"], "localSetId": row["localSetId"],
            "localizationId": row["localizationId"], "localSetCode": local_set["localSetCode"],
            "localSetName": local_set["localSetName"], **{k: v for k, v in row.items() if k not in (
                "setEditionId", "localSetId", "localizationId")},
            "sortKey": "|".join((row["releaseDate"] or "9999", local_set["locality"],
                                 natural_key(local_set["localSetCode"]), row["setEditionId"]))}
    return local_sets, editions


def catalogue_asset(row: dict) -> dict:
    base = SPECIMEN_ASSET_BASE_URL if row["path"].startswith(SPECIMEN_DIR) else ASSET_BASE_URL
    return {"assetId": row["assetId"], "path": row["path"], "url": base + quote(row["path"], safe="/"),
            "sha256": row["sha256"], "mimeType": MIME[row["path"].rsplit(".", 1)[-1].lower()],
            "imageScope": row["imageScope"], "altTextBasis": row["altTextBasis"], "attribution": dict(ATTRIBUTION)}


def catalogue_item(printing: dict, edition: dict, assets: dict, links: list) -> dict:
    finish, asset = printing["finish"], assets.get(printing["imageAssetId"]) or {}
    derived = {
        "localSetId": edition["localSetId"], "localizationId": edition["localizationId"],
        "localSetCode": edition["localSetCode"], "localSetName": edition["localSetName"],
        "collectorNumberSortKey": natural_key(printing["collectorNumber"]),
        "finishFamily": None if finish is None else CATALOGUE_FAMILY.get(finish),
        **{key: printing.get(key, edition[key]) for key in DATE_FIELDS},
        "imageScope": asset.get("imageScope", "unknown"),
        "sourceLinks": links, "evidenceLinks": links, "correctionLink": "",
    }
    derived["releaseSortKey"] = "|".join((
        derived["releaseDate"] or "9999", edition["localizationId"], natural_key(edition["localSetCode"]),
        derived["collectorNumberSortKey"], printing["identityAnchor"]))
    item = {key: derived.get(key, printing.get(key)) for key in ITEM_FIELDS if key in derived or key in printing}
    item["correctionLink"] = correction_link(item)
    return item


def kind_counts(items: list, per_legacy_row: bool) -> Counter:
    """Items (or predecessor rows, one per legacy checklist id) per item kind and progress class."""
    return Counter(value for item in items for _ in (item["legacyChecklistIds"] if per_legacy_row else [0])
                   for value in (item["itemKind"], item["progressClass"]))


def quality_summary(quality: dict, document: dict) -> dict:
    items = document["items"]
    kinds, legacy = kind_counts(items, False), kind_counts(items, True)
    return {
        **{key: quality[key] for key in quality if key != "predecessor"},
        "counts": {
            **{name: len(document[name]) for name in ("localizations", "localSets", "setEditions", "works", "items")},
            "verifiedPrintings": kinds["verified-printing"], "finishCandidates": kinds["finish-candidate"],
            "researchPlaceholders": kinds["research-placeholder"], "currentKnown": kinds["current-known"],
            "research": kinds["research"], "assets": len(document["assets"])},
        "predecessor": quality["predecessor"],
        "graphAccounting": {"cardReleases": len({item["cardReleaseId"] for item in items}),
                            "physicalPrintings": sum(1 for item in items if item["physicalPrintingId"])},
        "candidateProgressPolicy": CANDIDATE_PROGRESS_POLICY,
        "legacyCompatibility": {**LEGACY_COMPATIBILITY, "counts": {
            "legacyRows": sum(len(item["legacyChecklistIds"]) for item in items),
            "verifiedPrintings": legacy["verified-printing"], "finishCandidates": legacy["finish-candidate"],
            "researchPlaceholders": legacy["research-placeholder"], "currentKnown": legacy["current-known"],
            "research": legacy["research"]}},
    }


def fingerprint(document: dict) -> str:
    """The catalogue hashed without its own fingerprint field."""
    hashed = dict(document, meta={k: v for k, v in document["meta"].items() if k != "catalogueFingerprint"})
    canonical = json.dumps(hashed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def catalogue(printings_doc: dict, sets: dict, images: dict, evidence: dict) -> dict:
    local_sets, editions = set_tables(sets)
    assets = {row["assetId"]: catalogue_asset(row) for row in images["assets"]}
    links = {row["itemId"]: row["sourceLinks"] for row in evidence["printings"]}
    items = sorted((catalogue_item(row, editions[row["setEditionId"]], assets, links[row["itemId"]])
                    for row in printings_doc["printings"]), key=lambda row: (row["releaseSortKey"], row["itemId"]))
    names = {}
    for item in filter(lambda row: row["workId"], items):
        names.setdefault(item["workId"], item["cardName"])
    meta = printings_doc["meta"]
    document = {
        "meta": {**CATALOGUE_META, "dataAsOf": meta["dataAsOf"], "catalogueFingerprint": "",
                 "previousFingerprint": meta["previousFingerprint"], "assetBaseUrl": ASSET_BASE_URL,
                 "scope": CATALOGUE_SCOPE, "licenceRefs": ["LICENSE.md", "THIRD_PARTY_NOTICES.md"]},
        "localizations": sorted(sets["localizations"], key=lambda row: (row["displayOrder"], row["localizationId"])),
        "localSets": sorted(local_sets.values(), key=lambda row: row["sortKey"]),
        "setEditions": sorted(editions.values(), key=lambda row: row["sortKey"]),
        "works": sorted((dict(row, displayName=names.get(row["workId"])) for row in sets["works"]),
                        key=lambda row: row["workId"]),
        "items": items,
        "assets": sorted(assets.values(), key=lambda row: row["assetId"]),
    }
    document["qualitySummary"] = quality_summary(meta["legacyQuality"], document)
    document["meta"]["catalogueFingerprint"] = fingerprint(document)
    return document


# --- index.html table rows ---

def mark_values(item: dict, key: str) -> list:
    return [mark[key] for mark in item["markings"] if mark.get(key)]


def date_view(item: dict) -> tuple[str, str, str]:
    """dateSort, dateDisplay and dateStatus of a table row."""
    date = item["releaseDate"] or "9999"
    date_sort = release_sort(date)
    if date_sort.startswith("9999"):
        return date_sort, "Undated", "unknown"
    if item["releaseApproximate"]:
        return date_sort, "~" + date, "approximate"
    return date_sort, date, "exact"


def finish_view(item: dict) -> tuple[dict, list, list]:
    """Best status per finish family, the families and the technical finishes of a table row."""
    status, finish = item["finishVerificationStatus"], item["finish"]
    best = {}
    if STATUS_RANK.get(status, 0) > 0:  # pending, not-applicable and unranked states show no pill
        best[TABLE_FAMILY.get(finish, finish)] = status
    technical = {finish} & TABLE_FAMILY.keys()
    return best, sorted({TABLE_FAMILY[f] for f in technical} | set(best)), sorted(technical)


def edition_label(item: dict) -> str:
    return item["edition"] or {"not-applicable": "none"}.get(item["editionAssignmentStatus"], "unknown")


def row_image(asset: dict):
    """A specimen original is published as its preview derivative."""
    return asset.get("preview") if str(asset.get("path")).startswith(SPECIMEN_DIR) else asset.get("path")


def language_evidence(grade: dict, provider: dict) -> dict:
    return {"tier": provider["authorityTier"], "provider": provider["displayName"],
            "corroborated": grade["corroborated"], "checkable": grade["checkable"]}


def table_row(item: dict, localization: dict, printing: dict, asset: dict, grades: dict, providers: dict) -> dict:
    language = {"LATAM": "Spanish (Latin America)"}.get(localization["locality"], localization["language"])
    date_sort, display, date_status = date_view(item)
    best, finishes, technical = finish_view(item)
    patterns = list(filter(None, [item["foilPattern"]]))
    markings = sorted(set(mark_values(item, "text")))
    lang_codes = [LANG_CODE[language]] if language in LANG_CODE else []
    grade = grades["languageEvidence"]
    row = {
        "rowId": item["itemId"], "sourceRowId": item["itemId"],
        "printingIds": list(filter(None, [item["physicalPrintingId"]])),
        "splitPhysicalPrinting": False, "itemKind": item["itemKind"], "localizationId": item["localizationId"],
        "languageLabel": localization["displayName"], "sourceLinks": item["sourceLinks"],
        "name": item["cardName"], "setCode": item["localSetCode"] or "Unknown",
        "setName": item["localSetName"] or "Unknown", "number": printed_number(item),
        "variant": item["finish"] or "unresolved", "variantName": f'{localization["locality"]} · {language}',
        "rarity": item["rarity"]["display"], "artist": printing.get("artist"),
        "edition": edition_label(item),
        "dateSort": date_sort, "dateDisplay": display, "dateStatus": date_status,
        "dateSource": grades["dateSource"], "image": row_image(asset),
        "finishes": finishes, "technicalFinishes": technical,
        "finishDisplay": [{"label": FINISH_LABEL[f], "status": best.get(f, "pending")}
                          for f in ("non-holo", "holo", "reverse-holo") if f in finishes],
        "patterns": patterns, "markings": markings, "markingRoles": sorted(set(mark_values(item, "role"))),
        "sizes": [item["cardSize"] or "standard"],
        "distributions": list(filter(None, [(item["distribution"] or {}).get("kind")])),
        "evidence": sorted(filter(None, {item["finishVerificationStatus"] or "pending",
                                         item["completenessStatus"], item["itemKind"]})),
        "confirmedLanguages": [language], "langCodes": lang_codes,
        "langEvidence": {code: language_evidence(grade, providers[grade["providerId"]]) for code in lang_codes},
        "correctionUrl": item["correctionLink"],
    }
    row["search"] = row_search(row)
    return row


def row_search(row: dict) -> str:
    words = [row[key] for key in ("name", "setCode", "setName", "number", "variant", "languageLabel", "variantName")]
    words += [row["rarity"] or "", row["artist"] or "", row["edition"], *map(" ".join, (
        row["finishes"], row["technicalFinishes"], row["patterns"], row["markings"], row["langCodes"])),
        row["dateDisplay"]]
    return " ".join(str(value).lower() for value in words)


def table_rows(document: dict, printings: dict, images: dict, evidence: dict) -> list[dict]:
    localizations = {row["localizationId"]: row for row in document["localizations"]}
    assets = {row["assetId"]: row for row in images["assets"]}
    grades = {row["itemId"]: row for row in evidence["printings"]}
    providers = {row["providerId"]: row for row in evidence["providers"]}
    return [table_row(item, localizations[item["localizationId"]], printings[item["itemId"]],
                      assets.get(item["imageAssetId"]) or {}, grades[item["itemId"]], providers)
            for item in document["items"] if item["active"] and item["itemKind"] == "verified-printing"]


# --- gallery.html cards ---

def gallery_card(item: dict, language: str, group: str, artist, image: dict | None) -> dict:
    card = {
        "id": item["itemId"], "group": group, "name": item["localCardName"] or item["cardName"],
        "set": item["localSetName"], "setCode": item["localSetCode"], "number": printed_number(item),
        "artist": artist, "language": language, "edition": item["edition"], "finish": item["finish"],
        "foilPattern": item["foilPattern"], "markings": mark_values(item, "text"),
        "distribution": (item["distribution"] or {}).get("name"), "cardSize": item["cardSize"],
        "date": item["releaseDate"], "datePrecision": item["releaseDatePrecision"],
        "approximate": item["releaseApproximate"], "kind": item["itemKind"],
        "status": item["finishVerificationStatus"], "note": item.get("researchNote"),
        "thumbnail": None, "preview": None, "imageSource": None, "imageScope": None,
        "sources": sorted(item["sourceLinks"]),
    }
    if image:
        sizes = image["images"]
        card.update(thumbnail=sizes[0]["path"], preview=sizes[-1]["path"],
                    imageSource=published_link(image["source"]), imageScope=image["scope"])
        card["_prepared"] = {"imageSizes": sizes, "imageWidth": sizes[-1]["width"], "imageHeight": sizes[-1]["height"],
                             "imageRecipe": image["recipe"], "mediaKind": image["mediaKind"]}
    return card


def placeholder_item(base: dict, row: dict) -> dict:
    """An open research hypothesis, shown beside the printing it varies."""
    return dict(base, itemId=row["id"], itemKind="research-placeholder", finish=row["finish"],
                foilPattern=row["foilPattern"], finishVerificationStatus=row["status"], researchNote=row["note"],
                distribution={"name": row["distribution"]} if row["distribution"] else None, markings=[],
                sourceLinks=row["sources"], releaseDate=None, releaseDatePrecision=None, releaseApproximate=False)


def gallery_artists(items: list, printings: dict) -> tuple[dict, dict]:
    """Verified-printing artists, and the one artist of a release where its printings agree."""
    artists = {row["itemId"]: printings[row["itemId"]]["artist"] for row in items
               if row["itemKind"] == "verified-printing" and printings[row["itemId"]].get("artist")}
    credits = {}
    for item in filter(lambda row: row["itemId"] in artists, items):
        credits.setdefault(item["cardReleaseId"], set()).add(artists[item["itemId"]])
    return artists, {release: next(iter(names)) for release, names in credits.items() if len(names) == 1}


def chronological(cards: list) -> list:
    """A group sorts by its earliest verified printing, then set code and number (gallery.py)."""
    unplaced = (UNDATED, "", float("inf"))
    dates = {c["id"]: release_sort(c["date"]) if c["date"] else UNDATED for c in cards}
    group_keys = {}
    for c in filter(lambda c: c["kind"] == "verified-printing", cards):
        key = (dates[c["id"]], (c["setCode"] or "").casefold(), number_key(c["number"]))
        group_keys[c["group"]] = min(group_keys.get(c["group"], unplaced), key)
    cards.sort(key=lambda c: (group_keys.get(c["group"], unplaced), c["group"], dates[c["id"]], c["id"]))
    numbers = {group: n for n, group in enumerate(dict.fromkeys(c["group"] for c in cards), start=1)}
    for c in cards:
        c["artworkNumber"] = numbers[c["group"]]
        c.update(c.pop("_prepared", {}))
    return cards


def gallery_cards(document: dict, printings: dict, images: dict) -> list[dict]:
    languages = {row["localizationId"]: row["displayName"] for row in document["localizations"]}
    groups = {row["cardReleaseId"]: row["group"] for row in images["artworkGroups"]}
    prepared = {row["itemId"]: row for row in images["galleryImages"]}
    items = [row for row in document["items"] if row["active"]]
    by_id = {row["itemId"]: row for row in items}
    artists, fallback = gallery_artists(items, printings)

    def card(item, image=None):
        release = item["cardReleaseId"]
        return gallery_card(item, languages[item["localizationId"]], groups.get(release, release),
                            artists.get(item["itemId"], fallback.get(release)), image)

    cards = [card(item, prepared.get(item["itemId"])) for item in items]
    cards += [card(placeholder_item(by_id[row["baseItemId"]], row)) for row in images["placeholders"]]
    return chronological(cards)


# --- pages ---

INDEX_TEMPLATE = ROOT / "templates" / "index.html"
GALLERY_TEMPLATE = ROOT / "site" / "gallery.html"  # the page source site.py reads, used in place
# Owner-only decision record, read in place: the published licence wording must come from the record
# the publication gate enforces, never from a copy (AGENTS.md: owner files move unchanged).
DECISIONS = ROOT / "publication-decisions.json"
# Frozen legacy copy: both headers name the generator that is still the release path until the cut.
INDEX_HEADER = "<!-- Generated by scripts/site.py. Do not edit index.html directly. -->"
GALLERY_HEADER = "<!-- Generated by scripts/site.py. Edit site/gallery.html instead. -->"
STAT_LABELS = (
    ("establishedLanguageClaims", "established legacy language claims"),
    ("languageClaimsNeedingEvidence", "language claims needing evidence"),
    ("adjudicatedNotPrinted", "adjudicated not printed"), ("disputedClaims", "disputed claims"),
    ("finishUnits", "current-known finish units"), ("confirmedFinishes", "current-known confirmed finishes"),
    ("checklistItems", "current-known checklist items"), ("evidenceRecords", "distinct sources"),
    ("confirmedLegacyPairs", "confirmed legacy card×language pairs"),
)


def json_block(element_id: str, payload) -> str:
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="{element_id}">{text}</script>'


def render(template: str, slots: dict) -> str:
    """Fill every {{name}} slot exactly; an unfilled or unknown slot is an error."""
    pattern = r"\{\{([a-z_:-]+)\}\}"
    assert set(re.findall(pattern, template)) == set(slots), "template slots differ from the values"
    return re.sub(pattern, lambda match: str(slots[match.group(1)]), template)


# confirmed_releases.py's language order: the legacy pairs count only these languages.
LEGACY_LANGUAGES = [name for name in LANG_CODE if name != "Spanish (Latin America)"]


def page_counts(document: dict, sets: dict, claims: dict, evidence: dict) -> dict:
    """The index page's counts, over the language claims, finish units and items."""
    rows = claims["languageClaims"]
    status = Counter(row["applicationStatus"] for row in rows)
    names = {row["languageCode"]: row["sourceName"] for row in sets["languages"]}
    units = claims["finishUnits"]
    code_cards = {row["productId"] for row in claims["legacyProducts"] if row["isCodeCard"]}
    return {
        "establishedLanguageClaims": status["exists"], "languageClaimsNeedingEvidence": status["needs-evidence"],
        "adjudicatedNotPrinted": status["not-printed"], "disputedClaims": status["disputed"],
        "finishUnits": len(units), "confirmedFinishes": sum(u["availabilityStatus"] == "confirmed" for u in units),
        "checklistItems": document["qualitySummary"]["legacyCompatibility"]["counts"]["legacyRows"],
        "confirmedLegacyPairs": sum(row["applicationStatus"] == "exists" and row["productId"] not in code_cards
                                    and names[row["languageCode"]] in LEGACY_LANGUAGES for row in rows),
        "openLegacyClaims": sum(row["repositoryVerdict"] in ("pending", "needs-manual-review") for row in rows),
        **evidence["meta"]["frozenRegistryCounts"],
    }


def stats_html(row_count: int, counts: dict) -> str:
    stats = [(row_count, "current confirmed physical printings")] + [(counts[key], label) for key, label in STAT_LABELS]
    return "".join(f'<div class="stat"><span class="n">{n}</span><span class="k">{html.escape(k)}</span></div>'
                   for n, k in stats)


def licence_slots() -> dict:
    decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
    licensor = str(decisions.get("licensor") or "undecided")
    granted = decisions.get("licenseGrantsApproved") is True
    return {"licensor": html.escape(licensor),
            "licensor_contact": html.escape("https://www.instagram.com/" + licensor.lower() + "/"),
            "grants_state": f"<strong>in force</strong>, granted by {html.escape(licensor)}" if granted
            else "<strong>not yet operative</strong> until the owner records approval"}


def open_claims_note(count: int) -> str:
    """A scope warning that appears only while legacy claims are open (site.py, #68)."""
    return (f"<li><strong>{count} legacy claims remain open.</strong> They are shown as "
            f"unresolved rather than quietly dropped. This is queue depth inside the frozen candidate "
            f"universe, not a count of undiscovered local printings.</li>" if count else "")


def index_page(rows: list, generated: str, counts: dict) -> str:
    languages = [{"code": code, "name": name} for name, code in LANG_CODE.items()]
    return render(INDEX_TEMPLATE.read_text(encoding="utf-8"), {
        "header": INDEX_HEADER, "stats": stats_html(len(rows), counts),
        "needs_evidence": counts["languageClaimsNeedingEvidence"],
        "open_claims_note": open_claims_note(counts["openLegacyClaims"]),
        "claims_attributed": counts["claimsAttributed"], "evidence_records": counts["evidenceRecords"],
        "unique_urls": counts["uniqueUrls"], "non_url_classes": counts["nonUrlEvidenceClasses"],
        **licence_slots(), "generated": generated, "baseline_id": html.escape(COVERAGE["candidateUniverseId"]),
        "block:data-rows": json_block("data-rows", rows), "block:data-coverage": json_block("data-coverage", COVERAGE),
        "block:data-meta": json_block("data-meta", {"languages": languages, "generated": generated}),
    })


def gallery_page(cards: list) -> str:
    text = GALLERY_TEMPLATE.read_text(encoding="utf-8")
    assert text.count("<!-- GALLERY_HEADER -->") == text.count("<!-- GALLERY_DATA -->") == 1
    return text.replace("<!-- GALLERY_HEADER -->", GALLERY_HEADER).replace(
        "<!-- GALLERY_DATA -->", json_block("gallery-data", cards))


# --- snoredex.sqlite ---

SCHEMA_SQL = ROOT / "templates" / "schema.sql"
DATABASE_SCHEMA = ("snoredex-database", "2.0.0")
OWNER_ADJUDICATIONS = ROOT / "verification" / "owner_adjudications.json"  # owner file, read in place
SPECIMENS = ROOT / "verification" / "specimens.json"  # curated specimen store, read in place


def snake(key: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key).lower()


def sql_value(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return int(value) if isinstance(value, bool) else value


def sql_row(record: dict, columns: list) -> list:
    """A model record as a row: snake_case names, JSON for nested values; every field must land."""
    row = {}
    for key, value in record.items():
        name = snake(key)
        row[name + "_json" if name + "_json" in columns else name] = value
    assert set(row) <= set(columns), sorted(set(row) - set(columns))
    return [sql_value(row.get(column)) for column in columns]


def insert(db, table: str, records) -> int:
    columns = [row[1] for row in db.execute(f'PRAGMA table_info("{table}")')]
    rows = [sql_row(record, columns) for record in records]
    db.executemany(f'INSERT INTO "{table}" VALUES ({", ".join("?" * len(columns))})', rows)
    return len(rows)


def without_keys(record: dict, *keys: str) -> dict:
    return {key: value for key, value in record.items() if key not in keys}


def finish_printing_rows(items: list, assets: dict, finish_printings: list) -> list[dict]:
    """Finish printings resolved: the item that carries one supplies the facts they share."""
    carried = {row["sourcePrintingId"]: row for row in items if row["sourcePrintingId"]}
    rows = []
    for rec in finish_printings:
        item = carried.get(rec["printingId"])
        base = rec if item is None else {
            "finishUnitId": item["finishUnitId"], "finish": item["finish"], "foilPattern": item["foilPattern"],
            "cardSize": item["cardSize"], "verificationStatus": item["finishVerificationStatus"],
            "distribution": item["distribution"], "markings": item["markings"]}
        rows.append({"printingId": rec["printingId"], "itemId": (item or {}).get("itemId"),
                     **without_keys(base, "printingId", "productId", "releaseDate", "image", "sources",
                                    "physicalPrintingId"),
                     "finishFamily": CATALOGUE_FAMILY.get(base["finish"]), "productId": rec.get("productId"),
                     "releaseDate": rec.get("releaseDate"),
                     "imagePath": rec.get("image", assets.get((item or {}).get("imageAssetId"))),
                     "physicalPrintingId": rec.get("physicalPrintingId")})
    return rows


def printing_records(document: dict, printings: dict, evidence: dict) -> list[dict]:
    grades = {row["itemId"]: row for row in evidence["printings"]}
    records = []
    for item in sorted(document["items"], key=lambda row: row["itemId"]):
        stored, grade = printings[item["itemId"]], grades[item["itemId"]]
        language = grade.get("languageEvidence") or {}
        records.append({**without_keys(item, "legacyChecklistIds", "markings", "sourceLinks", "evidenceLinks"),
                        "identityAnchor": stored["identityAnchor"], "artist": stored.get("artist"),
                        "languageProviderId": language.get("providerId"),
                        "languageCorroborated": language.get("corroborated"),
                        "languageCheckable": language.get("checkable"), "dateSource": grade.get("dateSource")})
    return records


def printing_children(db, items: list) -> list[int]:
    items = sorted(items, key=lambda row: row["itemId"])
    return [
        insert(db, "printing_legacy_ids", ({"itemId": i["itemId"], "legacyChecklistId": legacy}
                                            for i in items for legacy in i["legacyChecklistIds"])),
        insert(db, "printing_markings", ({"itemId": i["itemId"], "markingOrder": n, **mark}
                                          for i in items for n, mark in enumerate(i["markings"]))),
        insert(db, "printing_source_links", ({"itemId": i["itemId"], "url": url}
                                              for i in items for url in i["sourceLinks"])),
    ]


def source_records(finish_printings: list):
    for rec in finish_printings:
        for order, entry in enumerate(rec["sources"]):
            source = entry["source"]
            yield {"printing_id": rec["printingId"], "source_order": order, "provider_id": entry["providerId"],
                   "url": source.get("url"), "identity_url": source.get("identityUrl"),
                   "source_type": source["sourceType"], "evidence": source["evidence"],
                   "authority_class": source.get("authorityTier"), "coverage": source.get("coverage"),
                   "retrieved_at": source.get("retrievedAt"), "source_json": source}


def claim_tables(db, model: dict) -> list[int]:
    claims = model["claims"]
    units = claims["finishUnits"]
    owner = json.loads(OWNER_ADJUDICATIONS.read_text(encoding="utf-8"))["decisions"]
    specimens = json.loads(SPECIMENS.read_text(encoding="utf-8"))["specimens"]
    return [
        insert(db, "legacy_products", claims["legacyProducts"]),
        insert(db, "owner_adjudications", sorted(owner, key=lambda row: row["adjudicationId"])),
        insert(db, "language_claims", claims["languageClaims"]),
        insert(db, "release_rows", (dict(row, dateSort=release_sort(row["releaseDate"]))
                                    for row in claims["releaseRows"])),
        insert(db, "finish_units", (without_keys(unit, "products") for unit in units)),
        insert(db, "finish_unit_products", ({"finishUnitId": u["finishUnitId"], **p} for u in units
                                             for p in u["products"])),
        insert(db, "finish_printings", model["finishRows"]),
        insert(db, "finish_printing_sources", source_records(claims["finishPrintings"])),
        insert(db, "specimens", ({"specimen_id": s["specimenId"], "specimen_json": s}
                                 for s in sorted(specimens, key=lambda row: row["specimenId"]))),
    ]


def model_tables(db, model: dict) -> list[int]:
    document, images = model["document"], model["images"]
    previews = {row["assetId"]: row.get("preview") for row in images["assets"]}
    return [
        insert(db, "metadata", ({"key": k, "value": v} for k, v in sorted(model["metadata"].items()))),
        insert(db, "languages", model["sets"]["languages"]),
        insert(db, "localizations", document["localizations"]),
        insert(db, "local_sets", document["localSets"]),
        insert(db, "set_editions", (without_keys(row, "localSetCode", "localSetName") for row in document["setEditions"])),
        insert(db, "works", document["works"]),
        insert(db, "assets", (dict(row, preview=previews[row["assetId"]]) for row in document["assets"])),
        insert(db, "providers", model["evidence"]["providers"]),
        insert(db, "printings", printing_records(document, model["printings"], model["evidence"])),
        *printing_children(db, document["items"]),
        insert(db, "gallery_images", images["galleryImages"]),
        insert(db, "artwork_groups", images["artworkGroups"]),
        insert(db, "gallery_placeholders", images["placeholders"]),
    ]


def database_metadata(document: dict) -> dict:
    return {"schema": DATABASE_SCHEMA[0], "schema_version": DATABASE_SCHEMA[1],
            "data_as_of": document["meta"]["dataAsOf"],
            "catalogue_fingerprint": document["meta"]["catalogueFingerprint"],
            "catalogue_schema_version": document["meta"]["schemaVersion"],
            "candidate_universe_id": COVERAGE["candidateUniverseId"],
            "legacy_source_commit": COVERAGE["sourceCommit"]}


def write_database(path: Path, model: dict) -> dict:
    """Build the database from the model; the schema file is the contract. Returns rows per table."""
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))
    model_tables(db, model)
    claim_tables(db, model)
    db.commit()
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    broken = db.execute("PRAGMA foreign_key_check").fetchall()
    tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY rowid")]
    counts = {name: db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in tables}
    db.close()
    assert integrity == "ok" and not broken, (integrity, broken[:5])
    return counts


def sqlite_dump(path: Path) -> str:
    """A logical dump: page layouts differ across SQLite builds even when every row is the same."""
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return "\n".join(db.iterdump())
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path, help="directory to write the end product into")
    args = parser.parse_args()
    printings_doc, sets, images, evidence, claims = (read(name) for name in (
        "printings.json", "sets.json", "images.json", "evidence.json", "claims.json"))
    printings = {row["itemId"]: row for row in printings_doc["printings"]}
    document = catalogue(printings_doc, sets, images, evidence)
    rows = table_rows(document, printings, images, evidence)
    cards = gallery_cards(document, printings, images)
    outputs = {
        "collector_catalogue.json": json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        "index.html": index_page(rows, printings_doc["meta"]["siteGenerated"],
                                 page_counts(document, sets, claims, evidence)),
        "gallery.html": gallery_page(cards),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    for name, text in outputs.items():
        (args.out / name).write_text(text, encoding="utf-8", newline="\n")
    counts = write_database(args.out / "snoredex.sqlite", {
        "document": document, "images": images, "sets": sets, "evidence": evidence, "printings": printings,
        "claims": claims, "metadata": database_metadata(document),
        "finishRows": finish_printing_rows(document["items"], {a["assetId"]: a["path"] for a in images["assets"]},
                                           claims["finishPrintings"])})
    seeded = collection.init(args.out / "snoredex-tracker-template.sqlite", args.out / "snoredex.sqlite", force=True)
    print(f"{args.out}: {len(document['items'])} items, {len(rows)} rows, {len(cards)} gallery cards; "
          f"{document['meta']['catalogueFingerprint']}; snoredex.sqlite {sum(counts.values())} rows in "
          f"{len(counts)} tables; tracker template {seeded} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Read item-scoped date evidence from the existing release override owner.

These observations change dates only. They cannot admit a card or establish a
language, finish, edition, or distribution. Graph identities guard their scope.
"""

from datetime import date
import json
from pathlib import Path
import re

PATH = Path(__file__).resolve().parent.parent / "verification" / "confirmed_release_overrides.json"
DATE_FIELDS = ("releaseDate", "releaseDatePrecision", "releaseApproximate")
IDENTITY_FIELDS = ("cardReleaseId", "physicalPrintingId", "localizationId", "legacyChecklistIds")


def load_reviewed_dates():
    document = json.loads(PATH.read_text(encoding="utf-8"))
    rows = document["releaseDates"].get("reviewedItems", [])
    by_item, by_legacy = {}, {}
    for row in rows:
        validate_date(row)
        if row["itemId"] in by_item:
            raise ValueError(f"duplicate reviewed release date: {row['itemId']}")
        by_item[row["itemId"]] = row
        for legacy_id in row["legacyChecklistIds"]:
            if legacy_id in by_legacy:
                raise ValueError(f"duplicate reviewed predecessor date: {legacy_id}")
            by_legacy[legacy_id] = row
    return document, by_item, by_legacy


def validate_date(row):
    value = row["releaseDate"]
    precision = row["releaseDatePrecision"]
    patterns = {"day": r"\d{4}-\d{2}-\d{2}", "month": r"\d{4}-\d{2}", "year": r"\d{4}"}
    if precision not in patterns or not re.fullmatch(patterns[precision], value):
        raise ValueError(f"invalid reviewed release precision: {value}")
    date.fromisoformat(value + {"day": "", "month": "-01", "year": "-01-01"}[precision])
    if not isinstance(row["releaseApproximate"], bool) or not row["sources"] or not row["basis"]:
        raise ValueError(f"incomplete reviewed release date: {row['itemId']}")
    for source in row["sources"]:
        if not source["url"].startswith("https://") or not source["providerId"] or not source["evidencePath"]:
            raise ValueError(f"incomplete reviewed release provenance: {row['itemId']}")
        date.fromisoformat(source["retrievedAt"][:10])


def guard_item(row, item):
    if any(row[key] != item[key] for key in IDENTITY_FIELDS):
        raise ValueError(f"reviewed release date identity changed: {row['itemId']}")


def date_source(row):
    source = row["sources"][0]
    return {"url": source["url"], "provider": source["providerId"],
            "retrievedAt": source["retrievedAt"], "evidencePath": source["evidencePath"],
            "scope": row["basis"]}


def apply_item_date(item, reviewed_dates, link=str):
    """Overlay one reviewed date; `link` maps each source URL to the emitted link form (#429)."""
    row = reviewed_dates.get(item["itemId"])
    if row:
        guard_item(row, item)
        item.update({key: row[key] for key in DATE_FIELDS})
        item["releaseSortKey"] = row["releaseDate"] + "|" + item["releaseSortKey"].split("|", 1)[1]
        links = sorted(set(item["sourceLinks"]) | {link(source["url"]) for source in row["sources"]})
        item["sourceLinks"] = item["evidenceLinks"] = links
    return item


def apply_predecessor_dates(items, reviewed_dates, sort_date):
    missing = set(reviewed_dates) - {item["checklistId"] for item in items}
    if missing:
        raise ValueError(f"reviewed release predecessors missing: {sorted(missing)}")
    for item in items:
        row = reviewed_dates.get(item["checklistId"])
        if row:
            if item["printingId"] != row["sourcePrintingId"]:
                raise ValueError(f"reviewed release predecessor identity changed: {item['checklistId']}")
            item.update({key: row[key] for key in DATE_FIELDS})
            item["releaseSort"] = sort_date(item["releaseDate"])
            item["releaseDateSource"] = date_source(row)


def check_reviewed_targets(items, reviewed_dates):
    missing = set(reviewed_dates) - {item["itemId"] for item in items}
    if missing:
        raise ValueError(f"reviewed release date targets missing: {sorted(missing)}")

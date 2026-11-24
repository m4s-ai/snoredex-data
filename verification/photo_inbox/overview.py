"""Every printing of the catalogue and how far its own photo has come on the way to Instagram (#641).

The catalogue comes from a checkout of `main` (`--repo`), whether a printing is online from the
published site. Nothing here writes to the repository, the photo archive or the site. Every number
the page shows is counted from these rows.
"""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import time
from urllib.request import urlopen

from derive import derive

# the furthest stage reached wins, earlier ones count as done
STAGES = ("none", "assigned", "filed", "online", "ready", "posted")
SHORT_BASE = "https://go.m4s.eu/"
SITE_TTL = 600
SPEC_PATH = re.compile(r"verification/specimens/(SPEC-\d+)\.\w+")
ITEM_ID = re.compile(r"item-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_json(url):
    with urlopen(url, timeout=20) as response:  # noqa: S310  (the site's own https URL)
        return json.load(response)


def archive_digest(folder):
    """The SHA-256 of the archive copy intake makes from this job, cached beside the job.

    A job is filed as SPEC-nnnn exactly when its archive copy is that specimen's photograph. Only a
    digest is cached: a failure may be passing (a read error on the share), so it is tried again."""
    cached = folder / "archive.sha256"
    if cached.is_file():
        return cached.read_text(encoding="utf-8").strip()
    try:
        digest = "sha256:" + sha256(derive(folder)[0]).hexdigest()
    except (ValueError, KeyError, IndexError, struct.error, OSError, StopIteration):
        return None  # no archive copy can be made now, so nothing can be matched against it
    cached.write_text(digest + "\n", encoding="utf-8", newline="\n")
    return digest


def label(item, languages):
    """The printing as the owner picks it: every fact that tells two variants apart is named."""
    number = "/".join(filter(None, (item.get("collectorNumber"), item.get("collectorNumberDenominator"))))
    size = item.get("cardSize") if item.get("cardSize") != "standard" else None
    marks = ", ".join(mark["text"] for mark in item.get("markings") or [])
    parts = (" ".join(filter(None, (item.get("localSetCode"), number))), languages.get(item["localizationId"], ""),
             item.get("finish"), item.get("foilPattern"), item.get("edition"), size, marks,
             item.get("localCardName") or item["cardName"])
    return " · ".join(str(part) for part in parts if part)


def unique_labels(items, languages):
    """itemId -> label, distinct for every printing: the page maps the picked label back to its item."""
    labels = {item_id: label(item, languages) for item_id, item in items.items()}
    counts = Counter(labels.values())
    return {item_id: text if counts[text] == 1 else f"{text} · {item_id}" for item_id, text in labels.items()}


class Catalogue:
    """The data of one `main` checkout, re-read whenever a file changes, and the published site."""

    FILES = ("collector_catalogue.json", "verification/specimens.json", "data/social.json", "data/images.json")

    def __init__(self, repo, fetch=fetch_json):
        self.repo = Path(repo).resolve()
        missing = [name for name in self.FILES if not (self.repo / name).is_file()]
        if missing:
            raise ValueError(f"Im Katalog fehlt {missing[0]}.")
        self.fetch, self.stamp, self.site, self.site_at, self.site_error = fetch, None, {}, 0.0, None
        self.refresh()

    def refresh(self):
        stamp = tuple((self.repo / name).stat().st_mtime_ns for name in self.FILES)
        if stamp == self.stamp:
            return
        doc, specimens, social, images = (read_json(self.repo / name) for name in self.FILES)
        self.doc, self.stamp = doc, stamp
        self.base = doc["meta"]["assetBaseUrl"]
        self.items = {item["itemId"]: item for item in doc["items"] if item["active"]}
        self.languages = {row["localizationId"]: row["displayName"] for row in doc["localizations"]}
        self.labels = unique_labels(self.items, self.languages)
        self.asset_paths = {asset["assetId"]: asset["path"] for asset in doc["assets"]}
        self.owner = {row["specimenId"]: row for row in specimens["specimens"]
                      if row.get("photographedBy") == "collection owner"}
        self.by_photo = {row["photographSha256"]: row["specimenId"] for row in specimens["specimens"]
                         if row.get("photographSha256")}
        self.social = {row["itemId"]: row for row in social}
        self.thumbs = {row["itemId"]: min(row["images"], key=lambda image: image["width"])["path"]
                       for row in images["galleryImages"] if row.get("images")}

    def published(self):
        """itemId -> image asset of the catalogue Pages serves now, re-read every ten minutes."""
        if time.monotonic() - self.site_at > SITE_TTL or not self.site_at:
            try:
                doc = self.fetch(self.base + "collector_catalogue.json")
                self.site = {item["itemId"]: item.get("imageAssetId") for item in doc["items"]}
                self.site_error = None
            except (OSError, ValueError, KeyError) as error:
                self.site_error = f"Die Website war nicht lesbar: {error}"
            self.site_at = time.monotonic()
        return self.site

    def active_items(self):
        self.refresh()
        return self.items

    def filed_as(self, folder):
        """The SPEC this job was filed as, read against the checkout as it is now."""
        self.refresh()
        digest = archive_digest(folder)
        return self.by_photo.get(digest) if digest else None

    def owner_specimen(self, item):
        match = SPEC_PATH.fullmatch(self.asset_paths.get(item.get("imageAssetId"), ""))
        return match[1] if match and match[1] in self.owner else None

    def stage(self, item, specimen, jobs, site):
        social = self.social.get(item["itemId"]) or {}
        reached = [bool(jobs), bool(specimen),
                   bool(specimen) and site.get(item["itemId"]) == item.get("imageAssetId"),
                   bool(social.get("shortAlias")), bool(social.get("instagramPosts"))]
        return STAGES[max((index + 1 for index, done in enumerate(reached) if done), default=0)]

    def row(self, item, jobs, site):
        specimen = self.owner_specimen(item)
        social = self.social.get(item["itemId"]) or {}
        thumb = self.thumbs.get(item["itemId"])
        return {"itemId": item["itemId"], "label": self.labels[item["itemId"]],
                "set": item["localSetCode"], "language": self.languages.get(item["localizationId"], ""),
                "stage": self.stage(item, specimen, jobs, site), "specimen": specimen, "jobs": jobs,
                "preview": self.base + thumb if thumb else None, "card": self.base + f"cards/{item['itemId']}/",
                "shortUrl": SHORT_BASE + social["shortAlias"] if social.get("shortAlias") else None,
                "posts": social.get("instagramPosts", [])}

    def overview(self, jobs):
        """One row per active printing, with the inbox jobs that belong to it."""
        self.refresh()
        site = self.published()
        owner_item = {self.owner_specimen(item): item_id for item_id, item in self.items.items()}
        owner_item.pop(None, None)
        by_item = {}
        for job in jobs:
            item_id = owner_item.get(job.get("filedAs")) or job.get("itemId")
            if item_id:
                by_item.setdefault(item_id, []).append(job["id"])
        rows = [self.row(item, by_item.get(item_id, []), site) for item_id, item in self.items.items()]
        return {"dataAsOf": self.doc["meta"]["dataAsOf"], "siteError": self.site_error, "stages": STAGES,
                "rows": sorted(rows, key=lambda row: row["label"].casefold())}

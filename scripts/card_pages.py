"""Public share metadata and link validation for the Instagram pilot."""
from html import escape
from pathlib import Path
from string import Template
import json
import re

from build import ASSET_BASE_URL, gallery_cards
from check import load
from owner_photo import owner_specimen

ROOT = Path(__file__).resolve().parents[1]
SOCIAL_FILE = "data/social.json"
ITEM_ID = re.compile(r"item-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
POST_URL = re.compile(r"https://www\.instagram\.com/(?:p|reel)/[\w-]+/", re.ASCII)
SHORT_ALIAS = re.compile(r"[a-zA-Z0-9-]+")


def checked_posts(links, used: set) -> None:
    if not isinstance(links, list) or any(not isinstance(url, str) or not POST_URL.fullmatch(url) for url in links):
        raise ValueError("Invalid Instagram permalink")
    if used.intersection(links) or len(set(links)) != len(links):
        raise ValueError("Duplicate Instagram permalink")
    used.update(links)


def checked_alias(alias, aliases: set) -> None:
    if alias is None:
        return
    if not isinstance(alias, str) or not SHORT_ALIAS.fullmatch(alias) or alias in aliases:
        raise ValueError(f"Invalid or duplicate short alias: {alias}")
    aliases.add(alias)


def read_social(root: Path) -> dict:
    rows = json.loads((root / SOCIAL_FILE).read_text(encoding="utf-8"))
    items, aliases, posts = {}, set(), set()
    for row in rows:
        if not isinstance(row, dict) or row.keys() - {"itemId", "specimenId", "instagramPosts", "shortAlias"}:
            raise ValueError("Unexpected social fields")
        item_id, links = row["itemId"], row["instagramPosts"]
        if not ITEM_ID.fullmatch(item_id) or item_id in items:
            raise ValueError(f"Invalid or duplicate social item: {item_id}")
        checked_posts(links, posts)
        checked_alias(row.get("shortAlias"), aliases)
        items[item_id] = row
    return items


def share_page(template: Template, item_id: str, card: dict | None, preview: str = "") -> str:
    title = "Retired printing"
    description = "This printing is no longer in the active collection."
    image_meta = ""
    if card:
        title = " · ".join(filter(None, (card["name"], card["number"], card["language"],
                                        card["finish"], card["foilPattern"])))
        description = f"{card['set']} · {title}"
        image_meta = (f'<meta property="og:image" content="{escape(ASSET_BASE_URL + preview)}">\n'
                      f'<meta property="og:image:alt" content="{escape("Card front: " + title)}">')
    return template.substitute(title=escape(title), description=escape(description), image_meta=image_meta,
                               url=ASSET_BASE_URL + f"cards/{item_id}/",
                               detail=f"../../card.html?item={item_id}")


def approved_preview(root: Path, model: dict, row: dict, photos: dict) -> str:
    specimen, printing = owner_specimen(model, row["specimenId"])
    asset = photos.get("verification/specimens/" + specimen["photograph"])
    if printing["itemId"] != row["itemId"] or not asset or asset["imageScope"] != "exact-printing":
        raise ValueError(f"{row['itemId']}: requires a matching exact owner photo")
    preview = asset["preview"]
    if not preview or asset["sha256"] != specimen["photographSha256"] or not (root / preview).is_file():
        raise ValueError(f"{row['itemId']}: own preview does not match its archived specimen")
    return preview


def render_pages(root: Path = ROOT) -> dict[str, str]:
    rows = read_social(root)
    model = load()
    doc = json.loads((root / "collector_catalogue.json").read_text(encoding="utf-8"))
    printings = {row["itemId"]: row for row in model["printings"]["printings"]}
    gallery, _ = gallery_cards(doc, printings, model["images"])
    cards = {card["id"]: card for card in gallery}
    photos = {asset["path"]: asset for asset in model["images"]["assets"]}
    template = Template((root / "templates/card.html").read_text(encoding="utf-8"))
    pages = {}
    for item_id, row in rows.items():
        name = f"cards/{item_id}/index.html"
        if item_id in printings and not printings[item_id]["active"]:
            pages[name] = share_page(template, item_id, None)
        else:
            preview = approved_preview(root, model, row, photos)
            pages[name] = share_page(template, item_id, cards[item_id], preview)
    return pages

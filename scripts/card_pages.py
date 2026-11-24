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
# the permalinks the uploader reports for the other two platforms (#646)
PLATFORM_URLS = {"instagramPosts": POST_URL,
                 "facebookPosts": re.compile(r"https://www\.facebook\.com/[\w./?=&%-]+", re.ASCII),
                 "threadsPosts": re.compile(r"https://www\.threads\.(?:net|com)/@[\w.]+/post/[\w-]+/?", re.ASCII)}
SHORT_ALIAS = re.compile(r"[a-zA-Z0-9-]+")
SPECIMEN_ID = re.compile(r"SPEC-[0-9]{4,8}")
SOCIAL_FIELDS = {"itemId", "specimenId", "shortAlias", "postCorners", "carousel", *PLATFORM_URLS}


def checked_posts(links, used: set, pattern=POST_URL) -> None:
    if not isinstance(links, list) or any(not isinstance(url, str) or not pattern.fullmatch(url) for url in links):
        raise ValueError("Invalid post permalink")
    if used.intersection(links) or len(set(links)) != len(links):
        raise ValueError("Duplicate post permalink")
    used.update(links)


def checked_carousel(slides, item_id: str) -> None:
    """Further own photos after the cover, in order, each with its corners and its own alt text (#646)."""
    if slides is None:
        return
    if not isinstance(slides, list) or not 1 <= len(slides) <= 19:
        raise ValueError(f"Invalid carousel: {item_id}")
    for slide in slides:
        if not valid_slide(slide):
            raise ValueError(f"Invalid carousel slide: {item_id}")
        checked_corners(slide.get("postCorners"), item_id)


def valid_slide(slide) -> bool:
    return (isinstance(slide, dict) and slide.keys() <= {"specimenId", "postCorners", "altText"}
            and isinstance(slide.get("specimenId"), str) and bool(SPECIMEN_ID.fullmatch(slide["specimenId"]))
            and isinstance(slide.get("altText"), str) and 0 < len(slide["altText"].strip()) <= 1000)


def checked_alias(alias, aliases: set) -> None:
    if alias is None:
        return
    if not isinstance(alias, str) or not SHORT_ALIAS.fullmatch(alias) or alias in aliases:
        raise ValueError(f"Invalid or duplicate short alias: {alias}")
    aliases.add(alias)


def checked_corners(corners, item_id: str) -> None:
    """The post cover's card corners: four [x, y] pixel pairs of the upright original, clockwise from top left."""
    if corners is None:
        return
    if not (isinstance(corners, list) and len(corners) == 4 and all(
            isinstance(pair, list) and len(pair) == 2 and all(type(v) is int and v >= 0 for v in pair)
            for pair in corners)):
        raise ValueError(f"Invalid post corners: {item_id}")


def read_social(root: Path) -> dict:
    rows = json.loads((root / SOCIAL_FILE).read_text(encoding="utf-8"))
    items, aliases, posts = {}, set(), set()
    for row in rows:
        if not isinstance(row, dict) or row.keys() - SOCIAL_FIELDS or "instagramPosts" not in row:
            raise ValueError("Unexpected social fields")
        item_id = row["itemId"]
        if not ITEM_ID.fullmatch(item_id) or item_id in items:
            raise ValueError(f"Invalid or duplicate social item: {item_id}")
        checked_corners(row.get("postCorners"), item_id)
        checked_carousel(row.get("carousel"), item_id)
        for field, pattern in PLATFORM_URLS.items():
            checked_posts(row.get(field, []), posts, pattern)
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
    if card and preview:
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


def own_preview(root: Path, model: dict, item: dict, photos: dict) -> str:
    """The preview of the item's own exact owner photo, or "" when its image is anything else."""
    asset = next((row for row in photos.values() if row["assetId"] == item.get("imageAssetId")), None)
    match = asset and re.fullmatch(r"verification/specimens/(SPEC-\d+)\.\w+", asset["path"])
    if not match:
        return ""
    try:
        return approved_preview(root, model, {"itemId": item["itemId"], "specimenId": match[1]}, photos)
    except ValueError:
        return ""


def render_pages(root: Path = ROOT) -> dict[str, str]:
    """A share page for every printing: built from the data, never added one by one (owner, 2026-11-23).

    The preview image is the printing's own exact owner photo; a social row must have one."""
    rows = read_social(root)
    model = load()
    doc = json.loads((root / "collector_catalogue.json").read_text(encoding="utf-8"))
    printings = {row["itemId"]: row for row in model["printings"]["printings"]}
    if unknown := rows.keys() - printings.keys():
        raise ValueError(f"social rows name unknown printings: {sorted(unknown)}")
    gallery, _ = gallery_cards(doc, printings, model["images"])
    cards = {card["id"]: card for card in gallery}
    photos = {asset["path"]: asset for asset in model["images"]["assets"]}
    template = Template((root / "templates/card.html").read_text(encoding="utf-8"))
    pages = {}
    for item_id, item in printings.items():
        if not item["active"]:
            card, preview = None, ""
        elif item_id in rows:
            card, preview = cards[item_id], approved_preview(root, model, rows[item_id], photos)
        else:
            card, preview = cards[item_id], own_preview(root, model, item, photos)
        pages[f"cards/{item_id}/index.html"] = share_page(template, item_id, card, preview)
    return pages

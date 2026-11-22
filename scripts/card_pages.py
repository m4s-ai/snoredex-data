"""Static card pages and links for the Instagram pilot."""
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


def link_list(urls: list, title: str) -> str:
    if not urls:
        return ""
    links = "".join(f'<li><a href="{escape(url)}">{escape(label)}</a></li>' for url, label in urls)
    return f"<h2>{title}</h2><ul>{links}</ul>"


def card_page(template: Template, card: dict, row: dict, image: tuple[str, str]) -> str:
    title = " · ".join(filter(None, (card["name"], card["number"], card["language"], card["finish"],
                                    card["foilPattern"])))
    details = {"Set": card["set"], "Set code": card["printedSetCode"] or card["setCode"],
               "Card number": card["number"], "Language": card["language"], "Edition": card["edition"],
               "Finish": card["finish"], "Foil pattern": card["foilPattern"], "Artist": card["artist"],
               "Markings": ", ".join(card["markings"])}
    facts = "".join(f"<dt>{label}</dt><dd>{escape(value)}</dd>"
                    for label, value in details.items() if value and value != "unknown")
    posts = [(url, f"Instagram post {n}") for n, url in enumerate(row["instagramPosts"], start=1)]
    sources = [(url, url) for url in card["sources"] if url.startswith(("https://", "http://"))]
    photo, preview = image
    values = {"url": f"{ASSET_BASE_URL}cards/{row['itemId']}/", "title": title,
              "description": f"{card['set']} · {title}", "preview": ASSET_BASE_URL + preview,
              "alt": f"Card front: {title}", "photo": "../../" + photo}
    return template.substitute({key: escape(value) for key, value in values.items()}, facts=facts,
                               sources=link_list(sources, "Sources"), posts=link_list(posts, "On Instagram"))


def approved_image(root: Path, model: dict, card: dict, row: dict, photos: dict) -> tuple[str, str]:
    specimen, printing = owner_specimen(model, row["specimenId"])
    asset = photos.get("verification/specimens/" + specimen["photograph"])
    if printing["itemId"] != row["itemId"] or not asset or asset["imageScope"] != "exact-printing":
        raise ValueError(f"{row['itemId']}: requires a matching exact owner photo")
    preview = asset["preview"]
    if not preview or asset["sha256"] != specimen["photographSha256"] or not (root / preview).is_file():
        raise ValueError(f"{row['itemId']}: own preview does not match its archived specimen")
    if card["imageScope"] == "exact-printing" and (card["imageSource"] or "").endswith("/" + specimen["photograph"]):
        return card["preview"], preview
    return preview, preview


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
            pages[name] = (root / "templates/retired-card.html").read_text(encoding="utf-8")
        else:
            image = approved_image(root, model, cards[item_id], row, photos)
            pages[name] = card_page(template, cards[item_id], row, image)
    return pages

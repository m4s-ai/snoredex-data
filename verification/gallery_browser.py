
"""Browser checks and contact sheets for the gallery workflow."""
from __future__ import annotations

from collections import defaultdict
from html import escape
from pathlib import Path
from urllib.parse import unquote, urlsplit

from gallery_workflow import local_path, require, write
from test_site import serve_site

VIEWPORTS = {
    "desktop": {"viewport": {"width": 1440, "height": 1000}},
    "mobile-dpr2": {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2,
                    "is_mobile": True, "has_touch": True},
}


def key_selector(key):
    require(all(c.isalnum() or c in "-_" for c in key), f"Invalid gallery ID: {key}")
    return f'[data-card-id="{key}"]'


def check_image(node, card, artifact):
    from PIL import Image

    if not card["preview"]:
        require(node.locator(".gallery-placeholder").count() == 1, f"Missing placeholder: {card['id']}")
        return
    image = node.locator("img")
    image.scroll_into_view_if_needed()
    source, width, dpr = image.evaluate(
        "async img => { await img.decode(); return "
        "[img.currentSrc, img.getBoundingClientRect().width, devicePixelRatio]; }")
    path = unquote(urlsplit(source).path).lstrip("/")
    declared = {row["path"]: row["width"] for row in card["imageSizes"]}
    require(path in declared, f"Wrong image shown: {card['id']}")
    with Image.open(local_path(artifact, path, "images/gallery/")) as decoded:
        require(decoded.width == declared[path] and decoded.width >= min(card["imageWidth"], width * dpr) - 2,
                f"Browser selected a low resolution image: {card['id']}")


def check_grid(page, cards, keys, artifact):
    for key in keys:
        card = cards[key]
        node = page.locator(key_selector(key))
        check_image(node, card, artifact)
        node.click()
        check_image(page.locator("#card-picture"), card, artifact)
        require(card["number"] in page.locator("#card-facts").inner_text(), f"Wrong details for {key}")
        note = page.get_by_text("Representative card image", exact=True).count()
        require(note == int(card["imageScope"] == "representative"), f"Wrong scope label for {key}")
        page.get_by_role("button", name="Close", exact=True).click()


def check_binder(page, keys, cards, artifact):
    page.locator("#binder-toggle").click()
    for size in (2, 3, 4, 5):
        for order in ("page", "row"):
            page.locator("input[name=rows]").fill(str(size))
            page.locator("input[name=columns]").fill(str(size))
            page.locator("select[name=order]").select_option(order)
            page.get_by_role("button", name="Apply layout", exact=True).click()
            for key in keys:
                # The main browser suite separately tests the actual paging controls.
                page.evaluate("(id) => { spread=Math.floor(orderedCards.findIndex(c=>c.id===id)"
                              "/(2*rows*columns)); render(); }", key)
                check_image(page.locator(key_selector(key)), cards[key], artifact)
            require(page.evaluate("document.documentElement.scrollWidth === innerWidth"), "Binder page overflows.")


def by_group(cards):
    groups = defaultdict(list)
    for card in cards.values():
        groups[card["group"]].append(card)
    return groups


def group_samples(cards):
    for group in by_group(cards).values():
        for scope in (None, "exact-printing", "representative"):
            found = next((card["id"] for card in group if card["imageScope"] == scope), None)
            if found:
                yield found


def check_page(page, origin, cards, keys, artifact, all_groups):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("response", lambda response: errors.append(f"{response.status}: {response.url}")
            if response.url.startswith(origin + "/") and response.status >= 400 else None)
    page.goto(origin + "/gallery.html")
    displayed = page.locator("#gallery-data").evaluate("node => JSON.parse(node.textContent)")
    require(displayed == list(cards.values()), "Artifact embeds different card data.")
    if all_groups:
        keys_in_dom = page.locator("[data-card-id]").evaluate_all("nodes => nodes.map(node => node.dataset.cardId)")
        require(set(keys_in_dom) == set(cards) and len(keys_in_dom) == len(cards), "Grid omits or repeats cards.")
    check_grid(page, cards, keys, artifact)
    check_binder(page, keys, cards, artifact)
    require(not errors, "Browser errors: " + ", ".join(errors[:5]))


def run(artifact, cards, targets, all_groups=False):
    from playwright.sync_api import sync_playwright

    keys = list(group_samples(cards)) if all_groups else list(targets)
    with serve_site(artifact) as origin, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for viewport in VIEWPORTS.values():
            page = browser.new_page(**viewport, reduced_motion="reduce")
            check_page(page, origin, cards, keys, artifact, all_groups)
            page.close()
        browser.close()
    return {"viewports": list(VIEWPORTS), "cardsCheckedInGridLightboxAndBinder": keys,
            "binderLayoutsPerViewport": 8, "fullGridMembershipChecked": all_groups}


def card_tile(card, artifact):
    name = escape(" · ".join(str(card.get(key) or "") for key in ("name", "number", "language", "finish")))
    label = escape(card["imageScope"] or "Image needed")
    image = ""
    if card["preview"]:
        uri = local_path(artifact, card["preview"], "images/gallery/").as_uri()
        image = f'<img src="{escape(uri, quote=True)}" alt="{name}" loading="lazy">'
    identifier = escape(card["id"])
    return f"<figure>{image}<figcaption>{name}<br>{label}<br><small>{identifier}</small></figcaption></figure>"


def review_packet(folder, cards, artifact):
    sections = []
    inventory = []
    for group, entries in by_group(cards).items():
        tiles = "".join(card_tile(card, artifact) for card in entries)
        sections.append(f'<section><h2>{escape(group)}</h2><div class="cards">{tiles}</div></section>')
        inventory.append({"group": group, "items": [card["id"] for card in entries]})
    html = ('<!DOCTYPE html><html lang="en"><meta charset="utf-8"><title>Gallery contact sheets</title>'
            '<style>body{font:16px sans-serif;margin:2rem}.cards{display:grid;'
            'grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:1rem}'
            'figure{margin:0;overflow-wrap:anywhere}img{width:100%;height:auto}</style>'
            '<h1>Gallery contact sheets</h1><p>Inspect every group for full faces, correct edition, framing, '
            'color, legibility and image scope. Record remaining needs and any corrections before sign-off.</p>'
            + "".join(sections) + "</html>")
    from gallery_workflow import save

    save(folder / "contact-sheets.html", html.encode("utf-8"))
    write(folder / "group-inventory.json", inventory)

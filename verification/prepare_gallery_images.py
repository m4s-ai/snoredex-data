#!/usr/bin/env python3
"""Prepare selected gallery recipes with the pinned Chromium, without changing evidence originals.

python verification/prepare_gallery_images.py --prepare RECIPE_ID [RECIPE_ID ...]
python verification/prepare_gallery_images.py --check

Review candidates and recipes in verification/gallery_image_inventory.json and
verification/gallery_image_recipes.json. Corners use decoded-image pixels in upright TL/TR/BR/BL
order; choosing the upright first corner handles rotation. Run scripts/site.py after preparing.
Acceptance is a separate recipe review followed by preparation again. Normal checks need no browser.
"""

import argparse
import base64
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from atomic_write import atomic_write
from file_digest import sha256_hex
from gallery_image_assets import (
    MANIFEST, MIN_WIDTH, RECIPES, RENDERER, crop_dimensions, processor_digest, read_store,
    recipe_digest, validated_recipes, validate_output,
)
from gallery_image_inventory import local_source


def render_recipe(page, recipe, root):
    path = local_source(root, recipe["source"])
    source = base64.b64encode(path.read_bytes()).decode("ascii")
    kind = "image/png" if path.read_bytes().startswith(b"\x89PNG") else "image/jpeg"
    renderer = (root / RENDERER).read_text(encoding="utf-8")
    return page.evaluate(renderer, {
        "source": f"data:{kind};base64,{source}", "recipe": recipe, "dimensions": crop_dimensions(recipe),
    })


def save_image(root, image):
    prefix, encoded = image.pop("data").split(",", 1)
    if prefix != "data:image/webp;base64":
        raise ValueError("Browser did not encode WebP")
    data = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(data).hexdigest()
    relative = f"images/gallery/{digest}.webp"
    path = local_source(root, relative)
    image.update(path=relative, sha256=digest)
    if path.exists():
        validate_output(image, root)
        return image
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, data)
    validate_output(image, root)
    return image


def prepare_recipe(recipe, page, engine, root):
    source = local_source(root, recipe["source"])
    before = sha256_hex(source)
    if before != recipe["sourceSha256"]:
        raise ValueError("Original changed before preparation")
    dimensions = crop_dimensions(recipe)
    record = {
        "sourceSha256": before, "recipeSha256": recipe_digest(recipe),
        "processorSha256": processor_digest(root), "engine": engine,
        "dimensions": list(dimensions), "quality": "below-minimum", "images": [],
    }
    if dimensions[0] >= MIN_WIDTH:
        images = render_recipe(page, recipe, root)
        record.update(quality="ready", images=[save_image(root, image) for image in images])
    if sha256_hex(source) != before:
        raise ValueError("Original changed during preparation")
    return record


def prepare(ids, root=ROOT):
    from playwright.sync_api import sync_playwright

    inventory = read_store(root, "verification/gallery_image_inventory.json")
    recipes, entries = validated_recipes(inventory, root, replacing=ids)
    by_id = {recipe["id"]: recipe for recipe in recipes}
    if len(set(ids)) != len(ids) or set(ids) - by_id.keys():
        raise ValueError("Specify unique, existing recipe IDs")
    pin = next(line.split("==")[1] for line in (root / "requirements.txt").read_text().splitlines()
               if line.startswith("playwright=="))
    if version("playwright") != pin:
        raise ValueError("Install the pinned requirements before preparing gallery images")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.route("**/*", lambda route: route.abort())
            engine = {"playwright": pin, "chromium": browser.version}
            for recipe_id in ids:
                entries[recipe_id] = prepare_recipe(by_id[recipe_id], page, engine, root)
        finally:
            browser.close()
    body = json.dumps({"schemaVersion": 1, "entries": entries}, indent=2, ensure_ascii=False) + "\n"
    if (root / MANIFEST).read_text(encoding="utf-8") != body:
        atomic_write(root / MANIFEST, body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--prepare", nargs="+", metavar="RECIPE_ID")
    actions.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        validated_recipes(read_store(ROOT, "verification/gallery_image_inventory.json"), ROOT)
        print("Gallery recipes, original hashes and prepared images are current.")
        return 0
    lock = ROOT / "verification/gallery_image_manifest.json.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.close(descriptor)
        prepare(args.prepare, ROOT)
    finally:
        lock.unlink()
    print(f"Prepared {len(args.prepare)} gallery recipes; run python scripts/site.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

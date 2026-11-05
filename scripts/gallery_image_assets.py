"""Validate and select separately prepared gallery images using only the standard library."""

import hashlib
import json
import math
import re

from file_digest import sha256_hex
from gallery_image_inventory import ROOT, inventory_inputs, local_source

RECIPES = "verification/gallery_image_recipes.json"
MANIFEST = "verification/gallery_image_manifest.json"
RENDERER = "verification/gallery_image_renderer.js"
PROCESSOR = "verification/prepare_gallery_images.py"
MIN_WIDTH = 600
MAX_WIDTH = 1200


def read_store(root, relative):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def recipe_digest(recipe):
    data = json.dumps(recipe, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def processor_digest(root):
    data = (root / RENDERER).read_bytes() + (root / PROCESSOR).read_bytes()
    return hashlib.sha256(data).hexdigest()


def crop_dimensions(recipe):
    corners = recipe["corners"]
    top, bottom = math.dist(corners[0], corners[1]), math.dist(corners[3], corners[2])
    left, right = math.dist(corners[0], corners[3]), math.dist(corners[1], corners[2])
    area = abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(corners, corners[1:] + corners[:1]))) / 2
    width = min(top, bottom, area / max(left, right))
    height = min(left, right, area / max(top, bottom))
    aspect = recipe["aspectRatio"][0] / recipe["aspectRatio"][1]
    available = min(width, height * aspect)
    output_width = min(MAX_WIDTH, math.floor(available))
    return output_width, math.floor(output_width / aspect)


def validate_geometry(recipe, source):
    dimensions = recipe.get("sourceDimensions", [])
    if sorted(dimensions) != sorted(source["dimensions"]):
        raise ValueError("Recipe source dimensions do not match the retained original")
    corners = recipe.get("corners", [])
    if len(corners) != 4:
        raise ValueError("Four corners are required, in upright TL, TR, BR, BL order")
    for point in corners:
        validate_point(point, dimensions)
    for index in range(4):
        a, b, c = (corners[(index + offset) % 4] for offset in range(3))
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if cross <= 0:
            raise ValueError("Crop must be a non-degenerate clockwise convex quadrilateral")
    validate_aspect(recipe.get("aspectRatio", []))


def validate_aspect(ratio):
    if len(ratio) != 2 or not all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0 for value in ratio):
        raise ValueError("A finite positive card aspect ratio is required")
    if not 0.2 <= ratio[0] / ratio[1] <= 5:
        raise ValueError("Unsupported card aspect ratio")


def validate_point(point, dimensions):
    if not isinstance(point, list) or len(point) != 2:
        raise ValueError("Crop points must have two coordinates")
    for coordinate, limit in zip(point, dimensions):
        if not isinstance(coordinate, (float, int)) or not math.isfinite(coordinate) or not 0 <= coordinate <= limit:
            raise ValueError("Crop points must be within the decoded source image")


def validate_targets(recipe, items):
    targets = recipe.get("targets", [])
    if not targets or len({target["itemId"] for target in targets}) != len(targets):
        raise ValueError("Unique target item IDs are required")
    for target in targets:
        validate_target(recipe, target, items)


def validate_target(recipe, target, items):
    item = items.get(target["itemId"])
    if item is None:
        raise ValueError(f"Unknown gallery item: {target['itemId']}")
    candidates = [row for row in item["candidates"] if row["source"] == recipe["source"]]
    if not candidates:
        raise ValueError(f"Source does not belong to target item: {target['itemId']}")
    scope = target.get("scope")
    if scope not in {"exact-printing", "representative"}:
        raise ValueError("Invalid image scope")
    if scope == "exact-printing" and not any(row["scope"] == scope for row in candidates):
        raise ValueError("A representative source cannot assert exact-printing scope")


def validate_recipe(recipe, inventory, root=ROOT):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", recipe.get("id", "")):
        raise ValueError("Invalid gallery recipe ID")
    source = inventory["sources"].get(recipe.get("source"))
    if source is None or source["kind"] == "remote":
        raise ValueError("Recipe requires a retained local candidate source")
    path = local_source(root, recipe["source"])
    if sha256_hex(path) != recipe.get("sourceSha256"):
        raise ValueError("Gallery original changed; review its recipe again")
    if recipe.get("mediaKind") not in {"photo", "render"}:
        raise ValueError("Recipe must classify its source as photo or render")
    validate_review(recipe.get("review", {}))
    validate_geometry(recipe, source)
    validate_targets(recipe, {item["itemId"]: item for item in inventory["items"]})


def validate_review(review):
    note = review.get("note")
    if review.get("status") not in {"pending", "accepted", "rejected"} or not isinstance(note, str) or not note.strip():
        raise ValueError("A review status and descriptive review note are required")


def webp_dimensions(data):
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("Gallery derivative is not WebP")
    if int.from_bytes(data[4:8], "little") + 8 != len(data):
        raise ValueError("Truncated gallery WebP")
    chunk = data[12:16]
    if chunk == b"VP8X":
        return int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1
    if chunk == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
        return int.from_bytes(data[26:28], "little") & 16383, int.from_bytes(data[28:30], "little") & 16383
    if chunk == b"VP8L" and data[20] == 47:
        packed = int.from_bytes(data[21:25], "little")
        return (packed & 16383) + 1, ((packed >> 14) & 16383) + 1
    raise ValueError("Unsupported WebP header")


def validate_output(output, root):
    path = output.get("path", "")
    digest = output.get("sha256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or path != f"images/gallery/{digest}.webp":
        raise ValueError("Gallery outputs must use content-addressed WebP paths")
    local = local_source(root, path)
    if sha256_hex(local) != digest:
        raise ValueError(f"Gallery output changed: {path}")
    if webp_dimensions(local.read_bytes()) != (output["width"], output["height"]):
        raise ValueError(f"Gallery output dimensions changed: {path}")


def validate_record(recipe, record, root):
    if record.get("recipeSha256") != recipe_digest(recipe) or record.get("sourceSha256") != recipe["sourceSha256"]:
        raise ValueError("Gallery derivative belongs to an older source or recipe")
    if record.get("processorSha256") != processor_digest(root):
        raise ValueError("Gallery processor changed; re-prepare the derivative")
    engine = record.get("engine", {})
    pin = next(line.split("==")[1] for line in (root / "requirements.txt").read_text().splitlines()
               if line.startswith("playwright=="))
    if engine.get("playwright") != pin or not engine.get("chromium"):
        raise ValueError("Gallery preparation must use the pinned Playwright and Chromium")
    dimensions = crop_dimensions(recipe)
    if record.get("dimensions") != list(dimensions):
        raise ValueError("Output resolution does not match the reviewed crop")
    validate_record_images(record, dimensions, root)


def validate_record_images(record, dimensions, root):
    outputs = record.get("images", [])
    if dimensions[0] < MIN_WIDTH:
        if outputs or record.get("quality") != "below-minimum":
            raise ValueError("Small crops must stay rejected, without upscaled derivatives")
        return
    if record.get("quality") != "ready":
        raise ValueError("Invalid gallery image quality status")
    widths = sorted({240, 480, dimensions[0]})
    if [row["width"] for row in outputs] != widths:
        raise ValueError("Incomplete responsive gallery image sizes")
    for output in outputs:
        if output["height"] != math.floor(output["width"] * dimensions[1] / dimensions[0]):
            raise ValueError("Responsive image aspect ratio changed")
        validate_output(output, root)


def validated_recipes(inventory, root=ROOT, replacing=()):
    if inventory.get("meta", {}).get("inputs") != inventory_inputs(root):
        raise ValueError("Gallery inventory is stale; regenerate it with scripts/site.py")
    store = read_store(root, RECIPES)
    recipes = store["recipes"]
    unavailable_targets(store, inventory)
    manifest = read_store(root, MANIFEST)
    if manifest.get("schemaVersion") != 1 or store.get("schemaVersion") != 1:
        raise ValueError("Unsupported gallery image store version")
    ids = {recipe["id"] for recipe in recipes}
    if len(ids) != len(recipes) or set(manifest["entries"]) - ids:
        raise ValueError("Duplicate recipes or orphan gallery derivatives")
    for recipe in recipes:
        validate_recipe(recipe, inventory, root)
        validate_prepared_recipe(recipe, manifest["entries"].get(recipe["id"]), replacing, root)
    return recipes, manifest["entries"]


def unavailable_targets(store, inventory):
    entries = {item["itemId"]: item for item in inventory["items"]}
    targets = set()
    for target in store.get("unavailableTargets", []):
        item_id = target.get("itemId")
        note = target.get("note")
        if item_id not in entries or item_id in targets or not isinstance(note, str) or not note.strip():
            raise ValueError("Unavailable targets require unique known item IDs and review notes")
        if entries[item_id]["candidates"]:
            raise ValueError("A source-less image need gained candidates; review those sources")
        targets.add(item_id)
    return targets


def validate_prepared_recipe(recipe, record, replacing, root):
    if recipe["id"] in replacing:
        return
    if recipe["review"]["status"] == "accepted" and not record:
        raise ValueError("Accepted gallery recipe has no prepared output")
    if record:
        validate_record(recipe, record, root)


def select_prepared(recipes, records):
    selected = {}
    for recipe in sorted(recipes, key=lambda row: (row["mediaKind"] != "photo", row["id"])):
        record = records.get(recipe["id"], {})
        if recipe["review"]["status"] != "accepted" or record.get("quality") != "ready":
            continue
        for target in recipe["targets"]:
            selected.setdefault(target["itemId"], (recipe, record, target))
    return selected


def prepared_image(recipe, record, target):
    outputs = record["images"]
    return {
        "imageSource": recipe["source"], "imageScope": target["scope"],
        "thumbnail": outputs[0]["path"], "preview": outputs[-1]["path"],
        "imageSizes": outputs, "imageWidth": outputs[-1]["width"], "imageHeight": outputs[-1]["height"],
        "imageRecipe": recipe["id"], "mediaKind": recipe["mediaKind"],
    }


def apply_prepared(cards, inventory, root=ROOT):
    recipes, records = validated_recipes(inventory, root)
    selected = select_prepared(recipes, records)
    targeted = {target["itemId"] for recipe in recipes for target in recipe["targets"]}
    targeted.update(unavailable_targets(read_store(root, RECIPES), inventory))
    entries = {item["itemId"]: item for item in inventory["items"]}
    for card in cards:
        item_id = card["id"]
        if item_id in targeted:
            card.update(thumbnail=None, preview=None, imageSource=None, imageScope=None)
            entries[item_id]["status"] = "needs-image"
        if item_id in selected:
            recipe, record, target = selected[item_id]
            card.update(prepared_image(recipe, record, target))
            entries[item_id].update(status="accepted", selectedRecipe=recipe["id"])
    return cards


def published_gallery_images(root):
    if not (root / RECIPES).exists():
        return set()
    inventory = read_store(root, "verification/gallery_image_inventory.json")
    recipes, records = validated_recipes(inventory, root)
    return {output["path"] for recipe, record, target in select_prepared(recipes, records).values()
            for output in record["images"]}


def filter_gallery_outputs(paths, root):
    gallery = published_gallery_images(root)
    return [path for path in paths if not path.startswith("images/gallery/") or path in gallery]

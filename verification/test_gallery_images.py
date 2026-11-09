"""Gallery recipe identity, quality selection and integrity regressions, without a browser."""

import copy
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from artwork_derivatives import encode_png
from gallery_image_assets import (
    MANIFEST, MIN_WIDTH, RECIPES, apply_prepared, crop_dimensions, read_store, recipe_digest, select_prepared,
    validated_recipes, validate_recipe, validate_record, unavailable_targets, published_gallery_images,
)
from gallery_image_inventory import INPUTS, inventory_inputs, item_candidates, source_info


def fixture(root):
    source = "verification/specimens/fixture.png"
    path = root / source
    path.parent.mkdir(parents=True)
    path.write_bytes(encode_png(800, 1120, [(0, 0, 255)] * (800 * 1120)))
    info = source_info(root, source)
    for relative in INPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", newline="\n")
    inventory = {"meta": {"inputs": inventory_inputs(root)}, "sources": {source: info}, "items": [{
        "itemId": "fixture-item", "candidates": [{"source": source, "scope": "exact-printing"}],
    }]}
    recipe = {
        "id": "fixture-photo", "source": source, "sourceSha256": info["sha256"],
        "sourceDimensions": [800, 1120], "corners": [[0, 0], [800, 0], [800, 1120], [0, 1120]],
        "aspectRatio": [5, 7], "mediaKind": "photo",
        "review": {"status": "accepted", "note": "Synthetic geometry and identity fixture"},
        "targets": [{"itemId": "fixture-item", "scope": "exact-printing"}],
    }
    return inventory, recipe


def must_reject(operation):
    try:
        operation()
    except ValueError:
        return
    raise AssertionError("Seeded violation was accepted")


def check_recipe_integrity(root, inventory, recipe):
    validate_recipe(recipe, inventory, root)
    assert crop_dimensions(recipe) == (800, 1120)
    wrong = copy.deepcopy(recipe)
    wrong["targets"][0]["itemId"] = "other-printing"
    must_reject(lambda: validate_recipe(wrong, inventory, root))
    limited = copy.deepcopy(inventory)
    limited["items"][0]["candidates"][0]["scope"] = "representative"
    must_reject(lambda: validate_recipe(recipe, limited, root))
    bad_geometry = copy.deepcopy(recipe)
    bad_geometry["corners"][1] = [0, 1120]
    must_reject(lambda: validate_recipe(bad_geometry, inventory, root))
    missing_review = copy.deepcopy(recipe)
    missing_review["review"]["note"] = None
    must_reject(lambda: validate_recipe(missing_review, inventory, root))
    path = root / recipe["source"]
    original = path.read_bytes()
    path.write_bytes(original + b"changed")
    must_reject(lambda: validate_recipe(recipe, inventory, root))
    path.write_bytes(original)


def check_finish_printing_citation(recipe):
    source = recipe["source"]
    member = {"images": [{"src": source, "observationId": "specimen:SPEC-0001"}]}
    assets = {"asset": {"assetId": "asset", "path": source}}
    item = {"itemId": "fixture-item", "imageAssetId": "asset", "imageScope": "card-release",
            "sourcePrintingId": "F0001-P01"}
    citations = {"F0001-P01": {"SPEC-0001"}}
    assert item_candidates(item, member, assets, {}, citations) == [{
        "source": source, "scope": "exact-printing", "identityBasis": "finish-printing-citation",
        "sourceRef": "specimen:SPEC-0001",
    }]
    sibling = {**item, "sourcePrintingId": "F0001-P02"}
    assert item_candidates(sibling, member, assets, {}, citations)[0]["scope"] == "representative"


def check_quality_selection(recipe):
    render = copy.deepcopy(recipe)
    render.update(id="fixture-render", mediaKind="render")
    ready = {"quality": "ready"}
    selected = select_prepared([render, recipe], {render["id"]: ready, recipe["id"]: ready})
    assert selected["fixture-item"][0]["mediaKind"] == "photo"
    selected = select_prepared([recipe, render], {recipe["id"]: {"quality": "below-minimum"}, render["id"]: ready})
    assert selected["fixture-item"][0]["mediaKind"] == "render"
    assert select_prepared([recipe], {recipe["id"]: {"quality": "below-minimum"}}) == {}
    small = copy.deepcopy(recipe)
    small["corners"] = [[0, 0], [300, 0], [300, 420], [0, 420]]
    assert crop_dimensions(small) == (300, 420)
    sheared = copy.deepcopy(recipe)
    sheared["corners"] = [[0, 0], [1000, 1000], [2000, 2001], [1000, 1001]]
    assert crop_dimensions(sheared)[0] < 600


def check_specimen_media(root, inventory, recipe):
    # Storage identifies retained evidence, not whether its pixels came from a camera.
    assert inventory["sources"][recipe["source"]]["kind"] == "unclassified"
    render = copy.deepcopy(recipe)
    render.update(id="fixture-render", mediaKind="render")
    validate_recipe(render, inventory, root)
    validate_recipe(recipe, inventory, root)
    unreviewed = copy.deepcopy(render)
    unreviewed["mediaKind"] = "unclassified"
    must_reject(lambda: validate_recipe(unreviewed, inventory, root))
    source = "verification/specimens/SPEC-0507.png"
    info = source_info(ROOT, source)
    assert info["kind"] == "unclassified" and info["dimensions"] == [660, 920]
    actual = copy.deepcopy(render)
    actual.update(source=source, sourceSha256=info["sha256"], sourceDimensions=[660, 920],
                  corners=[[0, 0], [660, 0], [660, 920], [0, 920]])
    actual_inventory = {"sources": {source: info}, "items": [{"itemId": "fixture-item",
        "candidates": [{"source": source, "scope": "exact-printing"}]}]}
    validate_recipe(actual, actual_inventory, ROOT)
    selected = select_prepared([actual, recipe], {actual["id"]: {"quality": "ready"},
                                                recipe["id"]: {"quality": "ready"}})
    assert selected["fixture-item"][0]["mediaKind"] == "photo"


def check_stale_outputs(root, inventory, recipe):
    verification = root / "verification"
    (verification / "gallery_image_recipes.json").write_text(json.dumps({"schemaVersion": 1, "recipes": [recipe]}), newline="\n")
    (verification / "gallery_image_manifest.json").write_text(json.dumps({"schemaVersion": 1, "entries": {}}), newline="\n")
    must_reject(lambda: validated_recipes(inventory, root))
    must_reject(lambda: validate_record(recipe, {"recipeSha256": recipe_digest(recipe),
                                                "sourceSha256": "0" * 64}, root))
    pending = copy.deepcopy(recipe)
    pending["review"]["status"] = "pending"
    (verification / "gallery_image_recipes.json").write_text(json.dumps({"schemaVersion": 1, "recipes": [pending]}), newline="\n")
    cards = [{"id": "fixture-item", "thumbnail": "legacy.jpg", "preview": "legacy.jpg"},
             {"id": "later-batch", "thumbnail": "untouched.jpg"}]
    apply_prepared(cards, inventory, root)
    assert cards[0]["thumbnail"] is None and cards[0]["preview"] is None
    assert cards[1]["thumbnail"] == "untouched.jpg"
    (root / "collector_catalogue.json").write_text('{"changed":true}', newline="\n")
    must_reject(lambda: validated_recipes(inventory, root))


def check_source_less_targets(root, inventory):
    inventory = copy.deepcopy(inventory)
    inventory["items"].append({"itemId": "research-no-source", "candidates": []})
    store = {"schemaVersion": 1, "recipes": [], "unavailableTargets": [
        {"itemId": "research-no-source", "note": "Need a retained localized prerelease front"}]}
    path = root / "verification/gallery_image_recipes.json"
    path.write_text(json.dumps(store), newline="\n")
    (root / "verification/gallery_image_inventory.json").write_text(json.dumps(inventory), newline="\n")
    (root / "verification/gallery_image_manifest.json").write_text(json.dumps({"schemaVersion": 1, "entries": {}}), newline="\n")
    cards = [{"id": "research-no-source", "thumbnail": "wrong.jpg", "preview": "wrong.jpg"},
             {"id": "fixture-item", "thumbnail": "untouched.jpg"}]
    apply_prepared(cards, inventory, root)
    assert cards[0]["thumbnail"] is None and cards[0]["preview"] is None
    assert inventory["items"][-1]["status"] == "needs-image"
    assert cards[1]["thumbnail"] == "untouched.jpg" and not published_gallery_images(root)
    for target in [{"itemId": "unknown", "note": "Need a front"},
                   {"itemId": "research-no-source", "note": " "},
                   {"itemId": "fixture-item", "note": "Has an actual candidate"}]:
        wrong = {**store, "unavailableTargets": [target]}
        must_reject(lambda: unavailable_targets(wrong, inventory))
    must_reject(lambda: unavailable_targets({**store, "unavailableTargets": store["unavailableTargets"] * 2}, inventory))
    inventory["items"][-1]["candidates"] = [{"source": "new-front.png"}]
    must_reject(lambda: validated_recipes(inventory, root))


def require(condition, item_id, message):
    if not condition:
        raise ValueError(f"{item_id}: {message}")


def published_state(root):
    page = (root / "gallery.html").read_text(encoding="utf-8")
    cards = re.search(r'<script[^>]*id="gallery-data"[^>]*>(.*?)</script>', page, re.S).group(1)
    return {"cards": json.loads(cards), "inventory": read_store(root, "verification/gallery_image_inventory.json"),
            "store": read_store(root, RECIPES), "records": read_store(root, MANIFEST)["entries"]}


def image_need_reasons(store, records):
    reviewed = {target["itemId"] for recipe in store["recipes"] for target in recipe["targets"]
                if recipe["review"]["status"] == "rejected"
                or records.get(recipe["id"], {}).get("quality") == "below-minimum"}
    return reviewed | {row["itemId"] for row in store.get("unavailableTargets", []) if row["note"].strip()}


def check_accepted_card(card, item, choice, root):
    item_id = card["id"]
    require(choice, item_id, "accepted without a selected prepared recipe")
    recipe, record, target = choice
    require(item["selectedRecipe"] == card["imageRecipe"] == recipe["id"], item_id, "selected recipe differs")
    paths = [row["path"] for row in card["imageSizes"]]
    require(paths == [row["path"] for row in record["images"]], item_id, "srcset differs from the manifest")
    require(card["thumbnail"] == paths[0] and card["preview"] == paths[-1], item_id, "preview is not a variant")
    require(all(path.startswith("images/gallery/") and (root / path).is_file() for path in paths),
            item_id, "prepared image missing")
    require(card["imageWidth"] == record["images"][-1]["width"] >= MIN_WIDTH, item_id, "width below minimum")
    require(card["imageSource"].endswith(recipe["source"]) and (root / recipe["source"]).is_file(),
            item_id, "imageSource is not the recipe's retained original")
    require(card["imageScope"] == target["scope"], item_id, "imageScope differs from the recipe target")


def check_unprepared_card(card, item, reasons, batched):
    item_id = card["id"]
    require(not (item.get("selectedRecipe") or card.get("imageRecipe") or card.get("imageSizes")),
            item_id, "unprepared card carries a prepared image")
    if item["status"] == "awaiting-batch":  # no recipe yet: keeps its legacy image until its batch begins
        require(item_id not in batched, item_id, "batched item still awaits its batch")
        return
    require(item["status"] == "needs-image", item_id, "unknown status")
    require(not any(card.get(key) for key in ("thumbnail", "preview", "imageSource")),
            item_id, "needs-image card shows an image")
    require(item_id in reasons, item_id, "needs-image without a reviewed rejection or unavailable note")


def check_published_items(state, root=ROOT):
    """Join every published card to its inventory item, recipe and prepared images."""
    cards, items, store = state["cards"], {item["itemId"]: item for item in state["inventory"]["items"]}, state["store"]
    require(len(cards) == len(items) == len({card["id"] for card in cards} & items.keys()),
            "gallery", "one card per inventory item")
    selected = select_prepared(store["recipes"], state["records"])
    reasons = image_need_reasons(store, state["records"])
    batched = {target["itemId"] for recipe in store["recipes"] for target in recipe["targets"]}
    batched |= {row["itemId"] for row in store.get("unavailableTargets", [])}
    for card in cards:
        item = items[card["id"]]
        if item["status"] == "accepted":
            check_accepted_card(card, item, selected.get(card["id"]), root)
        else:
            check_unprepared_card(card, item, reasons, batched)


def unprepared_variant(state, index, status, show=None, unbatch=True, note=False):
    """Turn the accepted card at index into an unprepared item, independent of what the data holds."""
    seeded = copy.deepcopy(state)
    card = seeded["cards"][index]
    next(row for row in seeded["inventory"]["items"] if row["itemId"] == card["id"]).update(
        status=status, selectedRecipe=None)
    card.update(dict.fromkeys(("thumbnail", "preview", "imageSource", "imageScope", "imageSizes", "imageRecipe")))
    card.update(show or {})
    for recipe in seeded["store"]["recipes"] if unbatch else []:
        recipe["targets"] = [target for target in recipe["targets"] if target["itemId"] != card["id"]]
    if note:
        seeded["store"].setdefault("unavailableTargets", []).append({"itemId": card["id"], "note": "Seeded need."})
    return seeded


def check_published_violations(state):
    accepted = next(index for index, card in enumerate(state["cards"]) if card.get("imageRecipe"))
    check_published_items(unprepared_variant(state, accepted, "awaiting-batch"))
    check_published_items(unprepared_variant(state, accepted, "needs-image", note=True))
    scope = {"exact-printing": "representative"}.get(state["cards"][accepted]["imageScope"], "exact-printing")
    seeds = [{"imageScope": scope}, {"imageWidth": MIN_WIDTH - 1},
             {"imageSource": "verification/specimens/SPEC-0001.png"}, {"preview": "images/gallery/missing.webp"}]
    for change in seeds:
        seeded = copy.deepcopy(state)
        seeded["cards"][accepted].update(change)
        must_reject(lambda: check_published_items(seeded))
    for seeded in (unprepared_variant(state, accepted, "needs-image", {"preview": "images/gallery/x.webp"}, note=True),
                   unprepared_variant(state, accepted, "needs-image"),
                   unprepared_variant(state, accepted, "awaiting-batch", unbatch=False),
                   unprepared_variant(state, accepted, "awaiting-batch", {"imageRecipe": "seeded"}),
                   {**state, "cards": state["cards"] + [state["cards"][accepted]]}):
        must_reject(lambda: check_published_items(seeded))


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        inventory, recipe = fixture(root)
        check_recipe_integrity(root, inventory, recipe)
        check_finish_printing_citation(recipe)
        check_quality_selection(recipe)
        check_specimen_media(root, inventory, recipe)
        check_source_less_targets(root, inventory)
        check_stale_outputs(root, inventory, recipe)
    state = published_state(ROOT)
    check_published_items(state)
    check_published_violations(state)
    print(f"Gallery image checks passed for {len(state['cards'])} published items, "
          "including seeded identity, source, scope and stale-output violations.")


if __name__ == "__main__":
    main()

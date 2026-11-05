"""Gallery recipe identity, quality selection and integrity regressions, without a browser."""

import copy
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from artwork_derivatives import encode_png
from gallery_image_assets import (
    apply_prepared, crop_dimensions, recipe_digest, select_prepared, validated_recipes, validate_recipe,
    validate_record,
    unavailable_targets, published_gallery_images,
)
from gallery_image_inventory import INPUTS, inventory_inputs, source_info


def fixture(root):
    source = "verification/specimens/fixture.png"
    path = root / source
    path.parent.mkdir(parents=True)
    path.write_bytes(encode_png(800, 1120, [(0, 0, 255)] * (800 * 1120)))
    info = source_info(root, source)
    for relative in INPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
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
    (verification / "gallery_image_recipes.json").write_text(json.dumps({"schemaVersion": 1, "recipes": [recipe]}))
    (verification / "gallery_image_manifest.json").write_text(json.dumps({"schemaVersion": 1, "entries": {}}))
    must_reject(lambda: validated_recipes(inventory, root))
    must_reject(lambda: validate_record(recipe, {"recipeSha256": recipe_digest(recipe),
                                                "sourceSha256": "0" * 64}, root))
    pending = copy.deepcopy(recipe)
    pending["review"]["status"] = "pending"
    (verification / "gallery_image_recipes.json").write_text(json.dumps({"schemaVersion": 1, "recipes": [pending]}))
    cards = [{"id": "fixture-item", "thumbnail": "legacy.jpg", "preview": "legacy.jpg"},
             {"id": "later-batch", "thumbnail": "untouched.jpg"}]
    apply_prepared(cards, inventory, root)
    assert cards[0]["thumbnail"] is None and cards[0]["preview"] is None
    assert cards[1]["thumbnail"] == "untouched.jpg"
    (root / "collector_catalogue.json").write_text('{"changed":true}')
    must_reject(lambda: validated_recipes(inventory, root))


def check_source_less_targets(root, inventory):
    inventory = copy.deepcopy(inventory)
    inventory["items"].append({"itemId": "research-no-source", "candidates": []})
    store = {"schemaVersion": 1, "recipes": [], "unavailableTargets": [
        {"itemId": "research-no-source", "note": "Need a retained localized prerelease front"}]}
    path = root / "verification/gallery_image_recipes.json"
    path.write_text(json.dumps(store))
    (root / "verification/gallery_image_inventory.json").write_text(json.dumps(inventory))
    (root / "verification/gallery_image_manifest.json").write_text(json.dumps({"schemaVersion": 1, "entries": {}}))
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


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        inventory, recipe = fixture(root)
        check_recipe_integrity(root, inventory, recipe)
        check_quality_selection(recipe)
        check_specimen_media(root, inventory, recipe)
        check_source_less_targets(root, inventory)
        check_stale_outputs(root, inventory, recipe)
    print("Gallery image checks passed, including seeded identity, source and stale-output violations.")


if __name__ == "__main__":
    main()

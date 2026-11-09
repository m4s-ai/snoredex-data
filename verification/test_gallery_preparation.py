"""Browser verification of full-detail decoding, rotation, perspective and gallery output integrity."""

import base64
import copy
from importlib.metadata import version
import json
import io
from pathlib import Path
import sys
import subprocess
import struct
import tempfile
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from gallery_image_assets import (
    MANIFEST, PROCESSOR, RECIPES, RENDERER, apply_prepared, filter_gallery_outputs,
    prepared_image, published_gallery_images, validate_record,
)
from gallery_image_inventory import INPUTS, inventory_inputs, source_info
import prepare_gallery_images
from prepare_gallery_images import prepare_recipe
from test_gallery_images import must_reject


def synthetic_source(page, root, kind="png"):
    encoded = page.evaluate("""(kind) => {
      const canvas = document.createElement('canvas');
      canvas.width = 800;
      canvas.height = 1120;
      const ctx = canvas.getContext('2d');
      const field = ctx.createImageData(800, 1120);
      for (let y = 0; y < 1120; y++) for (let x = 0; x < 800; x++) {
        const pixel = (y * 800 + x) * 4;
        field.data[pixel] = x % 256;
        field.data[pixel + 1] = y % 256;
        field.data[pixel + 2] = (x + y) % 256;
        field.data[pixel + 3] = 255;
      }
      ctx.putImageData(field, 0, 0);
      for (const [x, y, color] of [[0, 0, '#f00'], [650, 0, '#0f0'],
          [650, 970, '#00f'], [0, 970, '#ff0']]) {
        ctx.fillStyle = color;
        ctx.fillRect(x, y, 150, 150);
      }
      for (let x = 200; x < 600; x++) {
        ctx.fillStyle = x % 4 < 2 ? '#000' : '#fff';
        ctx.fillRect(x, 500, 1, 100);
      }
      return canvas.toDataURL(kind === 'png' ? 'image/png' : 'image/jpeg', .99).split(',')[1];
    }""", kind)
    source = f"verification/specimens/fixture.{kind}"
    path = root / source
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(encoded))
    return source


def fixture_recipe(root, source):
    return {
        "id": "browser-fixture", "source": source, "sourceSha256": source_info(root, source)["sha256"],
        "sourceDimensions": [800, 1120], "corners": [[0, 0], [800, 0], [800, 1120], [0, 1120]],
        "aspectRatio": [5, 7], "mediaKind": "photo",
        "review": {"status": "accepted", "note": "Synthetic browser regression fixture"},
        "targets": [{"itemId": "fixture-item", "scope": "exact-printing"}],
    }


def pixel_samples(page, root, record):
    encoded = base64.b64encode((root / record["images"][-1]["path"]).read_bytes()).decode("ascii")
    return page.evaluate("""async (encoded) => {
      const image = new Image();
      image.src = 'data:image/webp;base64,' + encoded;
      await image.decode();
      const canvas = document.createElement('canvas');
      canvas.width = image.width;
      canvas.height = image.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(image, 0, 0);
      const pixel = (x, y) => [...ctx.getImageData(x, y, 1, 1).data].slice(0, 3);
      const colors = new Set();
      for (let y = 200; y < 450; y += 3) for (let x = 160; x < 640; x += 3) {
        colors.add(pixel(x, y).join(','));
      }
      return {corner: pixel(40, 40), stripe1: pixel(300, 550), stripe2: pixel(302, 550),
        colors: colors.size};
    }""", encoded)


def check_prepared_binding(root, recipe, record):
    (root / RECIPES).write_text(json.dumps({"schemaVersion": 1, "recipes": [recipe]}), newline="\n")
    (root / MANIFEST).write_text(json.dumps({"schemaVersion": 1, "entries": {recipe["id"]: record}}), newline="\n")
    for relative in INPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", newline="\n")
    inventory = {"meta": {"inputs": inventory_inputs(root)},
                 "sources": {recipe["source"]: source_info(root, recipe["source"])},
                 "items": [{"itemId": "fixture-item", "candidates": [
                     {"source": recipe["source"], "scope": "exact-printing"}]}]}
    cards = [{"id": "fixture-item"}]
    apply_prepared(cards, inventory, root)
    assert cards[0]["imageSizes"] == record["images"]
    assert cards[0]["imageSource"] == recipe["source"]
    assert inventory["items"][0]["status"] == "accepted"
    (root / "verification/gallery_image_inventory.json").write_text(json.dumps(inventory), newline="\n")
    assert published_gallery_images(root) == {output["path"] for output in record["images"]}
    assert filter_gallery_outputs(["index.html", "images/gallery/orphan.webp"], root) == ["index.html"]
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in root.rglob("*") if path.is_file()}
    with patch.object(prepare_gallery_images, "ROOT", root), patch.object(
        sys, "argv", ["prepare_gallery_images.py", "--check"]
    ), redirect_stdout(io.StringIO()):
        assert prepare_gallery_images.main() == 0
    assert before == {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in root.rglob("*") if path.is_file()}
    changed_recipe = copy.deepcopy(recipe)
    changed_recipe["corners"][0][0] = 1
    must_reject(lambda: validate_record(changed_recipe, record, root))
    output = root / record["images"][0]["path"]
    original = output.read_bytes()
    output.write_bytes(original[:-1])
    must_reject(lambda: validate_record(recipe, record, root))
    output.write_bytes(original)


def check_gallery_preparation(browser):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for relative in (RENDERER, PROCESSOR, "requirements.txt"):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / relative).read_bytes())
        page = browser.new_page()
        engine = {"playwright": version("playwright"), "chromium": browser.version}
        for kind in ("png", "jpg"):
            source = synthetic_source(page, root, kind)
            recipe = fixture_recipe(root, source)
            original = (root / source).read_bytes()
            record = prepare_recipe(recipe, page, engine, root)
            validate_record(recipe, record, root)
            assert (root / source).read_bytes() == original
            samples = pixel_samples(page, root, record)
            assert samples["corner"][0] > 220 and samples["corner"][1] < 30
            assert abs(samples["stripe1"][0] - samples["stripe2"][0]) > 150
            assert samples["colors"] > 216
            check_prepared_binding(root, recipe, record)
        check_responsive_gallery(browser, root, recipe, record)
        check_prepare_command(root, recipe)
        check_exif_orientation(page, root, recipe, engine)
        rotated = copy.deepcopy(recipe)
        rotated["corners"] = [[800, 0], [800, 1120], [0, 1120], [0, 0]]
        rotated["aspectRatio"] = [7, 5]
        record = prepare_recipe(rotated, page, engine, root)
        assert record["dimensions"] == [1120, 800]
        samples = pixel_samples(page, root, record)
        assert samples["corner"][1] > 220 and samples["corner"][0] < 30
        perspective = copy.deepcopy(recipe)
        perspective["corners"] = [[30, 20], [770, 60], [740, 1050], [60, 1090]]
        record = prepare_recipe(perspective, page, engine, root)
        validate_record(perspective, record, root)
        assert record["dimensions"][0] >= 600
        small = copy.deepcopy(recipe)
        small["corners"] = [[0, 0], [300, 0], [300, 420], [0, 420]]
        record = prepare_recipe(small, page, engine, root)
        assert record["quality"] == "below-minimum" and record["images"] == []
        page.close()
    print("Gallery preparation browser checks passed for PNG/JPEG detail, geometry and integrity.")


def check_exif_orientation(page, root, recipe, engine):
    source = (root / recipe["source"]).read_bytes()
    tiff = b"II" + struct.pack("<HIH", 42, 8, 1)
    tiff += struct.pack("<HHIHHI", 274, 3, 1, 6, 0, 0)
    exif = b"Exif\0\0" + tiff
    encoded = source[:2] + b"\xff\xe1" + struct.pack(">H", len(exif) + 2) + exif + source[2:]
    path = root / "verification/specimens/oriented.jpg"
    path.write_bytes(encoded)
    oriented = fixture_recipe(root, "verification/specimens/oriented.jpg")
    oriented.update(sourceDimensions=[1120, 800], aspectRatio=[7, 5],
                    corners=[[0, 0], [1120, 0], [1120, 800], [0, 800]])
    record = prepare_recipe(oriented, page, engine, root)
    samples = pixel_samples(page, root, record)
    assert samples["corner"][0] > 220 and samples["corner"][1] > 220


def check_prepare_command(root, recipe):
    script = (
        "from pathlib import Path; import sys; sys.path.insert(0, sys.argv[1]); "
        "import prepare_gallery_images as p; p.ROOT = Path(sys.argv[2]); "
        "sys.argv = ['prepare_gallery_images.py', '--prepare', sys.argv[3]]; raise SystemExit(p.main())"
    )
    command = [sys.executable, "-c", script, str(ROOT / "verification"), str(root), recipe["id"]]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in root.rglob("*") if path.is_file()}
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert before == {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in root.rglob("*") if path.is_file()}


def check_responsive_gallery(browser, root, recipe, record):
    for relative in ("site/app.css", "site/gallery.css", "site/gallery.js"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    card = {
        "id": "fixture-item", "name": "Synthetic card", "set": "Fixture", "setCode": "FIX",
        "number": "1", "language": "English", "finish": "holo", "markings": [], "sources": [],
        "kind": "verified-printing", "status": "confirmed", "artworkNumber": 1,
    }
    card.update(prepared_image(recipe, record, recipe["targets"][0]))
    template = (ROOT / "site/gallery.html").read_text(encoding="utf-8")
    data = '<script id="gallery-data" type="application/json">' + json.dumps([card]) + "</script>"
    (root / "gallery.html").write_text(template.replace("<!-- GALLERY_DATA -->", data), encoding="utf-8", newline="\n")
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    page.goto((root / "gallery.html").as_uri())
    thumbnail = page.locator(".gallery-card img")
    assert thumbnail.get_attribute("srcset")
    assert thumbnail.get_attribute("width") == str(record["dimensions"][0])
    page.locator(".gallery-card").click()
    page.wait_for_function("document.querySelector('#card-picture img').complete")
    assert page.locator("#card-picture img").evaluate("(i) => i.currentSrc").endswith(record["images"][-1]["path"])
    assert page.get_by_role("link", name="Retained exact-printing image").get_attribute("href") == recipe["source"]
    page.keyboard.press("Escape")
    page.evaluate("() => { cards[0].imageScope = 'representative'; render(); }")
    page.locator(".gallery-card").click()
    assert page.get_by_text("Representative card image", exact=True).is_visible()
    assert page.get_by_role("link", name="Retained representative image").get_attribute("href") == recipe["source"]
    page.close()


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        check_gallery_preparation(browser)
        browser.close()

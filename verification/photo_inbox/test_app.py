"""Acceptance checks for the private photo inbox (#626): JPEG and DNG, restart, the German mobile page
and the derived archive copy.

Needs the inbox and browser requirements:
    pip install -r requirements.txt -r verification/photo_inbox/requirements.txt
    python verification/photo_inbox/test_app.py
"""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import struct
import subprocess
from tempfile import TemporaryDirectory
import threading

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright
from waitress.server import create_server

from app import create_app
from derive import carries_location, derive


def jpeg(colour=(200, 40, 40), size=(64, 48), gps=False):
    exif = Image.Exif()
    if gps:  # synthetic coordinates: the inbox keeps the raw bytes, GPS included, private
        exif.get_ifd(0x8825).update({1: "N", 2: (10.0, 20.0, 30.0), 3: "E", 4: (10.0, 20.0, 30.0)})
    out = BytesIO()
    Image.new("RGB", size, colour).save(out, "JPEG", exif=exif)
    return out.getvalue()


def dng(order=b"II", tag=50706):
    """The smallest TIFF whose first IFD holds one tag; 50706 (DNGVersion) makes it a DNG."""
    end = "<" if order == b"II" else ">"
    entry = struct.pack(end + "HHI", tag, 1, 4) + bytes([1, 4, 0, 0])
    return order + struct.pack(end + "HI", 42, 8) + struct.pack(end + "H", 1) + entry + bytes(68)


def post(client, body, **headers):
    sent = {"Content-Type": "application/octet-stream", "X-Snoredex-Owner": "yes"}
    sent.update({key.replace("_", "-"): value for key, value in headers.items()})
    return client.post("/uploads", data=body, headers={k: v for k, v in sent.items() if v is not None})


def jobs(root):
    return sorted(path.name for path in root.iterdir())


def api_checks(root):
    app = create_app(root)
    client = app.test_client()
    photo = jpeg(gps=True)
    digest = sha256(photo).hexdigest()

    first = post(client, photo, X_Snoredex_Specimen="spec-0774")
    assert first.status_code == 201 and first.json == {"id": digest, "status": "received", "existing": False}
    stored = root / digest
    assert (stored / "photo.jpg").read_bytes() == photo, "raw bytes kept unchanged"
    with Image.open(stored / "photo.jpg") as kept:
        assert kept.getexif().get_ifd(0x8825), "GPS stays in the private original"
    receipt = json.loads((stored / "job.json").read_text(encoding="utf-8"))
    assert receipt["specimenHint"] == "SPEC-0774" and receipt["ownPhoto"] is True and receipt["sha256"] == digest
    assert b"\r\n" not in (stored / "job.json").read_bytes()

    repeat = post(client, photo, X_Snoredex_Specimen="SPEC-0774")
    assert repeat.status_code == 200 and repeat.json["existing"] is True, "double tap is the same job"
    assert post(client, photo, X_Snoredex_Note="andere%20Karte").status_code == 409, "conflicting details"

    raw = dng(b"MM")
    taken = post(client, raw, X_Snoredex_Note="Relaxo DNG")
    assert taken.status_code == 201 and (root / taken.json["id"] / "photo.dng").read_bytes() == raw, "a DNG is kept"
    assert json.loads((root / taken.json["id"] / "job.json").read_text(encoding="utf-8"))["file"] == "photo.dng"
    assert post(client, dng(b"II"), X_Snoredex_Note="x").status_code == 201, "little-endian DNG"
    kept = jobs(root)

    tiff = BytesIO()
    Image.new("RGB", (8, 8)).save(tiff, "TIFF")
    refused = [
        (post(client, tiff.getvalue(), X_Snoredex_Note="x"), 400),
        (post(client, dng(tag=305), X_Snoredex_Note="x"), 400),
        (post(client, dng()[:12], X_Snoredex_Note="x"), 400),
        (post(client, jpeg((1, 2, 3)), Content_Type="image/jpeg", X_Snoredex_Note="x"), 415),
        (post(client, jpeg((1, 2, 3)), X_Snoredex_Owner=None, X_Snoredex_Note="x"), 400),
        (post(client, jpeg((1, 2, 3))), 400),
        (post(client, jpeg((1, 2, 3)), X_Snoredex_Specimen="SPEC-12"), 400),
        (post(client, jpeg((1, 2, 3)), X_Snoredex_Note="x" * 241), 400),
        (post(client, jpeg((1, 2, 3)), X_Snoredex_Note="%FF"), 400),
        (post(client, b"not a jpeg", X_Snoredex_Note="x"), 400),
        (post(client, jpeg((1, 2, 3))[:300], X_Snoredex_Note="x"), 400),
    ]
    for response, expected in refused:
        assert response.status_code == expected and response.json["error"], (expected, response.status_code)
    assert jobs(root) == kept, "a refused upload leaves nothing behind"
    app.config["MAX_CONTENT_LENGTH"] = 1024
    too_big = post(client, bytes(2048), X_Snoredex_Note="x")
    assert too_big.status_code == 413 and "200 MB" in too_big.json["error"]
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

    big = BytesIO()
    Image.new("L", (7800, 7800)).save(big, "JPEG")
    assert post(client, big.getvalue(), X_Snoredex_Note="x").status_code == 400, "over 60 megapixels"

    page = client.get("/")
    assert page.status_code == 200 and page.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]

    restarted = create_app(root).test_client()
    again = post(restarted, photo, X_Snoredex_Specimen="SPEC-0774")
    assert again.status_code == 200 and again.json["existing"] is True, "the job survives a restart"
    return photo, digest


def refuses_checkout():
    with TemporaryDirectory() as temp:
        subprocess.run(["git", "init", "-q", temp], check=True)
        try:
            create_app(Path(temp) / "inbox")
        except ValueError:
            return
    raise AssertionError("an inbox inside a Git checkout must be refused")


def browser_checks(root, photo_path, digest, dng_path):
    server = create_server(create_app(root), host="127.0.0.1", port=0)
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{server.effective_port}/"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 375, "height": 812})
            problems = []  # script errors and CSP refusals
            page.on("pageerror", lambda error: problems.append(str(error)))
            page.on("console", lambda message: message.type == "error" and problems.append(message.text))
            page.goto(url)
            page.set_input_files("#photo", str(photo_path))
            page.check("#owner")
            page.click("button")
            assert "SPEC-Nummer oder eine kurze Notiz" in page.text_content("#status"), "hint checked before upload"

            page.fill("#specimen", "SPEC-0774")
            page.click("button")
            page.wait_for_selector("#status.ok")
            assert digest in page.text_content("#status") and "lag schon" in page.text_content("#status")

            page.set_input_files("#photo", str(dng_path))
            page.fill("#specimen", "")
            page.fill("#note", "Relaxo, im Browser als DNG")
            page.click("button")
            page.wait_for_selector("#status.ok >> text=Foto empfangen")
            assert sha256(dng_path.read_bytes()).hexdigest() in page.text_content("#status")
            assert page.evaluate("document.documentElement.scrollWidth") <= 375, "no sideways scroll on a phone"
            assert not problems, problems
            browser.close()
    finally:
        server.close()


def camera_jpeg():
    """A phone-like JPEG: GPS, maker and XMP data, an ICC profile, orientation 6 and a second frame."""
    exif = Image.Exif()
    exif.update({271: "TestMaker", 274: 6})
    exif.get_ifd(0x8825).update({1: "N", 2: (10.0, 20.0, 30.0), 3: "E", 4: (10.0, 20.0, 30.0)})
    out, extra = BytesIO(), BytesIO()
    Image.new("RGB", (64, 48), (90, 140, 60)).save(out, "JPEG", exif=exif, icc_profile=b"test-icc",
                                                   xmp=b"<x:xmpmeta>GPSLatitude 10,20</x:xmpmeta>")
    Image.new("L", (8, 8), 128).save(extra, "JPEG")
    return out.getvalue() + extra.getvalue()


def dng_with_preview(preview, compression=7):
    """A DNG whose IFD0 stores the preview as one strip, as an iPhone ProRAW file does."""
    entries = [(254, 4, 1), (259, 3, compression), (273, 4, 74), (279, 4, len(preview))]
    ifd = struct.pack("<H", 5) + b"".join(struct.pack("<HHII", tag, kind, 1, value) for tag, kind, value in entries)
    ifd += struct.pack("<HHI", 50706, 1, 4) + bytes([1, 6, 0, 0]) + bytes(4)
    return b"II*\0" + struct.pack("<I", 8) + ifd + preview


def derive_checks(temp):
    source = camera_jpeg()
    copies = {}
    for name, body in (("photo.dng", dng_with_preview(source)), ("photo.jpg", source)):
        job = Path(temp) / name.replace(".", "-")
        job.mkdir()
        (job / name).write_bytes(body)
        copies[name] = derive(job)[0]
    copy = copies["photo.dng"]
    assert copies["photo.jpg"] == copy, "a DNG preview and the same JPEG derive the same copy"
    with Image.open(BytesIO(source)) as before, Image.open(BytesIO(copy)) as after:
        assert ImageChops.difference(before.convert("RGB"), after.convert("RGB")).getbbox() is None
        assert dict(after.getexif()) == {274: 6} and after.info["icc_profile"] == b"test-icc"
    assert not carries_location(copy) and b"TestMaker" not in copy and b"xmpmeta" not in copy
    assert copy.count(b"\xff\xd8") == 1, "the second frame is dropped"
    flat = Path(temp) / "flat"
    flat.mkdir()
    (flat / "photo.dng").write_bytes(dng_with_preview(source, compression=1))
    try:
        derive(flat)
    except ValueError:
        return
    raise AssertionError("a DNG without a JPEG preview must be refused")


def main():
    refuses_checkout()
    with TemporaryDirectory() as temp:
        derive_checks(temp)
    with TemporaryDirectory() as temp:
        root = Path(temp) / "inbox"
        photo, digest = api_checks(root)
        photo_path = Path(temp) / "upload.jpg"
        photo_path.write_bytes(photo)
        dng_path = Path(temp) / "browser.dng"
        dng_path.write_bytes(dng() + b"browser")
        browser_checks(root, photo_path, digest, dng_path)
    print("photo inbox: all checks passed")


if __name__ == "__main__":
    main()

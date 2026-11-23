"""Acceptance checks for the private photo inbox (#626): API, restart and the German mobile page.

Needs the inbox and browser requirements:
    pip install -r requirements.txt -r verification/photo_inbox/requirements.txt
    python verification/photo_inbox/test_app.py
"""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import threading

from PIL import Image
from playwright.sync_api import sync_playwright
from waitress.server import create_server

from app import MAX_UPLOAD, create_app

TOKEN = "inbox-test-code-0123456789"
WRONG = "wrong-code-0123456789"
AUTH = {"Authorization": "Bearer " + TOKEN}


def jpeg(colour=(200, 40, 40), size=(64, 48), gps=False):
    exif = Image.Exif()
    if gps:  # synthetic coordinates: the inbox keeps the raw bytes, GPS included, private
        exif.get_ifd(0x8825).update({1: "N", 2: (10.0, 20.0, 30.0), 3: "E", 4: (10.0, 20.0, 30.0)})
    out = BytesIO()
    Image.new("RGB", size, colour).save(out, "JPEG", exif=exif)
    return out.getvalue()


def post(client, body, **headers):
    sent = {"Content-Type": "application/octet-stream", "X-Snoredex-Owner": "yes", **AUTH}
    sent.update({key.replace("_", "-"): value for key, value in headers.items()})
    return client.post("/uploads", data=body, headers={k: v for k, v in sent.items() if v is not None})


def jobs(root):
    return sorted(path.name for path in root.iterdir())


def api_checks(root):
    client = create_app(root, TOKEN).test_client()
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

    refused = [
        (post(client, jpeg((1, 2, 3)), Authorization="Bearer " + WRONG, X_Snoredex_Note="x"), 401),
        (post(client, jpeg((1, 2, 3)), Authorization=None, X_Snoredex_Note="x"), 401),
        (post(client, jpeg((1, 2, 3)), Content_Type="image/jpeg", X_Snoredex_Note="x"), 415),
        (post(client, jpeg((1, 2, 3)), X_Snoredex_Owner=None, X_Snoredex_Note="x"), 400),
        (post(client, jpeg((1, 2, 3))), 400),
        (post(client, jpeg((1, 2, 3)), X_Snoredex_Specimen="SPEC-12"), 400),
        (post(client, jpeg((1, 2, 3)), X_Snoredex_Note="x" * 241), 400),
        (post(client, jpeg((1, 2, 3)), X_Snoredex_Note="%FF"), 400),
        (post(client, b"not a jpeg", X_Snoredex_Note="x"), 400),
        (post(client, jpeg((1, 2, 3))[:300], X_Snoredex_Note="x"), 400),
        (post(client, b"\0" * (MAX_UPLOAD + 1), X_Snoredex_Note="x"), 413),
    ]
    for response, expected in refused:
        assert response.status_code == expected and response.json["error"], (expected, response.status_code)
    assert jobs(root) == [digest], "a refused upload leaves nothing behind"

    big = BytesIO()
    Image.new("L", (7800, 7800)).save(big, "JPEG")
    assert post(client, big.getvalue(), X_Snoredex_Note="x").status_code == 400, "over 60 megapixels"

    page = client.get("/")
    assert page.status_code == 200 and page.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]

    restarted = create_app(root, TOKEN).test_client()
    again = post(restarted, photo, X_Snoredex_Specimen="SPEC-0774")
    assert again.status_code == 200 and again.json["existing"] is True, "the job survives a restart"
    return photo, digest


def refuses_checkout():
    with TemporaryDirectory() as temp:
        subprocess.run(["git", "init", "-q", temp], check=True)
        try:
            create_app(Path(temp) / "inbox", TOKEN)
        except ValueError:
            return
    raise AssertionError("an inbox inside a Git checkout must be refused")


def browser_checks(root, photo_path, digest):
    server = create_server(create_app(root, TOKEN), host="127.0.0.1", port=0)
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{server.effective_port}/"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 375, "height": 812})
            problems = []  # script errors and CSP refusals; a refused upload's own 401 line is expected
            page.on("pageerror", lambda error: problems.append(str(error)))
            page.on("console", lambda message: message.type == "error"
                    and "Failed to load resource" not in message.text and problems.append(message.text))
            page.goto(url)
            page.set_input_files("#photo", str(photo_path))
            page.check("#owner")
            page.fill("#code", WRONG)
            page.click("button")
            assert "SPEC-Nummer oder eine kurze Notiz" in page.text_content("#status"), "hint checked before upload"

            page.fill("#specimen", "SPEC-0774")
            page.click("button")
            page.wait_for_selector("#status.error >> text=Upload-Code stimmt nicht")

            page.fill("#code", TOKEN)
            page.click("button")
            page.wait_for_selector("#status.ok")
            assert digest in page.text_content("#status") and "lag schon" in page.text_content("#status")
            assert TOKEN not in page.url and "?" not in page.url, "the code stays out of the URL"

            page.reload()
            assert page.input_value("#code") == TOKEN, "the code is remembered on this device"
            assert page.evaluate("document.documentElement.scrollWidth") <= 375, "no sideways scroll on a phone"
            assert not problems, problems
            browser.close()
    finally:
        server.close()


def main():
    refuses_checkout()
    with TemporaryDirectory() as temp:
        root = Path(temp) / "inbox"
        photo, digest = api_checks(root)
        photo_path = Path(temp) / "upload.jpg"
        photo_path.write_bytes(photo)
        browser_checks(root, photo_path, digest)
    print("photo inbox: all checks passed")


if __name__ == "__main__":
    main()

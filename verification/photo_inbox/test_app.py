"""Acceptance checks for the private photo inbox (#626, #639, #641): bulk upload of JPEG and DNG, the
dashboard that describes each job, the trash, the overview of every printing, restart, the German
mobile page and the derived archive copy.

Needs the inbox and browser requirements:
    pip install -r requirements.txt -r verification/photo_inbox/requirements.txt
    python verification/photo_inbox/test_app.py
"""

from datetime import datetime, timedelta, timezone
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
from overview import STAGES, unique_labels
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


def post(client, body, content_type="application/octet-stream"):
    return client.post("/uploads", data=body, headers={"Content-Type": content_type})


def jobs(root):
    return sorted(path.name for path in root.iterdir() if path.name != ".trash")


def upload_checks(root, app, client):
    """Photos arrive without details: each is its own job, all of them the owner's own (#639)."""
    photo = jpeg(gps=True)
    digest = sha256(photo).hexdigest()
    first = post(client, photo)
    assert first.status_code == 201 and first.json == {"id": digest, "status": "received", "existing": False}
    stored = root / digest
    assert (stored / "photo.jpg").read_bytes() == photo, "raw bytes kept unchanged"
    with Image.open(stored / "photo.jpg") as kept:
        assert kept.getexif().get_ifd(0x8825), "GPS stays in the private original"
    receipt = json.loads((stored / "job.json").read_text(encoding="utf-8"))
    assert receipt["ownPhoto"] is True and receipt["sha256"] == digest and receipt["receivedAt"]
    assert receipt["specimenHint"] is None and receipt["note"] == ""
    assert b"\r\n" not in (stored / "job.json").read_bytes()
    assert post(client, photo).json["existing"] is True, "double tap is the same job"

    raw = dng(b"MM")
    taken = post(client, raw)
    assert taken.status_code == 201 and (root / taken.json["id"] / "photo.dng").read_bytes() == raw, "a DNG is kept"
    assert post(client, dng(b"II")).status_code == 201, "little-endian DNG"
    kept = jobs(root)

    tiff = BytesIO()
    Image.new("RGB", (8, 8)).save(tiff, "TIFF")
    big = BytesIO()
    Image.new("L", (7800, 7800)).save(big, "JPEG")
    refused = [(tiff.getvalue(), 400), (dng(tag=305), 400), (dng()[:12], 400), (b"not a photo", 400),
               (jpeg((1, 2, 3))[:300], 400), (big.getvalue(), 400)]
    for body, expected in refused:
        response = post(client, body)
        assert response.status_code == expected and response.json["error"], (expected, response.status_code)
    assert post(client, jpeg((1, 2, 3)), "image/jpeg").status_code == 415
    assert jobs(root) == kept, "a refused upload leaves nothing behind"
    app.config["MAX_CONTENT_LENGTH"] = 1024
    too_big = post(client, bytes(2048))
    assert too_big.status_code == 413 and "200 MB" in too_big.json["error"]
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024
    return photo, digest


def dashboard_checks(root, client, digest):
    """The list, the previews and the description, saved like the single workflow saved it."""
    listed = client.get("/jobs").json["jobs"]
    assert {job["id"] for job in listed} == set(jobs(root))
    assert [job["receivedAt"] for job in listed] == sorted((job["receivedAt"] for job in listed), reverse=True)
    assert all(not job["described"] for job in listed)

    with_preview = post(client, dng_with_preview(camera_jpeg())).json["id"]
    for job_id in (digest, with_preview):
        picture = client.get(f"/jobs/{job_id}/preview?size=400")
        assert picture.status_code == 200 and picture.mimetype == "image/jpeg"
        with Image.open(BytesIO(picture.data)) as small:
            assert max(small.size) <= 400 and not small.getexif(), "small, upright, no Exif or GPS"
            assert not carries_location(picture.data)
    with Image.open(BytesIO(client.get(f"/jobs/{with_preview}/preview?size=1600").data)) as large:
        assert large.size == (48, 64), "the DNG's preview, turned upright by its orientation"
    plain_dng = next(job["id"] for job in listed if job["file"] == "photo.dng")
    assert client.get(f"/jobs/{plain_dng}/preview?size=400").status_code == 404, "no embedded preview"
    assert client.get(f"/jobs/{digest}/preview?size=999").status_code == 404
    assert client.get("/jobs/../../etc/preview?size=400").status_code == 404

    for bad in ({}, {"specimen": "SPEC-12"}, {"note": "x" * 241}, {"itemId": ITEMS["none"]}):
        assert client.post(f"/jobs/{digest}", json=bad).status_code == 400, bad
    assert client.post(f"/jobs/{'0' * 64}", json={"note": "x"}).status_code == 404
    saved = client.post(f"/jobs/{digest}", json={"specimen": "spec-0774", "note": " Relaxo "})
    assert saved.status_code == 200 and saved.json["described"] is True
    record = json.loads((root / digest / "job.json").read_text(encoding="utf-8"))
    assert record["specimenHint"] == "SPEC-0774" and record["note"] == "Relaxo" and record["describedAt"]
    fixed = client.post(f"/jobs/{digest}", json={"note": "Relaxo, korrigiert"}).json
    assert fixed["specimenHint"] is None and fixed["note"] == "Relaxo, korrigiert", "a description can be corrected"
    assert (root / digest / "photo.jpg").read_bytes() == jpeg(gps=True), "describing never touches the photo"
    assert post(client, jpeg(gps=True)).json["existing"] is True, "a described photo uploads as the same job"


def api_checks(root):
    app = create_app(root)
    client = app.test_client()
    photo, digest = upload_checks(root, app, client)
    dashboard_checks(root, client, digest)
    page = client.get("/")
    assert page.status_code == 200 and page.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]
    restarted = create_app(root).test_client()
    again = [job for job in restarted.get("/jobs").json["jobs"] if job["id"] == digest]
    assert again and again[0]["note"] == "Relaxo, korrigiert", "jobs and descriptions survive a restart"
    refused = restarted.delete(f"/jobs/{digest}")
    assert refused.status_code == 409 and "Katalog" in refused.json["error"], "no deleting blind"
    assert restarted.get("/overview").status_code == 404
    return photo, digest


ITEMS = {stage: f"item-{index:08d}-0000-0000-0000-000000000000" for index, stage in enumerate(STAGES)}
BASE = "https://example.test/snoredex/"
OWNER_STAGES = ("filed", "online", "ready", "posted")


def item(stage):
    language = "LOCALIZATION:WEST:en" if stage == "none" else "LOCALIZATION:WEST:de"
    return {"itemId": ITEMS[stage], "active": True, "localSetCode": "JU", "collectorNumber": str(STAGES.index(stage) + 1),
            "collectorNumberDenominator": "64", "localizationId": language, "finish": "holo",
            "edition": "1st Edition", "cardName": "Snorlax", "localCardName": "Relaxo", "imageAssetId": f"asset-{stage}"}


def catalogue_repo(folder, filed_photo):
    """A checkout of main with one printing at every stage; `filed` holds the inbox photo `filed_photo`."""
    assets = [{"assetId": f"asset-{stage}", "path": f"verification/specimens/SPEC-0{900 + index}.jpg"}
              for index, stage in enumerate(STAGES)]
    specimens = [{"specimenId": f"SPEC-0{900 + STAGES.index(stage)}", "photographedBy": "collection owner",
                  "photographSha256": filed_photo if stage == "filed" else f"sha256:{stage}"} for stage in OWNER_STAGES]
    # the printings without an own photo show a third party's photo
    specimens += [{"specimenId": f"SPEC-0{900 + index}", "photographedBy": "third party", "photographSha256": None}
                  for index in range(2)]
    files = {
        "collector_catalogue.json": {
            "meta": {"assetBaseUrl": BASE, "dataAsOf": "2026-11-24"},
            "items": [item(stage) for stage in STAGES] + [dict(item("none"), itemId="item-retired", active=False)],
            "localizations": [{"localizationId": "LOCALIZATION:WEST:de", "displayName": "German"},
                              {"localizationId": "LOCALIZATION:WEST:en", "displayName": "English"}],
            "assets": assets},
        "verification/specimens.json": {"specimens": specimens},
        "data/social.json": [{"itemId": ITEMS["ready"], "specimenId": "SPEC-0904", "instagramPosts": [],
                              "shortAlias": "sdready"},
                             {"itemId": ITEMS["posted"], "specimenId": "SPEC-0905", "shortAlias": "sdposted",
                              "instagramPosts": ["https://www.instagram.com/p/test/"]}],
        "data/images.json": {"galleryImages": []},
    }
    for name, data in files.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(json.dumps(data), encoding="utf-8", newline="\n")
    return folder


def published(_url):
    """The site as Pages serves it: the online stages show their own photo, `filed` still an older one."""
    return {"items": [{"itemId": ITEMS[stage], "imageAssetId": "asset-old" if stage == "filed" else f"asset-{stage}"}
                      for stage in STAGES]}


def unreachable(_url):
    raise OSError("offline")


def mark_filed(repo, folder, specimen_id):
    """Intake files this job: the checkout now names its archive copy as a specimen's photograph."""
    path = repo / "verification/specimens.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    photo = "sha256:" + sha256(derive(folder)[0]).hexdigest()
    data["specimens"].append({"specimenId": specimen_id, "photographedBy": "collection owner", "photographSha256": photo})
    path.write_text(json.dumps(data), encoding="utf-8", newline="\n")


def age(record):
    old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(timespec="seconds")
    aged = dict(json.loads(record.read_text(encoding="utf-8")), deletedAt=old)
    record.write_text(json.dumps(aged), encoding="utf-8", newline="\n")


def guard_checks(root, repo):
    """A filed job is never lost, however it is deleted, and the checkout is read as it is now."""
    client = create_app(root, repo, published).test_client()
    late = post(client, jpeg((11, 22, 33))).json["id"]
    mark_filed(repo, root / late, "SPEC-0950")  # no overview call in between
    assert client.delete(f"/jobs/{late}").status_code == 409, "a job filed since the last overview stays"
    trashed = post(client, jpeg((44, 55, 66))).json["id"]
    assert client.delete(f"/jobs/{trashed}").status_code == 200
    mark_filed(repo, root / ".trash" / trashed, "SPEC-0951")  # filed after it was trashed
    assert client.delete(f"/trash/{trashed}").status_code == 409, "no deleting a filed job for good"
    age(root / ".trash" / trashed / "job.json")
    listed = client.get("/trash").json["jobs"]
    assert [(job["id"], job["filedAs"]) for job in listed] == [(trashed, "SPEC-0951")], "the sweep keeps it"
    assert client.post(f"/trash/{trashed}/restore").status_code == 200

    blind = post(client, jpeg((77, 88, 99))).json["id"]
    client.delete(f"/jobs/{blind}")
    age(root / ".trash" / blind / "job.json")
    create_app(root)  # a restart without catalogue cannot tell, so it keeps the trash
    assert (root / ".trash" / blind).is_dir()
    create_app(root, repo, published).test_client().get("/trash")
    assert not (root / ".trash" / blind).exists()

    path = repo / "collector_catalogue.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["items"].append(dict(item("none"), itemId="item-99999999-0000-0000-0000-000000000000"))
    path.write_text(json.dumps(doc), encoding="utf-8", newline="\n")
    added = client.post(f"/jobs/{late}", json={"itemId": "item-99999999-0000-0000-0000-000000000000"})
    assert added.status_code == 200, "a printing added to the checkout is offered at once"

    broken = post(client, dng_with_preview(b"\xff\xd8\xff\xe0\x00\x10garbage")).json["id"]
    assert client.get("/jobs").status_code == 200, "a job intake cannot derive does not break the list"
    assert not (root / broken / "archive.sha256").exists(), "a failed derivation is tried again later"


def label_checks():
    """The picker maps a label back to its printing, so no two printings may share one."""
    languages = {"LOCALIZATION:WEST:de": "German", "LOCALIZATION:WEST:en": "English"}
    base = item("none")
    twins = {"item-a": dict(base, foilPattern="poke-ball"), "item-b": dict(base, foilPattern="master-ball"),
             "item-c": dict(base, cardSize="jumbo"),
             "item-d": dict(base, markings=[{"kind": "staff", "text": "Staff", "role": "distribution-promo"}]),
             "item-e": dict(base), "item-f": dict(base)}
    labels = unique_labels(twins, languages)
    assert len(set(labels.values())) == len(twins), labels
    assert "poke-ball" in labels["item-a"] and "jumbo" in labels["item-c"] and "Staff" in labels["item-d"]
    assert labels["item-e"].endswith("item-e") and labels["item-f"].endswith("item-f"), "true twins carry their id"


def overview_checks(root, temp):
    """Every printing at the furthest stage it reached; jobs land on their printing."""
    label_checks()
    filed = post(create_app(root).test_client(), jpeg((30, 60, 90))).json["id"]
    copy = "sha256:" + sha256(derive(root / filed)[0]).hexdigest()
    repo = catalogue_repo(Path(temp) / "repo", copy)
    client = create_app(root, repo, published).test_client()
    assigned = post(client, jpeg((60, 30, 90))).json["id"]
    assert client.post(f"/jobs/{assigned}", json={"itemId": "item-unknown"}).status_code == 400
    assert client.post(f"/jobs/{assigned}", json={"itemId": ITEMS["assigned"]}).json["described"] is True
    jobs = {job["id"]: job for job in client.get("/jobs").json["jobs"]}
    assert jobs[filed]["filedAs"] == "SPEC-0902" and jobs[assigned]["filedAs"] is None
    view = client.get("/overview").json
    rows = {row["itemId"]: row for row in view["rows"]}
    assert set(rows) == set(ITEMS.values()), "retired printings stay out"
    assert {stage: rows[ITEMS[stage]]["stage"] for stage in STAGES} == {stage: stage for stage in STAGES}
    assert rows[ITEMS["filed"]]["jobs"] == [filed] and rows[ITEMS["assigned"]]["jobs"] == [assigned]
    assert rows[ITEMS["filed"]]["specimen"] == "SPEC-0902" and rows[ITEMS["none"]]["specimen"] is None
    assert rows[ITEMS["ready"]]["shortUrl"] == "https://go.m4s.eu/sdready"
    assert rows[ITEMS["posted"]]["posts"] == ["https://www.instagram.com/p/test/"]
    assert rows[ITEMS["none"]]["label"] == "JU 1/64 · English · holo · 1st Edition · Relaxo"
    assert rows[ITEMS["filed"]]["card"] == BASE + f"cards/{ITEMS['filed']}/" and view["siteError"] is None
    assert "img-src 'self' https://example.test;" in client.get("/").headers["Content-Security-Policy"]
    offline = create_app(root, repo, unreachable).test_client().get("/overview").json
    stages = {row["itemId"]: row["stage"] for row in offline["rows"]}
    assert stages[ITEMS["online"]] == "filed" and "nicht lesbar" in offline["siteError"], "an unread site is not online"
    return repo, filed


def trash_checks(root, client, digest, filed):
    """Only an unfiled job goes to the trash; it can come back, or go for good."""
    refused = client.delete(f"/jobs/{filed}")
    assert refused.status_code == 409 and "SPEC-0902" in refused.json["error"], refused.json
    assert client.delete(f"/jobs/{digest}").json["status"] == "deleted"
    assert digest not in {job["id"] for job in client.get("/jobs").json["jobs"]} and not (root / digest).exists()
    trashed = client.get("/trash").json
    assert trashed["keepDays"] == 30 and [job["id"] for job in trashed["jobs"]] == [digest]
    assert trashed["jobs"][0]["deletedAt"]
    assert client.get(f"/trash/{digest}/preview?size=400").status_code == 200
    assert client.post(f"/trash/{digest}/restore").status_code == 200 and (root / digest / "photo.jpg").is_file()
    assert "deletedAt" not in json.loads((root / digest / "job.json").read_text(encoding="utf-8"))
    client.delete(f"/jobs/{digest}")
    assert post(client, jpeg(gps=True)).status_code == 201, "a deleted photo uploaded again is a new job"
    assert not (root / ".trash" / digest).exists() and client.get("/trash").json["jobs"] == []
    client.delete(f"/jobs/{digest}")
    assert client.delete(f"/trash/{digest}").json["status"] == "gone" and not (root / ".trash" / digest).exists()
    assert client.delete(f"/trash/{digest}").status_code == 404
    post(client, jpeg(gps=True))
    client.delete(f"/jobs/{digest}")
    age(root / ".trash" / digest / "job.json")
    assert client.get("/trash").json["jobs"] == [] and not (root / ".trash" / digest).exists(), "emptied after 30 days"
    post(client, jpeg(gps=True))


def refuses_checkout():
    with TemporaryDirectory() as temp:
        subprocess.run(["git", "init", "-q", temp], check=True)
        try:
            create_app(Path(temp) / "inbox")
        except ValueError:
            return
    raise AssertionError("an inbox inside a Git checkout must be refused")


def browser_checks(root, files, repo):
    """Bulk upload with one bad file, describe a job, the overview and the trash, on a phone-sized page."""
    server = create_server(create_app(root, repo, published), host="127.0.0.1", port=0)
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{server.effective_port}/"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 375, "height": 812})
            problems = []  # script errors and CSP refusals; the bad file's own 400 line is expected
            page.on("pageerror", lambda error: problems.append(str(error)))
            page.on("console", lambda message: message.type == "error"
                    and "Failed to load resource" not in message.text and problems.append(message.text))
            page.goto(url)
            page.set_input_files("#photos", [str(path) for path in files])
            assert page.locator("#chosen").text_content() == "4 Fotos gewählt."
            page.click("#upload button")
            # the page's CSP forbids eval, so wait with locators rather than wait_for_function
            page.locator("#transfers li.ok, #transfers li.error").nth(len(files) - 1).wait_for()
            lines = page.locator("#transfers li").all_text_contents()
            assert sum("neu im Eingang" in line for line in lines) == 2, lines
            assert sum("JPEG- oder DNG-Foto" in line for line in lines) == 1, lines
            assert any("schon vorhanden" in line for line in lines), lines

            new = sha256(files[1].read_bytes()).hexdigest()
            page.click("#tab-fotos")
            item = page.locator(f'li.job[data-job="{new}"]')
            item.wait_for()
            for _ in range(50):
                if item.locator("img").evaluate("image => image.complete && image.naturalWidth > 0"):
                    break
                page.wait_for_timeout(100)
            else:
                raise AssertionError("the preview of the new DNG did not load")
            assert item.locator(".state").text_content() == "ohne Angabe"
            item.locator("textarea").fill("Relaxo, Sammel-Upload")
            item.locator('input[name="item"]').fill("JU 1/64 · English · holo · 1st Edition · Relaxo")
            item.locator('button[type="submit"]').click()
            item.locator(".saved.ok").wait_for()
            assert item.locator(".state").text_content() == "beschrieben"
            page.click("#tab-uebersicht")
            none_row = page.locator(f'li.row[data-item="{ITEMS["none"]}"]')
            none_row.locator(f'a[href="#job-{new}"]').click()
            item.wait_for()
            assert page.url.endswith(f"#job-{new}") and item.is_visible(), "a row's photo link opens the photos tab"
            page.locator("#tab-uebersicht").click()
            assert none_row.locator(".badge").text_content() == "hochgeladen, zugeordnet"

            page.reload()
            assert page.locator("#panel-uebersicht").is_visible(), "a reload keeps the open tab"
            page.click("#tab-fotos")
            page.select_option("#job-view", "open")
            page.locator(f'li.job[data-job="{new}"]').wait_for(state="detached")
            page.select_option("#job-view", "all")
            page.locator(f'li.job[data-job="{new}"] textarea').wait_for()
            assert page.locator(f'li.job[data-job="{new}"] textarea').input_value() == "Relaxo, Sammel-Upload"
            assert page.locator(f'li.job[data-job="{new}"] input[name="item"]').input_value().startswith("JU 1/64")
            overview_page(page)
            trash_page(page, new)
            assert page.evaluate("document.documentElement.scrollWidth") <= 375, "no sideways scroll on a phone"
            tab_checks(page, url)
            assert not problems, problems
            browser.close()
    finally:
        server.close()


def tab_checks(page, url):
    """One tab bar: at the bottom within thumb reach on a phone, under the title on a wide screen."""
    page.goto("about:blank")  # a fresh load, not a jump within the page already open
    page.goto(url + "#papierkorb")
    assert page.locator("#panel-papierkorb").is_visible() and not page.locator("#panel-hochladen").is_visible()
    assert page.locator("#tab-papierkorb").get_attribute("aria-selected") == "true"
    assert page.evaluate("window.scrollY === 0 && document.activeElement === document.body"), "a tab link jumps nowhere"
    tabs = page.locator('[role="tab"]')
    for index in range(tabs.count()):
        box = tabs.nth(index).bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44, ("target size", index, box)
        assert box["y"] + box["height"] >= 812 - 1, "the phone tab bar sits at the bottom"
    page.locator("#tab-papierkorb").focus()
    page.keyboard.press("ArrowRight")
    assert page.evaluate("document.activeElement.id") == "tab-hochladen", "arrows wrap around"
    assert page.locator("#panel-hochladen").is_visible() and page.url.endswith("#hochladen")
    page.keyboard.press("End")
    assert page.evaluate("document.activeElement.id") == "tab-papierkorb"
    page.keyboard.press("Home")
    page.keyboard.press("ArrowLeft")
    assert page.locator("#tab-papierkorb").get_attribute("tabindex") == "0"
    assert [tabs.nth(index).get_attribute("tabindex") for index in range(4)] == ["-1"] * 4, "one tab stop"
    page.set_viewport_size({"width": 1280, "height": 800})
    page.click("#tab-uebersicht")
    assert page.locator("#tab-uebersicht").bounding_box()["y"] < 80, "the wide tab bar sits at the top"
    assert page.evaluate("document.documentElement.scrollWidth") <= 1280
    page.set_viewport_size({"width": 375, "height": 812})


def overview_page(page):
    """Views, stage filter, search, counts and statistics come from the same rows."""
    page.click("#tab-uebersicht")
    counts = page.locator("#stage-counts li").all_text_contents()
    assert counts == ["kein eigenes Foto: 0", "hochgeladen, zugeordnet: 2", "verarbeitet: 1", "online: 1",
                      "bereit für Instagram: 1", "gepostet: 1"], counts
    page.select_option("#view", "own")
    assert page.locator("#rows li").count() == 4
    page.select_option("#view", "missing")
    assert page.locator("#rows li").count() == 2
    page.select_option("#view", "all")
    page.select_option("#stage", "posted")
    assert page.locator("#rows li .badge").all_text_contents() == ["gepostet"]
    assert page.locator("#rows li a", has_text="Instagram 1").count() == 1
    page.select_option("#stage", "")
    page.fill("#search", "english")
    assert page.locator("#rows li").count() == 1
    page.fill("#search", "")
    page.click("#tab-statistik")
    stats = page.locator("#stats tr").all_text_contents()
    assert stats == ["SpracheDruckemit Owner-Fotoonlinegepostet", "German5431", "English1000"], stats
    page.select_option("#group-by", "set")
    assert page.locator("#stats tr").nth(1).text_content() == "JU6431"


def trash_page(page, job):
    """Delete after confirming, restore, delete again and purge for good; a filed job has no delete."""
    page.on("dialog", lambda dialog: dialog.accept())
    page.click("#tab-fotos")
    open_jobs = page.locator("#count-fotos").text_content()
    card = page.locator(f'#jobs li[data-job="{job}"]')
    card.locator(".delete").click()
    card.wait_for(state="detached")
    assert page.locator("#count-papierkorb").text_content() == "1" and open_jobs, "the tabs show what waits"
    page.click("#tab-papierkorb")
    trashed = page.locator(f'#trash li[data-job="{job}"]')
    assert "endgültig gelöscht am" in trashed.locator(".when").text_content()
    trashed.locator(".restore").click()
    card.wait_for(state="attached")
    assert page.locator("#count-papierkorb").is_hidden()
    page.click("#tab-fotos")
    card.locator(".delete").click()
    page.click("#tab-papierkorb")
    trashed.locator(".purge").click()
    trashed.wait_for(state="detached")
    assert page.locator("#trash-status").text_content() == "Der Papierkorb ist leer."
    page.click("#tab-fotos")
    filed = page.locator("#jobs li", has_text="übernommen als SPEC-0902")
    assert filed.count() == 1 and filed.locator(".delete").is_hidden(), "a filed job offers no delete"


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
        root = Path(temp) / "inbox"
        photo, digest = api_checks(root)
        repo, filed = overview_checks(root, temp)
        guard_checks(Path(temp) / "guard", catalogue_repo(Path(temp) / "guard-repo", "sha256:none"))
        trash_checks(root, create_app(root, repo, published).test_client(), digest, filed)
        names = ("again.jpg", "new.dng", "notes.txt", "new.jpg")
        bodies = (photo, dng_with_preview(jpeg((5, 6, 7), size=(48, 64))), b"not a photo", jpeg((9, 9, 9)))
        files = []
        for name, body in zip(names, bodies):
            files.append(Path(temp) / name)
            files[-1].write_bytes(body)
        browser_checks(root, files, repo)
    print("photo inbox: all checks passed")


if __name__ == "__main__":
    main()

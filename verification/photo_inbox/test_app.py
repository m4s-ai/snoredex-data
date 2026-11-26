"""Acceptance checks for the private photo inbox (#626, #639, #641): bulk upload of JPEG and DNG, the
dashboard that describes each job, the trash, the overview of every printing, restart, the German
mobile page and the derived archive copy.

Needs the inbox and browser requirements:
    pip install -r requirements.txt -r verification/photo_inbox/requirements.lock
    python verification/photo_inbox/test_app.py
"""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading

from PIL import Image, ImageChops, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
from waitress.server import create_server

from app import create_app
from overview import STAGES, unique_labels
import posting
from derive import carries_location, derive


def jpeg(colour=(200, 40, 40), size=(64, 48), gps=False):
    exif = Image.Exif()
    if gps:  # synthetic coordinates: the inbox keeps the raw bytes, GPS included, private
        exif.get_ifd(0x8825).update({1: "N", 2: (10.0, 20.0, 30.0), 3: "E", 4: (10.0, 20.0, 30.0)})
    out = BytesIO()
    Image.new("RGB", size, colour).save(out, "JPEG", exif=exif)
    return out.getvalue()


CARD = [[300, 400], [1380, 410], [1370, 1910], [310, 1900]]  # a card's corners in card_photo(), upright


def card_photo(number=None):
    """A phone photo stored sideways (orientation 6): one light card on a dark wall, as on its stand,
    with its collector number printed at the bottom right when given."""
    upright = Image.new("RGB", (1700, 2300), (20, 20, 24))
    draw = ImageDraw.Draw(upright)
    draw.polygon([tuple(p) for p in CARD], fill=(225, 205, 60))
    if number:
        draw.text((1080, 1800), number, fill=(10, 10, 10), font=ImageFont.load_default(size=56))
    exif = Image.Exif()
    exif[274] = 6
    out = BytesIO()
    upright.transpose(Image.Transpose.ROTATE_90).save(out, "JPEG", exif=exif, quality=92)
    return out.getvalue()


def dng(order=b"II", tag=50706):
    """The smallest TIFF whose first IFD holds one tag; 50706 (DNGVersion) makes it a DNG."""
    end = "<" if order == b"II" else ">"
    entry = struct.pack(end + "HHI", tag, 1, 4) + bytes([1, 4, 0, 0])
    return order + struct.pack(end + "HI", 42, 8) + struct.pack(end + "H", 1) + entry + bytes(68)


def post(client, body, content_type="application/octet-stream"):
    return client.post("/uploads", data=body, headers={"Content-Type": content_type})


def jobs(root):
    return sorted(path.name for path in root.iterdir() if path.name not in (".trash", ".drafts", ".posts"))


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
            "edition": "1st Edition", "cardName": "Snorlax", "localCardName": "Relaxo", "imageAssetId": f"asset-{stage}",
            "sourcePrintingId": f"P-{stage}",
            "markings": [{"text": "Prerelease stamp", "role": "distribution-promo"}] if stage == "online" else []}


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
    adoption_checks(client, repo, root / late)

    broken = post(client, dng_with_preview(b"\xff\xd8\xff\xe0\x00\x10garbage")).json["id"]
    assert client.get("/jobs").status_code == 200, "a job intake cannot derive does not break the list"
    assert not (root / broken / "archive.sha256").exists(), "a failed derivation is tried again later"


def cite(repo, specimen_id, printings):
    path = repo / "verification/specimens.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data["specimens"]:
        if row["specimenId"] == specimen_id:
            row["citedBy"] = printings
    path.write_text(json.dumps(data), encoding="utf-8", newline="\n")


def adoption_checks(client, repo, folder):
    """A filed job shows its SPEC and printing, and follows the catalogue when it reassigns them."""
    record = lambda: json.loads((folder / "job.json").read_text(encoding="utf-8"))
    picked = "item-99999999-0000-0000-0000-000000000000"
    client.get("/jobs")
    assert (record()["specimenHint"], record()["itemId"]) == ("SPEC-0950", picked), "uncited: the pick stays"
    cite(repo, "SPEC-0950", ["P-ready"])
    client.get("/jobs")
    assert (record()["specimenHint"], record()["itemId"]) == ("SPEC-0950", ITEMS["ready"])
    cite(repo, "SPEC-0950", ["P-assigned"])
    client.get("/jobs")
    assert record()["itemId"] == ITEMS["assigned"], "a reassignment is adopted"
    cite(repo, "SPEC-0950", ["P-assigned", "P-none"])
    client.post(f"/jobs/{folder.name}", json={"specimen": "SPEC-0001", "itemId": ITEMS["none"]})
    assert (record()["specimenHint"], record()["itemId"]) == ("SPEC-0950", ITEMS["none"]), \
        "the SPEC is the catalogue's; an ambiguous citation keeps the pick"


FAKE_EXPORTER = """import json, pathlib, sys, time
spec, out = sys.argv[1], pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
here = pathlib.Path(__file__)
with here.with_suffix(".log").open("a") as log:
    log.write(spec + "\\n")
if spec == "SPEC-0905":
    sys.exit("Entwurf zurückgestellt: kein Foto im Archiv")
time.sleep(0.5)  # long enough for a second request to arrive meanwhile
out.mkdir(parents=True)
(out / "post.jpg").write_bytes(here.with_suffix(".jpg").read_bytes())
(out / "caption-draft.txt").write_text(f"Caption {spec}\\n", encoding="utf-8")
(out / "alt-text.txt").write_text(f"Alt {spec}\\n", encoding="utf-8")
(out / "manifest.json").write_text(json.dumps({"requiredBeforePosting": ["Owner review"]}), encoding="utf-8")
"""


def fake_exporter(temp):
    """Stands in for the checkout's instagram_package.py: one draft per SPEC, SPEC-0905 refused."""
    script = Path(temp) / "exporter.py"
    script.write_text(FAKE_EXPORTER, encoding="utf-8", newline="\n")
    script.with_suffix(".jpg").write_bytes(jpeg((20, 20, 20), size=(40, 50)))
    return [sys.executable, str(script)], script.with_suffix(".log")


def posts_checks(root, repo, temp):
    """Drafts of every shared printing, built once per catalogue state; nothing is posted."""
    refused = create_app(root, repo, published).test_client().get("/posts")
    assert refused.status_code == 404 and "--photos" in refused.json["error"]
    command, log = fake_exporter(temp)
    client = create_app(root, repo, published, photos=Path(temp), command=command).test_client()
    posts = {post["draftSpecimen"]: post for post in client.get("/posts").json["posts"]}
    assert set(posts) == {"SPEC-0904", "SPEC-0905"}, "only printings with a short link"
    ready = posts["SPEC-0904"]
    assert (ready["stage"], ready["caption"], ready["alt"], ready["open"]) == (
        "ready", "Caption SPEC-0904\n", "Alt SPEC-0904", ["Owner review"])
    assert "kein Foto" in posts["SPEC-0905"]["error"], "a failed draft shows its reason"
    image = client.get(ready["image"])
    assert image.status_code == 200 and image.mimetype == "image/jpeg"
    assert client.get("/posts/SPEC-0905/image").status_code == 404
    assert client.get("/posts/SPEC-0001/image").status_code == 404, "only shared printings"
    client.get("/posts")
    assert log.read_text().split().count("SPEC-0904") == 1, "a draft is built once per catalogue state"
    social = repo / "data/social.json"
    later = social.stat().st_mtime_ns + 10**9
    os.utime(social, ns=(later, later))
    client.get("/posts")
    assert log.read_text().split().count("SPEC-0904") == 2, "a changed catalogue rebuilds the draft"
    assert len(list((root / ".drafts").glob("SPEC-0904-*"))) == 1, "the older draft goes"
    script = Path(command[-1])
    edited = script.stat().st_mtime_ns + 10**9
    os.utime(script, ns=(edited, edited))  # a pulled change to the exporter's code, the catalogue unchanged
    client.get("/posts")
    assert log.read_text().split().count("SPEC-0904") == 3, "a changed exporter rebuilds the draft (#691)"
    os.utime(social, ns=(later + 10**9, later + 10**9))
    app = client.application
    replies = []
    requests = [threading.Thread(target=lambda: replies.append(app.test_client().get(ready["image"]).status_code))
                for _ in range(2)]
    for request in requests:
        request.start()
    for request in requests:
        request.join()
    assert replies == [200, 200], "two requests for an unbuilt draft both get it"
    assert log.read_text().split().count("SPEC-0904") == 4, "and it is built once"
    assert all(job["id"] != ".drafts" for job in client.get("/jobs").json["jobs"])
    return command


class FakeUploader:
    """Stands in for the owner's uploader: records every call and deduplicates on clientRef like it."""
    ACCOUNTS = [{"id": "ig:snoredex", "platform": "instagram", "displayName": "SnoreDex", "externalId": "secret"},
                {"id": "fb_page:1", "platform": "facebook_page", "displayName": "SnoreDex"},
                {"id": "threads:snoredex", "platform": "threads", "displayName": "SnoreDex"},
                {"id": "ig:other", "platform": "instagram", "displayName": "other.page"}]
    SNOREDEX = ["ig:snoredex", "fb_page:1", "threads:snoredex"]  # what the inbox may post to

    def __init__(self, failing_account_lists=0):
        self.media_calls, self.uploads, self.jobs, self.down, self.crash = [], [], {}, False, False
        self.failing_account_lists, self.held = failing_account_lists, None

    def accounts(self):
        if self.held:  # a slow uploader: the next account list waits until the test lets it go
            held, self.held = self.held, None
            held.wait(30)
        if self.failing_account_lists:
            self.failing_account_lists -= 1
            raise posting.UploaderError("Uploader nicht erreichbar")
        return self.ACCOUNTS

    def media(self, jpeg):
        if self.down:
            raise posting.UploaderError("Uploader nicht erreichbar")
        self.media_calls.append(jpeg)
        return f"https://uploader.test/media/{len(self.media_calls)}.jpg"

    def upload(self, body):
        if self.crash:  # the inbox stops while the request is on its way
            raise SystemExit("stopped")
        same = [job for job in self.jobs.values() if job["clientRef"] == body["clientRef"] and job["status"] != "failed"]
        if same:
            return same[0]
        self.uploads.append(body)
        job = {"id": f"job-{len(self.uploads)}", "status": "queued", "clientRef": body["clientRef"]}
        self.jobs[job["id"]] = job
        return job

    def job(self, job_id):
        return self.jobs[job_id]


def posting_checks(root, repo, temp, command):
    """Only the owner's order posts: now or at a time, once per account, a failure sent again on request."""
    uploader = FakeUploader()
    client = create_app(root, repo, published, photos=Path(temp), command=command, uploader=uploader,
                        schedule=False).test_client()
    assert client.get("/accounts").json["accounts"][0] == {"id": "ig:snoredex", "platform": "instagram",
                                                           "displayName": "SnoreDex"}, "no account internals"
    assert [account["id"] for account in client.get("/accounts").json["accounts"]] == FakeUploader.SNOREDEX, \
        "only SnoreDex on Instagram, Facebook and Threads, never the uploader's other accounts"
    listing = client.get("/posts").json
    mine = lambda: next(row for row in client.get("/posts").json["posts"] if row["draftSpecimen"] == "SPEC-0904")
    ready = mine()
    assert listing["canPost"] and ready["order"] is None and len(ready["slides"]) == 1
    accounts = FakeUploader.SNOREDEX
    order = lambda **body: client.post("/posts/SPEC-0904/order", json=dict(draft=ready["draft"], accounts=accounts) | body)
    assert order(draft="SPEC-0904-stale").status_code == 409, "only the draft the owner saw"
    assert order(accounts=[]).status_code == 400 and order(accounts=["ig:unknown"]).status_code == 400
    assert order(accounts=["ig:other"]).status_code == 400, "the uploader knows it, but it is not SnoreDex"
    assert order(at="2026-12-01T18:00").status_code == 400, "a time needs its zone"
    assert client.post("/posts/SPEC-0001/order", json={}).status_code == 404, "only shared printings"

    later = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    assert order(at=later).status_code == 201
    posting.tick(root, uploader)
    assert not uploader.uploads, "a scheduled post waits for its time"
    assert mine()["order"]["dueAt"], "the page shows the plan"
    posting.tick(root, uploader, datetime.now(timezone.utc) + timedelta(hours=3))
    assert len(uploader.uploads) == 3, "it goes out at its time, also after a restart: the order is on disk"
    shutil.rmtree(root / ".posts" / "SPEC-0904")

    assert order(at=later).status_code == 201 and client.delete("/posts/SPEC-0904/order").status_code == 200
    assert order(at=later).status_code == 201
    uploader.crash = True
    try:
        posting.tick(root, uploader, datetime.now(timezone.utc) + timedelta(hours=3))
    except SystemExit:
        pass
    uploader.crash = False
    assert client.delete("/posts/SPEC-0904/order").status_code == 409, "a send cut off on its way may have arrived"
    shutil.rmtree(root / ".posts" / "SPEC-0904")

    assert order().status_code == 201 and order().status_code == 409, "one order per draft"
    frozen = root / ".posts" / "SPEC-0904" / "post.jpg"
    frozen.write_bytes(b"frozen")  # stands for the approved image, against a later draft
    social = repo / "data/social.json"
    later_stamp = social.stat().st_mtime_ns + 10**10
    os.utime(social, ns=(later_stamp, later_stamp))
    shown = mine()
    assert (shown["draft"], shown["open"]) == (ready["draft"], []), "an ordered post shows what it froze"
    assert client.get(shown["image"]).data == b"frozen", "and its image is the frozen one"
    uploader.uploads.clear()
    uploader.down = True
    posting.tick(root, uploader)
    targets = mine()["order"]["targets"]
    assert targets["ig:snoredex"]["status"] == "pending" and "erreichbar" in targets["ig:snoredex"]["problem"]
    assert client.delete("/posts/SPEC-0904/order").status_code == 409, "a tried send may have arrived: no take-back"
    uploader.down = False
    posting.tick(root, uploader)
    assert len(uploader.media_calls) == 3 and len(uploader.uploads) == 3, "one image upload per round"
    first = uploader.uploads[0]
    assert (first["imageUrl"], first["altText"], first["caption"]) == (
        "https://uploader.test/media/3.jpg", "Alt SPEC-0904", "Caption SPEC-0904"), first
    assert client.delete("/posts/SPEC-0904/order").status_code == 409, "a sent post cannot be taken back"

    record = root / ".posts" / "SPEC-0904" / "order.json"
    crashed = json.loads(record.read_text(encoding="utf-8"))
    crashed["targets"]["ig:snoredex"] = {"attempt": 1, "status": "pending"}  # sent, but not recorded
    record.write_text(json.dumps(crashed), encoding="utf-8", newline="\n")
    posting.tick(root, uploader)
    assert len(uploader.uploads) == 3, "a resend after a crash finds the same job: no double post"
    uploader.jobs["job-1"].update(status="published", permalink="https://www.instagram.com/p/new/")
    uploader.jobs["job-2"].update(status="failed", error="Seite gesperrt")
    posting.tick(root, uploader)
    view = mine()["order"]["targets"]
    assert view["ig:snoredex"]["permalink"] == "https://www.instagram.com/p/new/"
    assert view["fb_page:1"]["error"] == "Seite gesperrt" and "media" not in json.dumps(view)
    assert client.post("/posts/SPEC-0904/retry", json={"account": "ig:snoredex"}).status_code == 409
    assert client.post("/posts/SPEC-0904/retry", json={"account": "fb_page:1"}).status_code == 200
    posting.tick(root, uploader)
    assert uploader.uploads[-1]["clientRef"].endswith("fb_page:1:2"), "a resend is a new attempt"
    assert all(job["id"] != ".posts" for job in client.get("/jobs").json["jobs"])
    assert posting.published_links(root) == {ITEMS["ready"]: {"instagramPosts": ["https://www.instagram.com/p/new/"]}}
    kept = record.read_text(encoding="utf-8")
    record.write_text("{not json", encoding="utf-8", newline="\n")  # #676: a broken order stays at its own post
    listing = client.get("/posts")
    assert listing.status_code == 200 and "error" in mine() and mine()["order"] is None, listing.json
    record.write_text(kept, encoding="utf-8", newline="\n")
    return uploader


def runs_checks(temp):
    """#685: the Läufe tab shows every run in its group with its links, retries a failed one exactly once,
    names the last nightly round, and says so when no runner is set up; no sideways scroll on a phone."""
    import runner as intake_runner

    root, repo = Path(temp) / "runs-inbox", catalogue_repo(Path(temp) / "runs-repo", "sha256:none")
    client = create_app(root, repo, published).test_client()
    ids = [post(client, jpeg(colour)).json["id"]
           for colour in ((11, 0, 0), (0, 11, 0), (0, 0, 11), (11, 11, 0), (0, 11, 11))]
    at = "2026-11-26T03:00:05+00:00"
    states = [{"status": "queued", "done": [], "origin": "night", "queuedAt": at},
              {"status": "running", "step": "merge", "done": ["intake"], "specimen": "SPEC-0101", "pr": 101,
               "origin": "button", "startedAt": at},
              {"status": "failed", "step": "publish", "done": ["intake", "merge"], "specimen": "SPEC-0102", "pr": 102,
               "error": "pages.yml endete mit failure: https://example.invalid/runs/1", "startedAt": at,
               "finishedAt": at, "approval": {"itemId": "x"}, "runs": {"pages.yml": {"request": "inbox-secret"}}},
              {"status": "done", "done": list(intake_runner.STEPS), "specimen": "SPEC-0103", "pr": 103, "aliasPr": 104,
               "alias": "sdabc", "startedAt": at, "finishedAt": at},
              # failed before filing, and its job has no printing now: a retry is refused (409)
              {"status": "failed", "step": "intake", "done": [], "origin": "night", "finishedAt": at,
               "error": "https://example.invalid/a-very-long-unbreakable-token-" + "x" * 80}]
    for job_id, state in zip(ids, states):
        intake_runner.write_state(root / job_id, state)
    (root / intake_runner.WORK).mkdir(exist_ok=True)
    (root / intake_runner.WORK / intake_runner.NIGHT).write_text(json.dumps({"at": at, "jobs": [ids[0]]}),
                                                                 encoding="utf-8", newline="\n")
    run = intake_runner.Runner(root, None)  # queues for real; schedule=False never starts it, nothing leaves
    listed = create_app(root, repo, published, runner=run, schedule=False).test_client().get("/runs").json
    assert "inbox-secret" not in json.dumps(listed) and "approval" not in json.dumps(listed), "no internals"
    servers = [create_server(create_app(root, repo, published, runner=chosen, schedule=False), host="127.0.0.1",
                             port=0)
               for chosen in (run, None)]
    for server in servers:
        threading.Thread(target=server.run, daemon=True).start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 375, "height": 812})
            page.goto(f"http://127.0.0.1:{servers[0].effective_port}/#laeufe")
            page.locator("#runs-done li").wait_for()
            group = lambda name: page.locator(f"#runs-{name} li").evaluate_all("items => items.map(i => i.dataset.job)")
            groups = {name: sorted(group(name)) for name in ("active", "failed", "done")}
            assert groups == {"active": sorted(ids[:2]), "failed": sorted([ids[2], ids[4]]), "done": [ids[3]]}, groups
            done = page.locator("#runs-done li .links a").evaluate_all("links => links.map(a => a.href)")
            assert done == ["https://github.com/m4s-ai/snoredex-data/pull/103",
                            "https://github.com/m4s-ai/snoredex-data/pull/104", "https://go.m4s.eu/sdabc"], done
            # a wide font, as the Linux runner's fallback, must not push the page sideways either
            page.evaluate("""() => { document.body.style.fontFamily = 'Verdana, "DejaVu Sans", sans-serif'; }""")
            assert page.evaluate("document.documentElement.scrollWidth") <= 375, "no sideways scroll on a phone"
            refused = page.locator(f'#runs-failed li[data-job="{ids[4]}"]')
            refused.locator(".retry").click()
            page.locator(f'#runs-failed li[data-job="{ids[4]}"] .error >> text=Nicht neu gestartet').wait_for()
            reason = refused.locator(".error").text_content()
            assert "Nicht neu gestartet: Dem Foto ist noch kein Druck zugeordnet." in reason, reason
            assert run.jobs.qsize() == 0, "a refused retry queues nothing"
            failed = page.locator(f'#runs-failed li[data-job="{ids[2]}"]')
            assert "pages.yml endete mit failure" in failed.locator(".error").text_content()
            assert failed.locator(".photo").get_attribute("href") == f"#job-{ids[2]}", "a jump to the photo"
            assert "Veröffentlichen" in failed.locator(".steps").text_content()
            assert "1 Auftrag" in page.locator("#runs-night").text_content()
            assert page.locator("#count-laeufe").text_content() == "4", "waiting, running and failed runs"
            assert page.evaluate("document.documentElement.scrollWidth") <= 375, "no sideways scroll on a phone"
            failed.locator(".retry").click()
            failed.wait_for(state="detached")
            assert sorted(group("active")) == sorted(ids[:3]) and run.jobs.qsize() == 1, "queued exactly once"
            assert "Nicht neu gestartet" in refused.locator(".error").text_content(), "and survives a refresh"
            assert intake_runner.read_state(root / ids[2])["status"] == "queued"
            page.goto(f"http://127.0.0.1:{servers[1].effective_port}/#laeufe")
            page.locator("#runs-done li").wait_for()
            assert "nicht eingerichtet" in page.locator("#runs-status").text_content(), "without a runner it says so"
            assert page.locator("#runs-active .retry:visible, #runs-failed .retry:visible").count() == 0
            browser.close()
    finally:
        for server in servers:
            server.close()


def queue_checks(temp):
    """#676: a finished target costs no call and no write; a broken order blocks no other one."""
    root = Path(temp) / "queue"
    uploader, calls, writes = FakeUploader(), [], []
    for name in ("media", "upload", "job"):
        setattr(uploader, name, lambda *args, call=getattr(uploader, name), name=name: calls.append(name) or call(*args))
    written = posting.write_json
    posting.write_json = lambda path, data: writes.append(path.parent.name) or written(path, data)

    def place(specimen, **targets):
        folder = root / posting.POSTS / specimen
        folder.mkdir(parents=True)
        (folder / "post.jpg").write_bytes(jpeg())
        order = {"specimen": specimen, "itemId": "item-x", "id": "abc", "createdAt": "2026-11-26T09:00:00+00:00",
                 "dueAt": "2026-11-26T09:00:00+00:00", "caption": "Caption", "images": [{"file": "post.jpg", "alt": "Alt"}],
                 "targets": targets}
        written(folder / "order.json", order)

    def target(specimen, account):
        return posting.read_order(root, specimen)["targets"][account]

    try:
        done = {"attempt": 1, "status": "published", "tried": True, "jobId": "job-0", "permalink": "https://x.test/p"}
        place("SPEC-0001", **{account: dict(done) for account in FakeUploader.SNOREDEX})
        posting.tick(root, uploader)
        posting.tick(root, uploader)
        assert (calls, writes) == ([], []), ("three published targets, two rounds: no call, no write", calls, writes)

        uploader.jobs["job-9"] = {"id": "job-9", "status": "processing", "clientRef": "x"}
        place("SPEC-0002", **{"ig:snoredex": dict(done), "fb_page:1": {"attempt": 1, "status": "processing",
                                                                        "tried": True, "jobId": "job-9"}})
        posting.tick(root, uploader)  # the running target is followed; its first answer adds its fields
        calls.clear(), writes.clear()
        posting.tick(root, uploader)
        assert (calls, writes) == (["job"], []), ("only the running target is followed; unchanged, not written",
                                                  calls, writes)
        uploader.jobs["job-9"].update(status="published", permalink="https://x.test/q")
        posting.tick(root, uploader)
        assert writes == ["SPEC-0002"] and target("SPEC-0002", "fb_page:1")["permalink"] == "https://x.test/q"
        assert target("SPEC-0002", "ig:snoredex") == done, "the published target stays as it was"

        broken = root / posting.POSTS / "SPEC-0000"
        broken.mkdir(parents=True)
        (broken / "order.json").write_text("{not json", encoding="utf-8", newline="\n")
        place("SPEC-0003", **{"ig:snoredex": {"attempt": 1, "status": "pending"}})
        calls.clear(), writes.clear()
        posting.tick(root, uploader)  # SPEC-0000 sorts first and cannot be read
        assert calls == ["media", "upload"] and target("SPEC-0003", "ig:snoredex")["status"] == "queued", calls
        assert writes == ["SPEC-0003", "SPEC-0003"], ("marked as tried before the send, then the job", writes)
    finally:
        posting.write_json = written


def permalink_checks(temp):
    """The data PR's input: each published permalink once, in its platform's field, nothing else."""
    from permalinks import record

    repo, inbox = Path(temp) / "links-repo", Path(temp) / "links-inbox"
    (repo / "data").mkdir(parents=True)
    social = [{"itemId": ITEMS["ready"], "specimenId": "SPEC-0904", "instagramPosts": []}]
    (repo / "data/social.json").write_text(json.dumps(social, indent=2) + "\n", encoding="utf-8", newline="\n")
    (inbox / ".posts/SPEC-0904").mkdir(parents=True)
    targets = {"ig:snoredex": {"status": "published", "permalink": "https://www.instagram.com/p/abc/"},
               "fb_page:1": {"status": "published", "permalink": "https://www.facebook.com/1/posts/2"},
               "threads:snoredex": {"status": "failed", "permalink": None}}
    (inbox / ".posts/SPEC-0904/order.json").write_text(json.dumps({"itemId": ITEMS["ready"], "targets": targets}),
                                                          encoding="utf-8", newline="\n")
    assert record(inbox, repo) == 2 and record(inbox, repo) == 0, "each link once"
    row = json.loads((repo / "data/social.json").read_text(encoding="utf-8"))[0]
    assert row == dict(social[0], instagramPosts=["https://www.instagram.com/p/abc/"],
                       facebookPosts=["https://www.facebook.com/1/posts/2"]), row


def corner_checks(root, repo):
    """Corners are suggested, approved only for an assigned printing, and dropped when it changes (#657)."""
    client = create_app(root, repo, published).test_client()
    job = post(client, card_photo()).json["id"]
    found = client.get(f"/jobs/{job}/corners").json
    assert found["size"] == [1700, 2300] and found["approved"] is None, "the upright photo's pixels"
    error = max(abs(a - b) for quad in found["candidates"][:1] for p, q in zip(quad, CARD) for a, b in zip(p, q))
    assert error <= 0.02 * 1080, found["candidates"]
    approve = lambda corners: client.post(f"/jobs/{job}/corners", json={"corners": corners})
    assert approve(CARD).status_code == 400, "no printing, no corners"
    client.post(f"/jobs/{job}", json={"itemId": ITEMS["none"]})
    assert approve(CARD[::-1]).status_code == 400, "clockwise from top left"
    assert approve([[0, 0], [500, 0], [500, 700], [0, 700]]).status_code == 400, "too narrow for the gallery"
    assert approve([[0, 0], [1800, 0], [1800, 2000], [0, 2000]]).status_code == 400, "inside the photo"
    collapsed = [CARD[0], CARD[2], [CARD[2][0], CARD[2][1] + 1], CARD[3]]  # top right dragged onto bottom right
    assert approve(collapsed).status_code == 400, "a quad the gallery crop cannot use"
    approved = approve(CARD)
    assert approved.status_code == 200 and approved.json["corners"] == CARD and approved.json["cornersApprovedAt"]
    cover = client.get(f"/jobs/{job}/cover?c=" + ",".join(str(v) for p in CARD for v in p))
    with Image.open(BytesIO(cover.data)) as image:
        assert cover.status_code == 200 and image.size == (1080, 1350), "the post's title image"
    assert client.get(f"/jobs/{job}/cover?c=1,2,3").status_code == 400
    record = lambda: json.loads((root / job / "job.json").read_text(encoding="utf-8"))
    client.post(f"/jobs/{job}", json={"itemId": ITEMS["none"], "note": "same printing"})
    assert record()["corners"] == CARD, "a new note keeps the approval"
    client.post(f"/jobs/{job}", json={"itemId": ITEMS["assigned"]})
    assert "corners" not in record() and "cornersApprovedAt" not in record(), "another printing drops it"
    mark_filed(repo, root / job, "SPEC-0960")
    assert approve(CARD).status_code == 409, "a filed job's corners are the catalogue's"
    number_checks(client, root)


def number_checks(client, root):
    """The number read at approval guards the assignment; without Tesseract it is only marked (#658)."""
    job = post(client, card_photo("1/64")).json["id"]  # ITEMS["none"] is 1/64
    record = lambda: json.loads((root / job / "job.json").read_text(encoding="utf-8"))
    client.post(f"/jobs/{job}", json={"itemId": ITEMS["none"]})
    check = client.post(f"/jobs/{job}/corners", json={"corners": CARD}).json["numberCheck"]
    assert check["itemId"] == ITEMS["none"] and check["expected"] == "1/64"
    assert client.post(f"/jobs/{job}/number").status_code == 400, "nothing to confirm without a mismatch"
    if check["result"] == "unavailable":
        print("note: Tesseract not installed, the number readings were not exercised")
        return
    assert check["result"] == "match", check
    client.post(f"/jobs/{job}", json={"itemId": ITEMS["assigned"]})  # 2/64: the wrong printing
    assert "numberCheck" not in record(), "a check of another printing goes with it"
    check = client.post(f"/jobs/{job}/corners", json={"corners": CARD}).json["numberCheck"]
    assert (check["result"], check["expected"], check["read"]) == ("mismatch", "2/64", ["1/64"]), check
    confirmed = client.post(f"/jobs/{job}/number")
    assert confirmed.status_code == 200 and confirmed.json["numberConfirmedAt"]
    client.post(f"/jobs/{job}/corners", json={"corners": CARD})
    assert "numberConfirmedAt" not in record(), "a new frame is read and confirmed again"


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
    assert (jobs[filed]["specimenHint"], jobs[filed]["itemId"]) == ("SPEC-0902", ITEMS["filed"]), \
        "a filed job takes the printing whose image its SPEC is"
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


def pick_printing(item):
    """The picker matches every typed word, German language names and "Stempel" included."""
    picker, hits = item.locator('input[name="item"]'), item.locator(".picks button")
    picker.fill("ju stempel")
    assert hits.count() == 1 and "Prerelease stamp" in hits.first.text_content(), "Stempel finds the marked print"
    picker.fill("english 1/64")
    assert hits.count() == 1, "the English words match as well"
    picker.fill("relaxo englisch 1/64")
    assert hits.count() == 1 and "JU 1/64 · Englisch" in hits.first.text_content(), "words in any order, in German"
    picker.press("Tab")
    assert hits.first.evaluate("button => button === document.activeElement"), "Tab reaches the first hit"
    hits.first.press("ArrowUp")
    assert picker.evaluate("input => input === document.activeElement"), "ArrowUp goes back to the field"
    picker.press("ArrowDown")
    assert hits.first.evaluate("button => button === document.activeElement"), "ArrowDown enters the hits"
    hits.first.press("Enter")
    assert picker.input_value() == "JU 1/64 · English · holo · 1st Edition · Relaxo"
    assert item.locator(".picks").is_hidden(), "a pick closes the list"
    assert picker.evaluate("input => input === document.activeElement"), "the focus goes back to the field"


def browser_checks(root, files, repo, command, photos):
    """Bulk upload with one bad file, describe a job, the overview and the trash, on a phone-sized page."""
    uploader = FakeUploader()
    idle = type("IdleRunner", (), {"submit": lambda self, job_id: True})()  # the intake box, no runs
    server = create_server(create_app(root, repo, published, photos=photos, command=command,
                                      uploader=uploader, schedule=False, runner=idle), host="127.0.0.1", port=0)
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
                if item.locator(".photo img").evaluate("image => image.complete && image.naturalWidth > 0"):
                    break
                page.wait_for_timeout(100)
            else:
                raise AssertionError("the preview of the new DNG did not load")
            assert item.locator(".state").text_content() == "ohne Angabe"
            item.locator("textarea").fill("Relaxo, Sammel-Upload")
            pick_printing(item)
            item.locator('button[type="submit"]').click()
            item.locator(".saved.ok").wait_for()
            assert item.locator(".state").text_content() == "beschrieben"
            page.click("#tab-uebersicht")
            none_row = page.locator(f'li.row[data-item="{ITEMS["none"]}"]')
            none_row.locator(f'a[href="#job-{new}"]').click()
            item.wait_for()
            assert page.url.endswith(f"#job-{new}") and item.is_visible(), "a row's photo link opens the photos tab"
            header = page.locator(".top").bounding_box()
            assert item.bounding_box()["y"] >= header["y"] + header["height"], "the job stops below the header"
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
            locked_job(page, root, new)
            overview_page(page)
            trash_page(page, new)
            corner_page(page, root)
            posts_page(page, root, uploader)
            assert page.evaluate("document.documentElement.scrollWidth") <= 375, "no sideways scroll on a phone"
            tab_checks(page, url)
            assert not problems, problems
            browser.close()
    finally:
        server.close()


def locked_job(page, root, job_id):
    """D01 (#672): while a run holds the approval, the printing field and the corners are closed, with why."""
    state = root / job_id / "intake-run.json"
    state.write_text(json.dumps({"status": "queued", "done": []}), encoding="utf-8", newline="\n")
    try:
        page.reload()
        item = page.locator(f'li.job[data-job="{job_id}"]')
        item.wait_for()
        assert item.locator('input[name="item"]').is_disabled(), "the printing stays as approved"
        assert "läuft" in item.locator(".locked").text_content() and item.locator(".locked").is_visible()
        assert item.locator(".corners-open").is_hidden(), "so do the corners"
        item.locator("textarea").fill("Relaxo, Sammel-Upload")
        item.locator('button[type="submit"]').click()
        item.locator(".saved.ok").wait_for()  # the note still saves: the disabled field sends the same printing
    finally:
        state.unlink()
    page.reload()
    page.locator(f'li.job[data-job="{job_id}"] input[name="item"]:not([disabled])').wait_for()


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
    labels = page.locator('[role="tab"] span:not(.count)')
    # every label in its selected (bold) weight, in the system font and in a wide one, as a phone may have (#677)
    selected = page.evaluate("""() => [...document.querySelectorAll('[role="tab"]')].map(tab => {
        const was = tab.getAttribute("aria-selected"); tab.setAttribute("aria-selected", "true"); return was; })""")
    for font in ("", 'Verdana, "DejaVu Sans", sans-serif'):
        page.evaluate("font => document.querySelectorAll('.tabs button').forEach(b => b.style.fontFamily = font)", font)
        for width in (320, 375):
            page.set_viewport_size({"width": width, "height": 812})
            for index in range(labels.count()):
                assert labels.nth(index).evaluate("label => label.scrollWidth <= label.parentElement.clientWidth"), \
                    ("a tab label fits its tab", width, font, labels.nth(index).text_content())
    page.evaluate("""selected => document.querySelectorAll('[role="tab"]').forEach((tab, i) => {
        tab.setAttribute("aria-selected", selected[i]); tab.style.fontFamily = ""; })""", selected)
    page.locator("#tab-papierkorb").focus()
    page.keyboard.press("ArrowRight")
    assert page.evaluate("document.activeElement.id") == "tab-hochladen", "arrows wrap around"
    assert page.locator("#panel-hochladen").is_visible() and page.url.endswith("#hochladen")
    page.keyboard.press("End")
    assert page.evaluate("document.activeElement.id") == "tab-papierkorb"
    page.keyboard.press("Home")
    page.keyboard.press("ArrowLeft")
    assert page.locator("#tab-papierkorb").get_attribute("tabindex") == "0"
    assert [tabs.nth(index).get_attribute("tabindex") for index in range(5)] == ["-1"] * 5, "one tab stop"
    page.set_viewport_size({"width": 1280, "height": 800})
    page.click("#tab-uebersicht")
    assert page.locator("#tab-uebersicht").bounding_box()["y"] < 80, "the wide tab bar sits at the top"
    assert page.evaluate("document.documentElement.scrollWidth") <= 1280
    line = page.locator("#version").bounding_box()
    assert 720 <= line["y"] and line["y"] + line["height"] <= 800, ("the version line stays in view on a wide screen", line)
    page.set_viewport_size({"width": 375, "height": 812})


def corner_page(page, root):
    """On the phone: the suggested frame, handles a thumb can hit, keyboard and drag, then approval."""
    base = page.url.split("#")[0]
    job = page.request.post(base + "uploads", data=card_photo(),
                            headers={"Content-Type": "application/octet-stream"}).json()["id"]
    page.request.post(base + f"jobs/{job}", data=json.dumps({"itemId": ITEMS["none"]}),
                      headers={"Content-Type": "application/json"})
    page.goto(base + "#fotos")
    page.reload()
    item = page.locator(f'li.job[data-job="{job}"]')
    item.locator(".corners-open").click()
    handles = item.locator(".handle")
    handles.nth(3).wait_for()
    assert item.locator(".corners-status").text_content().startswith("Karte erkannt")
    assert item.locator(".choices").is_hidden(), "one card, no choice to make"
    for index in range(4):
        box = handles.nth(index).bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44, ("target size", index, box)
    label = lambda: handles.nth(0).get_attribute("aria-label")
    suggested = label()
    before = int(label().split(": ")[1].split(",")[0])
    handles.nth(0).focus()
    page.keyboard.press("Shift+ArrowRight")
    assert int(label().split(": ")[1].split(",")[0]) == before + 40, label()
    assert item.locator(".loupe").is_visible(), "the loupe shows the corner under the thumb"
    box = handles.nth(2).bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] / 2 + 10, box["y"] + box["height"] / 2 + 10, steps=4)
    page.mouse.up()
    approved(item)
    stored = json.loads((root / job / "job.json").read_text(encoding="utf-8"))["corners"]
    assert stored[0][0] == before + 40 and stored[2][0] > CARD[2][0] - 40, stored
    number = item.locator(".number-status")
    assert number.is_visible() and "hält nichts auf" in number.text_content(), "a card without a number stops nothing"
    assert item.locator(".number-confirm").is_hidden()
    for _ in range(100):
        if item.locator(".cover").evaluate("image => image.complete && image.naturalWidth === 1080"):
            break
        page.wait_for_timeout(100)
    else:
        raise AssertionError("the title image from the corners did not load")
    assert page.evaluate("document.documentElement.scrollWidth") <= 375, "no sideways scroll"
    item.locator(".corners-open").click()
    assert item.locator(".corners-status").text_content().startswith("Ecken freigegeben am"), "reopened, it says so"
    item.locator(".reset").click()
    assert label() == suggested, "the suggestion comes back unchanged after dragging"
    reopened_editor(page, root, item, job)


def approved(item):
    """The answer to an approval shows where the owner looks: the editor below the fold closes onto its button."""
    item.locator(".approve").click()
    opener = item.locator(".corners-open", has_text="Ecken freigegeben am")
    opener.wait_for()
    assert item.locator(".corners").is_hidden(), "the editor closes, so what follows comes into view"
    assert opener.evaluate("button => button === document.activeElement"), "the focus lands on the result"
    assert item.locator(".approve").is_enabled() and item.locator(".approve").text_content() == "Ecken freigeben"


def reopened_editor(page, root, item, job):
    """Another printing resets the editor; built again, one click still approves once."""
    item.locator('input[name="item"]').fill(ITEMS["assigned"])
    item.locator('button[type="submit"]').click()
    item.locator(".saved.ok").wait_for()
    assert item.locator(".corners").is_hidden() and item.locator(".corners-open").text_content() == "Ecken festlegen"
    assert "corners" not in json.loads((root / job / "job.json").read_text(encoding="utf-8"))
    item.locator(".corners-open").click()
    item.locator(".handle").nth(3).wait_for()
    assert item.locator(".handle").count() == 4, "the handles are built once"
    sent = []
    page.on("request", lambda request: request.method == "POST" and request.url.endswith("/corners")
            and sent.append(request.url))
    approved(item)
    page.wait_for_timeout(300)
    assert len(sent) == 1, "one click approves once"


def posts_page(page, root, uploader):
    """The draft of a printing ready for Instagram: image, caption, alt text, open points, and the order form."""
    held = uploader.held = threading.Event()
    page.reload()
    page.click("#tab-posts")
    post = page.locator("#posts li.post")
    post.wait_for(timeout=3000)
    assert page.locator("#count-posts").text_content() == "1", "the drafts and their count never wait for the uploader"
    assert post.locator(".send").is_hidden()
    held.set()
    post.locator(".send").wait_for()  # the send form follows once the uploader names the accounts
    uploader.failing_account_lists = 1
    page.reload()
    page.click("#tab-posts")
    post.wait_for()
    assert post.locator(".send").is_hidden(), "no accounts, no form"
    page.select_option("#post-view", "all")
    page.select_option("#post-view", "ready")
    post.locator(".send").wait_for()  # the accounts are asked for again once the uploader answers
    assert page.locator("#count-posts").text_content() == "1"
    assert post.count() == 1 and post.locator(".badge").text_content() == "bereit für Instagram"
    for _ in range(50):
        if post.locator("img").evaluate("image => image.complete && image.naturalWidth > 0"):
            break
        page.wait_for_timeout(100)
    else:
        raise AssertionError("the post image did not load")
    assert post.locator(".caption").input_value() == "Caption SPEC-0904\n"
    assert post.locator(".alt").input_value() == "Alt SPEC-0904"
    assert post.locator(".todo").text_content() == "Vor dem Posten: Abnahme durch dich"
    assert post.get_by_role("link", name="Bild laden").get_attribute("download") == "SPEC-0904-post.jpg"
    boxes = post.locator("input[name=account]")
    assert boxes.count() == 3 and all(boxes.nth(index).is_checked() for index in range(3)), \
        "SnoreDex on Instagram, Facebook and Threads, all preselected; the uploader's other accounts never show"
    assert post.locator(".accounts").text_content().startswith("Instagram SnoreDex")
    send = post.locator(".send button")
    assert send.text_content() == "Jetzt posten"
    page.once("dialog", lambda dialog: dialog.dismiss())
    send.click()
    assert not list((root / ".posts").glob("SPEC-*")), "a dismissed confirmation posts nothing"
    post.locator("input[name=at]").fill("2030-01-01T18:00")
    assert send.text_content() == "Einplanen"
    boxes.nth(1).uncheck()
    page.once("dialog", lambda dialog: dialog.accept())
    send.click()
    post.locator(".targets li").first.wait_for()
    assert post.locator(".targets").text_content().count("wartet") == 2, "only the chosen accounts"
    assert post.locator(".sent").text_content().startswith("Eingeplant für")
    held = uploader.held = threading.Event()  # the plan is taken back while the page still waits for the accounts
    page.reload()
    page.click("#tab-posts")
    page.once("dialog", lambda dialog: dialog.accept())
    post.locator(".cancel").click()
    post.locator(".send").wait_for()
    assert not list((root / ".posts").glob("SPEC-*")), "a plan can be taken back before it goes"
    held.set()
    page.wait_for_timeout(1000)
    assert post.locator(".send").is_visible() and not post.locator(".sent").text_content(), \
        "accounts that arrive late never bring back a plan that was taken back"
    page.select_option("#post-view", "posted")
    assert "kein Foto" in page.locator("#posts li.post .todo.error").text_content()


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
    accept = lambda dialog: dialog.accept()
    page.on("dialog", accept)
    trash_flow(page, job)
    page.remove_listener("dialog", accept)


def trash_flow(page, job):
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
    specimen, printing = filed.locator('input[name="specimen"]'), filed.locator('input[name="item"]')
    assert specimen.input_value() == "SPEC-0902" and printing.input_value().startswith("JU 3/64"), \
        "a filed job shows its SPEC and printing"
    specimen.fill("SPEC-0001")
    filed.locator('button[type="submit"]').click()
    filed.locator(".saved.ok").wait_for()
    assert specimen.input_value() == "SPEC-0902", "after saving the form shows what was stored"


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


def commit_file(repo, name, text):
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    (repo / name).write_text(text, encoding="utf-8", newline="\n")
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=test"]
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", name], check=True)
    return subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()


def version_checks(temp):
    """#666: the page and /version name the image's commit and the checkouts; a data commit keeps the
    code current, an inbox-code commit asks for a rebuild, anything unreadable stays unknown."""
    repo = catalogue_repo(Path(temp) / "version-repo", "sha256:none")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    built = commit_file(repo, "verification/photo_inbox/app.py", "one\n")
    os.environ.update(INBOX_COMMIT=built, INBOX_BUILT_AT="2026-11-25T10:00:00Z")
    try:
        client = create_app(Path(temp) / "version-inbox", repo, published).test_client()
        found = client.get("/version").get_json()
        assert found["code"] == {"commit": built, "date": "2026-11-25T10:00:00Z", "source": "image"}, found
        assert found["data"]["commit"] == built and found["photos"] is None and found["codeChanged"] is False
        page = client.get("/").get_data(as_text=True)
        assert built[:7] in page and "Code aktuell" in page and "Fotos: unbekannt" in page, page
        import toolchain  # #681: the running tools against the accepted ones, in /version and the line
        assert found["tools"] == toolchain.report(), found["tools"]
        assert ("Werkzeuge wie abgenommen" if found["tools"]["matches"] else "Werkzeuge weichen ab") in page
        data = commit_file(repo, "data/printings.json", "{}\n")
        found = client.get("/version").get_json()
        assert found["data"]["commit"] == data and found["codeChanged"] is False, "a data commit needs no rebuild"
        commit_file(repo, "verification/check.py", "two\n")
        assert client.get("/version").get_json()["codeChanged"] is True, "a code commit needs a rebuild"
        assert "neu bauen" in client.get("/").get_data(as_text=True)
        os.environ.update(INBOX_COMMIT="0" * 40, INBOX_BUILT_AT="")
        assert client.get("/version").get_json()["code"]["commit"] == built, "the code is read once at start"
        unknown = create_app(Path(temp) / "version-inbox", repo, published).test_client()
        assert unknown.get("/version").get_json()["codeChanged"] is None, "an unknown commit is unknown"
        page = unknown.get("/")
        assert page.status_code == 200 and "0000000</a>" in page.get_data(as_text=True), "no build date is no error"
    finally:
        os.environ.pop("INBOX_COMMIT", None)
        os.environ.pop("INBOX_BUILT_AT", None)
    assert create_app(Path(temp) / "version-inbox").test_client().get("/version").get_json()["code"]["source"] == "checkout"


def main():
    refuses_checkout()
    with TemporaryDirectory() as temp:
        version_checks(temp)
    with TemporaryDirectory() as temp:
        derive_checks(temp)
        root = Path(temp) / "inbox"
        photo, digest = api_checks(root)
        repo, filed = overview_checks(root, temp)
        guard_checks(Path(temp) / "guard", catalogue_repo(Path(temp) / "guard-repo", "sha256:none"))
        trash_checks(root, create_app(root, repo, published).test_client(), digest, filed)
        corner_checks(Path(temp) / "corners", catalogue_repo(Path(temp) / "corners-repo", "sha256:none"))
        command = posts_checks(root, repo, temp)
        names = ("again.jpg", "new.dng", "notes.txt", "new.jpg")
        bodies = (photo, dng_with_preview(jpeg((5, 6, 7), size=(48, 64))), b"not a photo", jpeg((9, 9, 9)))
        files = []
        for name, body in zip(names, bodies):
            files.append(Path(temp) / name)
            files[-1].write_bytes(body)
        browser_checks(root, files, repo, command, Path(temp))
        posting_checks(root, repo, temp, command)
        queue_checks(temp)
        runs_checks(temp)
        permalink_checks(temp)
    print("photo inbox: all checks passed")


if __name__ == "__main__":
    main()

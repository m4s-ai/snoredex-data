"""Receive the owner's own JPEG or DNG photos in a private local inbox, then describe them.

Upload and card assignment are separate (#639): photos arrive without details, and a dashboard
lists every job with a preview and saves its SPEC number, note or exact printing. A job that has not
been filed as a specimen can be moved to a trash, restored from it, or deleted for good; the trash
empties itself after 30 days. With a catalogue checkout, an overview shows every printing and how
far its own photo has come (#641). Every photo here is the owner's own; images found elsewhere go
through the regular specimen intake, never through this inbox.
"""

from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
import json
from math import dist
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import threading
from tempfile import TemporaryDirectory

from flask import Flask, abort, jsonify, render_template, request, send_file
from PIL import Image, ImageOps
from waitress import serve

import corners as card_corners
from dng import dng_preview
import number_check
from overview import ITEM_ID, Catalogue
import posting
import runner as intake_runner

# an iPhone ProRAW DNG at 48 megapixels is often 75-100 MB
MAX_UPLOAD = 200 * 1024 * 1024
CHUNK = 64 * 1024
DNG_VERSION_TAG = 50706
JOB_ID = re.compile(r"[0-9a-f]{64}")
PREVIEW_SIZES = (400, 1600)
# hidden, and never read by intake: it takes job folders named by their hash only
TRASH = ".trash"
DRAFTS = ".drafts"  # Instagram drafts, rebuilt from the checkout; intake reads hash folders only
KEEP_DELETED = timedelta(days=30)
BUSY = ("queued", "running", "done")  # an intake run in these states gets no new start (#659)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def private_directory(directory):
    root = directory.resolve()
    if any((ancestor / ".git").exists() for ancestor in (root, *root.parents)):
        raise ValueError("Der Eingang muss außerhalb aller Git-Checkouts liegen.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def description(form, items=None):
    """The card details for one job, checked like the single upload always was, plus its printing."""
    specimen = str(form.get("specimen") or "").strip().upper()
    note = str(form.get("note") or "").strip()
    item = str(form.get("itemId") or "").strip()
    if specimen and not re.fullmatch(r"SPEC-[0-9]{4,8}", specimen):
        raise ValueError("Gib die SPEC-Nummer im Format SPEC-0774 ein.")
    if item and (not ITEM_ID.fullmatch(item) or items is None or item not in items):
        raise ValueError("Wähle den Druck aus der Liste des Katalogs.")
    if not (specimen or note or item) or len(note) > 240:
        raise ValueError("Gib die SPEC-Nummer, den Druck oder eine kurze Notiz zur Karte an (bis 240 Zeichen).")
    return {"specimenHint": specimen or None, "note": note, "itemId": item or None}


def check_jpeg(path):
    try:
        with Image.open(path, formats=("JPEG",)) as image:
            if image.width * image.height > 60_000_000:
                raise ValueError("Das JPEG darf bis zu 60 Megapixel groß sein.")
            image.load()
    except (OSError, Image.DecompressionBombError) as error:
        raise ValueError("Bitte wähle ein vollständiges JPEG-Foto.") from error


def is_dng(photo):
    """A TIFF whose first IFD carries DNGVersion, as the DNG specification requires."""
    order = {b"II*\0": "<", b"MM\0*": ">"}.get(photo.read(4))
    if not order:
        return False
    try:
        photo.seek(struct.unpack(order + "I", photo.read(4))[0])
        count = struct.unpack(order + "H", photo.read(2))[0]
        entries = photo.read(12 * count)
        if len(entries) < 12 * count:
            return False
        tags = {struct.unpack_from(order + "H", entries, 12 * index)[0] for index in range(count)}
    except (struct.error, OSError, ValueError):
        return False
    # ponytail: header-level check only; a raw decoder at intake proves the pixel data
    return DNG_VERSION_TAG in tags


def photo_kind(path):
    with path.open("rb") as photo:
        if photo.read(3) == b"\xff\xd8\xff":
            check_jpeg(path)
            return "jpg"
        photo.seek(0)
        if is_dng(photo):
            return "dng"
    raise ValueError("Bitte wähle ein JPEG- oder DNG-Foto.")


def write_photo(stream, folder):
    digest = sha256()
    upload = folder / "upload"
    with upload.open("xb") as photo:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
            photo.write(chunk)
    name = "photo." + photo_kind(upload)
    upload.rename(folder / name)
    return digest.hexdigest(), name


def write_json(path, data):
    """Replace a job record in one step, so a crash leaves the old or the new one."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def receive(root, stream):
    """Store one photo as its own job; the job is the bytes, so a repeat is the same job."""
    with TemporaryDirectory(prefix=".incoming-", dir=root) as temp:
        staged = Path(temp) / "job"
        staged.mkdir(mode=0o700)
        digest, name = write_photo(stream, staged)
        receipt = {"id": digest, "status": "received", "file": name, "sha256": digest, "ownPhoto": True,
                   "specimenHint": None, "note": "", "receivedAt": now()}
        write_json(staged / "job.json", receipt)
        try:
            staged.rename(root / digest)
        except OSError:
            if not (root / digest).is_dir():
                raise
            return {"id": digest, "status": "received", "existing": True}
    # the photo is back, so its deleted copy is no longer needed
    shutil.rmtree(root / TRASH / digest, ignore_errors=True)
    return {"id": digest, "status": "received", "existing": False}


def job_folder(root, job_id):
    folder = root / job_id
    if not JOB_ID.fullmatch(job_id) or not (folder / "job.json").is_file():
        abort(404)
    return folder


def job_summary(folder, catalogue=None):
    job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
    received = job.get("receivedAt") or datetime.fromtimestamp(
        (folder / "job.json").stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    filed = catalogue.filed_as(folder) if catalogue else None
    if filed:
        adopt_filing(folder, job, received, filed, catalogue.filed_item(filed))
    described = bool(job.get("specimenHint") or job.get("note") or job.get("itemId"))
    return dict(job, receivedAt=received, described=described, filedAs=filed)


def adopt_filing(folder, job, received, specimen, item_id):
    """A filed job takes its SPEC and printing from the catalogue, again whenever the catalogue
    reassigns them; a printing the catalogue cannot name unambiguously keeps the job's own pick."""
    adopted = {"specimenHint": specimen, **({"itemId": item_id} if item_id else {})}
    if any(job.get(key) != value for key, value in adopted.items()):
        job.update(adopted, receivedAt=received, describedAt=now())
        write_json(folder / "job.json", job)


def all_jobs(root, catalogue=None):
    folders = [path for path in root.iterdir() if JOB_ID.fullmatch(path.name) and (path / "job.json").is_file()]
    jobs = (job_summary(folder, catalogue) for folder in folders)
    return sorted(jobs, key=lambda job: job["receivedAt"], reverse=True)


def keep_filed(folder, catalogue):
    """The one guard of every way a job is lost: a filed job keeps its private original."""
    if catalogue is None:
        raise PermissionError("Ohne Katalog kann der Eingang nicht prüfen, ob das Foto schon übernommen ist.")
    filed = catalogue.filed_as(folder)
    if filed:
        raise PermissionError(f"Das Foto ist schon als {filed} übernommen und bleibt erhalten.")


def empty_trash(trash, catalogue):
    """Delete for good what has lain in the trash for longer than 30 days, except a filed job."""
    limit = datetime.now(timezone.utc) - KEEP_DELETED
    for job in all_jobs(trash):
        if datetime.fromisoformat(job.get("deletedAt") or job["receivedAt"]) < limit:
            try:
                keep_filed(trash / job["id"], catalogue)
            except PermissionError:
                continue
            shutil.rmtree(trash / job["id"])


def to_trash(root, folder, catalogue):
    """Move one job out of the inbox, unless intake may already have filed it."""
    keep_filed(folder, catalogue)
    job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
    write_json(folder / "job.json", dict(job, receivedAt=job_summary(folder)["receivedAt"], deletedAt=now()))
    trash = root / TRASH
    trash.mkdir(mode=0o700, exist_ok=True)
    shutil.rmtree(trash / folder.name, ignore_errors=True)
    folder.rename(trash / folder.name)


def preview(folder, size):
    """A small JPEG of the job's photo: upright, without Exif or XMP, kept beside the job."""
    cached = folder / f"preview-{size}.jpg"
    if not cached.is_file():
        photo = next(folder.glob("photo.*"))
        data = photo.read_bytes()
        try:
            source = dng_preview(data) if photo.suffix == ".dng" else data
        except (ValueError, KeyError, struct.error):
            abort(404)
        with Image.open(BytesIO(source)) as image:
            upright = ImageOps.exif_transpose(image).convert("RGB")
            profile = image.info.get("icc_profile")
        upright.thumbnail((size, size), Image.Resampling.LANCZOS)
        out = BytesIO()
        upright.save(out, "JPEG", quality=85, icc_profile=profile)
        cached.with_suffix(".tmp").write_bytes(out.getvalue())
        os.replace(cached.with_suffix(".tmp"), cached)
    return cached


def source_photo(folder):
    """The photo the archive copy is made of: a DNG's embedded full-size preview, or the JPEG itself."""
    photo = next(folder.glob("photo.*"))
    data = photo.read_bytes()
    try:
        return dng_preview(data) if photo.suffix == ".dng" else data
    except (ValueError, KeyError, struct.error):
        abort(404)


def suggested_corners(folder):
    """Card quads in the upright full-size photo, the coordinates intake uses; cached beside the job."""
    cached = folder / "corners-suggested.json"
    if not cached.is_file():
        with Image.open(BytesIO(source_photo(folder))) as image:
            upright = ImageOps.exif_transpose(image)
            found = {"size": list(upright.size), "candidates": card_corners.suggest(upright)}
        write_json(cached, found)
    return json.loads(cached.read_text(encoding="utf-8"))


def approved_corners(value, size):
    """Four [x, y] pairs clockwise from top left inside the photo, framing a card wide enough for the gallery."""
    try:
        quad = [[int(x), int(y)] for x, y in value]
    except (TypeError, ValueError):
        quad = []
    if len(quad) != 4 or any(not (0 <= x < size[0] and 0 <= y < size[1]) for x, y in quad):
        raise ValueError("Die Ecken müssen alle vier im Foto liegen.")
    turn = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(quad, quad[1:] + quad[:1]))
    if turn <= 0:
        raise ValueError("Die Ecken stehen nicht im Uhrzeigersinn ab oben links.")
    # the face as gallery_prepare.extract measures it, so an approval is one intake can crop
    width = int(min(dist(quad[0], quad[1]), dist(quad[3], quad[2])))
    height = int(min(dist(quad[0], quad[3]), dist(quad[1], quad[2])))
    if width < 600:
        raise ValueError("Die Karte ist im Foto schmaler als 600 Pixel. Bitte näher fotografieren.")
    if height <= width:
        raise ValueError("Die Ecken ergeben keine hochkant stehende Karte. Bitte die Ecken prüfen.")
    return quad


def repository_modules():
    root = Path(__file__).resolve().parents[2]
    for path in (root / "scripts", root / "verification"):
        if str(path) not in sys.path:
            sys.path.append(str(path))


def cover(folder, quad):
    """The post's title image from these corners, as the Instagram exporter makes it."""
    repository_modules()
    from instagram_package import post_image

    return post_image(source_photo(folder), [tuple(pair) for pair in quad])[0]


def number_reading(folder, quad, item, language):
    """The collector number read from the card face these corners frame, against the printing (#658)."""
    repository_modules()
    from gallery_prepare import extract

    with Image.open(BytesIO(source_photo(folder))) as image:
        face, _ = extract(ImageOps.exif_transpose(image).convert("RGB"), [tuple(pair) for pair in quad])
    found = number_check.check(face, item.get("collectorNumber"), item.get("collectorNumberDenominator"), language)
    return dict(found, itemId=item["itemId"], checkedAt=now())


def restore(root, folder):
    if (root / folder.name).exists():
        raise PermissionError("Dieses Foto ist schon wieder im Eingang.")
    job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
    job.pop("deletedAt", None)
    write_json(folder / "job.json", job)
    folder.rename(root / folder.name)


def exporter(repo):
    """The checkout's own Instagram exporter, which reads that checkout's data (#625)."""
    return [sys.executable, str(Path(repo) / "verification" / "instagram_package.py")]


def draft(cache, command, photos, specimen, stamp):
    """The post draft of one specimen, built once per catalogue state into the private data folder."""
    key = sha256(repr((stamp, specimen)).encode()).hexdigest()[:16]
    folder = cache / f"{specimen}-{key}"
    if not (folder / "manifest.json").is_file():
        try:
            done = subprocess.run([*command, specimen, "--photos", str(photos), "--out", str(folder)],
                                  capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError(f"Der Entwurf ließ sich nicht bauen: {error}") from error
        if done.returncode:
            lines = (done.stderr or done.stdout).strip().splitlines()
            raise ValueError(lines[-1] if lines else "Der Entwurf ließ sich nicht bauen.")
        for old in cache.glob(f"{specimen}-*"):  # drafts of an older catalogue state
            if old != folder:
                shutil.rmtree(old, ignore_errors=True)
    return folder


def post_view(row, folder):
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    image = f"/posts/{row['draftSpecimen']}/image"
    slides = [{"image": f"{image}?n={number}",
               "alt": (folder / posting.alt_name(name)).read_text(encoding="utf-8").strip()}
              for number, name in enumerate(posting.slides(folder), start=1)]
    return dict(row, caption=(folder / "caption-draft.txt").read_text(encoding="utf-8"),
                alt=slides[0]["alt"], slides=slides, draft=folder.name,
                open=manifest["requiredBeforePosting"], image=image)


def frozen_view(row, order):
    """An ordered post as it goes out: the caption, images and alt texts its order froze."""
    image = f"/posts/{row['draftSpecimen']}/image"
    slides = [{"image": f"{image}?n={number}", "alt": frozen["alt"]}
              for number, frozen in enumerate(order["images"], start=1)]
    return dict(row, caption=order["caption"] + "\n", alt=slides[0]["alt"], slides=slides, draft=order["draft"],
                open=[], image=image)


def security_headers(response, image_origin):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    images = " ".join(filter(None, ("'self'", image_origin)))
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; img-src {images}; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    return response


# what the image copies of the repository: a change here on main needs a rebuild (#666)
CODE_PATHS = ("scripts", "verification/photo_inbox", ":(glob)verification/*.py")


def git_output(checkout, *args):
    """git's exit code and output in a checkout; None when git cannot run there."""
    try:
        done = subprocess.run(["git", "-C", str(checkout), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.returncode, done.stdout


def head(checkout):
    """A checkout's HEAD commit and its date; None when it is no readable checkout."""
    done = git_output(checkout, "log", "-1", "--format=%H %cI") if checkout else None
    parts = done[1].split() if done and done[0] == 0 else []
    return {"commit": parts[0], "date": parts[1]} if len(parts) == 2 else None


def code_version():
    """The code this process runs, read once at start (#666): the image names the commit it was built
    from (INBOX_COMMIT); run from a checkout, it is that checkout's HEAD at start. Unknown stays None."""
    built = os.environ.get("INBOX_COMMIT")
    if built:
        return {"commit": built, "date": os.environ.get("INBOX_BUILT_AT") or None, "source": "image"}
    return dict(head(Path(__file__).resolve().parents[2]) or {"commit": None, "date": None}, source="checkout")


def running_version(code, repo, photos):
    """The running code and the mounted checkouts as they are now (#666)."""
    changed = None  # whether the synced catalogue checkout carries other inbox code than is running
    if repo and code["commit"]:
        done = git_output(repo, "diff", "--quiet", code["commit"], "HEAD", "--", *CODE_PATHS)
        changed = {0: False, 1: True}.get(done[0]) if done else None
    return {"code": code, "codeChanged": changed, "data": head(repo), "photos": head(photos)}


def intake_blocked(folder, filed):
    """Why the job cannot be filed now, or None when it can (#659): the intake script's own rules."""
    if filed:
        return f"Schon übernommen als {filed}."
    import intake  # loads the repository's modules only where a runner is set up
    try:
        intake.job_input(folder)
    except intake.Refused as error:
        return str(error)
    return None


def run_blocked(folder, filed, run):
    """Why no run may start now, or None. A run that failed after its filing resumes although the
    catalogue already names the job's SPEC: only publishing and the alias are left."""
    if run.get("status") in BUSY:
        return None  # the page shows the run itself
    if run.get("status") == "failed" and "intake" in run.get("done", []):
        return None
    return intake_blocked(folder, filed)


def with_intake(job, folder, runner):
    """A job as the page lists it, with its intake run and whether the button may start one."""
    if runner is None:
        return dict(job, intake=None)
    run = intake_runner.read_state(folder)
    return dict(job, intake={"run": run or None, "blocked": run_blocked(folder, job["filedAs"], run),
                             "locked": intake_runner.assignment_lock(run)})


def refuse_if_locked(folder):
    """D01 (#672): an approval holds for one printing, so a run's printing and corners stay as approved."""
    locked = intake_runner.assignment_lock(intake_runner.read_state(folder))
    if locked:
        raise PermissionError(locked)


def ready_jobs(root, catalogue):
    """The nightly round: every job that may start a run, a failed one included."""
    ready = []
    for job in all_jobs(root, catalogue):
        folder = root / job["id"]
        run = intake_runner.read_state(folder)
        if run.get("status") not in BUSY and not run_blocked(folder, job["filedAs"], run):
            ready.append(job["id"])
    return ready


def create_app(directory, repo=None, fetch=None, photos=None, command=None, uploader=None, schedule=True,
               runner=None):
    root = private_directory(directory)
    (root / posting.POSTS).mkdir(mode=0o700, exist_ok=True)
    queue = threading.Lock()  # the scheduler and the order routes never change an order at once
    if uploader and schedule:
        posting.run_scheduler(root, uploader, queue)
    trash = root / TRASH
    trash.mkdir(mode=0o700, exist_ok=True)
    drafts = root / DRAFTS
    drafts.mkdir(mode=0o700, exist_ok=True)
    catalogue = Catalogue(repo, **({"fetch": fetch} if fetch else {})) if repo else None
    empty_trash(trash, catalogue)
    # catalogue thumbnails come from the published site; the page loads nothing else from outside
    image_origin = "/".join(catalogue.base.split("/")[:3]) if catalogue else ""
    code = code_version()  # a later pull into the checkout does not change the code already imported
    if runner and schedule:
        runner.start()
        runner.nightly(lambda: ready_jobs(root, catalogue))
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD

    @app.after_request
    def private_response(response):
        return security_headers(response, image_origin)

    @app.get("/")
    def index():
        return render_template("index.html", version=running_version(code, repo, photos))

    @app.get("/version")
    def version():
        return jsonify(running_version(code, repo, photos))

    @app.errorhandler(413)
    def upload_limit(_error):
        return jsonify(error="Bitte wähle ein Foto bis 200 MB."), 413

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="Diesen Auftrag gibt es nicht."), 404

    @app.errorhandler(PermissionError)
    def refused(error):
        return jsonify(error=str(error)), 409

    @app.post("/uploads")
    def upload():
        if request.mimetype != "application/octet-stream":
            return jsonify(error="Bitte wähle ein JPEG- oder DNG-Foto."), 415
        try:
            receipt = receive(root, request.stream)
        except ValueError as error:
            return jsonify(error=str(error)), 400
        return jsonify(receipt), 200 if receipt["existing"] else 201

    @app.get("/jobs")
    def jobs():
        listed = [with_intake(job, root / job["id"], runner) for job in all_jobs(root, catalogue)]
        return jsonify(jobs=listed, catalogue=catalogue is not None, intake=runner is not None)

    @app.post("/jobs/<job_id>/intake")
    def start_intake(job_id):
        """The owner's "Übernehmen" (#659): queue the job for the intake run."""
        folder = job_folder(root, job_id)
        if runner is None:
            return jsonify(error="Die Übernahme ist hier nicht eingerichtet."), 503
        job = with_intake(job_summary(folder, catalogue), folder, runner)
        if job["intake"]["blocked"]:
            return jsonify(error=job["intake"]["blocked"]), 409
        if (job["intake"]["run"] or {}).get("status") in BUSY:
            return jsonify(error="Die Übernahme läuft schon oder ist fertig."), 409
        runner.submit(job_id)
        return jsonify(with_intake(job_summary(folder, catalogue), folder, runner)), 202

    @app.get("/<any(jobs, trash):place>/<job_id>/preview")
    def job_preview(place, job_id):
        size = request.args.get("size", type=int)
        if size not in PREVIEW_SIZES:
            abort(404)
        folder = job_folder(root if place == "jobs" else trash, job_id)
        # bytes, not a path: no open handle outlives the response (Windows cannot delete an open file)
        return send_file(BytesIO(preview(folder, size).read_bytes()), mimetype="image/jpeg")

    @app.post("/jobs/<job_id>")
    def describe(job_id):
        folder = job_folder(root, job_id)
        form = request.get_json(silent=True) or {}
        job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
        if (str(form.get("itemId") or "").strip() or None) != job.get("itemId"):
            refuse_if_locked(folder)  # the note and the SPEC hint stay open
        try:
            details = description(form, catalogue.active_items() if catalogue else None)
        except ValueError as error:
            return jsonify(error=str(error)), 400
        if details["itemId"] != job.get("itemId"):  # corners and their check belong to the old printing
            for key in ("corners", "cornersApprovedAt", "numberCheck", "numberConfirmedAt"):
                job.pop(key, None)
        # an older job keeps the upload time it is listed by once its record is rewritten
        job.update(details, receivedAt=job_summary(folder)["receivedAt"], describedAt=now())
        write_json(folder / "job.json", job)
        return jsonify(with_intake(job_summary(folder, catalogue), folder, runner))

    @app.get("/jobs/<job_id>/corners")
    def corner_suggestion(job_id):
        folder = job_folder(root, job_id)
        job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
        return jsonify(dict(suggested_corners(folder), approved=job.get("corners")))

    @app.post("/jobs/<job_id>/corners")
    def approve_corners(job_id):
        """The owner's approval of the card corners intake crops and frames the post with (#657)."""
        folder = job_folder(root, job_id)
        if catalogue and catalogue.filed_as(folder):
            raise PermissionError("Das Foto ist schon übernommen; seine Ecken stehen im Katalog.")
        refuse_if_locked(folder)
        job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
        if not job.get("itemId"):
            return jsonify(error="Ordne dem Foto zuerst einen Druck zu."), 400
        try:
            quad = approved_corners((request.get_json(silent=True) or {}).get("corners"),
                                    suggested_corners(folder)["size"])
        except ValueError as error:
            return jsonify(error=str(error)), 400
        job.update(corners=quad, cornersApprovedAt=now())
        job.pop("numberConfirmedAt", None)  # a new frame is read again, and confirmed again if it must be
        item = catalogue.active_items().get(job["itemId"]) if catalogue else None
        if item:
            job["numberCheck"] = number_reading(folder, quad, item, catalogue.languages.get(item.get("localizationId")))
        write_json(folder / "job.json", job)
        return jsonify(with_intake(job_summary(folder, catalogue), folder, runner))

    @app.post("/jobs/<job_id>/number")
    def confirm_number(job_id):
        """The owner confirms the assignment although the number read differs: intake may go on."""
        folder = job_folder(root, job_id)
        job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
        if (job.get("numberCheck") or {}).get("result") != "mismatch":
            return jsonify(error="Es gibt keine abweichende Nummer zu bestätigen."), 400
        job["numberConfirmedAt"] = now()
        write_json(folder / "job.json", job)
        return jsonify(with_intake(job_summary(folder, catalogue), folder, runner))

    @app.get("/jobs/<job_id>/cover")
    def cover_preview(job_id):
        folder = job_folder(root, job_id)
        values = [int(v) for v in request.args.get("c", "").split(",") if v.strip().isdigit()]
        try:
            quad = approved_corners(list(zip(values[::2], values[1::2])), suggested_corners(folder)["size"])
        except ValueError as error:
            return jsonify(error=str(error)), 400
        return send_file(BytesIO(cover(folder, quad)), mimetype="image/jpeg")

    @app.delete("/jobs/<job_id>")
    def delete(job_id):
        folder = job_folder(root, job_id)
        if intake_runner.read_state(folder).get("status") in ("queued", "running"):
            raise PermissionError("Die Übernahme dieses Fotos läuft gerade.")
        to_trash(root, folder, catalogue)
        return jsonify(id=job_id, status="deleted")

    @app.get("/trash")
    def trashed():
        empty_trash(trash, catalogue)
        return jsonify(jobs=all_jobs(trash, catalogue), keepDays=KEEP_DELETED.days)

    @app.post("/trash/<job_id>/restore")
    def restore_job(job_id):
        restore(root, job_folder(trash, job_id))
        return jsonify(id=job_id, status="received")

    @app.delete("/trash/<job_id>")
    def delete_for_good(job_id):
        folder = job_folder(trash, job_id)
        keep_filed(folder, catalogue)
        shutil.rmtree(folder)
        return jsonify(id=job_id, status="gone")

    @app.get("/overview")
    def overview():
        if catalogue is None:
            return jsonify(error="Die Übersicht braucht einen Katalog (--repo)."), 404
        return jsonify(catalogue.overview(all_jobs(root, catalogue)))

    building = threading.Lock()

    def current_draft(specimen):
        # one build at a time: two requests for an unbuilt draft would race for the same folder
        with building:
            return draft(drafts, command or exporter(repo), photos, specimen, catalogue.stamp)

    @app.get("/posts")
    def posts():
        """The drafts of every printing ready for Instagram or posted, each with its order (#646)."""
        if catalogue is None:
            return jsonify(error="Die Posts brauchen einen Katalog (--repo)."), 404
        if photos is None:
            return jsonify(error="Für die Entwürfe fehlt das Fotoarchiv (--photos)."), 404
        views = []
        for row in catalogue.shares():
            order = posting.read_order(root, row["draftSpecimen"])
            try:
                # an ordered post shows what it froze, which is what goes out, never a newer draft
                view = frozen_view(row, order) if order else post_view(row, current_draft(row["draftSpecimen"]))
                views.append(dict(view, order=posting.order_view(order)))
            except (ValueError, OSError, KeyError) as error:
                views.append(dict(row, error=str(error), order=posting.order_view(order)))
        return jsonify(posts=views, canPost=uploader is not None)

    def shared_specimen(specimen):
        rows = [row for row in catalogue.shares() if row["draftSpecimen"] == specimen] if catalogue and photos else []
        if not rows:
            abort(404)
        return rows[0]

    @app.get("/posts/<specimen>/image")
    def post_image(specimen):
        shared_specimen(specimen)
        folder = posting.order_folder(root, specimen)
        if not (folder / "order.json").is_file():
            try:
                folder = current_draft(specimen)
            except ValueError:
                abort(404)
        names = posting.slides(folder)
        number = request.args.get("n", 1, type=int)
        if not 1 <= number <= len(names):
            abort(404)
        return send_file(BytesIO((folder / names[number - 1]).read_bytes()), mimetype="image/jpeg",
                         download_name=f"{specimen}-{names[number - 1]}")

    # the inbox posts only as SnoreDex on Instagram, its Facebook page and Threads, never to the
    # uploader's other accounts (owner decision 2026-11-25)
    def snoredex_accounts():
        return [account for account in uploader.accounts()
                if account.get("platform") in ("instagram", "facebook_page", "threads")
                and (account.get("displayName") or "").casefold() == "snoredex"]

    @app.get("/accounts")
    def accounts():
        if uploader is None:
            return jsonify(error="Zum Posten fehlt der Uploader (--uploader)."), 404
        try:
            return jsonify(accounts=[{key: account.get(key) for key in ("id", "platform", "displayName")}
                                     for account in snoredex_accounts()])
        except posting.UploaderError as error:
            return jsonify(error=str(error)), 502

    @app.post("/posts/<specimen>/order")
    def place_order(specimen):
        """Only the owner's click lands here: post now, or at the time they chose."""
        row = shared_specimen(specimen)
        if uploader is None:
            return jsonify(error="Zum Posten fehlt der Uploader (--uploader)."), 404
        body = request.get_json(silent=True) or {}
        try:
            folder = current_draft(specimen)
            if body.get("draft") != folder.name:
                raise PermissionError("Der Entwurf hat sich geändert. Bitte die neue Fassung prüfen.")
            known = {account["id"] for account in snoredex_accounts()}
            with queue:
                order = posting.place_order(root, specimen, row, folder, body.get("accounts"), known, body.get("at"))
        except (ValueError, posting.UploaderError) as error:
            return jsonify(error=str(error)), 400
        return jsonify(order=posting.order_view(order)), 201

    @app.delete("/posts/<specimen>/order")
    def cancel_order(specimen):
        with queue:
            try:
                posting.cancel_order(root, specimen)
            except LookupError:
                abort(404)
        return jsonify(status="cancelled")

    @app.post("/posts/<specimen>/retry")
    def retry(specimen):
        with queue:
            try:
                order = posting.retry_target(root, specimen, (request.get_json(silent=True) or {}).get("account"))
            except LookupError:
                abort(404)
        return jsonify(order=posting.order_view(order))

    return app


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="private persistent folder outside Git")
    parser.add_argument("--host", default="127.0.0.1", help="0.0.0.0 makes it reachable in the home network")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--repo", type=Path, help="checkout of snoredex-data main for the overview and the trash")
    parser.add_argument("--photos", type=Path, help="checkout of snoredex-photos for the Instagram drafts")
    parser.add_argument("--uploader", help="base URL of the owner's uploader; its key comes from UPLOADER_KEY")
    args = parser.parse_args()
    key = os.environ.get("UPLOADER_KEY")
    if args.uploader and not key:
        parser.error("--uploader braucht den Schlüssel in UPLOADER_KEY")
    # the intake run only with both accesses (#659); compose mounts /dev/null where no key is set
    token, deploy_key = os.environ.get("INTAKE_GITHUB_TOKEN"), os.environ.get("PHOTOS_DEPLOY_KEY")
    deploy_key = deploy_key if deploy_key and Path(deploy_key).is_file() else None
    try:
        app = create_app(args.data_dir, args.repo, photos=args.photos,
                         uploader=posting.Uploader(args.uploader, key) if args.uploader else None,
                         runner=intake_runner.Runner(args.data_dir, intake_runner.GitHub(token), deploy_key)
                         if token and deploy_key else None)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    serve(app, host=args.host, port=args.port, threads=2, inbuf_overflow=MAX_UPLOAD + CHUNK,
          max_request_body_size=MAX_UPLOAD)


if __name__ == "__main__":
    main()

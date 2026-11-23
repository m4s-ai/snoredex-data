"""Receive the owner's own JPEG or DNG photos in a private local inbox, then describe them.

Upload and card assignment are separate (#639): photos arrive without details, and a dashboard
lists every job with a preview and saves its SPEC number or note. Every photo here is the owner's
own; images found elsewhere go through the regular specimen intake, never through this inbox.
"""

from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import struct
from tempfile import TemporaryDirectory

from flask import Flask, abort, jsonify, render_template, request, send_file
from PIL import Image, ImageOps
from waitress import serve

from dng import dng_preview

# an iPhone ProRAW DNG at 48 megapixels is often 75-100 MB
MAX_UPLOAD = 200 * 1024 * 1024
CHUNK = 64 * 1024
DNG_VERSION_TAG = 50706
JOB_ID = re.compile(r"[0-9a-f]{64}")
PREVIEW_SIZES = (400, 1600)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def private_directory(directory):
    root = directory.resolve()
    if any((ancestor / ".git").exists() for ancestor in (root, *root.parents)):
        raise ValueError("Der Eingang muss außerhalb aller Git-Checkouts liegen.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def description(form):
    """The card details for one job, checked like the single upload always was."""
    specimen = str(form.get("specimen") or "").strip().upper()
    note = str(form.get("note") or "").strip()
    if specimen and not re.fullmatch(r"SPEC-[0-9]{4,8}", specimen):
        raise ValueError("Gib die SPEC-Nummer im Format SPEC-0774 ein.")
    if not (specimen or note) or len(note) > 240:
        raise ValueError("Gib die SPEC-Nummer oder eine kurze Notiz zur Karte an (bis 240 Zeichen).")
    return {"specimenHint": specimen or None, "note": note}


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
    return {"id": digest, "status": "received", "existing": False}


def job_folder(root, job_id):
    folder = root / job_id
    if not JOB_ID.fullmatch(job_id) or not (folder / "job.json").is_file():
        abort(404)
    return folder


def job_summary(folder):
    job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
    received = job.get("receivedAt") or datetime.fromtimestamp(
        (folder / "job.json").stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    return dict(job, receivedAt=received, described=bool(job.get("specimenHint") or job.get("note")))


def all_jobs(root):
    folders = [path for path in root.iterdir() if JOB_ID.fullmatch(path.name) and (path / "job.json").is_file()]
    return sorted((job_summary(folder) for folder in folders), key=lambda job: job["receivedAt"], reverse=True)


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


def create_app(directory):
    root = private_directory(directory)
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD

    @app.after_request
    def private_response(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(413)
    def upload_limit(_error):
        return jsonify(error="Bitte wähle ein Foto bis 200 MB."), 413

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="Diesen Auftrag gibt es nicht."), 404

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
        return jsonify(jobs=all_jobs(root))

    @app.get("/jobs/<job_id>/preview")
    def job_preview(job_id):
        size = request.args.get("size", type=int)
        if size not in PREVIEW_SIZES:
            abort(404)
        # bytes, not a path: no open handle outlives the response (Windows cannot delete an open file)
        return send_file(BytesIO(preview(job_folder(root, job_id), size).read_bytes()), mimetype="image/jpeg")

    @app.post("/jobs/<job_id>")
    def describe(job_id):
        folder = job_folder(root, job_id)
        try:
            details = description(request.get_json(silent=True) or {})
        except ValueError as error:
            return jsonify(error=str(error)), 400
        job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
        # an older job keeps the upload time it is listed by once its record is rewritten
        job.update(details, receivedAt=job_summary(folder)["receivedAt"], describedAt=now())
        write_json(folder / "job.json", job)
        return jsonify(job_summary(folder))

    return app


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="private persistent folder outside Git")
    parser.add_argument("--host", default="127.0.0.1", help="0.0.0.0 makes it reachable in the home network")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        app = create_app(args.data_dir)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    serve(app, host=args.host, port=args.port, threads=2, inbuf_overflow=MAX_UPLOAD + CHUNK,
          max_request_body_size=MAX_UPLOAD)


if __name__ == "__main__":
    main()

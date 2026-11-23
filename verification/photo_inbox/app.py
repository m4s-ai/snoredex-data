"""Receive owner JPEG or DNG photos in a private local inbox without publishing them."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
from tempfile import TemporaryDirectory
from urllib.parse import unquote

from flask import Flask, jsonify, render_template, request
from PIL import Image
from waitress import serve


# an iPhone ProRAW DNG at 48 megapixels is often 75-100 MB
MAX_UPLOAD = 200 * 1024 * 1024
CHUNK = 64 * 1024
DNG_VERSION_TAG = 50706


class ExistingJob(ValueError):
    """The same bytes are already associated with different intake details."""


def private_directory(directory):
    root = directory.resolve()
    if any((ancestor / ".git").exists() for ancestor in (root, *root.parents)):
        raise ValueError("Der Eingang muss außerhalb aller Git-Checkouts liegen.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def submission(headers):
    if headers.get("X-Snoredex-Owner") != "yes":
        raise ValueError("Bitte bestätige, dass du das Foto selbst aufgenommen hast.")
    specimen = headers.get("X-Snoredex-Specimen", "").strip().upper()
    note = unquote(headers.get("X-Snoredex-Note", ""), errors="strict").strip()
    if specimen and not re.fullmatch(r"SPEC-[0-9]{4,8}", specimen):
        raise ValueError("Gib die SPEC-Nummer im Format SPEC-0774 ein.")
    if not (specimen or note) or len(note) > 240:
        raise ValueError("Gib die SPEC-Nummer oder eine kurze Notiz zur Karte an.")
    return {"specimenHint": specimen or None, "note": note, "ownPhoto": True}


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


def receive(root, stream, details):
    with TemporaryDirectory(prefix=".incoming-", dir=root) as temp:
        staged = Path(temp) / "job"
        staged.mkdir(mode=0o700)
        digest, name = write_photo(stream, staged)
        receipt = dict(details, id=digest, status="received", file=name, sha256=digest)
        (staged / "job.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                                         newline="\n")
        final = root / digest
        try:
            staged.rename(final)
        except OSError:
            if not final.is_dir():
                raise
            existing = json.loads((final / "job.json").read_text(encoding="utf-8"))
            if existing != receipt:
                raise ExistingJob("Dieses Foto liegt bereits mit anderen Angaben im Eingang.") from None
            return {"id": digest, "status": "received", "existing": True}
    return {"id": digest, "status": "received", "existing": False}


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

    @app.post("/uploads")
    def upload():
        if request.mimetype != "application/octet-stream":
            return jsonify(error="Bitte wähle ein JPEG- oder DNG-Foto."), 415
        try:
            receipt = receive(root, request.stream, submission(request.headers))
        except ExistingJob as error:
            return jsonify(error=str(error)), 409
        except ValueError as error:
            return jsonify(error=str(error)), 400
        return jsonify(receipt), 200 if receipt["existing"] else 201

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

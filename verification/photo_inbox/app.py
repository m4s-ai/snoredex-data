"""Receive owner JPEGs in a private local inbox without publishing them."""

from argparse import ArgumentParser
from hashlib import sha256
from hmac import compare_digest
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from urllib.parse import unquote

from flask import Flask, jsonify, render_template, request
from PIL import Image
from waitress import serve


MAX_UPLOAD = 24 * 1024 * 1024
CHUNK = 64 * 1024


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


def write_jpeg(stream, path):
    digest = sha256()
    with path.open("xb") as photo:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
            photo.write(chunk)
    try:
        with Image.open(path, formats=("JPEG",)) as image:
            if image.width * image.height > 60_000_000:
                raise ValueError("Das JPEG darf bis zu 60 Megapixel groß sein.")
            image.load()
    except (OSError, Image.DecompressionBombError) as error:
        raise ValueError("Bitte wähle ein vollständiges JPEG-Foto.") from error
    return digest.hexdigest()


def receive(root, stream, details):
    with TemporaryDirectory(prefix=".incoming-", dir=root) as temp:
        staged = Path(temp) / "job"
        staged.mkdir(mode=0o700)
        digest = write_jpeg(stream, staged / "photo.jpg")
        receipt = dict(details, id=digest, status="received", file="photo.jpg", sha256=digest)
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


def create_app(directory, token):
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
        return jsonify(error="Bitte wähle ein JPEG bis 24 MB."), 413

    @app.post("/uploads")
    def upload():
        supplied = request.headers.get("Authorization", "")
        if not compare_digest(supplied.encode(), f"Bearer {token}".encode()):
            return jsonify(error="Der Upload-Code stimmt nicht."), 401
        if request.mimetype != "application/octet-stream":
            return jsonify(error="Bitte wähle ein JPEG-Foto."), 415
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
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    token = os.environ.get("SNOREDEX_INBOX_TOKEN", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", token):
        parser.error("SNOREDEX_INBOX_TOKEN braucht 16–128 Buchstaben, Ziffern, Bindestriche oder Unterstriche.")
    try:
        app = create_app(args.data_dir, token)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    serve(app, host=args.host, port=args.port, threads=2, inbuf_overflow=MAX_UPLOAD + CHUNK,
          max_request_body_size=MAX_UPLOAD)


if __name__ == "__main__":
    main()

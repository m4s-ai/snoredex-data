#!/usr/bin/env python3
"""File a photograph into the specimen registry, from a local file or a reachable URL.

WHY THIS EXISTS

`specimens.json` has carried `photograph: null` on all six records since #32, and
`scripts/source_registry.py` still holds a note saying the `inspected-specimen` provider can be
renamed back to `photographed-specimen` "once images land in verification/specimens/". They have
not landed, and the reason is transport, not policy: the owner supplies card photographs by
dragging them into a GitHub issue, and the URL GitHub mints for that is unreachable from an agent
session.

    $ curl -sS https://github.com/user-attachments/assets/<uuid>
    {"message":"This GitHub API path is not available: sessions are bound to their configured
     repositories. Use repository-scoped endpoints (repos/{owner}/{repo}/...)."}

That 403 is the agent proxy, not GitHub. The block is not a permission failure — this repository
is public and the asset is world-readable in a browser — it is that the attachment namespace has
no entry in the proxy's allowlist. Note the older, *repository-scoped* attachment form
(`github.com/{owner}/{repo}/assets/{userid}/{uuid}`) is refused by the same rule, so "add the repo
to the path" is not a workaround. What is reachable, verified by probe:

    raw.githubusercontent.com                 302 -> 200
    objects.githubusercontent.com             reaches origin
    private-user-images.githubusercontent.com reaches origin
    user-images.githubusercontent.com         reaches origin
    github.com/{owner}/{repo}/releases/download/...  reaches origin
    github.com/{owner}/{repo}/... (HTML)      200

So an attachment URL cannot be resolved here, but every channel it would have redirected *to* can.
This script takes the bytes from whichever of those routes they arrived by — most often a file
already committed to a branch — validates them, and records them against a specimen id.

Committing the image is the right end state regardless of the proxy. Rule 1 in CLAUDE.md files a
marketplace listing photograph as a SPEC record rather than a bare link because "listings are
deleted and the observation has to outlive them"; a GitHub attachment is exactly as perishable,
and it disappears with the issue. `--attachment-url` keeps the original URL as provenance while
the repository keeps the bytes.

WHAT IT ENFORCES

Checks S9 and S10 in `review_findings.py` already guard the result: a declared photograph must
exist and decode, and a file nobody references is a finding. This script is the write side of
that contract and refuses anything those checks would reject, plus two they cannot express — a
truncated download, and an image too small to read a card off.

Accepted formats are PNG and JPEG only. `scripts/publish.py` also allowlists `.webp` for the
directory, but `image_format` in `review_findings.py` recognises PNG and JPEG magic alone, so a
committed `.webp` would fail S9. The narrower set is the one that passes the gate.

USAGE

    python verification/fetch_attachment.py --list
    python verification/fetch_attachment.py --specimen SPEC-0001 --from ~/SPEC-0001.jpg \
        --attachment-url https://github.com/user-attachments/assets/<uuid>
    python verification/fetch_attachment.py --specimen SPEC-0001 --from <reachable-url> --dry-run

Idempotent in the sense that matters: re-filing identical bytes for a specimen that already
declares them is a no-op, and replacing a different photograph requires `--replace`.

Exit codes: 0 success or no-op, 1 usage or validation failure, 2 the source could not be reached
(matching `verify_finish_sources.py` and `finishes.py` — the artifacts are not wrong, the upstream
bytes are missing, so retry rather than investigate).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
VERIFICATION = ROOT / "verification"
SPECIMENS_JSON = VERIFICATION / "specimens.json"
SPECIMEN_DIR = VERIFICATION / "specimens"

# Kept in step with `image_format` in review_findings.py deliberately: a format this cannot name is
# a format check S9 will reject after the file is committed.
IMAGE_MAGIC = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpg"}

MAX_BYTES = 25 * 1024 * 1024
MIN_LONG_EDGE = 200  # a card photograph; an avatar or a placeholder is not one
TIMEOUT = 30
USER_AGENT = "snoredex-data/fetch_attachment (+https://github.com/m4s-ai/snoredex-data)"

# The one namespace the proxy refuses, in both the current and the historical form. Detected by
# hand so the failure is a sentence a person can act on rather than an opaque 403.
BLOCKED_HOSTS = {"github.com", "www.github.com"}


class SourceUnreachable(Exception):
    """The bytes could not be retrieved. Distinct from bytes that arrived and were rejected."""


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


# --------------------------------------------------------------------------------------------- #
# Acquiring the bytes
# --------------------------------------------------------------------------------------------- #

def is_attachment_url(url: str) -> bool:
    """Whether this is a GitHub comment attachment, which no route from here can resolve."""
    parts = urlparse(url)
    if parts.hostname not in BLOCKED_HOSTS:
        return False
    segments = [s for s in parts.path.split("/") if s]
    # github.com/user-attachments/assets/<uuid>  and  github.com/<owner>/<repo>/assets/<uid>/<uuid>
    return segments[:1] == ["user-attachments"] or "assets" in segments[:3]


ATTACHMENT_GUIDANCE = """\
That is a GitHub comment attachment URL, and it cannot be resolved from an agent session: the
proxy refuses the whole `assets` namespace on github.com, in the repository-scoped form too. The
403 is not about permissions — this repository is public and the image opens fine in a browser.

Three routes get the bytes here instead, best first:

  1. Commit the image to a branch, then point --from at the working-tree path (or at its
     raw.githubusercontent.com URL). This is the end state anyway: the file has to live in
     verification/specimens/ for checks S9 and S10, and an attachment outlives neither the issue
     nor a repository migration.
  2. Attach it to a GitHub Release — github.com/{owner}/{repo}/releases/download/... is reachable.
  3. Open the attachment in a browser and copy the URL it lands on. It resolves to
     private-user-images.githubusercontent.com, which is reachable, but the signed token expires
     in minutes, so this works only immediately.

Whichever route supplies the bytes, pass the original attachment URL as --attachment-url so the
record keeps its provenance."""


def read_local(path: Path) -> bytes:
    if not path.is_file():
        fail(f"{path} is not a file")
    if path.stat().st_size > MAX_BYTES:
        fail(f"{path} is larger than the {MAX_BYTES // 1024 // 1024} MiB cap")
    return path.read_bytes()


def download(url: str) -> bytes:
    """Fetch a URL, refusing to treat an error page or an oversized body as an answer."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                raise SourceUnreachable(f"{url} answered HTTP {response.status}")
            blob = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise SourceUnreachable(f"{url} answered HTTP {error.code}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise SourceUnreachable(f"{url} could not be reached: {error}") from error
    if len(blob) > MAX_BYTES:
        raise SourceUnreachable(f"{url} is larger than the {MAX_BYTES // 1024 // 1024} MiB cap")
    if not blob:
        raise SourceUnreachable(f"{url} returned an empty body")
    return blob


def acquire(source: str) -> bytes:
    """Bytes from a path or a URL. A blocked attachment URL is a usage error, not a retry."""
    if "://" not in source:
        return read_local(Path(source).expanduser())
    if is_attachment_url(source):
        print(ATTACHMENT_GUIDANCE, file=sys.stderr)
        raise SystemExit(1)
    if urlparse(source).scheme not in {"http", "https"}:
        fail(f"unsupported scheme in {source}")
    return download(source)


# --------------------------------------------------------------------------------------------- #
# Validating them
# --------------------------------------------------------------------------------------------- #

def image_format(data: bytes) -> str | None:
    return next((ext for sig, ext in IMAGE_MAGIC.items() if data.startswith(sig)), None)


def image_complete(data: bytes, ext: str) -> bool:
    """Whether the file carries its own end marker, which a truncated download does not."""
    if ext == "png":
        return data.rstrip().endswith(b"IEND\xaeB`\x82")
    return data.rstrip().endswith(b"\xff\xd9")


def image_size(data: bytes, ext: str) -> tuple[int, int] | None:
    """Dimensions from the header. None when the header is not where it should be."""
    if ext == "png":
        if len(data) < 24 or data[12:16] != b"IHDR":
            return None
        return (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big"))
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            return (int.from_bytes(data[i + 7:i + 9], "big"),
                    int.from_bytes(data[i + 5:i + 7], "big"))
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return None


def validate(blob: bytes, allow_small: bool) -> tuple[str, tuple[int, int] | None]:
    ext = image_format(blob)
    if ext is None:
        head = blob[:16].hex()
        extra = ""
        if blob.lstrip()[:1] in (b"<", b"{"):
            extra = " — it looks like an HTML or JSON error page rather than an image"
        fail(f"not a PNG or JPEG (first bytes {head}){extra}")
    if not image_complete(blob, ext):
        fail(f"the {ext} is truncated — it has no end marker, so the download did not finish")
    size = image_size(blob, ext)
    if size is None:
        fail(f"the {ext} header is malformed — dimensions could not be read")
    if not allow_small and max(size) < MIN_LONG_EDGE:
        fail(f"{size[0]}x{size[1]} is too small to read a card off "
             f"(minimum long edge {MIN_LONG_EDGE}px; pass --allow-small to override)")
    return ext, size


# --------------------------------------------------------------------------------------------- #
# Recording them
# --------------------------------------------------------------------------------------------- #

def load_registry() -> dict:
    return json.loads(SPECIMENS_JSON.read_text(encoding="utf-8"))


def write_registry(doc: dict) -> None:
    # indent=2, ensure_ascii=False and a trailing newline round-trip the committed file exactly, so
    # filing a photograph produces a one-record diff rather than a reformat of the whole store.
    SPECIMENS_JSON.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8", newline="\n")


def with_photograph(specimen: dict, filename: str, provenance: str) -> dict:
    """A copy carrying the photograph fields, with `photographSource` next to `photograph`.

    Rebuilt rather than assigned so a first-time record does not append the provenance after
    `citedBy`, which reads as though the URL belonged to the citation list.
    """
    updated: dict = {}
    for key, value in specimen.items():
        if key == "photographSource":
            continue
        updated[key] = filename if key == "photograph" else value
        if key == "photograph":
            updated["photographSource"] = provenance
    return updated


def describe(specimen: dict) -> str:
    photo = specimen.get("photograph") or "—"
    return (f"{specimen['specimenId']}  {specimen['setCode']:<10} {specimen['number']:<8} "
            f"{specimen['variant']:<5} {specimen['language']:<12} {photo}")


def command_list(doc: dict) -> int:
    specimens = doc["specimens"]
    with_photo = [s for s in specimens if s.get("photograph")]
    print(f"{len(with_photo)} of {len(specimens)} specimens carry a committed photograph\n")
    print(f"{'ID':<11} {'SET':<10} {'NUMBER':<8} {'VAR':<5} {'LANGUAGE':<12} PHOTOGRAPH")
    for specimen in specimens:
        print(describe(specimen))
    return 0


def command_file(doc: dict, args: argparse.Namespace) -> int:
    specimen = next((s for s in doc["specimens"] if s["specimenId"] == args.specimen), None)
    if specimen is None:
        known = ", ".join(s["specimenId"] for s in doc["specimens"])
        fail(f"no specimen {args.specimen} in the registry (known: {known})")

    blob = acquire(args.source)
    ext, size = validate(blob, args.allow_small)

    # The id is the filename. It cannot drift when a record's metadata is corrected, and it makes
    # the S10 pairing between file and registry entry readable without opening either.
    filename = f"{specimen['specimenId']}.{ext}"
    destination = SPECIMEN_DIR / filename

    existing = specimen.get("photograph")
    if existing and not args.replace:
        if existing == filename and destination.is_file() and destination.read_bytes() == blob:
            print(f"{specimen['specimenId']} already carries these exact bytes as {existing} — "
                  f"nothing to do")
            return 0
        fail(f"{specimen['specimenId']} already declares {existing}; pass --replace to overwrite it")

    provenance = args.attachment_url or args.source
    if args.dry_run:
        print(f"DRY RUN — would write {destination.relative_to(ROOT)} "
              f"({len(blob):,} bytes, {size[0]}x{size[1]} {ext})")
        print(f"DRY RUN — would set {specimen['specimenId']}.photograph = {filename!r}")
        print(f"DRY RUN — would set {specimen['specimenId']}.photographSource = {provenance!r}")
        return 0

    SPECIMEN_DIR.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(blob)

    stale = existing and existing != filename
    index = doc["specimens"].index(specimen)
    doc["specimens"][index] = with_photograph(specimen, filename, provenance)
    write_registry(doc)

    print(f"wrote {destination.relative_to(ROOT)} ({len(blob):,} bytes, {size[0]}x{size[1]} {ext})")
    print(f"set {specimen['specimenId']}.photograph = {filename}")
    print(f"set {specimen['specimenId']}.photographSource = {provenance}")
    if stale:
        print(f"NOTE: {existing} is now unreferenced — delete it or S10 will fail")
    print("\nnext:")
    print("  python verification/review_findings.py   # S9/S10 cover the file you just added")
    print("  python scripts/database.py               # specimens.json is an input to the database")
    print("  # first photograph in the repository? scripts/source_registry.py carries a note about")
    print("  # renaming `inspected-specimen` back to `photographed-specimen` once images land.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="File a card photograph into verification/specimens/ against a SPEC id.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="GitHub comment attachment URLs cannot be resolved from an agent session; run with "
               "one to see the routes that work.")
    parser.add_argument("--list", action="store_true",
                        help="show every specimen and whether its photograph is committed")
    parser.add_argument("--specimen", metavar="SPEC-nnnn",
                        help="the specimen the photograph is evidence for")
    parser.add_argument("--from", dest="source", metavar="PATH|URL",
                        help="local path, or a reachable URL, holding the image")
    parser.add_argument("--attachment-url", metavar="URL",
                        help="the original GitHub attachment URL, recorded as provenance")
    parser.add_argument("--replace", action="store_true",
                        help="overwrite a photograph this specimen already declares")
    parser.add_argument("--allow-small", action="store_true",
                        help=f"accept an image whose long edge is under {MIN_LONG_EDGE}px")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate and report without writing anything")
    args = parser.parse_args(argv)

    doc = load_registry()
    if args.list:
        return command_list(doc)
    if not args.specimen or not args.source:
        parser.error("--specimen and --from are both required (or use --list)")

    try:
        return command_file(doc, args)
    except SourceUnreachable as error:
        print(f"UNREACHABLE: {error}", file=sys.stderr)
        print("The bytes are missing, not wrong — retry rather than investigate.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

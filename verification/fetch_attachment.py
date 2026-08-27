#!/usr/bin/env python3
"""File a photograph into the specimen registry, from a local file or a reachable URL.

WHY THIS EXISTS

`specimens.json` historically carried `photograph: null` on the physical records, and
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

So a bare attachment URL cannot be resolved here, but the issue's own HTML exposes the signed
`private-user-images` candidate. `--issue NUMBER --manifest PATH` follows that route for every
manifest row, while the single-specimen mode takes bytes from a local file or any reachable URL.
Both modes validate the image and record it against a stable specimen id.

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
    python verification/fetch_attachment.py --issue 269 --manifest verification/evidence/issue-269.json
    python scripts/regen.py
    python verification/fetch_attachment.py --evidence-check
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
import hashlib
import json
from html.parser import HTMLParser
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parents[1]
VERIFICATION = ROOT / "verification"
SPECIMENS_JSON = VERIFICATION / "specimens.json"
SPECIMEN_DIR = VERIFICATION / "specimens"
FINISH_UNITS = VERIFICATION / "finish_units.json"
AUTHORITATIVE_GRAPH = VERIFICATION / "authoritative_graph.json"

# Kept in step with `image_format` in review_findings.py deliberately: a format this cannot name is
# a format check S9 will reject after the file is committed.
IMAGE_MAGIC = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpg"}

MAX_BYTES = 25 * 1024 * 1024
MIN_LONG_EDGE = 200  # a card photograph; an avatar or a placeholder is not one
TIMEOUT = 30
USER_AGENT = "snoredex-data/fetch_attachment (+https://github.com/m4s-ai/snoredex-data)"
SPECIMEN_ID_PATTERN = re.compile(r"SPEC-\d{4}\Z")
SPECIMEN_FINISHES = {"non-holo", "holo", "reverse-holo", "mirror-holo"}
SPECIMEN_EDITIONS = {"1st Edition", "Unlimited"}
SPECIMEN_MARKING_ROLES = {"print-identity", "reverse-holo-treatment", "distribution-promo"}
SPECIMEN_CARD_SIZES = {"standard", "jumbo", "unknown"}
OWNER_ATTESTABLE_FIELDS = {"finish", "edition"}
DISTRIBUTION_FIELDS = {"kind", "name", "region", "date", "text"}

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


def attachment_candidate(url: str) -> bool:
    """Return true for an issue image, not avatars or decorative GitHub assets."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    path = unquote(parsed.path).casefold()
    if host in {"github.com", "www.github.com"}:
        return "/user-attachments/assets/" in path or "/assets/" in path
    if host.endswith("user-images.githubusercontent.com"):
        return True
    if host == "marketplace-article-scans.s3.cardmarket.com":
        return True
    return Path(path).suffix in {".png", ".jpg", ".jpeg"}


def canonical_issue_attachment_provenance(issue_url: str, stable: str, position: int) -> str:
    """Use one issue-scoped key for every GitHub representation of an attachment.

    GitHub issue HTML may expose the same image as a ``github.com/user-attachments``
    link, a signed ``private-user-images`` URL, or only the latter.  Those URLs are
    transport forms, not durable identity.  The attachment ordinal in the issue is
    the stable identity we can retain in the specimen registry.
    """
    parsed = urlparse(stable)
    host = (parsed.hostname or "").casefold()
    path = unquote(parsed.path).casefold()
    is_github_attachment = (
        host in {"github.com", "www.github.com"}
        and ("/user-attachments/assets/" in path or "/assets/" in path)
    ) or host.endswith("user-images.githubusercontent.com")
    if is_github_attachment:
        return f"{issue_url}#attachment-{position}"
    return stable


class _IssueAttachmentParser(HTMLParser):
    """Collect stable attachment links and the signed image URL beside each link."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.groups: dict[str, list[str]] = {}
        self.active: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value for key, value in attrs if value}
        if tag == "a" and values.get("href") and attachment_candidate(values["href"]):
            stable = values["href"]
            self.groups.setdefault(stable, [stable])
            self.active = stable
        if tag == "img" and values.get("src") and attachment_candidate(values["src"]):
            image = values["src"]
            stable = self.active or image
            candidates = self.groups.setdefault(stable, [stable])
            if image not in candidates:
                candidates.append(image)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self.active = None


def issue_attachments(html: str) -> list[tuple[str, list[str]]]:
    """Return ``(stable provenance URL, download candidates)`` in document order."""
    parser = _IssueAttachmentParser()
    parser.feed(html)
    return list(parser.groups.items())


def select_issue_attachment(
    attachments: list[tuple[str, list[str]]], selector: object, index: int
) -> tuple[str, list[str]]:
    """Select by one-based ordinal, stable URL, or URL basename from a manifest row."""
    if selector is None:
        if index < 1 or index > len(attachments):
            fail(f"attachment index {index} is outside the issue ({len(attachments)} found)")
        return attachments[index - 1]
    if isinstance(selector, int) and not isinstance(selector, bool):
        return select_issue_attachment(attachments, None, selector)
    needle = str(selector)
    for stable, candidates in attachments:
        if needle == stable or needle in candidates:
            return stable, candidates
    for stable, candidates in attachments:
        if Path(urlparse(needle).path).name == Path(urlparse(stable).path).name:
            return stable, candidates
    fail(f"manifest attachment {needle!r} was not found in the issue HTML")


def download_candidates(candidates: list[str]) -> bytes:
    """Try the stable URL first, then its signed browser-rendered counterpart."""
    errors: list[str] = []
    for candidate in candidates:
        try:
            if is_attachment_url(candidate):
                raise SourceUnreachable(f"{candidate} is the blocked GitHub attachment route")
            return download(candidate)
        except SourceUnreachable as error:
            errors.append(str(error))
    raise SourceUnreachable("; ".join(errors) or "no attachment download candidate")


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


def content_hash(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def ensure_unique_photo_hash(owners: dict[str, str], digest: str, specimen_id: str) -> None:
    """Reject one committed image being filed as two independent specimens."""
    owner = owners.get(digest)
    if owner and owner != specimen_id:
        fail(f"image bytes already belong to {owner}; duplicate evidence cannot create {specimen_id}")
    owners[digest] = specimen_id


def ensure_specimen_id_available(
    current: dict | None, source_match: dict | None, specimen_id: str, replace: bool
) -> None:
    """Reject an explicit id collision unless the manifest points at that same source."""
    if current and not source_match and not current.get("photograph") and not replace:
        fail(f"{specimen_id} already exists for another observation; choose a new id")


def specimen_identity(record: dict) -> tuple[str, str, str, str]:
    return (
        str(record.get("setCode") or ""),
        str(record.get("number") or "").split("/", 1)[0],
        str(record.get("variant") or "base"),
        str(record.get("language") or ""),
    )


def ensure_cited_identity(current: dict | None, candidate: dict) -> None:
    """Do not retarget a stable specimen id that is already cited by a claim."""
    cited_by = list((current or {}).get("citedBy") or [])
    if current and cited_by and specimen_identity(current) != specimen_identity(candidate):
        fail(f"{current['specimenId']} is cited by {', '.join(map(str, cited_by))}; "
             "a replacement must keep its set, number, variant and language")


def validate_observation(
    physical: object, specimen_id: str, known_specimen_ids: set[str] | None = None
) -> dict:
    if not isinstance(physical, dict):
        fail(f"manifest row for {specimen_id} needs physicalObservation")
    finish = physical.get("finish")
    if not isinstance(finish, str) or not finish:
        fail(f"manifest row for {specimen_id} needs physicalObservation.finish")
    if finish not in SPECIMEN_FINISHES:
        fail(f"manifest row for {specimen_id} has invalid physicalObservation.finish")
    if not isinstance(physical.get("basis"), str) or not physical["basis"].strip():
        fail(f"manifest row for {specimen_id} needs physicalObservation.basis")
    edition = physical.get("edition")
    if edition is not None and (not isinstance(edition, str) or edition not in SPECIMEN_EDITIONS):
        fail(f"manifest row for {specimen_id} has invalid physicalObservation.edition")
    owner_attested_fields = physical.get("ownerAttestedFields")
    if owner_attested_fields is not None and (
        not isinstance(owner_attested_fields, list)
        or not owner_attested_fields
        or len(owner_attested_fields) != len(set(owner_attested_fields))
        or any(field not in OWNER_ATTESTABLE_FIELDS for field in owner_attested_fields)
        or any(physical.get(field) is None for field in owner_attested_fields)
    ):
        fail(
            f"manifest row for {specimen_id} has invalid "
            "physicalObservation.ownerAttestedFields"
        )
    foil_pattern = physical.get("foilPattern")
    if foil_pattern is not None and not isinstance(foil_pattern, str):
        fail(f"manifest row for {specimen_id} needs text physicalObservation.foilPattern")
    markings = physical.get("markings")
    role = physical.get("markingRole")
    if markings is not None and not isinstance(markings, str):
        fail(f"manifest row for {specimen_id} needs text physicalObservation.markings")
    if markings and (not isinstance(role, str) or role not in SPECIMEN_MARKING_ROLES):
        fail(f"manifest row for {specimen_id} needs a valid physicalObservation.markingRole")
    if role is not None and (not isinstance(role, str) or role not in SPECIMEN_MARKING_ROLES):
        fail(f"manifest row for {specimen_id} has invalid physicalObservation.markingRole")
    distribution = physical.get("distribution")
    if distribution is not None and (
        not isinstance(distribution, dict)
        or set(distribution) - DISTRIBUTION_FIELDS
        or any(value is not None and not isinstance(value, str)
               for value in distribution.values())
    ):
        fail(f"manifest row for {specimen_id} has invalid physicalObservation.distribution")
    card_size = physical.get("cardSize")
    if card_size is not None and (
        not isinstance(card_size, str) or card_size not in SPECIMEN_CARD_SIZES
    ):
        fail(f"manifest row for {specimen_id} has invalid physicalObservation.cardSize")
    covers_multiple_cards = physical.get("coversMultipleCards")
    if covers_multiple_cards is not None and not isinstance(covers_multiple_cards, bool):
        fail(f"manifest row for {specimen_id} needs boolean physicalObservation.coversMultipleCards")
    conflicts = physical.get("conflictsWith")
    if conflicts is not None and (
        not isinstance(conflicts, list)
        or any(not isinstance(ref, str) or ref == specimen_id for ref in conflicts)
        or (known_specimen_ids is not None and any(ref not in known_specimen_ids for ref in conflicts))
    ):
        fail(f"manifest row for {specimen_id} has invalid physicalObservation.conflictsWith")
    return physical


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


def source_first_release_for(
    releases: list[dict], set_code: object, number: object, language: object
) -> dict | None:
    key = (str(set_code), str(number or "").split("/", 1)[0], str(language))
    matches = [
        payload for payload in releases
        if payload.get("state") == "identified"
        and payload.get("sourceFirstRecordIds")
        and (str(payload.get("localSetCode") or payload.get("viaLegacySetCode")),
             str(payload.get("localNumber") or payload.get("viaLegacyNumber") or "").split("/", 1)[0],
             str(payload.get("language"))) == key
    ]
    if len(matches) > 1:
        fail(f"ambiguous authoritative source-first release for {key}")
    return matches[0] if matches else None


def load_source_first_releases() -> list[dict]:
    graph = json.loads(AUTHORITATIVE_GRAPH.read_text(encoding="utf-8-sig"))
    return [
        row.get("payload") or {}
        for row in graph.get("entities", [])
        if row.get("entityType") == "card-release"
    ]


def write_registry(doc: dict) -> None:
    # indent=2, ensure_ascii=False and a trailing newline round-trip the committed file exactly, so
    # filing a photograph produces a one-record diff rather than a reformat of the whole store.
    SPECIMENS_JSON.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8", newline="\n")


def with_photograph(
    specimen: dict, filename: str, provenance: str, digest: str, *, allow_small: bool = False
) -> dict:
    """A copy carrying the photograph fields, provenance, and committed bytes hash.

    Rebuilt rather than assigned so a first-time record does not append the provenance after
    `citedBy`, which reads as though the URL belonged to the citation list.
    """
    updated: dict = {}
    for key, value in specimen.items():
        if key in {"photographSource", "photographSha256", "photographAllowSmall"}:
            continue
        updated[key] = filename if key == "photograph" else value
        if key == "photograph":
            updated["photographSource"] = provenance
            updated["photographSha256"] = digest
    if allow_small:
        updated["photographAllowSmall"] = True
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
    digest = content_hash(blob)
    photo_hash_owners = existing_photo_hash_owners(doc)
    ensure_unique_photo_hash(photo_hash_owners, digest, specimen["specimenId"])
    if args.dry_run:
        print(f"DRY RUN — would write {destination.relative_to(ROOT)} "
              f"({len(blob):,} bytes, {size[0]}x{size[1]} {ext})")
        print(f"DRY RUN — would set {specimen['specimenId']}.photograph = {filename!r}")
        print(f"DRY RUN — would set {specimen['specimenId']}.photographSource = {provenance!r}")
        print(f"DRY RUN — would set {specimen['specimenId']}.photographSha256 = {digest!r}")
        return 0

    SPECIMEN_DIR.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(blob)

    stale = existing and existing != filename
    index = doc["specimens"].index(specimen)
    doc["specimens"][index] = with_photograph(
        specimen, filename, provenance, digest, allow_small=args.allow_small
    )
    write_registry(doc)

    print(f"wrote {destination.relative_to(ROOT)} ({len(blob):,} bytes, {size[0]}x{size[1]} {ext})")
    print(f"set {specimen['specimenId']}.photograph = {filename}")
    print(f"set {specimen['specimenId']}.photographSource = {provenance}")
    print(f"set {specimen['specimenId']}.photographSha256 = {digest}")
    if stale:
        print(f"NOTE: {existing} is now unreferenced — delete it or S10 will fail")
    print("\nnext:")
    print("  python verification/review_findings.py   # S9/S10 cover the file you just added")
    print("  python scripts/database.py               # specimens.json is an input to the database")
    print("  # first photograph in the repository? scripts/source_registry.py carries a note about")
    print("  # renaming `inspected-specimen` back to `photographed-specimen` once images land.")
    return 0


def next_specimen_id(specimens: list[dict]) -> str:
    numbers = [
        int(str(row.get("specimenId", "")).split("-", 1)[1])
        for row in specimens
        if str(row.get("specimenId", "")).startswith("SPEC-")
        and str(row.get("specimenId", ""))[5:].isdigit()
    ]
    return f"SPEC-{max(numbers, default=0) + 1:04d}"


def validate_specimen_id(value: object) -> str:
    """Return a safe stable id, rejecting values that could escape SPECIMEN_DIR."""
    specimen_id = str(value)
    if not SPECIMEN_ID_PATTERN.fullmatch(specimen_id):
        fail(f"invalid specimen id {specimen_id!r}; expected SPEC-nnnn")
    return specimen_id


def existing_photo_hash_owners(doc: dict) -> dict[str, str]:
    return {
        row["photographSha256"]: row["specimenId"]
        for row in doc.get("specimens", [])
        if row.get("photographSha256")
    }


def validate_manifest_fields(item: dict, specimen_id: str) -> None:
    required = ("setCode", "number", "variant", "language", "heldBy", "inspectedFrom",
                "observed", "recordedAt")
    missing = [field for field in required if not isinstance(item.get(field), str) or not item[field]]
    if missing:
        fail(f"manifest row for {specimen_id} is missing: {', '.join(missing)}")


def build_specimen(item: dict, specimen_id: str, filename: str, provenance: str,
                   digest: str, *, listing_url: str | None = None,
                   allow_small: bool = False, cited_by: list | None = None,
                   known_specimen_ids: set[str] | None = None) -> dict:
    validate_manifest_fields(item, specimen_id)
    physical = item.get("physicalObservation")
    if physical is not None:
        physical = validate_observation(physical, specimen_id, known_specimen_ids)
    if item.get("heldBy") == "third-party seller" and not listing_url:
        fail(f"manifest row for {specimen_id} needs listingUrl for third-party seller evidence")
    record = {
        "specimenId": specimen_id,
        "setCode": item["setCode"],
        "number": item["number"],
        "variant": item["variant"],
        "language": item["language"],
        "heldBy": item["heldBy"],
        "inspectedFrom": item["inspectedFrom"],
        "photograph": filename,
        "photographSource": provenance,
        "photographSha256": digest,
        "observed": item["observed"],
        "recordedAt": item["recordedAt"],
        "citedBy": list(item.get("citedBy") or []) if cited_by is None else list(cited_by),
    }
    if physical is not None:
        record["physicalObservation"] = physical
    if listing_url:
        record["listingUrl"] = listing_url
    if allow_small:
        record["photographAllowSmall"] = True
    return record


def commit_import(doc: dict, prepared: list[tuple[Path, bytes]], records: list[dict]) -> None:
    """Commit every image and the registry together, restoring the prior state on failure."""
    registry_before = SPECIMENS_JSON.read_bytes()
    prepared_destinations = {destination for destination, _ in prepared}
    current_by_id = {row["specimenId"]: row for row in doc["specimens"]}
    still_referenced = {
        str(row.get("photograph"))
        for row in doc["specimens"]
        if row.get("photograph")
        and row.get("specimenId") not in {record["specimenId"] for record in records}
    }
    superseded: set[Path] = set()
    for record in records:
        previous = current_by_id.get(record["specimenId"], {})
        old_name = previous.get("photograph")
        new_name = record.get("photograph")
        if not old_name or not new_name or old_name == new_name:
            continue
        if str(old_name) in still_referenced \
                or SPECIMEN_DIR / str(old_name) in prepared_destinations:
            continue
        old_path = SPECIMEN_DIR / str(old_name)
        # Registry photographs are filenames under SPECIMEN_DIR.  Do not let a
        # malformed legacy value turn replacement cleanup into an out-of-tree delete.
        if old_path.parent == SPECIMEN_DIR:
            superseded.add(old_path)
    files_before = {
        path: path.read_bytes() if path.is_file() else None
        for path in {destination for destination, _ in prepared} | superseded
    }
    try:
        SPECIMEN_DIR.mkdir(parents=True, exist_ok=True)
        for destination, blob in prepared:
            destination.write_bytes(blob)
        for old_path in superseded:
            old_path.unlink(missing_ok=True)
        by_id = {row["specimenId"]: row for row in doc["specimens"]}
        for record in records:
            by_id[record["specimenId"]] = record
        doc["specimens"] = sorted(by_id.values(), key=lambda row: row["specimenId"])
        doc["count"] = len(doc["specimens"])
        write_registry(doc)
    except Exception:
        SPECIMENS_JSON.write_bytes(registry_before)
        for destination, previous in files_before.items():
            if previous is None:
                if destination.exists():
                    destination.unlink()
            else:
                destination.write_bytes(previous)
        raise


def command_issue(doc: dict, args: argparse.Namespace) -> int:
    """Import an issue's images from one explicit observation manifest."""
    issue_url = f"https://github.com/m4s-ai/snoredex-data/issues/{args.issue}"
    html = (
        Path(args.issue_html).read_text(encoding="utf-8")
        if args.issue_html
        else download(issue_url).decode("utf-8", errors="replace")
    )
    attachments = issue_attachments(html)
    if not attachments:
        fail(f"no image attachments found in issue #{args.issue}")

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8-sig"))
    observations = manifest.get("observations") if isinstance(manifest, dict) else manifest
    if not isinstance(observations, list) or not observations:
        fail("manifest must contain a non-empty observations list")
    if isinstance(manifest, dict) and manifest.get("issue") not in (None, args.issue):
        fail(f"manifest is for issue #{manifest['issue']}, not #{args.issue}")
    try:
        finish_units = json.loads(FINISH_UNITS.read_text(encoding="utf-8-sig")).get("units", [])
        source_first_releases = load_source_first_releases()
    except (OSError, ValueError, TypeError) as error:
        fail(f"cannot load canonical finish units: {error}")
    known_observed_specimen_ids = {
        str(row.get("specimenId"))
        for row in doc.get("specimens", [])
        if isinstance(row.get("physicalObservation"), dict)
    }
    for item in observations:
        if isinstance(item, dict) and item.get("specimenId") is not None:
            specimen_id = validate_specimen_id(item.get("specimenId"))
            if isinstance(item.get("physicalObservation"), dict):
                known_observed_specimen_ids.add(specimen_id)

    existing_by_source = {
        row.get("photographSource"): row
        for row in doc["specimens"]
        if row.get("photographSource")
    }
    photo_hash_owners = existing_photo_hash_owners(doc)
    used_ids: set[str] = set()
    prepared: list[tuple[Path, bytes]] = []
    records: list[dict] = []
    next_id = next_specimen_id(doc["specimens"])
    for ordinal, item in enumerate(observations, 1):
        if not isinstance(item, dict):
            fail(f"manifest observation {ordinal} is not an object")
        stable, candidates = select_issue_attachment(
            attachments, item.get("attachment", item.get("attachmentIndex")), ordinal
        )
        selected_position = next(
            position for position, (candidate_stable, _) in enumerate(attachments, 1)
            if candidate_stable == stable
        )
        provenance = canonical_issue_attachment_provenance(
            issue_url, stable, selected_position
        )
        existing = existing_by_source.get(provenance) or existing_by_source.get(stable)
        specimen_id = validate_specimen_id(
            item.get("specimenId") or (existing or {}).get("specimenId") or next_id
        )
        if specimen_id in used_ids:
            fail(f"manifest uses specimen {specimen_id} more than once")
        used_ids.add(specimen_id)
        if specimen_id == next_id:
            next_id = f"SPEC-{int(next_id[5:]) + 1:04d}"
        number = str(item.get("number") or "").split("/", 1)[0]
        finish_unit = next((unit for unit in finish_units if (
            str(unit.get("setCode")) == str(item.get("setCode"))
            and str(unit.get("number")) == number
            and str(unit.get("language")) == str(item.get("language"))
        )), None)
        variant = str(item.get("variant") or "base")
        if finish_unit is None:
            source_first_release = source_first_release_for(
                source_first_releases, item.get("setCode"), number, item.get("language")
            )
            if source_first_release is None or variant != "base":
                fail(f"manifest row for {specimen_id} has no canonical finish unit or source-first release")
        elif not any(str(product.get("variant")) == variant
                     and product.get("claimStatus") != "contradicted"
                     for product in finish_unit.get("products", [])):
            fail(f"manifest row for {specimen_id} has no canonical product variant {variant}")
        current = next((row for row in doc["specimens"] if row["specimenId"] == specimen_id), None)
        ensure_cited_identity(current, item)

        blob = download_candidates(candidates)
        ext, size = validate(blob, args.allow_small)
        filename = f"{specimen_id}.{ext}"
        destination = SPECIMEN_DIR / filename
        ensure_specimen_id_available(current, existing, specimen_id, args.replace)
        if destination.is_file() and not current:
            fail(f"{destination.relative_to(ROOT)} exists without a matching specimen record")

        digest = content_hash(blob)
        ensure_unique_photo_hash(photo_hash_owners, digest, specimen_id)
        listing_url = item.get("listingUrl")
        if not isinstance(listing_url, str) or not listing_url:
            listing_url = (current or {}).get("listingUrl")
        cited_by = (
            list(item.get("citedBy") or [])
            if "citedBy" in item else list((current or {}).get("citedBy") or [])
        )
        record = build_specimen(
            item, specimen_id, filename, provenance, digest, listing_url=listing_url,
            allow_small=args.allow_small, cited_by=cited_by,
            known_specimen_ids=known_observed_specimen_ids,
        )
        if current and not args.replace:
            existing_without_photo = {key: value for key, value in current.items()
                                      if key not in {"photograph", "photographSource", "photographSha256"}}
            record_without_photo = {key: value for key, value in record.items()
                                    if key not in {"photograph", "photographSource", "photographSha256"}}
            if existing_without_photo != record_without_photo:
                fail(f"{specimen_id} metadata differs; pass --replace to update it")
            if current.get("photograph"):
                if current.get("photograph") == filename and destination.is_file() \
                        and destination.read_bytes() == blob:
                    print(f"{specimen_id} already carries these exact bytes — nothing to do")
                    continue
                fail(f"{specimen_id} already has a photograph; pass --replace to overwrite it")
        records.append(record)
        prepared.append((destination, blob))
        print(f"prepared {specimen_id}: {size[0]}x{size[1]} {ext} from attachment {selected_position}")

    if args.dry_run:
        print(f"DRY RUN — would import {len(records)} specimen(s) from issue #{args.issue}")
        return 0
    commit_import(doc, prepared, records)
    print(f"imported {len(records)} specimen(s) from issue #{args.issue}")
    result = command_evidence_check(check_projection=False)
    if result == 0:
        print("next: python scripts/regen.py && "
              "python verification/fetch_attachment.py --evidence-check")
    return result


def command_evidence_check(*, check_projection: bool = True) -> int:
    """Check the evidence slice without network access or generated-output writes."""
    errors: list[str] = []
    specimens = load_registry().get("specimens", [])
    photographed = [row for row in specimens if row.get("photograph")]
    for specimen in photographed:
        photograph = specimen.get("photograph")
        path = SPECIMEN_DIR / str(photograph or "")
        if not path.is_file():
            errors.append(f"{specimen['specimenId']}: photograph is missing")
            continue
        try:
            blob = path.read_bytes()
            validate(blob, allow_small=bool(specimen.get("photographAllowSmall")))
            expected_hash = specimen.get("photographSha256")
            if not expected_hash:
                errors.append(f"{specimen['specimenId']}: photograph hash is missing")
            elif expected_hash != content_hash(blob):
                errors.append(f"{specimen['specimenId']}: photograph hash differs")
        except SystemExit as error:
            errors.append(f"{specimen['specimenId']}: invalid photograph ({error})")

    if not check_projection:
        if errors:
            print("physical evidence check: FAIL", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
        print(f"photograph integrity check: OK "
              f"({len(photographed)} photographed specimens, offline)")
        return 0

    observed = [
        row for row in photographed
        if row.get("physicalObservation")
        and not row["physicalObservation"].get("coversMultipleCards")
        and not str(row.get("photographSource") or "").startswith("/tmp/")
    ]

    finish_document = json.loads(FINISH_UNITS.read_text(encoding="utf-8-sig"))
    finish_by_key = {
        (str(unit.get("setCode")), str(unit.get("number")), str(unit.get("language"))): unit
        for unit in finish_document.get("units", [])
    }
    for specimen in observed:
        observation = specimen["physicalObservation"]
        key = (str(specimen.get("setCode")), str(specimen.get("number", "")).split("/", 1)[0],
               str(specimen.get("language")))
        unit = finish_by_key.get(key)
        if not unit:
            try:
                source_first = source_first_release_for(
                    load_source_first_releases(), specimen.get("setCode"), key[1], specimen.get("language")
                )
            except (OSError, ValueError, TypeError, KeyError) as error:
                source_first = None
                errors.append(f"{specimen['specimenId']}: source-first identity check failed: {error}")
            if source_first is None:
                errors.append(f"{specimen['specimenId']}: finish unit is missing")
            continue
        if not any(specimen["specimenId"] in (printing.get("specimenIds") or [])
                   for printing in unit.get("printings", [])):
            errors.append(f"{specimen['specimenId']}: finish projection is missing its source")
        if not any(printing.get("finish") == observation.get("finish")
                   for printing in unit.get("printings", [])):
            errors.append(f"{specimen['specimenId']}: observed finish is not projected")

    try:
        import importlib.util
        graph_module_path = ROOT / "scripts" / "authoritative_graph.py"
        spec = importlib.util.spec_from_file_location("authoritative_graph", graph_module_path)
        graph_module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(graph_module)
        graph = json.loads((VERIFICATION / "authoritative_graph.json").read_text(encoding="utf-8"))
        errors.extend(graph_module.validate(graph))
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        errors.append(f"authoritative graph check failed to run: {error}")
    try:
        collector = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "collector_catalogue.py"), "--check"],
            cwd=ROOT, text=True, encoding="utf-8", stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if collector.returncode:
            detail = collector.stdout.strip().replace("\n", " | ")
            errors.append(f"collector identity check failed: {detail}")
    except OSError as error:
        errors.append(f"collector identity check failed to run: {error}")
    if errors:
        print("physical evidence check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"physical evidence check: OK ({len(observed)} observed specimens, offline)")
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
    parser.add_argument("--issue", type=int, metavar="NUMBER",
                        help="import all selected images from a repository issue")
    parser.add_argument("--manifest", metavar="PATH",
                        help="JSON observation manifest for --issue")
    parser.add_argument("--issue-html", metavar="PATH",
                        help="offline issue HTML fixture (tests and dry runs)")
    parser.add_argument("--evidence-check", action="store_true",
                        help="check photographs, finish projection and graph without writing")
    args = parser.parse_args(argv)

    doc = load_registry()
    if args.list:
        return command_list(doc)
    if args.evidence_check:
        return command_evidence_check()
    if args.issue:
        if args.specimen or args.source:
            parser.error("--issue cannot be combined with --specimen or --from")
        if not args.manifest:
            parser.error("--issue requires --manifest")
        try:
            return command_issue(doc, args)
        except SourceUnreachable as error:
            print(f"UNREACHABLE: {error}", file=sys.stderr)
            print("The bytes are missing, not wrong — retry rather than investigate.", file=sys.stderr)
            return 2
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

"""Sensitive-expression scanner for the P4 (tree) and P6 (history) publication checks.

Moved verbatim out of `review_findings.py` (#460) so its exact bytes can fingerprint a memo: a Git
blob is immutable, so a blob this scanner version has already read never needs reading again. The
memo lives in `<git-common-dir>/snoredex-memo/`, outside the working tree; deleting it only costs
time, and `SNOREDEX_MEMO=off` (the L4 reference lane) disables it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
from pathlib import Path
from typing import Iterator

# Files that quote the sensitive-expression patterns themselves, so P4 and P6 would otherwise
# match on the check's own vocabulary. Both paths of the readiness audit are listed on purpose:
# P6 walks *history*, where blobs carry the path the file had at the time, and #102 moved it to
# verification/history/. Rewriting the old path out is what broke P6 in that PR.
SENSITIVE_SCAN_EXEMPT = frozenset({
    "verification/PUBLIC-READINESS-AUDIT.md",          # pre-#102 path, still in history
    "verification/history/PUBLIC-READINESS-AUDIT.md",  # current path
    "verification/review_findings.py",
    "verification/sensitive_scan.py",                  # #460: the patterns moved here
})

# Reviewed 30th campaign HTML embeds public New Relic input-masking code. Its three
# password literals are a type comparison and two boolean mask settings, not secrets.
# Pin exact blobs (including the two LF-normalized versions in local commit history).
# Never exempt paths, changed bytes, or other findings in these same responses.
PUBLIC_MASKING_RESPONSE_HASHES = frozenset({
    "48636dd43d1fd020e2744e840bc9b1723f92597b265ac96a251b5d5da67852ab",  # id
    "baa1867e8814b378e29f6fb19f10a88f2ef8e05fa4482a0fbc983286c78b6e21",  # my
    "d92677a3eda4616ae93d206f80f0208a3f206b09ec2b12de30bac60d9b66ad74",  # sg
    "ced799972589624e94060523d73cef76df7cfe8b13d2c5875e2060166a49598a",  # my, LF
    "13f027aa3714b87e61d08eb0e625cd0e21d38131f4add7dd6002b5ee48ae45bb",  # sg, LF
    "b0e8cafa960da6a7066f6c2a224bbb0c6a512c9bd945ea861c38b8adec1a6695",  # SG campaign, same masking code
})

# Official Korean footer contact, reviewed in these exact retained public responses only.
PUBLIC_CONTACT_RESPONSE_HASHES = frozenset({
    "4c46c8025c6bb7f6a3b3f0d596c7ca7f39ad3d28e197bf9f735b66846ecdf3a0",  # retained provenance excerpts of the same public footer
    "698436be2fb952fc23de610391ae2168ce4a31a2f22234dc784eebe096712f83",
    "8a1e3a4a2834426213924d2342ff8843f9dee8929b243d0ca2559bcea6bde893",
    "3332426eecddfdf9641675600ae6df045c2e432bbe51a4ee1282265c59ad0432",
})

NON_EMAIL_PATTERN = re.compile(
    r"(?:api[_-]?key|passwd|password|Bearer\s+[A-Za-z0-9._-]{8,}|Authorization:|Cookie:)"
    r"|C:\\Users\\|(?<![A-Za-z0-9._-])/(?:Users/[a-z]|home/[a-z]+/)",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", re.IGNORECASE
)
EMAIL_LOCAL_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._%+-"
)
NON_EMAIL_MARKERS = (
    b"api_key", b"api-key", b"apikey", b"passwd", b"password", b"bearer",
    b"authorization:", b"cookie:", b"c:\\users\\", b"/users/", b"/home/",
)

MEMO_LIMIT = 5_000_000  # larger blobs are not scanned, as before
SCANNER_FINGERPRINT = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
MEMO_SCHEMA = "snoredex-sensitive-scan-memo"


def reviewed_public_masking_literal(data: bytes, found: str) -> bool:
    """Accept only the reviewed masking token in these exact public responses."""
    return found == "password" and hashlib.sha256(data).hexdigest() in PUBLIC_MASKING_RESPONSE_HASHES


def reviewed_public_contact_literal(data: bytes, found: str) -> bool:
    return (found == "webmaster@pokemonkorea.co.kr"
            and hashlib.sha256(data).hexdigest() in PUBLIC_CONTACT_RESPONSE_HASHES)


def _email_matches(text: str) -> list[re.Match]:
    matches = []
    at = text.find("@")
    while at >= 0:
        start = at
        while start and text[start - 1] in EMAIL_LOCAL_CHARS:
            start -= 1
        match = EMAIL_PATTERN.match(text, start)
        if match is not None and match.start() <= at < match.end():
            matches.append(match)
        at = text.find("@", at + 1)
    return matches


def _is_source_asset_name(text: str, match: re.Match) -> bool:
    # Official source assets use names such as `S10a_F@4x.png`. In a URL path the segment
    # resembles an email syntactically but is an image-density filename, not contact data.
    # `SV2a F@4x.png` even contains a source-native space, so retain a short URL-context check
    # as well as the ordinary path-boundary check.
    found = match.group(0)
    preceding = text[match.start() - 1:match.start()]
    recent_url_start = text.rfind("https://", max(0, match.start() - 300), match.start())
    recent_url_prefix = text[recent_url_start:match.start()] if recent_url_start >= 0 else ""
    inside_source_url = bool(recent_url_prefix) and not any(
        delimiter in recent_url_prefix for delimiter in ('"', "'", "\n", "\r")
    )
    return ((preceding in {"/", "\\"} or inside_source_url)
            and found.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))


def _candidate_matches(data: bytes) -> tuple[str, list[re.Match]]:
    if b"\0" in data:
        return "", []
    has_email_candidate = b"@" in data
    has_other_candidate = any(marker in data.lower() for marker in NON_EMAIL_MARKERS)
    if not has_email_candidate and not has_other_candidate:
        return "", []
    text = data.decode("utf-8", errors="ignore")
    matches = list(NON_EMAIL_PATTERN.finditer(text)) if has_other_candidate else []
    if has_email_candidate:
        matches.extend(_email_matches(text))
    return text, matches


def blob_findings(data: bytes) -> list[str]:
    """Return the sensitive expressions in one blob, in text order, without a location label."""
    text, matches = _candidate_matches(data)
    reported = []
    for match in sorted(matches, key=lambda row: row.start()):
        found = match.group(0)
        if reviewed_public_masking_literal(data, found) or reviewed_public_contact_literal(data, found):
            continue
        if "noreply" not in found.lower() and not _is_source_asset_name(text, match):
            reported.append(found[:80])
    return reported


def _git(root: Path, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(["git", *args], cwd=root, input=data, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout


def memo_path(root: Path) -> Path | None:
    """The fingerprinted memo file outside the working tree, or None when the memo is off."""
    if os.environ.get("SNOREDEX_MEMO") == "off":
        return None
    try:
        common = _git(root, "rev-parse", "--git-common-dir").decode().strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    folder = (root / common).resolve() / "snoredex-memo" / "v1" / "sensitive-scan"
    return folder / f"{SCANNER_FINGERPRINT[:20]}.json"


def load_memo(path: Path | None) -> dict[str, list[str]]:
    """A missing, corrupt or foreign memo is an empty memo: the scan simply reads more."""
    if path is None:
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if (not isinstance(document, dict) or document.get("schema") != MEMO_SCHEMA
            or document.get("fingerprint") != SCANNER_FINGERPRINT
            or not isinstance(document.get("blobs"), dict)):
        return {}
    return document["blobs"]


def save_memo(path: Path | None, memo: dict[str, list[str]]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(
        {"schema": MEMO_SCHEMA, "fingerprint": SCANNER_FINGERPRINT, "blobs": memo},
        sort_keys=True, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, path)


def read_blobs(root: Path, shas: list[str]) -> Iterator[tuple[str, bytes]]:
    """Stream blob contents through one `git cat-file --batch`, fed by a writer thread.

    Writing one SHA and then waiting for its response turned 3,900 tiny pipe round-trips into
    minutes on Windows; the producer keeps the constant-memory protocol busy in both directions.
    """
    process = subprocess.Popen(["git", "cat-file", "--batch"], cwd=root,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    assert process.stdin is not None and process.stdout is not None

    def feed() -> None:
        try:
            process.stdin.writelines((sha + "\n").encode("ascii") for sha in shas)
        except BrokenPipeError:
            pass  # The return-code check below reports a failed git process.
        finally:
            process.stdin.close()

    writer = threading.Thread(target=feed)
    writer.start()
    for sha in shas:
        header = process.stdout.readline().decode("ascii", errors="replace").split()
        if len(header) < 3 or header[1] == "missing":
            continue
        data = process.stdout.read(int(header[2]))
        process.stdout.read(1)  # protocol newline
        yield sha, data
    writer.join()
    if process.wait(timeout=10) != 0:
        raise subprocess.CalledProcessError(process.returncode, "git cat-file --batch")


def _object_info(root: Path, shas: list[str]) -> dict[str, tuple[str, int]]:
    output = _git(root, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                  data="".join(sha + "\n" for sha in shas).encode("ascii"))
    info = {}
    for line in output.decode("ascii", errors="replace").splitlines():
        parts = line.split()
        if len(parts) == 3:
            info[parts[0]] = (parts[1], int(parts[2]))
    return info


def fill_memo(root: Path, memo: dict[str, list[str]], shas: list[str]) -> bool:
    """Scan every SHA the memo does not know yet; return whether the memo grew."""
    missing = sorted({sha for sha in shas if sha not in memo})
    for sha, data in read_blobs(root, missing):
        memo[sha] = blob_findings(data)
    return bool(missing)


def _history_candidates(root: Path) -> list[tuple[str, str]]:
    """Reachable blobs up to MEMO_LIMIT outside the exempt paths, typed without reading content."""
    objects = [line.partition(" ") for line in
               _git(root, "rev-list", "--objects", "--all").decode("utf-8", "surrogateescape").splitlines()]
    info = _object_info(root, [sha for sha, _, _ in objects])
    return [(sha, path) for sha, _, path in objects
            if info.get(sha, ("", 0))[0] == "blob" and info[sha][1] <= MEMO_LIMIT
            and path not in SENSITIVE_SCAN_EXEMPT]


def scan_history(root: Path) -> tuple[bool, int, list[str]]:
    """P6: scan every reachable blob up to MEMO_LIMIT, reading only blobs not yet in the memo."""
    try:
        if _git(root, "rev-parse", "--is-shallow-repository").decode().strip() == "true":
            return True, 0, []  # P6 fails on a shallow clone anyway; do not spend minutes first
        candidates = _history_candidates(root)
        location = memo_path(root)
        memo = load_memo(location)
        if fill_memo(root, memo, [sha for sha, _ in candidates]):
            save_memo(location, memo)
    except (OSError, subprocess.CalledProcessError):
        return True, 0, ["Git history could not be read"]
    hits = {f"{sha[:10]}:{path or '(unknown path)'}: {finding}"
            for sha, path in candidates for finding in memo.get(sha, [])}
    return False, len(candidates), sorted(hits)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _index_entries(root: Path) -> list[tuple[str, str, str, str]]:
    entries = []
    for raw in _git(root, "ls-files", "-s", "-z").split(b"\0"):
        if raw:
            meta, _, name = raw.partition(b"\t")
            mode, sha, stage = meta.decode("ascii").split()
            entries.append((mode, sha, stage, name.decode("utf-8", errors="surrogateescape")))
    return entries


def _scan_worktree_file(root: Path, relative: str, index_sha: str, memo: dict) -> list[str] | None:
    try:
        data = (root / relative).read_bytes()
    except OSError:
        return None
    findings = blob_findings(data)
    if git_blob_sha(data) == index_sha:
        memo[index_sha] = findings
    return findings


def _tree_entry_findings(root: Path, entry: tuple[str, str, str, str], dirty: set[str],
                         memo: dict[str, list[str]]) -> list[str] | None:
    mode, sha, stage, relative = entry
    clean = relative not in dirty and stage == "0" and mode in {"100644", "100755"}
    findings = memo.get(sha) if clean else None
    return findings if findings is not None else _scan_worktree_file(root, relative, sha, memo)


def scan_tree(root: Path) -> tuple[int, list[str]]:
    """P4: scan the tracked tree; clean files are answered from the blob memo by their index SHA."""
    dirty = {raw.decode("utf-8", errors="surrogateescape")
             for raw in _git(root, "diff-files", "--name-only", "-z").split(b"\0") if raw}
    location = memo_path(root)
    memo = load_memo(location)
    known = len(memo)
    scanned, hits = 0, []
    for entry in _index_entries(root):
        relative = entry[3]
        if relative in SENSITIVE_SCAN_EXEMPT:
            continue  # These files quote the expressions and known historical finding.
        findings = _tree_entry_findings(root, entry, dirty, memo)
        if findings is None:
            continue
        scanned += 1
        hits.extend(f"{relative}: {finding}" for finding in findings)
    if len(memo) != known:
        save_memo(location, memo)
    return scanned, hits

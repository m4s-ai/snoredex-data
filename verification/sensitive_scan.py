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

# Owner decision 2026-11-02 (#467): these exact blobs are old `verification/passes/*.ps1` versions that
# GitHub still serves through `refs/pull/N/head` of early pull requests. They carry the owner's
# Windows profile path, not a credential. The branches were rewritten long ago, but pull-request
# heads cannot be rewritten from the repository. The owner accepted this exposure instead of a
# GitHub Support removal. Only the profile-path finding in these exact bytes is accepted. Any other
# finding in them, and the same path in any other blob, still fails P6.
REVIEWED_PULL_HEAD_PROFILE_PATH = "C:\\Users\\"
REVIEWED_PULL_HEAD_BLOBS = frozenset({
    "037952dfb4f3273a483ebf2746e4e1fc1d31dc19",
    "0767f443436aae02bbec642a543983eada696a63",
    "09784f3d9624a005f091ec1b319c9b33bec7acb1",
    "0aa4d18e19f94be215662a9b27a94eacc56e9098",
    "0acbbf5d6b5da22f428ce8fb6fe1b012ec7a0ddb",
    "0d6791bc2e35efb947d9a9ff3060865cf8bd4a16",
    "0d9dba0e8849916e6e9abdc6a0ec159d616d2dc1",
    "0faf388e221fcbff9568b357d7b0ed03dc3ed497",
    "14ab2fca2e49dcd754fdbdd98f31d6d6c9188ccc",
    "2448b4c3812e304041e159339b0e3073559ab914",
    "2458569a942327774e26877d0aa785b0fe0ba4e1",
    "297757e141c6b5e705f48daef4819d2e2e994818",
    "2cc9481247eb3365320c3478b1a06eafeab0fce9",
    "2f24d952405bc5937ac0b828c611e3cb9b1269f1",
    "3199cf048b069a67475184d8e215434764011800",
    "37a2d3ccb1b26cd90d0918752fbc50045cc7961e",
    "38327362afbbd7dfdc22ae0dfd24a0841be0d1e1",
    "39317494367b19b39dc4dd6809b7b658bef40500",
    "3aa17cda40c3a963731320f4591d2293d5a1a701",
    "3de12e618a77a27e987f306c397a12b94055728a",
    "3f1a543b770e02a7d42c52eb9d22cb553261e0e6",
    "3f53ca860fdcabbc668dcb71ba2e2f995868d4df",
    "3fa811591a953df83bbfbcbcee15923e799a0aba",
    "411c8dcf0428f56d9269c59fe72c9da549785857",
    "46bb103182c9a8516df9657356e9b26319f776da",
    "4bb58e77fda22aac6824b5df43af1d63375900bd",
    "4d501b0294c0635618dba28545cebc6c37d252e5",
    "4ddbe389f9d43a0a7b8160b57fb65d58dc4e06bf",
    "53083e4874609c42ac89b845b09f13c84d7046d3",
    "61ada73c1ce6fc14e1b8297933d10013c63fea2f",
    "68085351871cd724ee001dc38992dd6db0a01775",
    "693ab4247ec7753b84e1a314a867d619a34bc687",
    "6b0255fd3c1b99ee578a5d9defe0c65408bb2130",
    "709fc0d3b3284dc9a8b38b697707e64f7c3aa56f",
    "73a9ed9b45b3ddb6815e0607113514efdba4d87d",
    "798f120d7c204ff8b4aecd1b2e272db0470f3e59",
    "7b4bcce1b8a306709703cd2a1b715f0ca00f69f2",
    "7fc8481a2dcea468f0529e1259d3d4efdaa558bb",
    "80a0e907f5bf55f87ab3757746967ec8ca75996d",
    "826799fc49db98488df687689dfbbda7b5e56015",
    "84dbd498bfe48d55dcd1657bd31daef4ce596496",
    "853982371941d67f86dc8f15eddfd6b81e398f3c",
    "8621e92bad1c6015ff746417c3692cbfb4004126",
    "887380c30ee25cbf0da3c3c4bd5c4938e0646c76",
    "8f75223d3a8d1871d7d867bbf337997404dd17da",
    "91561ed763bf9e4428b4dd4a5b99bf72032f78d6",
    "91a7e6bc5546e01fb7dabda7bad25719ac6a62af",
    "9496c0df1402377d03c72c1adfb2baa97070370c",
    "9627c87f2ed968186d71187c100f6a6a6e8a8a14",
    "9cea82d1e8b791687c1503fede2ed460cdbc303a",
    "9db898064813d37d854c7f0a69f385bdd27767e0",
    "a06fdb07724a1b4a296c215318185bce811a5522",
    "a489b252602a29ab6a8b5373de98e330990d654f",
    "a9e1b075ac66f4baa892bbd833794fd311d8d188",
    "ac288e6536c35b3ff4cc67022ac001c188cc2850",
    "b57167b29484bc4bc9b6a88cce42f58122ba2c5e",
    "b5ac3ac069bbb37e9b7d0444621d1a3118395876",
    "b62901f557c45d814ef27b37d4c7f653d1763026",
    "be378ab294177473dedc3c6c09b76d3d91694f92",
    "c748e977d4cc13059cbdc90ea3e1aba89cbdcd54",
    "c7fae5c789a35d6ce84fd894c61fdcbda54524bb",
    "c9d1dcecadf7dc896f7e9e0fbcf83cd6286f7d6f",
    "cbfb60e9835c05e8a912dd53f8ec88b15547d317",
    "cc13b2ed3336aa80ed7739bfe13207a75fa582b4",
    "ccbb2f368f888b8b71f3644fad279248d6adf35f",
    "cd6698a26a36dd4d6efcc0727078772a311782c8",
    "d445b93e024b35ffe8c04f50cc48e340bd3fa113",
    "d4d51d41e0344579c2ba70b9f3833e4b87e6b8b6",
    "d5055a4a21adf0088e866ad72ec613ec63922365",
    "d8ac9e5b515a7eafb52ce0fc3047e578fe74c7f8",
    "da34281efe25611e153d30cb9111d841f0d60daa",
    "e4797e641aab2a2cf2e6f4606f4f2e96dbd2eed9",
    "e77b8f992d4d3872efb2ff83b9d67a3c4a367830",
    "e8deb6be564f2996f1568b5d6c7f22016c7b9607",
    "ecdebc3d6913f07b0550315a9855eed464294364",
    "ede58eee843edeacace19566d7d95b830aed404b",
    "eff6ecaad01edf263968c7127a4568433a58f624",
    "f1d625b8cd6db79ac0c2080c5e423c95ec4a8893",
    "f1dbdf31833fbd208e3851ef2772c218f3403801",
    "fbe8e74a482b542f6e668618c76a2d0871f70146",
    "fd088df4bdfe2ce4f5b4c3d9fae40ce42e4f5b12",
    "ff7c8dd5c03b492c46f2cb57bf826a33a7ec4b7b",
})


def reviewed_history_finding(sha: str, finding: str) -> bool:
    """Whether the owner accepted this exact finding in this exact blob (#467)."""
    return finding == REVIEWED_PULL_HEAD_PROFILE_PATH and sha in REVIEWED_PULL_HEAD_BLOBS


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
            for sha, path in candidates for finding in memo.get(sha, [])
            if not reviewed_history_finding(sha, finding)}
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

#!/usr/bin/env python3
"""Regression checks for the P4/P6 sensitive scanner and its blob memo (#460).

Sample expressions are assembled at run time so this file itself never matches P4.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "verification"))
import sensitive_scan as scan  # noqa: E402

os.environ.pop("SNOREDEX_MEMO", None)  # the outer gate's memo mode must not switch this test's memo off
os.environ.pop("SNOREDEX_BLOB_MEMO", None)  # nor the Linux L4 lane's blob-memo switch

AT = "@"
MAIL = "someone" + AT + "example.org"
HOME = "/" + "home/someone/"
TOKEN = "Bear" + "er abcdefghijk"
ENDPOINT = b"10." + b"77.0.12:3002"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL).stdout


def make_repo(root: Path) -> None:
    git(root, "init", "-q")
    git(root, "config", "user.email", "test" + AT + "users.noreply.github.com")
    git(root, "config", "user.name", "test")
    (root / "notes.txt").write_text(f"contact {MAIL}\n", encoding="utf-8", newline="\n")
    (root / "clean.txt").write_text("nothing to see\n", encoding="utf-8", newline="\n")
    (root / "big.txt").write_text(MAIL + "\n" + "x" * scan.MEMO_LIMIT, encoding="utf-8", newline="\n")
    exempt = root / "verification" / "history" / "PUBLIC-READINESS-AUDIT.md"
    exempt.parent.mkdir(parents=True)
    exempt.write_text(MAIL + "\n", encoding="utf-8", newline="\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "fixture")


def verify_findings() -> None:
    assert scan.blob_findings(f"a {MAIL} b".encode()) == [MAIL]
    assert scan.blob_findings(("x " + "123+bot" + AT + "users.noreply.github.com").encode()) == []
    assert scan.blob_findings(("Author" + f"ization: {TOKEN}").encode())
    assert scan.blob_findings(f"path {HOME}x".encode())
    assert scan.blob_findings(b"\0" + MAIL.encode()) == []
    assert scan.blob_findings(("img/S10a_F" + AT + "4x.png").encode()) == []


def counting_reads(counter: list[int]):
    original = scan.read_blobs

    def wrapper(root, shas):
        counter.append(len(shas))
        return original(root, shas)
    return original, wrapper


def verify_history(root: Path) -> None:
    counter: list[int] = []
    original, wrapper = counting_reads(counter)
    scan.read_blobs = wrapper
    try:
        shallow, scanned, hits = scan.scan_history(root)
        assert not shallow and scanned == 2, (scanned, hits)  # notes.txt and clean.txt
        sha = git(root, "rev-parse", "HEAD:notes.txt").strip()
        assert hits == [f"{sha[:10]}:notes.txt: {MAIL}"], hits
        assert counter[-1] == 2
        assert scan.scan_history(root) == (shallow, scanned, hits) and counter[-1] == 0, \
            "a second run must answer every blob from the memo"
        scan.memo_path(root).write_text("{broken", encoding="utf-8", newline="\n")
        assert scan.scan_history(root) == (shallow, scanned, hits) and counter[-1] == 2
        verify_disabled_memo(root, (shallow, scanned, hits), counter)
    finally:
        os.environ.pop("SNOREDEX_MEMO", None)
        scan.read_blobs = original


def verify_disabled_memo(root: Path, expected: tuple, counter: list[int]) -> None:
    os.environ["SNOREDEX_MEMO"] = "off"
    assert scan.memo_path(root) is None
    assert scan.scan_history(root) == expected and counter[-1] == 2
    # Linux L4: steps run cold, but an immutable blob already read is answered from the memo.
    os.environ["SNOREDEX_BLOB_MEMO"] = "use"
    try:
        assert scan.memo_path(root) is not None
        assert scan.scan_history(root) == expected and counter[-1] == 0
    finally:
        os.environ.pop("SNOREDEX_BLOB_MEMO", None)


def verify_tree(root: Path) -> None:
    scanned, hits = scan.scan_tree(root)
    # P4 has no size limit: unlike P6 it also reads big.txt, as before #460.
    assert scanned == 3 and hits == [f"big.txt: {MAIL}", f"notes.txt: {MAIL}"], (scanned, hits)
    (root / "clean.txt").write_text(f"now {HOME}x\n", encoding="utf-8", newline="\n")
    scanned, hits = scan.scan_tree(root)
    assert f"clean.txt: {HOME}" in hits, "a dirty tracked file is read from the working tree"


def verify_endpoint_findings() -> None:
    """A private network endpoint in a tracked file is a P4 finding, address and port included."""
    assert scan.blob_findings(b"route: firecrawl http://" + ENDPOINT + b" via a host") == [ENDPOINT.decode()]
    assert scan.blob_findings(b"asset revision 10.508.02.148") == [], \
        "a three-digit segment is a version string, not an address"
    assert scan.blob_findings(b"serving on 127.0.0.1") == [], \
        "loopback names no real host, and every test server uses it"
    assert scan.blob_findings(b"version 1.2.3 on port 8080") == []


def verify_unportable_paths() -> None:
    """X6: every tracked path must be checkoutable on Windows (#465 shipped `s?-mirror…`)."""
    import publication_audit
    paths = [b"raw/s?-mirror.jpg", b"a/b:c.txt", b"docs/con.txt", b"dir./x", b"ok/name.jpg", b""]
    assert publication_audit.unportable_paths(paths) == [
        "raw/s?-mirror.jpg", "a/b:c.txt", "docs/con.txt", "dir./x"], publication_audit.unportable_paths(paths)

def verify_crlf_prone_writers() -> None:
    """X7: a text write without newline= writes CRLF on Windows and dirties every regenerated file."""
    import publication_audit
    nl = 'newline="' + chr(92) + 'n"'
    source = chr(10).join([
        'p.write_text(s, encoding="utf-8")',
        f'p.write_text(s, encoding="utf-8", {nl})',
        'open(p, "w", encoding="utf-8")',
        'open(p, "a")',
        f'open(p, "w", {nl})',
        'open(p, "wb")',
        'open(p)',
        'p.open("w")',
        'p.open(mode="r")',
        'tempfile.NamedTemporaryFile(mode="w", delete=False)',
        'tempfile.NamedTemporaryFile(mode="wb", delete=False)',
        'io.open(p, "w", **options)',
        'webbrowser.open("http://localhost:8000/")',
        'zipfile.ZipFile(p).open("data.json", "w")',
    ])
    found = publication_audit.crlf_prone_writers({"seed.py": source})
    assert found == ["seed.py:1", "seed.py:3", "seed.py:4", "seed.py:8", "seed.py:10"], found


def verify_reviewed_history(root: Path) -> None:
    """#467: only the owner-accepted finding in the exact pinned blob is accepted."""
    profile = "C:" + "\\" + "Users" + "\\"
    path = root / "old.ps1"
    path.write_text(f"Set-Location {profile}someone\\x\n# contact {MAIL}\n", encoding="utf-8", newline="\n")
    other = root / "other.ps1"
    other.write_text(f"Push-Location {profile}else\n", encoding="utf-8", newline="\n")
    git(root, "add", "old.ps1", "other.ps1")
    git(root, "commit", "-q", "-m", "old passes")
    pinned = git(root, "rev-parse", "HEAD:old.ps1").strip()
    original = scan.REVIEWED_PULL_HEAD_BLOBS
    scan.REVIEWED_PULL_HEAD_BLOBS = frozenset({pinned})
    try:
        hits = scan.scan_history(root)[2]
    finally:
        scan.REVIEWED_PULL_HEAD_BLOBS = original
    assert scan.REVIEWED_PULL_HEAD_PROFILE_PATH == profile
    assert not any(hit.startswith(pinned[:10]) and hit.endswith(profile) for hit in hits), hits
    assert any(hit.startswith(pinned[:10]) and hit.endswith(MAIL) for hit in hits), \
        "another finding in an accepted blob still fails"
    assert any("other.ps1" in hit and hit.endswith(profile) for hit in hits), \
        "the same path in any other blob still fails"


def verify_shallow(source: Path, target: Path) -> None:
    git(target.parent, "clone", "-q", "--depth", "1", source.as_uri(), str(target))
    assert scan.scan_history(target) == (True, 0, [])


def main() -> int:
    verify_findings()
    verify_endpoint_findings()
    verify_unportable_paths()
    verify_crlf_prone_writers()
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder) / "repo"
        root.mkdir()
        make_repo(root)
        verify_history(root)
        verify_tree(root)
        verify_reviewed_history(root)
        verify_shallow(root, Path(folder) / "shallow")
    print("sensitive scan passed: findings, memo reuse, corrupt/disabled memo, size and path limits, "
          "dirty tree files, shallow clone, private endpoints, Windows paths, owner-accepted history blobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

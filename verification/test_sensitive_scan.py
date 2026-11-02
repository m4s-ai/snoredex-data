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
    (root / "notes.txt").write_text(f"contact {MAIL}\n", encoding="utf-8")
    (root / "clean.txt").write_text("nothing to see\n", encoding="utf-8")
    (root / "big.txt").write_text(MAIL + "\n" + "x" * scan.MEMO_LIMIT, encoding="utf-8")
    exempt = root / "verification" / "history" / "PUBLIC-READINESS-AUDIT.md"
    exempt.parent.mkdir(parents=True)
    exempt.write_text(MAIL + "\n", encoding="utf-8")
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
        scan.memo_path(root).write_text("{broken", encoding="utf-8")
        assert scan.scan_history(root) == (shallow, scanned, hits) and counter[-1] == 2
        verify_disabled_memo(root, (shallow, scanned, hits), counter)
    finally:
        os.environ.pop("SNOREDEX_MEMO", None)
        scan.read_blobs = original


def verify_disabled_memo(root: Path, expected: tuple, counter: list[int]) -> None:
    os.environ["SNOREDEX_MEMO"] = "off"
    assert scan.memo_path(root) is None
    assert scan.scan_history(root) == expected and counter[-1] == 2


def verify_tree(root: Path) -> None:
    scanned, hits = scan.scan_tree(root)
    # P4 has no size limit: unlike P6 it also reads big.txt, as before #460.
    assert scanned == 3 and hits == [f"big.txt: {MAIL}", f"notes.txt: {MAIL}"], (scanned, hits)
    (root / "clean.txt").write_text(f"now {HOME}x\n", encoding="utf-8")
    scanned, hits = scan.scan_tree(root)
    assert f"clean.txt: {HOME}" in hits, "a dirty tracked file is read from the working tree"


def verify_pull_refs(folder: Path) -> None:
    """A locally mapped pull ref is not a published ref, so its blobs are not P6 findings (#465).

    A clone may fetch GitHub's pull namespace into `refs/remotes/origin/pr/N`. That is local
    configuration, so a blob reachable only through it must never turn P6 red while the same commit
    is green in a clean clone — that is what made one clone report 82 hits nobody could find.
    """
    root = folder / "refs-repo"
    root.mkdir()
    make_repo(root)
    git(root, "checkout", "-q", "-b", "stray")
    # Distinct bytes from notes.txt: `rev-list --objects` reports one path per blob, so a copy with
    # identical content would never appear under its own name.
    (root / "stray.txt").write_text(f"second contact {MAIL}\n", encoding="utf-8")
    git(root, "add", "stray.txt")
    git(root, "commit", "-q", "-m", "stray")
    sha = git(root, "rev-parse", "HEAD").strip()
    git(root, "checkout", "-q", "--detach", "HEAD~1")
    git(root, "branch", "-q", "-D", "stray")
    git(root, "update-ref", "refs/remotes/origin/pr/7", sha)
    assert "refs/remotes/origin/pr/7" not in scan.published_refs(root), scan.published_refs(root)
    assert not any("stray.txt" in hit for hit in scan.scan_history(root)[2]), \
        "a blob reachable only through a pull ref is not a finding"
    git(root, "update-ref", "refs/heads/stray", sha)
    assert any("stray.txt" in hit for hit in scan.scan_history(root)[2]), \
        "a real branch carrying the same blob is a finding"


def verify_endpoint_findings() -> None:
    """A private network endpoint in a tracked file is a P4 finding, address and port included."""
    assert scan.blob_findings(b"route: firecrawl http://" + ENDPOINT + b" via a host") == [ENDPOINT.decode()]
    assert scan.blob_findings(b"asset revision 10.508.02.148") == [], \
        "a three-digit segment is a version string, not an address"
    assert scan.blob_findings(b"serving on 127.0.0.1") == [], \
        "loopback names no real host, and every test server uses it"
    assert scan.blob_findings(b"version 1.2.3 on port 8080") == []


def verify_shallow(source: Path, target: Path) -> None:
    git(target.parent, "clone", "-q", "--depth", "1", source.as_uri(), str(target))
    assert scan.scan_history(target) == (True, 0, [])


def main() -> int:
    verify_findings()
    verify_endpoint_findings()
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder) / "repo"
        root.mkdir()
        make_repo(root)
        verify_history(root)
        verify_tree(root)
        verify_shallow(root, Path(folder) / "shallow")
        verify_pull_refs(Path(folder))
    print("sensitive scan passed: findings, memo reuse, corrupt/disabled memo, size and path limits, "
          "dirty tree files, shallow clone, private endpoints, pull refs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

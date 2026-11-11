#!/usr/bin/env python3
"""Publication-scope audit: the tree and history boundary checked before and after every push.

Carries the publication scope of the former findings harness unchanged (its section G8), together
with the two portability checks X6 and X7 of its section G9, which guard the same tracked tree. Exit 0 when no FAIL check fires.

    python verification/publication_audit.py
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from sensitive_scan import scan_history, scan_tree

ROOT = Path(__file__).resolve().parent.parent
WINDOWS_INVALID_NAME = re.compile(r'[<>:"|?*\x00-\x1f]')
WINDOWS_RESERVED_NAME = re.compile(r"^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$", re.IGNORECASE)
REQUIRED_LICENCES = {
    "LICENSES/PolyForm-Noncommercial-1.0.0.md": {
        "url": "https://github.com/polyformproject/polyform-licenses/blob/1.0.0/PolyForm-Noncommercial-1.0.0.md",
        "sha256": "c0ea4a896d2c8c394b29f9427589996db826cd501c512279ff0ed3ef48fabbe5",
    },
    "LICENSES/CC-BY-NC-SA-4.0.md": {
        "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.txt",
        "sha256": "e66c269d4819aaab34b49ef5220c4ddab6756f21bb5180761a4eb8561f2b7bbd",
    },
}
REQUIRED_DOCS = ("LICENSE.md", "THIRD_PARTY_NOTICES.md", "verification/history/PUBLIC-READINESS-AUDIT.md")
DECISION_KEYS = {
    "repositoryVisibility", "repositoryPublicationApproved", "sitePublicationApproved",
    "licenseGrantsApproved", "licensor", "ownerAttestationsApproved",
    "thirdPartyImagesApproved", "approvedBy", "approvedAt",
}
RESULTS: list[tuple[str, str, str, bool, str]] = []


def check(check_id: str, title: str, severity: str, ok: bool, detail: str = "") -> None:
    """Declare a finding. Severity INFO reports without ever failing the run."""
    RESULTS.append((check_id, title, severity, ok, detail))


def licences() -> None:
    missing = [name for name in REQUIRED_LICENCES if not (ROOT / name).exists()]
    wrong = [f"{name}: {hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}"
             for name, source in REQUIRED_LICENCES.items()
             if (ROOT / name).exists() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != source["sha256"]]
    check("L1", "Verbatim licence texts match their canonical publisher bytes", "FAIL", not missing and not wrong,
          f"missing={missing} wrong_hash={wrong}. Canonical sources and pinned SHA-256 values: {REQUIRED_LICENCES}")
    for index, doc in enumerate(REQUIRED_DOCS, start=1):
        check(f"P{index}", f"{doc} exists", "FAIL", (ROOT / doc).exists(), f"{doc} is required before publication (#5)")


def read_decisions() -> dict:
    try:
        return json.loads((ROOT / "publication-decisions.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def decisions_valid(decisions: dict) -> bool:
    flags = ("repositoryPublicationApproved", "sitePublicationApproved", "licenseGrantsApproved",
             "ownerAttestationsApproved", "thirdPartyImagesApproved")
    return (DECISION_KEYS <= set(decisions) and decisions.get("repositoryVisibility") in {"private", "public"}
            and all(isinstance(decisions.get(key), bool) for key in flags)
            and decisions.get("licensor") in {None, "M4S.Collection"}
            and (decisions.get("approvedBy") is None or isinstance(decisions.get("approvedBy"), str))
            and (decisions.get("approvedAt") is None
                 or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(decisions.get("approvedAt"))))))


def published_refs() -> list[str]:
    """Every ref this repository publishes, minus GitHub's synthetic pull-request merge refs.

    A `refs/pull/N/merge` commit exists only to be tested; its identity fields belong to GitHub and
    to whoever opened the pull request. Branches, tags and remotes are audited in full, because
    making a repository public publishes every one of them.
    """
    try:
        refs = subprocess.check_output(["git", "for-each-ref", "--format=%(refname)", "refs/heads", "refs/tags",
                                        "refs/remotes"], cwd=ROOT, text=True).split()
    except (OSError, subprocess.CalledProcessError):
        return []
    return [ref for ref in refs if "/pull/" not in ref]


def commit_emails() -> list[str]:
    try:
        audited = published_refs()
        fields = subprocess.check_output(["git", "log", "--format=%H%x00%ae%x00%ce"] + audited, cwd=ROOT).decode(
            "utf-8", errors="replace").splitlines() if audited else []
    except (OSError, subprocess.CalledProcessError):
        fields = ["\0commit metadata unavailable\0"]
    emails = {email.strip() for record in fields for email in record.partition("\0")[2].split("\0")}
    return sorted(email for email in emails if "@" in email and "noreply" not in email.lower())


def history(decisions: dict) -> None:
    shallow, scanned, hits = scan_history(ROOT)
    check("P5", "Publication decisions are explicit, complete, and well typed", "FAIL", decisions_valid(decisions),
          "publication-decisions.json must contain every decision with valid value types; the separate "
          "publication gate enforces approval before deployment")
    check("P6", "Full history was available and public-repository approval accounts for its findings", "FAIL",
          not shallow and (not decisions.get("repositoryPublicationApproved") or not hits),
          f"shallow={shallow}; {len(hits)} sensitive-history hits across {scanned} blobs. Public repository "
          f"approval must remain false unless these are reviewed or history is rewritten. e.g. {hits[:4]}")
    emails = commit_emails()
    check("P7", "No reachable commit exposes a personal email address", "FAIL", not emails,
          f"personal commit emails: {emails}")
    check("I3", "Full-history publication audit", "INFO", True,
          f"{scanned} reachable blobs scanned; {len(hits)} sensitive-history hits; repository publication "
          f"approved={decisions.get('repositoryPublicationApproved')}; personal commit emails={len(emails)}")


def tracker_reachability(decisions: dict) -> None:
    site = (ROOT / "index.html").read_text(encoding="utf-8") if (ROOT / "index.html").exists() else ""
    links = len(re.findall(r"https://github\.com/m4s-ai/snoredex-data", site))
    public = decisions.get("repositoryVisibility") == "public" and decisions.get("repositoryPublicationApproved") is True
    check("P8", "A published site never points its correction links into a private tracker", "FAIL",
          not (decisions.get("sitePublicationApproved") is True and links and not public),
          f"the site embeds {links} links to github.com/m4s-ai/snoredex-data. sitePublicationApproved="
          f"{decisions.get('sitePublicationApproved')}, repositoryVisibility={decisions.get('repositoryVisibility')}, "
          f"repositoryPublicationApproved={decisions.get('repositoryPublicationApproved')}. Publish both "
          f"together, or remove the correction affordance from the site.")
    check("I4", "Correction-loop reachability", "INFO", True,
          f"{links} repository links embedded in the site; tracker publicly reachable={public}. "
          f"Contributors can only file corrections once this is True.")


def unportable_paths(tracked: list[bytes]) -> list[str]:
    """Tracked paths a Windows checkout cannot represent (X6)."""
    unportable = []
    for raw_name in filter(None, tracked):
        name = raw_name.decode("utf-8", errors="surrogateescape")
        if any(WINDOWS_INVALID_NAME.search(part) or part.endswith((".", " ")) or WINDOWS_RESERVED_NAME.match(part)
               for part in name.split("/")):
            unportable.append(name)
    return unportable


def _mode_argument(call: ast.Call) -> ast.expr | None:
    # Path.open(mode) and NamedTemporaryFile(mode) take the mode first; open/io.open/os.fdopen second.
    func = call.func
    first = isinstance(func, ast.Attribute) and getattr(func.value, "id", None) not in {"io", "os", "codecs"}
    positional = call.args[0 if first else 1:][:1]
    keyword = [kw.value for kw in call.keywords if kw.arg == "mode"]
    return (keyword or positional or [None])[0]


def _write_mode(call: ast.Call) -> str:
    """The literal mode a call opens a file with ("w" for write_text), or "" when it opens none."""
    func = call.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    if name == "write_text":
        return "w"
    if name not in {"open", "fdopen", "NamedTemporaryFile"}:
        return ""
    mode = _mode_argument(call)
    value = mode.value if isinstance(mode, ast.Constant) and isinstance(mode.value, str) else ""
    return value if re.fullmatch(r"[rwaxbt+]+", value) else ""  # a URL or member name is no mode


def _is_crlf_prone(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    mode = _write_mode(node)
    return ("b" not in mode and bool(set(mode) & set("wax"))
            and not any(kw.arg in {"newline", None} for kw in node.keywords))


def crlf_prone_writers(sources: dict[str, str]) -> list[str]:
    """`file:line` of every text write without `newline=`; Windows would translate `\\n` to CRLF (X7)."""
    return [f"{name}:{node.lineno}" for name, text in sorted(sources.items())
            for node in ast.walk(ast.parse(text, filename=name)) if _is_crlf_prone(node)]


def portability() -> None:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    unportable = unportable_paths(tracked)
    check("X6", "Every tracked path is checkoutable on Windows", "FAIL", not unportable,
          f"{len(unportable)} tracked path(s) a Windows checkout cannot represent: {unportable[:5]}. "
          f"Rename the file and every reference to it.")
    names = (raw.decode("utf-8", errors="surrogateescape") for raw in tracked)
    sources = {name: (ROOT / name).read_text(encoding="utf-8") for name in names
               if name.endswith(".py") and name.startswith(("scripts/", "verification/"))
               and not name.startswith("verification/archive/") and (ROOT / name).exists()}
    writers = crlf_prone_writers(sources)
    check("X7", "Text writers pin LF line endings", "FAIL", not writers,
          f"{len(writers)} write_text/open(..., 'w') call(s) without newline=: {writers[:10]}. Pass newline=\"\\n\".")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    licences()
    scanned, hits = scan_tree(ROOT)
    check("P4", "No secrets, personal paths, or contact details in the complete tracked tree", "FAIL", not hits,
          f"{len(hits)} hits across {scanned} scanned files: {hits[:5]}")
    decisions = read_decisions()
    history(decisions)
    tracker_reachability(decisions)
    portability()
    failures = 0
    for check_id, title, severity, ok, detail in RESULTS:
        if severity == "INFO":
            print(f"[info] {check_id} {title}: {detail}")
            continue
        print(f"[ ok ] {check_id} {title}" if ok else f"[FAIL] {check_id} {title}\n       {detail}")
        failures += not ok
    total = sum(severity != "INFO" for _, _, severity, _, _ in RESULTS)
    print(f"\n{total - failures}/{total} checks passed, {failures} failing (scope=publication).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

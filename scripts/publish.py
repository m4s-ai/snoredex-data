#!/usr/bin/env python3
"""Assemble the public Pages artifact from an explicit allowlist (#11).

Copying the repository and excluding a few things is the wrong default: anything added later is
published unless someone remembers to exclude it. This inverts that — nothing is published unless
it is named here, so a new cache directory, a downloaded scan, or a scratch file cannot reach the
public site by omission.

    python scripts/publish.py --out _site            # build the artifact
    python scripts/publish.py --out _site --verify   # assert the artifact holds only allowlisted files
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Exact files. Each is here because the site links to it or a reader needs it.
FILES = [
    "index.html",
    "README.md",
    "LICENSE.md",
    "THIRD_PARTY_NOTICES.md",
    "snorlax_cards.json",
    "analysis_checklist.json",
    "analysis_confirmed_releases.json",
    "analysis_confirmed_releases.csv",
    "analysis_finishes.json",
    "analysis_artists.json",
    "analysis_variants.json",
    "analysis_shared_cards.json",
    "analysis_language_drift.json",
    "artists_pokemontcgio.json",
    "verification/confirmed-releases.html",
    "verification/source_registry.json",
    "verification/SOURCES.md",
    "verification/finish_units.json",
    "verification/units.json",
    "verification/CONTRADICTED.json",
    "verification/UNCONFIRMED.json",
    "verification/RESUME.md",
    "verification/FINISH_SOURCES.md",
    "verification/PUBLIC-READINESS-AUDIT.md",
]

# Whole directories, restricted by extension so a stray file cannot ride along.
TREES = [
    ("site", {".css", ".js"}),
    ("images", {".jpg", ".jpeg", ".png", ".webp"}),
    ("LICENSES", {".md", ".txt"}),
]

# Anything matching these must never appear in the artifact, even if a rule above would admit it.
FORBIDDEN = [
    re.compile(r"(^|/)cache(/|$)"),
    re.compile(r"(^|/)zoom(/|$)"),
    re.compile(r"(^|/)__pycache__(/|$)"),
    re.compile(r"(^|/)\.git(/|$)"),
    re.compile(r"(^|/)\.github(/|$)"),
    re.compile(r"_evidence_audit"),
    re.compile(r"\.(ps1|py|pyc|env|key|pem)$"),
]


def forbidden(relative: str) -> str | None:
    for pattern in FORBIDDEN:
        if pattern.search(relative):
            return pattern.pattern
    return None


def collect() -> list[str]:
    """Every path the artifact should contain, relative to the repository root."""
    wanted: list[str] = []
    for name in FILES:
        if (ROOT / name).exists():
            wanted.append(name)
        elif name.startswith("LICENSES/"):
            continue
        else:
            print(f"warning: allowlisted file missing, skipping: {name}", file=sys.stderr)
    for directory, extensions in TREES:
        base = ROOT / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in extensions:
                wanted.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    return wanted


def build(out: Path) -> list[str]:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    wanted = collect()
    for relative in wanted:
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    # Pages serves Jekyll by default, which would skip files beginning with an underscore.
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return wanted


def verify(out: Path) -> int:
    if not out.is_dir():
        print(f"{out} does not exist; run without --verify first", file=sys.stderr)
        return 1
    allowed = set(collect()) | {".nojekyll"}
    problems: list[str] = []
    present = []
    for path in sorted(out.rglob("*")):
        if not path.is_file():
            continue
        relative = str(path.relative_to(out)).replace("\\", "/")
        present.append(relative)
        reason = forbidden(relative)
        if reason:
            problems.append(f"forbidden pattern {reason}: {relative}")
        elif relative not in allowed:
            problems.append(f"not on the allowlist: {relative}")

    missing = sorted(allowed - set(present))
    for name in missing:
        if name != ".nojekyll":
            problems.append(f"allowlisted but absent from the artifact: {name}")

    index = out / "index.html"
    if index.exists():
        html = index.read_text(encoding="utf-8")
        # Every local asset the page references must exist in the artifact, or the published
        # site has a broken link that no unit test would catch.
        for match in re.finditer(r'(?:href|src)="([^"#:]+)"', html):
            target = match.group(1)
            if target.startswith(("http", "//", "mailto:", "data:")):
                continue
            if not (out / target).exists():
                problems.append(f"index.html references a missing local asset: {target}")

    if problems:
        print(f"artifact verification failed ({len(problems)} problems):", file=sys.stderr)
        for problem in problems[:25]:
            print(f"  {problem}", file=sys.stderr)
        return 1

    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"artifact verified: {len(present)} files, {size // 1024} KB, allowlist only")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="_site", help="output directory")
    parser.add_argument("--verify", action="store_true", help="verify instead of rebuilding")
    args = parser.parse_args()
    out = (ROOT / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)

    if args.verify:
        return verify(out)

    wanted = build(out)
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"assembled {len(wanted)} files into {out.relative_to(ROOT)} ({size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

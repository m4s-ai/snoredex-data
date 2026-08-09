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
import posixpath
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PREFIX = "_site"
REPO_BLOB = "https://github.com/m4s-ai/snoredex-data/blob/main/"

# Markdown links resolve against the repository, but the artifact is a strict subset of it, so a
# link to something deliberately left out (a script, the handover notes) silently breaks on the
# published site. Rather than publishing more than the allowlist intends, repoint those links at
# the repository itself. Anything present in the artifact keeps its relative link and stays
# browsable offline.
MARKDOWN_LINK = re.compile(r'(\]\()([^)\s]+)(\))')

# Exact files. Each is here because the site links to it or a reader needs it.
FILES = [
    "index.html",
    "README.md",
    "DATABASE.md",
    "FINDINGS.md",
    "LICENSE.md",
    "THIRD_PARTY_NOTICES.md",
    "legacy-cardmarket-baseline.json",
    "snorlax_cards.json",
    "snoredex.sqlite",
    "snoredex-tracker-template.sqlite",
    "analysis_checklist.json",
    "analysis_confirmed_releases.json",
    "analysis_confirmed_releases.csv",
    "analysis_finishes.json",
    "analysis_artists.json",
    "analysis_variants.json",
    "analysis_shared_cards.json",
    "analysis_language_drift.json",
    "artists_pokemontcgio.json",
    "AI-DECLARATION.md",
    "CONTRIBUTING.md",
    "publication-decisions.json",
    "verification/confirmed-releases.html",
    "verification/open-items.html",
    "verification/FINISH_REVIEW.csv",
    "verification/source_registry.json",
    "verification/source_capabilities.json",
    "verification/source_capability_schema.json",
    "verification/source_capability_graph.json",
    "verification/SOURCES.md",
    "verification/bulbapedia_release_dates.json",
    "verification/history/BULBAPEDIA-RELEASE-DATE-AUDIT.md",
    "verification/finish_units.json",
    "verification/units.json",
    "verification/owner_adjudications.json",
    "verification/CONTRADICTED.json",
    "verification/UNCONFIRMED.json",
    "verification/RESUME.md",
    "verification/FINISH_SOURCES.md",
    "verification/history/PUBLIC-READINESS-AUDIT.md",
    "verification/DATA-HANDOFF-AUDIT.md",
]

# Whole directories, restricted by extension so a stray file cannot ride along.
TREES = [
    ("site", {".css", ".js"}),
    ("images", {".jpg", ".jpeg", ".png", ".webp"}),
    # Owner specimen photographs, added as claims requiring them arise (#32). Listed here so a
    # photograph is published when it lands rather than silently dropped from the artifact, which
    # is what happens to anything not allowlisted. Publication rests on the owner decision in
    # LICENSE.md, which covers the category rather than a fixed list; the directory need not exist.
    ("verification/specimens", {".jpg", ".jpeg", ".png", ".webp"}),
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


def validate_output(out: Path) -> Path:
    """Restrict destructive rebuilds to a dedicated staging directory.

    The publisher intentionally replaces its output. Without this guard, a typo such as
    ``--out .`` targets the checkout itself, while an absolute path can target unrelated data.
    Requiring a direct child named ``_site*`` keeps the operation explicit and recoverable.
    """
    resolved = out.resolve()
    if resolved.parent != ROOT or not resolved.name.startswith(OUTPUT_PREFIX):
        raise ValueError(
            f"output must be a direct child of {ROOT} named {OUTPUT_PREFIX}*; got {resolved}"
        )
    return resolved


def relink_markdown(text: str, source: str, published: set[str]) -> str:
    """Repoint links that leave the artifact at the repository, leaving internal links alone."""
    base = Path(source).parent

    def replace(match: re.Match[str]) -> str:
        target = match.group(2)
        if target.startswith(("http://", "https://", "#", "mailto:", "data:", "//")):
            return match.group(0)
        path, _, fragment = target.partition("#")
        if not path:
            return match.group(0)
        # Normalize textually: the target need not exist on disk, and `..` must collapse the
        # same way on every platform.
        resolved = posixpath.normpath(posixpath.join(base.as_posix(), path)).lstrip("/")
        if resolved in published:
            return match.group(0)
        return f"{match.group(1)}{REPO_BLOB}{resolved}{'#' + fragment if fragment else ''}{match.group(3)}"

    return MARKDOWN_LINK.sub(replace, text)


def build(out: Path) -> list[str]:
    out = validate_output(out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    wanted = collect()
    published = set(wanted)
    for relative in wanted:
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
        if target.suffix == ".md":
            original = target.read_text(encoding="utf-8")
            rewritten = relink_markdown(original, relative, published)
            if rewritten != original:
                target.write_text(rewritten, encoding="utf-8")
    # Pages serves Jekyll by default, which would skip files beginning with an underscore.
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return wanted


def verify(out: Path) -> int:
    out = validate_output(out)
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

    # Every local reference in every published page must resolve inside the artifact. Checking
    # only index.html let the published Markdown accumulate links to files the allowlist
    # deliberately excludes, which read as broken pages to the very reviewers the site invites.
    for page in sorted(out.rglob("*")):
        if not page.is_file() or page.suffix not in {".html", ".md"}:
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        targets = re.findall(r'(?:href|src)="([^"]+)"', text)
        if page.suffix == ".md":
            targets += [match.group(2) for match in MARKDOWN_LINK.finditer(text)]
        name = page.relative_to(out).as_posix()
        for target in sorted(set(targets)):
            if target.startswith(("http://", "https://", "//", "mailto:", "data:", "#")):
                continue
            if "${" in target:
                continue  # A client-side template placeholder, resolved only in the browser.
            target = target.split("#")[0]
            if target and not (page.parent / target).exists():
                problems.append(f"{name} references a missing local target: {target}")

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
    candidate = ROOT / args.out if not Path(args.out).is_absolute() else Path(args.out)
    try:
        out = validate_output(candidate)
    except ValueError as error:
        print(f"refusing unsafe output path: {error}", file=sys.stderr)
        return 2

    if args.verify:
        return verify(out)

    wanted = build(out)
    # Count what is on disk, not what the allowlist asked for: build() also writes .nojekyll, so
    # the two lines disagreed by one and read as a discrepancy in an artifact whose whole point is
    # that its contents are known exactly (#68).
    present = [p for p in out.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in present)
    print(f"assembled {len(present)} files into {out.relative_to(ROOT)} ({size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

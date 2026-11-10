#!/usr/bin/env python3
"""Every relative link in the documents and page templates resolves to a file in the repository.

Markdown outside verification/archive, evidence and specimens, plus templates/index.html and
site/gallery.html (both rendered at the repository root). A `#fragment` on a Markdown target must
name a heading there. Exit 1 lists every broken link.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
# PUBLIC-READINESS-AUDIT.md is a dated record kept unchanged for publication check P3.
EXEMPT = ("verification/archive/", "verification/evidence/", "verification/specimens/",
          "verification/history/PUBLIC-READINESS-AUDIT.md")
PAGES = ("templates/index.html", "site/gallery.html")
MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")
HTML_LINK = re.compile(r'(?:href|src)="([^"]+)"')


def anchors(text: str) -> set[str]:
    """GitHub heading slugs: lower case, punctuation dropped, spaces to hyphens."""
    headings = re.findall(r"^#+\s+(.+?)\s*$", re.sub(r"```.*?```", "", text, flags=re.S), re.M)
    return {re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-") for heading in headings}


def targets(name: str, text: str) -> list[str]:
    if name.endswith(".md"):
        return MARKDOWN_LINK.findall(re.sub(r"```.*?```", "", text, flags=re.S))
    return HTML_LINK.findall(text)


def problems(files: dict[str, str]) -> list[str]:
    """Broken relative links in `files` (path -> text); targets resolve against the same dict."""
    found = []
    for name, text in sorted(files.items()):
        base = PurePosixPath("." if name in PAGES else PurePosixPath(name).parent)
        for target in targets(name, text):
            if re.match(r"[a-z]+:|//|\{\{", target):
                continue
            path, _, fragment = target.partition("#")
            resolved = str(PurePosixPath(*(base / path).parts)) if path else name
            resolved = re.sub(r"(^|/)\./", r"\1", resolved)
            while "/../" in f"/{resolved}":
                resolved = re.sub(r"(^|/)[^/]+/\.\./", r"\1", resolved, count=1)
            if resolved not in files:
                found.append(f"{name}: {target} -> missing {resolved}")
            elif fragment and resolved.endswith(".md") and fragment not in anchors(files[resolved]):
                found.append(f"{name}: {target} -> no heading #{fragment}")
    return found


def tracked() -> dict[str, str]:
    names = subprocess.check_output(["git", "-c", "core.quotepath=off", "ls-files", "-co", "--exclude-standard"],
                                    cwd=ROOT, text=True, encoding="utf-8").splitlines()
    return {name: (ROOT / name).read_text(encoding="utf-8", errors="replace")
            if name.endswith((".md", ".html")) else "" for name in names if (ROOT / name).is_file()}


def main() -> int:
    seeded = problems({"a.md": "[x](missing.md) [y](b.md#nowhere) [z](b.md#real-heading)", "b.md": "# Real heading\n"})
    assert seeded == ["a.md: missing.md -> missing missing.md", "a.md: b.md#nowhere -> no heading #nowhere"], seeded
    files = tracked()
    checked = {name: text for name, text in files.items()
               if (name.endswith(".md") and not name.startswith(EXEMPT)) or name in PAGES}
    broken = [problem for problem in problems(files) if problem.split(":", 1)[0] in checked]
    for problem in broken:
        print(problem)
    print(f"links: {len(checked)} documents checked, {len(broken)} broken")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())

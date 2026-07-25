#!/usr/bin/env python3
"""Regenerate the generated blocks in README.md from the current data.

The finish coverage table drifted twice by being hand-maintained: it claimed 276 non-holo and
24 both-non-holo-and-holo units while the generated data said 270 and 18, and the wrong numbers
were typed in the same commit that regenerated the data. Prose that restates generated facts
has to be generated, or it will disagree with them again.

Blocks are delimited by `<!-- generated:NAME -->` / `<!-- /generated:NAME -->`. Everything
between the markers is replaced; everything outside is left alone.

    python scripts/readme_stats.py          # rewrite
    python scripts/readme_stats.py --check  # fail if stale, for the release gate
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
README_PATH = ROOT / "README.md"
ANALYSIS_PATH = ROOT / "analysis_finishes.json"


def read_json(path: Path) -> Any:
    # Tolerate historical PowerShell 5.1 BOM output; all active writers now emit UTF-8 no-BOM.
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def finish_coverage_block(counts: dict[str, int]) -> str:
    rows = (
        ("Non-holo", "withNonHolo"),
        ("Holo", "withHolo"),
        ("Reverse holo", "withReverseHolo"),
        ("Mirror holo", "withMirrorHolo"),
        ("Both non-holo and holo", "withBothNonHoloAndHolo"),
    )
    lines = ["| Known available finish | Set-number-language units |", "|---|---:|"]
    lines += [f"| {label} | {counts[key]} |" for label, key in rows]
    return "\n".join(lines)


def replace_block(text: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- generated:{re.escape(name)}[^>]*-->\n).*?(\n<!-- /generated:{re.escape(name)} -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"README.md has no generated:{name} block")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text)


def main() -> int:
    counts = read_json(ANALYSIS_PATH)["counts"]
    original = README_PATH.read_text(encoding="utf-8")
    updated = replace_block(original, "finish-coverage", finish_coverage_block(counts))

    if "--check" in sys.argv:
        if updated != original:
            print("README.md generated blocks are stale; run python scripts/readme_stats.py")
            return 1
        print("README.md generated blocks are current")
        return 0

    if updated != original:
        with README_PATH.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(updated)
        print("README.md updated")
    else:
        print("README.md already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())

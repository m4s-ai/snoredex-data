#!/usr/bin/env python3
"""One-shot pass: give unnumbered cards one canonical collector number across every store.

Unnumbered products (`PJU`, `G2`, `EXS`, `DP1`, `UNP`) were `null` in `snorlax_cards.json` and
`verification/units.json` but `""` in `verification/finish_units.json`. Every join site
compensated with `str(x or "")`, which is load-bearing and undocumented: a future join that
forgets it silently matches nothing rather than raising.

`""` is the canonical form. It composes into stable IDs and sorts predictably, whereas `null`
does neither. Run once; it is idempotent.

    python verification/passes/normalize_collector_numbers.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent

TARGETS = (
    ("snorlax_cards.json", "cards"),
    ("verification/units.json", None),
    ("verification/finish_units.json", "units"),
    ("verification/excluded_codecards.json", None),
)


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any, indent: int) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=indent)
        handle.write("\n")


def detect_indent(path: Path) -> int:
    """Reuse the file's existing indent so the migration does not reformat the whole file.

    These stores are written with different indents (`finishes.py` uses 2, the chronological
    exports use 1). Rewriting with the wrong one buries a five-line change in a 600k-line diff.
    """
    with path.open(encoding="utf-8-sig") as handle:
        for line in handle:
            stripped = line.lstrip(" ")
            if stripped and stripped != line and stripped[0] in '"{[':
                return len(line) - len(stripped)
    return 2


def main() -> None:
    total = 0
    for relative, key in TARGETS:
        path = ROOT / relative
        if not path.exists():
            print(f"skip {relative} (absent)")
            continue
        document = read_json(path)
        rows = document if key is None else document.get(key, [])
        if not isinstance(rows, list):
            print(f"skip {relative} (unexpected shape)")
            continue
        changed = 0
        for row in rows:
            if isinstance(row, dict) and "number" in row and row["number"] is None:
                row["number"] = ""
                changed += 1
        if changed:
            write_json(path, document, detect_indent(path))
        total += changed
        print(f"{relative}: normalized {changed} null collector numbers")
    print(f"total: {total}")


if __name__ == "__main__":
    main()

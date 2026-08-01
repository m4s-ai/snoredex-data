#!/usr/bin/env python3
"""Fixture tests for the JP illustrator parser (#33).

    python verification/test_jp_parser.py

The fixtures are pages captured unmodified from pokemon-card.com, one per shape that the old
text-matching parser got wrong, plus two basic cards it got right. Keeping the working case in
the set matters: the fix has to leave the 41 credits that were already correct alone.

Keeping the pages whole matters too. A trimmed fixture would no longer reproduce the flattening
that caused the defect, so it could not fail if the parser regressed to reading page text.

The old regex, run against these same fixtures, reproduces both corrupted credits exactly:

    card_37716_vmax.html  ->  'aky CG Works V進化'
    card_22277_lvx.html   ->  'Shizurow レベルアップ LV. X'

so these tests fail without the fix rather than passing vacuously.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jp_parse import illustrator  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "jp"

# The labels the old parser absorbed, asserted separately so a regression names its own cause.
UI_TOKENS = ("V進化", "レベルアップ", "LV. X", "たね", "HP", "ポケモン", "タイプ", "ワザ")

CASES = (
    ("card_22230_basic.html", "Kouki Saitou", "basic card"),
    ("card_26054_basic.html", "Kent Kanetsuna", "basic card"),
    ("card_37716_vmax.html", "aky CG Works", "VMAX, credit followed by V進化"),
    ("card_22277_lvx.html", "Shizurow", "Lv.X, credit followed by レベルアップ LV. X"),
)

results: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok)))
    print(f"[{'ok ' if ok else 'FAIL'}] {name}{f' - {detail}' if detail and not ok else ''}")


def main() -> int:
    for filename, expected, shape in CASES:
        path = FIXTURES / filename
        if not path.is_file():
            check(f"fixture present: {filename}", False, "missing")
            continue
        got = illustrator(path.read_text(encoding="utf-8"))
        check(f"{shape}: {filename}", got == expected, f"expected {expected!r}, got {got!r}")

        dirty = [t for t in UI_TOKENS if got and t in got]
        check(f"no UI label in {filename}", not dirty, ", ".join(dirty))

    # Truncation is the other half of the failure mode: the fix must not trade a contaminated
    # name for a clipped one. 'aky CG Works' is the dataset's longest credit at three tokens.
    multi = illustrator((FIXTURES / "card_37716_vmax.html").read_text(encoding="utf-8"))
    check("multi-word credit kept whole", multi == "aky CG Works", f"got {multi!r}")

    # Degenerate input must yield None rather than a partial or invented name.
    check("empty page yields None", illustrator("") is None)
    check("None input yields None", illustrator(None) is None)
    check("page without an author field yields None",
          illustrator("<html><body>イラストレーター Shizurow レベルアップ</body></html>") is None)
    check("author field without an anchor yields None",
          illustrator('<div class="author"><h4>イラストレーター</h4></div>') is None)
    check("whitespace-only credit yields None",
          illustrator('<div class="author"><a href="#">   </a></div>') is None)

    # Credits are studio names as often as personal ones, and those carry entities.
    check("entities decoded",
          illustrator('<div class="author"><a href="#">Ariga &amp; Co.</a></div>') == "Ariga & Co.")

    failures = [name for name, ok in results if not ok]
    print(f"\n{len(results) - len(failures)}/{len(results)} JP parser checks passed.")
    if failures:
        print("FAILED: " + ", ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

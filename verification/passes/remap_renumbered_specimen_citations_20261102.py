"""Point two specimen citations at their printing again after ordinal renumbering (2026-11-02).

Finish printing ids are ordinal within a finish unit. Folding a printing into its sibling renumbers
the rest, and a specimen's `citedBy` keeps naming the old id. The source registry then drops the
specimen, because it joins citations against current printing ids.

* SPEC-0396 (CGC "Pokémon Jungle / Holo", Japanese) cited F0255-P02, the cosmos holo. Folding the
  pattern-less marketplace claim into that printing (#457) made it F0255-P01.
* SPEC-0404 (CGC "Jungle - 11/64 / Holo", caption "Italian Unlimited") cited F0164-P03. The earlier
  edition fold left Italian Jungle 11 with a 1st Edition (P01) and an Unlimited (P02) printing.

Check R8 now fails on any dangling finish-printing citation. Idempotent; `--check` reports pending
remaps without writing.
"""
import json
import sys
from pathlib import Path

SPECIMENS = Path(__file__).resolve().parents[2] / "verification" / "specimens.json"
REMAPS = {"SPEC-0396": ("F0255-P02", "F0255-P01"), "SPEC-0404": ("F0164-P03", "F0164-P02")}


def main(argv) -> int:
    document = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    pending = [row for row in document["specimens"]
               if row["specimenId"] in REMAPS and REMAPS[row["specimenId"]][0] in (row.get("citedBy") or [])]
    if "--check" in argv:
        for row in pending:
            print("pending:", row["specimenId"], "->", REMAPS[row["specimenId"]][1])
        return 1 if pending else 0
    for row in pending:
        old, new = REMAPS[row["specimenId"]]
        row["citedBy"] = [new if cited == old else cited for cited in row["citedBy"]]
    if pending:
        SPECIMENS.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

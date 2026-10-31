"""Attach the retained image of the Japanese Expansion Sheet 1 vending Snorlax (#436).

The vending printing of `EXS` Snorlax (1998-03-23, Uncommon rarity symbol) carried `image: null`;
only the Quick Starter Gift Set printing had a picture. SPEC-0661 retains pokumon.com's image of the
vending card: No. 143 with the diamond Uncommon symbol and no CoroCoro contest credit, which tells
it apart from the Quick Starter card. The reviewed override row now names that image. The image
supports identity only; the printing's finish rests on its existing sources.

Idempotent; `--check` reports the pending image without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = ROOT / "verification" / "finish_overrides.json"
IMAGE = "verification/specimens/SPEC-0661.jpg"


def vending_printing(document: dict) -> dict:
    row = next(row for row in document["overrides"] if row.get("setCode") == "EXS" and row.get("printings"))
    return next(printing for printing in row["printings"]
                if (printing.get("distribution") or {}).get("kind") == "vending-sheet")


def main(argv) -> int:
    document = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    printing = vending_printing(document)
    pending = printing.get("image") != IMAGE
    if "--check" in argv:
        if pending:
            print("pending: EXS vending printing image")
        return 1 if pending else 0
    if pending:
        printing["image"] = IMAGE
        text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        # The store keeps one hand-written compact list; preserve it byte for byte.
        text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
        OVERRIDES.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

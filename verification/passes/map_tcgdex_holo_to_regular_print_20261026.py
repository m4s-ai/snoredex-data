"""Map TCGdex `holo: true` to the regular holo print for VIV 131, PGO 055 and SSH 142.

TCGdex states per card and language that a holo exists. For these three cards that holo is the
regular V1 print, which the official localized checklists already establish. Without a mapping
the flag became a second, unmapped holo printing with unknown size in every European language,
which looked like a possible jumbo. The owner's Cardmarket research of 2026-10-26 showed that the
V2 products of VIV 131 and PGO 055 are the stamped / Cosmos promos (SPEC-0648..0652), not jumbos.
`mapAutoFinishes` (already used for reverse-holo here) now maps holo to V1 as well, so the
TCGdex source attaches to the regular printing. English keeps its explicit printings.

Idempotent; `--check` reports pending mappings without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = ROOT / "verification" / "finish_overrides.json"
CARDS = [("VIV", "131"), ("PGO", "055"), ("SSH", "142")]


def target(document, set_code, number):
    return next((row for row in document["overrides"] if row.get("setCode") == set_code
                 and row.get("number") == number and "mapAutoFinishes" in row
                 and "languages" not in row), None)


def main(argv) -> int:
    document = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    pending = []
    for set_code, number in CARDS:
        row = target(document, set_code, number)
        if row is None or row["mapAutoFinishes"].get("holo") != ["V1"]:
            pending.append((set_code, number, row))
    if "--check" in argv:
        for set_code, number, _ in pending:
            print("pending: holo -> V1 for", set_code, number)
        return 1 if pending else 0
    for set_code, number, row in pending:
        if row is None:
            document["overrides"].append({"setCode": set_code, "number": number,
                                          "mapAutoFinishes": {"holo": ["V1"]}})
        else:
            row["mapAutoFinishes"]["holo"] = ["V1"]
    if pending:
        text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        # The store keeps one hand-written compact list; preserve it byte for byte.
        text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
        OVERRIDES.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Bridge two Korean Snorlax specimens filed under their printed numbers to the Cardmarket units.

* s2 77: SPEC-0239 (official Pokémon Korea render) is filed under the printed `077/096`, while
  Cardmarket files the card as `s2 77`. The specimen grouped under `077` and became a separate
  non-holo item of unknown card size beside F0352-P01, which already carries SPEC-0455. The
  collection owner confirmed on 2026-10-28 that both images show the same card ("die
  koreanischen karte zeigt beides mal die gleiche karte").
* sv4K 059: SPEC-0445 shows the Korean Snorlax Doll printed `060/066`, while Cardmarket files the
  product as `sv4K 059`, the Japanese number. The owner confirmed on 2026-10-28 that "die
  koreanischen Nummern und japanischen nummern können abweichen auch wenn der set code in beiden
  sprachen der selbe ist".

A releaseNumber bridge lets each specimen join the existing printing; same mechanism as the
Korean Kisstick bridge (167/XY-P -> XY-P 149). Idempotent; `--check` reports pending bridges
without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = ROOT / "verification" / "finish_overrides.json"
BRIDGES = [
    {"setCode": "s2", "releaseSetCode": "s2", "releaseNumber": "077", "number": "77",
     "languages": ["Korean"], "printings": []},
    {"setCode": "sv4K", "releaseSetCode": "sv4K", "releaseNumber": "060", "number": "059",
     "languages": ["Korean"], "printings": []},
]


def main(argv) -> int:
    document = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    pending = [bridge for bridge in BRIDGES if bridge not in document["overrides"]]
    if "--check" in argv:
        for bridge in pending:
            print("pending: Korean bridge", bridge["setCode"], bridge["number"], "<-", bridge["releaseNumber"])
        return 1 if pending else 0
    if pending:
        document["overrides"] += pending
        text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        # The store keeps one hand-written compact list; preserve it byte for byte.
        text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
        OVERRIDES.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Bridge the Indonesian Hop's Snorlax print code MA3 I to its Cardmarket finish unit m2a 136.

SPEC-0644 (a seller photograph found on Instagram, finish determined by the collection owner on
2026-10-24) is filed under the printed code `MA3 I 136/193`, while Cardmarket files the card as
`m2a 136` Indonesian. Without a releaseSetCode bridge the specimen cannot reach that finish unit,
which stays a research placeholder beside the new printing. Same mechanism as the existing
Traditional-Chinese (`M2a F`) and Thai (`MA3`) bridges for this card.

Idempotent; `--check` reports the pending bridge without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = ROOT / "verification" / "finish_overrides.json"
BRIDGE = {"setCode": "m2a", "releaseSetCode": "MA3 I", "number": "136", "languages": ["Indonesian"],
          "printings": []}


def main(argv) -> int:
    document = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    pending = BRIDGE not in document["overrides"]
    if "--check" in argv:
        if pending:
            print("pending: m2a 136 Indonesian bridge to MA3 I")
        return 1 if pending else 0
    if pending:
        document["overrides"].append(BRIDGE)
        text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        # The store keeps one hand-written compact list; preserve it byte for byte.
        text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
        OVERRIDES.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

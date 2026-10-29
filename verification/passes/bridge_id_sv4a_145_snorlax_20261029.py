"""Bridge the Indonesian Snorlax print code SV4a I 145/190 to its Cardmarket finish unit sv4a 145.

SPEC-0562 (Reverse Holo) and SPEC-0179 (Non-Holo) are filed under the printed code
`SV4a I 145/190`, while Cardmarket files the Indonesian card as `sv4a 145` (product V1). Without a
releaseSetCode bridge the reverse-holo specimen became a separate item of unknown card size beside
the marketplace-claimed reverse-holo printing F0474-P01. The collection owner approved joining
them on 2026-10-28 ("ja 3 so umsetzen"). Same mechanism as the Indonesian `MA3 I` bridge for
Hop's Snorlax.

Idempotent; `--check` reports the pending bridge without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = ROOT / "verification" / "finish_overrides.json"
BRIDGE = {"setCode": "sv4a", "releaseSetCode": "SV4a I", "number": "145", "variant": "V1",
          "languages": ["Indonesian"], "printings": []}


def main(argv) -> int:
    document = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    pending = BRIDGE not in document["overrides"]
    if "--check" in argv:
        if pending:
            print("pending: sv4a 145 Indonesian bridge to SV4a I")
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

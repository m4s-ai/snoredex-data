"""Record that Hong Kong and Taiwan share the Traditional-Chinese sets (owner, 2026-10-30).

The Asian locality matrix kept a separate `asia-hk` track with the gap
`official-asia-hk-market-provenance`: the retained TW-locale results and TWHK set-symbol assets
established Traditional-Chinese card identities but were said not to distinguish Taiwan from Hong
Kong distribution. The collection owner ruled: "HK und TW sind die selben Sets". There is one
Traditional-Chinese edition serving both markets, so there is no separate Hong Kong print identity
to discover and the gap asked a question with no answer in the data.

* The `asia-hk` track and its local gap are removed; `asia-tw` now names the shared edition.
* ADR-0001 records the decision as D6.

The decision concerns market scope only. It confirms no card, settles no disputed
Traditional-Chinese unit and asserts no absence. Idempotent; `--check` reports pending changes
without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "verification" / "asia_locality_matrix.json"
HK_TRACK = "asia-hk"
HK_GAP = "official-asia-hk-market-provenance"
TW_TRACK = {
    "label": "Traditional Chinese — Taiwan and Hong Kong (shared edition)",
    "retryCondition": (
        "Rerun bounded positive slices for deltas and retain unmatched rows; do not infer missing "
        "cards. Taiwan and Hong Kong share one Traditional-Chinese edition (owner, 2026-10-30), so "
        "no separate Hong Kong print identity is tracked."),
}


def pending_changes(document: dict) -> list[str]:
    changes = []
    if any(track["trackId"] == HK_TRACK for track in document["tracks"]):
        changes.append("remove the asia-hk track")
    if any(gap["gapId"] == HK_GAP for gap in document["localGaps"]):
        changes.append("remove the Hong Kong provenance gap")
    tw = next(track for track in document["tracks"] if track["trackId"] == "asia-tw")
    if any(tw.get(key) != value for key, value in TW_TRACK.items()):
        changes.append("name the shared edition on asia-tw")
    return changes


def main(argv) -> int:
    document = json.loads(MATRIX.read_text(encoding="utf-8"))
    changes = pending_changes(document)
    if "--check" in argv:
        for change in changes:
            print("pending:", change)
        return 1 if changes else 0
    if changes:
        document["tracks"] = [track for track in document["tracks"] if track["trackId"] != HK_TRACK]
        document["localGaps"] = [gap for gap in document["localGaps"] if gap["gapId"] != HK_GAP]
        next(track for track in document["tracks"] if track["trackId"] == "asia-tw").update(TW_TRACK)
        MATRIX.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Record the owner's decisions on the Marumiya / Kisstick Snorlax (XY-P 149 JA, 167/XY-P KR).

The collection owner ruled on 2026-10-23 that the card "is neither in Japanese nor in Korean
reverse holo" ("die karte ist weder in japanisch noch auf koreanisch reverse holo"). Both
reverse-holo rows rest only on the Cardmarket catalogue hint for product "Snorlax V1 XY-P149";
the Japanese face (SPEC-0587) and the owner's Korean photograph (SPEC-0031) are non-holo.

* Two owner finish decisions close the list at non-holo and reject reverse-holo (schema 1.2.0).
* The reviewed launch date of the withdrawn Japanese reverse-holo row is removed; the non-holo
  row keeps its own identical date.
* The Korean card prints 167/XY-P while its Cardmarket product is filed as XY-P 149, so a finish
  bridge with `releaseNumber` lets SPEC-0031 join the legacy finish unit instead of leaving that
  unit without any printing once the reverse-holo hint is removed.

Idempotent; `--check` reports pending records without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "verification"
ADJUDICATIONS = V / "owner_adjudications.json"
DATES = V / "confirmed_release_overrides.json"
# A reviewed date on a rejected printing would name an item that no longer exists.
WITHDRAWN_DATE_ITEMS = {"item-5f6fb249-fc93-523c-bcb7-c21c86c05e56"}
OVERRIDES = V / "finish_overrides.json"
QUOTE = "die karte ist weder in japanisch noch auf koreanisch reverse holo"
BRIDGE = {"setCode": "XY-P", "releaseSetCode": "XY-P", "releaseNumber": "167", "number": "149",
          "variant": "V1", "languages": ["Korean"], "printings": []}


def decision(language: str, specimen: str, printed: str) -> dict:
    return {
        "adjudicationId": f"OAF-20261023-XY-P-149-{'ja' if language == 'Japanese' else 'ko'}",
        "setCode": "XY-P",
        "number": "149",
        "language": language,
        "decision": "finish-complete",
        "availableFinishes": ["non-holo"],
        "rejectedFinishes": ["reverse-holo"],
        "authority": "collection-owner",
        "basis": "owner-adjudication",
        "decidedAt": "2026-10-23",
        "rationale": (
            f"The collection owner ruled on 2026-10-23 that {language} Snorlax {printed} (the "
            f"Marumiya / Kisstick food promotion card) exists only as non-holo: \"{QUOTE}\". The "
            "reverse-holo row rested only on the Cardmarket catalogue hint for product 'Snorlax V1 "
            f"XY-P149'; {specimen} shows the non-holo face. Recorded as an owner decision, never "
            "attributed to a provider."),
        "evidenceRefs": [f"specimen:{specimen}", "https://github.com/m4s-ai/snoredex-data/pull/433"],
    }


DECISIONS = [decision("Japanese", "SPEC-0587", "XY-P 149"), decision("Korean", "SPEC-0031", "167/XY-P")]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_overrides(document: dict) -> None:
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    # The store keeps one hand-written compact list; preserve it byte for byte.
    text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
    OVERRIDES.write_text(text, encoding="utf-8", newline="\n")


def main(argv) -> int:
    adjudications, overrides = read(ADJUDICATIONS), read(OVERRIDES)
    present = {row["adjudicationId"] for row in adjudications["finishDecisions"]}
    pending = [row for row in DECISIONS if row["adjudicationId"] not in present]
    bridge = BRIDGE not in overrides["overrides"]
    dates = read(DATES)
    rows = dates["releaseDates"]["reviewedItems"]
    stale = [row for row in rows if row["itemId"] in WITHDRAWN_DATE_ITEMS]
    if "--check" in argv:
        if stale:
            print("pending: reviewed date on the withdrawn reverse-holo row")
        for row in pending:
            print("pending:", row["adjudicationId"])
        if bridge:
            print("pending: XY-P 149 Korean bridge to 167/XY-P")
        return 1 if pending or bridge or stale else 0
    if stale:
        dates["releaseDates"]["reviewedItems"] = [row for row in rows if row not in stale]
        DATES.write_text(json.dumps(dates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if pending:
        adjudications["finishDecisions"] += pending
        ADJUDICATIONS.write_text(json.dumps(adjudications, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8", newline="\n")
    if bridge:
        overrides["overrides"].append(BRIDGE)
        write_overrides(overrides)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

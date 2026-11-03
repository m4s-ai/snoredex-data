"""Close three #438 finish groups by the owner's rarity rule (2026-11-03).

Owner decision (finishDecisions): the collection owner stated the rule of thumb behind Pokémon
finishes — "Grundsätzlich ist es FAST immer so - Ausnahmen bestätigen die Regel": Common and
Uncommon cards are Non-Holo, Rares are Non-Holo and/or Holo, Western sets add Reverse Holos to
those rarities, and Japanese and other Asian languages (except Simplified Chinese) mostly carry
Reverse Holos only in High Class and special sets, not in regular releases. The owner then chose which
candidate groups that rule closes; the rarity-R non-holo group was deliberately left open.

- s5a 093/070 (JP, KR, ID, TH): the card is the gold UR full art; Reverse Holos belong to C/U/R,
  so the Cardmarket reverse axis is rejected and the confirmed holo stands. The Traditional
  Chinese unit has no confirmed finish yet and is not closed (E13).
- s4 84 (Traditional Chinese): s4 is a regular release; the owner already rejected the reverse
  for the Japanese and Korean units on 2026-11-02 (OAF-20261102-S4-84-ja/-ko). The confirmed
  non-holo (TCGdex) and holo stand.
- xsv2a 143/165 (JP, KR): xsv2a is the Poké Ball / Master Ball mirror product; the plain card is
  sv2a 143, where non-holo is confirmed separately. The non-holo claim under xsv2a is rejected.

s10a stays open: it is an Enhanced Expansion Pack with a reverse-holo slot per pack (owner,
2026-11-03). Recorded as owner decisions, never attributed to a provider.

Idempotent; `--check` reports pending records without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADJUDICATIONS = ROOT / "verification" / "owner_adjudications.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
sys.path.insert(0, str(ROOT / "scripts"))
from atomic_write import atomic_write  # noqa: E402

DATE = "2026-11-03"
ISSUE = "https://github.com/m4s-ai/snoredex-data/issues/438"
RULE = (
    "The collection owner's rarity rule (2026-11-03, 'FAST immer so - Ausnahmen bestätigen die "
    "Regel'): Common and Uncommon cards are Non-Holo, Rares are Non-Holo and/or Holo, Reverse "
    "Holos accompany those rarities, and Japanese and other Asian languages except Simplified "
    "Chinese carry Reverse Holos mostly in High Class and special sets only. "
)
GROUPS = {
    "gold-ur": (
        ["holo"], ["reverse-holo"],
        "The card is the gold UR full art, outside the rarities that receive a Reverse Holo. The "
        "reverse row rested on the Cardmarket axis alone; the confirmed holo stands.",
    ),
    "regular-s4": (
        ["non-holo", "holo"], ["reverse-holo"],
        "s4 is a regular release without Reverse Holos, as the owner already decided for the "
        "Japanese and Korean units (OAF-20261102-S4-84-ja/-ko). The reverse row rested on the "
        "Cardmarket axis alone; the confirmed non-holo and holo stand.",
    ),
    "xsv2a-mirror": (
        ["mirror-holo"], ["non-holo"],
        "xsv2a is the Poké Ball and Master Ball mirror product; the plain card is sv2a 143, where "
        "non-holo is confirmed separately. The non-holo row under xsv2a rested on the Cardmarket "
        "axis alone; the confirmed mirrors stand.",
    ),
}
UNITS = [
    ("s5a", "93", "Japanese", "ja", "gold-ur"),
    ("s5a", "93", "Korean", "ko", "gold-ur"),
    ("s5a", "93", "Indonesian", "id", "gold-ur"),
    ("s5a", "93", "Thai", "th", "gold-ur"),
    ("s4", "84", "T-Chinese", "zh-hant", "regular-s4"),
    ("xsv2a", "143", "Japanese", "ja", "xsv2a-mirror"),
    ("xsv2a", "143", "Korean", "ko", "xsv2a-mirror"),
]


def main() -> int:
    check = "--check" in sys.argv
    document = json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))
    decisions = document.setdefault("finishDecisions", [])
    pending = []
    for set_code, number, language, tag, group in UNITS:
        available, rejected, closing = GROUPS[group]
        adjudication_id = f"OAF-{DATE.replace('-', '')}-{set_code.upper()}-{number}-{tag}"
        existing = next((d for d in decisions if d.get("adjudicationId") == adjudication_id), None)
        entry = {
            "adjudicationId": adjudication_id,
            "setCode": set_code,
            "number": number,
            "language": language,
            "decision": "finish-complete",
            "availableFinishes": available,
            "rejectedFinishes": rejected,
            "authority": "collection-owner",
            "basis": "owner-adjudication",
            "decidedAt": DATE,
            "rationale": RULE + closing + " Recorded as an owner decision, never attributed to a provider.",
            "evidenceRefs": [ISSUE],
        }
        if existing is not None and all(existing.get(k) == v for k, v in entry.items()):
            continue
        pending.append((existing, entry))
    # Rejecting the xsv2a non-holo row renumbers the Korean printings: the Poké Ball mirror that
    # SPEC-0061 cites moves from F0615-P03 to F0615-P02 (R8 keeps specimen citations resolvable).
    specimens = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    spec_0061 = next(s for s in specimens["specimens"] if s["specimenId"] == "SPEC-0061")
    stale_citation = "F0615-P03" in spec_0061["citedBy"]
    if not pending and not stale_citation:
        print("no pending records; owner decisions already present")
        return 0
    print(f"pending {len(pending)} decision(s): {[e['adjudicationId'] for _, e in pending]}"
          + ("; SPEC-0061 F0615-P03 -> F0615-P02" if stale_citation else ""))
    if check:
        return 1
    if stale_citation:
        spec_0061["citedBy"] = ["F0615-P02" if c == "F0615-P03" else c for c in spec_0061["citedBy"]]
        atomic_write(SPECIMENS, json.dumps(specimens, indent=2, ensure_ascii=False) + "\n")
    for existing, entry in pending:
        if existing is None:
            decisions.append(entry)
        else:
            existing.clear()
            existing.update(entry)
    atomic_write(ADJUDICATIONS, json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {ADJUDICATIONS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

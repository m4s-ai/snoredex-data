"""Settle #438 Japanese and Korean reverse-holo candidates with Quuador's list (2026-11-02).

Owner decision (finishDecisions): the collection owner read Quuador's "Sets and Languages:
Compilation overview list" as enumerating each set's variants, and noted that "Unbroken Bonds /
Double Blaze" names no Japanese or Korean Reverse Holo even though every Western language carries
one. He concluded that the Japanese and Korean releases of those sets have no reverse holo:
"unter 'Unbroken Bonds / Double Blaze' fehlt bei Japanese ein Reverse Holo eintrag, ergo kann man
daraus schließen das es kein Reverse Holo für sm10 auf japanisch und koreanisch gibt".

Retained excerpts (`verification/evidence/issue-438-quuador-sm-era-languages-20261102/excerpts.json`)
show the same shape for "Rebel Clash / Rebellion Crash" (s2) and "Vivid Voltage / Amazing Volt
Tackle" (s4), and keep two contrast sections (GG End, Sky Legend) that do write "Korean Reverse
Holo" — the list states the variant where it exists.

All four Japanese and Korean units of s4 84 and sm10 076 are settled too. The owner extended his
reading to them on the same evidence — "reverse holo ist doch jetzt widerlegt für die beiden sets
sowohl auf japanisch als auch koreanisch" — so `reverse-holo` is rejected there as well. Their
`non-holo` rests on the Cardmarket axis alone; it stays as it was, marketplace-claimed, and the
closed list names it because it survives the rejection.

Idempotent; `--check` reports pending records without writing.
"""
import json
import sys
from pathlib import Path

V = Path(__file__).resolve().parents[2] / "verification"
ADJUDICATIONS = V / "owner_adjudications.json"
DATE = "2026-11-02"
QUUADOR = "https://www.elitefourum.com/t/sets-and-languages-compilation-overview-list/16565"
EVIDENCE = "verification/evidence/issue-438-quuador-sm-era-languages-20261102/excerpts.json"
UNITS = [
    ("s2", "77", "Japanese", "ja", ["non-holo"]),
    ("s2", "77", "Korean", "ko", ["non-holo"]),
    ("s4", "84", "Japanese", "ja", ["holo"]),
    ("s4", "84", "Korean", "ko", ["holo"]),
    ("sm10", "076", "Japanese", "ja", ["holo"]),
    ("sm10", "076", "Korean", "ko", ["holo"]),
]
RATIONALE = (
    "Quuador's sets-and-languages list enumerates each set's variants and writes a Reverse Holo "
    "line only where the author records one: 'Rebel Clash / Rebellion Crash', 'Unbroken Bonds / "
    "Double Blaze' and 'Vivid Voltage / Amazing Volt Tackle' list English, German, "
    "French, Italian, Spanish and Portuguese Reverse Holo entries and none for Japanese or Korean, "
    "while the retained contrast sections (GG End, Sky Legend) do carry 'Korean Reverse Holo'. The "
    "collection owner concluded from that structure that the Japanese and Korean release has no "
    "reverse holo. "
)
# The two outcomes differ in what survives the rejection, so they cannot share one sentence: s2 keeps
# the confirmed non-holo, s4/sm10 lose the non-holo row as well. A single stored rationale that
# claimed "the confirmed non-holo stands" for all six contradicted its own s4/sm10 records.
CLOSING = {
    ("s2", "non-holo"): (
        "The reverse-holo row rested on the Cardmarket reverse axis alone; the confirmed non-holo "
        "stands. Recorded as an owner decision, never attributed to a provider."
    ),
    ("holo",): (
        "The reverse-holo row rested on the Cardmarket reverse axis alone. The non-holo row the "
        "Cardmarket axis also listed is rejected as well: every rare in this set was printed holo "
        "only, so the confirmed holo stands alone. Recorded as an owner decision, never attributed "
        "to a provider."
    ),
}


def main() -> int:
    check = "--check" in sys.argv
    document = json.loads(ADJUDICATIONS.read_text())
    decisions = document.setdefault("finishDecisions", [])
    pending = []
    for set_code, number, language, tag, available in UNITS:
        adjudication_id = f"OAF-{DATE.replace('-', '')}-{set_code.upper()}-{number}-{tag}"
        # s4 and sm10 carry the owner's second finding: every rare in those sets is holo only,
        # so the non-holo row the Cardmarket axis invented goes with it.
        rejected = ["reverse-holo"] if available == ["non-holo"] else ["non-holo", "reverse-holo"]
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
            "rationale": RATIONALE + CLOSING[(set_code, "non-holo") if available == ["non-holo"]
                                                                           else ("holo",)],
            "evidenceRefs": [QUUADOR, EVIDENCE,
                             "https://github.com/m4s-ai/snoredex-data/issues/438"],
        }
        if existing is not None and all(existing.get(k) == v for k, v in entry.items()):
            continue
        pending.append((existing, entry))
    if not pending:
        print("no pending records; owner decisions already present")
        return 0
    print(f"pending {len(pending)} decision(s): {[e['adjudicationId'] for _, e in pending]}")
    if check:
        return 1
    for existing, entry in pending:
        if existing is None:
            decisions.append(entry)
        else:
            existing.clear()
            existing.update(entry)
    ADJUDICATIONS.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {ADJUDICATIONS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

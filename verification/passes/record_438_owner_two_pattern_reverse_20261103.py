"""Close the two-pattern Simplified Chinese reverse claims as satisfied (#438, 2026-11-03).

151C 143/151 and CSV7C 158/204 each have a photographed Poké Ball and Master Ball reverse holo
(SPEC-0683/0684, SPEC-0690/0691) and a photographed non-holo (SPEC-0676, SPEC-0678). Cardmarket's
pattern-less reverse axis cannot say which ball it means, so the generator kept it as a candidate.
The collection owner decided on 2026-11-03 to close it as satisfied ("Als erfüllt schließen"):
the finish list of each unit is complete with non-holo and reverse holo, and under a closed list
the pattern-less claim is evidence for both photographed reverses instead of a third printing.

Recorded as owner decisions, never attributed to a provider. Idempotent; `--check` reports
pending records without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADJUDICATIONS = ROOT / "verification" / "owner_adjudications.json"
sys.path.insert(0, str(ROOT / "scripts"))
from atomic_write import atomic_write  # noqa: E402

ROUTES = ROOT / "verification" / "collector_migration_routes.json"
DATE = "2026-11-03"
RETIRED_REKEYS = {"151c-143-s-chinese-none-mirror-holo", "csv7c-158-s-chinese-none-mirror-holo"}
_151C = ["151c-143-s-chinese-none-reverse-holo-master-ball", "151c-143-s-chinese-none-reverse-holo-poke-ball"]
_CSV7C = ["csv7c-158-s-chinese-none-reverse-holo-master-ball", "csv7c-158-s-chinese-none-reverse-holo-poke-ball"]
SPLITS = {  # retired pattern-less item -> the two photographed ball printings
    "item-f83e75d1-bc85-5ab7-a7e8-512d256ccf93": _151C,   # guide "mirror"
    "item-fd6f8218-8dd9-5986-8331-4f445793abce": _151C,   # Cardmarket reverse candidate
    "item-ba7860ab-0269-50d5-ab9c-b9cfc94d1cc2": _CSV7C,  # guide "mirror"
    "item-e98b65ce-5025-5cb8-8f69-3235700d7fa9": _CSV7C,  # Cardmarket reverse candidate
}
SPLIT_REASON = ("Pattern-less reverse satisfied by both photographed Poké Ball and Master Ball printings "
                "(owner, 2026-11-03, #438).")
UNITS = [("151C", "143", "SPEC-0683, SPEC-0684, SPEC-0676"), ("CSV7C", "158", "SPEC-0690, SPEC-0691, SPEC-0678")]



def main() -> int:
    check = "--check" in sys.argv
    document = json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))
    decisions = document.setdefault("finishDecisions", [])
    pending = []
    for set_code, number, specimens in UNITS:
        entry = {
            "adjudicationId": f"OAF-{DATE.replace('-', '')}-{set_code.upper()}-{number}-zh-hans",
            "setCode": set_code,
            "number": number,
            "language": "S-Chinese",
            "decision": "finish-complete",
            "availableFinishes": ["non-holo", "reverse-holo"],
            "authority": "collection-owner",
            "basis": "owner-adjudication",
            "decidedAt": DATE,
            "rationale": (
                f"Photographs establish a non-holo and a Poké Ball and a Master Ball reverse holo ({specimens}). "
                "The pattern-less Cardmarket reverse axis cannot name its ball; the collection owner closed "
                "the list as satisfied on 2026-11-03 ('Als erfüllt schließen'), so the claim supports both "
                "photographed reverses rather than a third printing. Recorded as an owner decision, never "
                "attributed to a provider."
            ),
            "evidenceRefs": ["https://github.com/m4s-ai/snoredex-data/issues/438"],
        }
        existing = next((d for d in decisions if d.get("adjudicationId") == entry["adjudicationId"]), None)
        if existing == entry:
            continue
        pending.append((existing, entry))
    # The pattern-less rows these decisions retire map to both photographed balls: a 1:N item split
    # (state needs the collector's choice), replacing the 1:1 rekeys this session first wrote.
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))
    stale_rekeys = [r for r in routes["cumulativeChecklistRekeys"] if r["from"] in RETIRED_REKEYS]
    known_splits = {row["fromItemId"] for row in routes["itemSplits"]}
    new_splits = [(item, targets) for item, targets in SPLITS.items() if item not in known_splits]
    if not pending and not stale_rekeys and not new_splits:
        print("no pending records; owner decisions already present")
        return 0
    print(f"pending {len(pending)} decision(s): {[e['adjudicationId'] for _, e in pending]}; "
          f"{len(stale_rekeys)} rekey(s) to retire; {len(new_splits)} item split(s)")
    if check:
        return 1
    if stale_rekeys or new_splits:
        # Line-level edits keep the file's layout: one rekey per line, one split per block.
        text = ROUTES.read_text(encoding="utf-8")
        for row in stale_rekeys:
            text = text.replace(",\n    " + json.dumps(row, ensure_ascii=False), "")
        blocks = "".join(
            ",\n    {\n      \"fromItemId\": " + json.dumps(item)
            + ",\n      \"toLegacyChecklistIds\": " + json.dumps(targets, ensure_ascii=False)
            + ",\n      \"reason\": " + json.dumps(SPLIT_REASON, ensure_ascii=False) + "\n    }"
            for item, targets in new_splits)
        end = text.rindex("\n  ]\n}")
        text = text[:end] + blocks + text[end:]
        parsed = json.loads(text)
        assert not any(r["from"] in RETIRED_REKEYS for r in parsed["cumulativeChecklistRekeys"])
        atomic_write(ROUTES, text)
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

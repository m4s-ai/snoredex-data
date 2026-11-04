"""Drop regulation marks recorded as print-identity markings (#438, 2026-11-03).

SPEC-0149 (CSZC 018) and SPEC-0153 (CSUC 010) stored the boxed "F" as an observed
`print-identity` marking. The collection owner clarified on 2026-11-03 that this F is the
regulation mark for competitive TCG events, printed on every card of the set, and no part of
the number or language (an F after the set code, as in "S10a F", marks Traditional Chinese).
A mark every copy carries distinguishes no printing, and as a marking it kept the CSZC 018
Cardmarket reverse claim from folding into the photographed confetti reverse holo.

The owner also confirmed CSZC 018 as a reverse holo: the foil does not cover the artwork, while
the printed confetti runs across it, so its pattern description stands.

Reviewed collector routes carry the renamed checklist ids. Idempotent; `--check` reports
pending changes without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECIMENS = ROOT / "verification" / "specimens.json"
ROUTES = ROOT / "verification" / "collector_migration_routes.json"
sys.path.insert(0, str(ROOT / "scripts"))
from atomic_write import atomic_write  # noqa: E402

TARGETS = ("SPEC-0149", "SPEC-0153")
REASON = "A regulation mark distinguishes no printing (owner, 2026-11-03, #438)."
CSZC = "cszc-018-s-chinese-none-reverse-holo-multicolour-sparkle-across-artwork-and-frame"
ROUTE_ROWS = [
    (CSZC + "-observed-marking-f-regulation-mark", CSZC, REASON),
    ("cszc-018-s-chinese-none-reverse-holo", CSZC,
     "The pattern-less Cardmarket reverse claim folds into the one photographed pattern "
     "(owner decision 2026-11-03, #438)."),
    ("csuc-010-s-chinese-none-holo-observed-marking-f-regulation-mark",
     "csuc-010-s-chinese-none-holo", REASON),
]


def main() -> int:
    check = "--check" in sys.argv
    specimens = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    routes_text = ROUTES.read_text(encoding="utf-8")
    routes = json.loads(routes_text)
    pending = []

    for spec in specimens["specimens"]:
        observation = spec.get("physicalObservation") or {}
        if spec["specimenId"] in TARGETS and "markings" in observation:
            pending.append(f"{spec['specimenId']}: drop regulation-mark marking")
            observation.pop("markings")
            observation.pop("markingRole", None)

    known = {row["from"] for row in routes["cumulativeChecklistRekeys"]}
    new_rows = [row for row in ROUTE_ROWS if row[0] not in known]
    pending += [f"route {old} -> {new}" for old, new, _ in new_rows]

    if not pending:
        print("no pending changes; regulation marks already dropped")
        return 0
    print(f"pending {len(pending)} change(s):", *pending, sep="\n  ")
    if check:
        return 1
    atomic_write(SPECIMENS, json.dumps(specimens, indent=2, ensure_ascii=False) + "\n")
    if new_rows:
        # The routes file keeps one route per line; append inside the rekey array.
        anchor = '\n  ],\n  "cardReleaseRekeys"'
        lines = "".join(
            ",\n    " + json.dumps({"from": old, "to": new, "reason": reason}, ensure_ascii=False)
            for old, new, reason in new_rows
        )
        index = routes_text.index(anchor)
        routes_text = routes_text[:index] + lines + routes_text[index:]
        json.loads(routes_text)
        atomic_write(ROUTES, routes_text)
    print("wrote", SPECIMENS.name, "and", ROUTES.name if new_rows else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())

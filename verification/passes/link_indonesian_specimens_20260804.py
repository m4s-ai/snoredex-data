#!/usr/bin/env python3
"""Point the two Indonesian adjudications at the photograph that backs them.

The decisions on #89 were recorded before the images could be examined, so their `evidenceRefs`
name the issue thread and nothing else. SPEC-0013 now records both mirror patterns on one card
photograph — the owner's correction established that the faint left pattern is the Poké Ball and
the right is the Master Ball — so the reference runs one way only: the specimen names the units,
the units do not name the specimen.

That asymmetry is the kind that rots. A reader auditing U0777 sees an issue link and a rationale
quoting the owner, with no route to the photograph sitting in the repository that shows the card.
SPEC-0012 is included for the same reason: it is the sealed single of the same promo.

This does not change any decision or any status. It records where the evidence lives.

Idempotent: re-running adds nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADJUDICATIONS = ROOT / "verification" / "owner_adjudications.json"

# unitId -> specimen references to add, in order.
LINKS = {
    "U0782": ["specimen:SPEC-0013", "specimen:SPEC-0012"],
    "U0777": ["specimen:SPEC-0013", "specimen:SPEC-0012"],
}


def main() -> None:
    document = json.loads(ADJUDICATIONS.read_text(encoding="utf-8-sig"))
    specimens = {
        s["specimenId"]
        for s in json.loads(
            (ROOT / "verification" / "specimens.json").read_text(encoding="utf-8-sig")
        )["specimens"]
    }

    added = 0
    for decision in document["decisions"]:
        wanted = LINKS.get(decision["unitId"])
        if not wanted:
            continue
        for ref in wanted:
            sid = ref.split(":", 1)[1]
            if sid not in specimens:
                raise SystemExit(f"{decision['unitId']} would cite unknown specimen {sid}")
            if ref not in decision["evidenceRefs"]:
                decision["evidenceRefs"].append(ref)
                added += 1

    if added:
        ADJUDICATIONS.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Added {added} specimen reference(s) to {len(LINKS)} Indonesian adjudication(s).")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Record the reviewed evidence scope on every legacy language unit (#351).

``units.json`` is the state store, so this migration adds the structured
``evidenceGranularity`` value without changing a verdict, source, or evidence text. The legacy
classifier is used only while this pass fills the new field. Once present, the projection reads the
field and treats ``sourceType`` as display/search text.

    python verification/passes/structure_evidence_granularity_20260907.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UNITS = ROOT / "verification" / "units.json"

sys.path.insert(0, str(ROOT))
from scripts.evidence_semantics import (  # noqa: E402
    CLOSED_LIST_SOURCE,
    EVIDENCE_GRANULARITIES,
    legacy_granularity,
)


def main() -> int:
    units = json.loads(UNITS.read_text(encoding="utf-8-sig"))
    changed = 0
    counts: Counter[str] = Counter()
    for unit in units:
        value = unit.get("evidenceGranularity")
        if value is None:
            value = legacy_granularity(unit)
            unit["evidenceGranularity"] = value
            changed += 1
        elif value not in EVIDENCE_GRANULARITIES:
            print(f"{unit.get('unitId')}: invalid evidenceGranularity {value!r}", file=sys.stderr)
            return 1
        if "evidenceIncludesCardList" not in unit:
            unit["evidenceIncludesCardList"] = bool(
                CLOSED_LIST_SOURCE.search(unit.get("sourceType") or "")
            )
            changed += 1
        elif not isinstance(unit["evidenceIncludesCardList"], bool):
            print(
                f"{unit.get('unitId')}: evidenceIncludesCardList must be boolean",
                file=sys.stderr,
            )
            return 1
        counts[value] += 1

    if changed:
        UNITS.write_text(json.dumps(units, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"recorded structured evidence fields on {changed} unit(s); {len(units)} total")
    for value in sorted(counts):
        print(f"  {value:18} {counts[value]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

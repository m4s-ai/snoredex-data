#!/usr/bin/env python3
"""Repair the reviewed CardRelease-to-Work state defect from producer issue #304.

The affected releases carry no reviewed Work relation.  They therefore remain
``needs-explicit-equivalence`` until a positive equivalence decision exists; this
pass never invents a Work id.  The precondition is deliberately exact so a future
graph change cannot silently broaden the repair.

    python verification/passes/repair_issue304_work_mapping_20260825.py
    python verification/passes/repair_issue304_work_mapping_20260825.py --check
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "verification" / "authoritative_graph.json"
REVIEWED_AT = "2026-08-25"
EXPECTED_RELEASES = frozenset({
    "RELEASE:JP:Japanese:DP-P:126:None",
    "RELEASE:JP:Japanese:DP-P:127:None",
    "RELEASE:JP:Japanese:UNP:unnumbered:None",
    "RELEASE:KR:Korean:via-DP-P:unknown-local-set:via-127:None:unknown-local-id",
    "RELEASE:WEST:English:RR:111:None",
    "RELEASE:WEST:French:RR:111:None",
    "RELEASE:WEST:German:RR:111:None",
    "RELEASE:WEST:Italian:RR:111:None",
})


def read_graph() -> dict:
    return json.loads(GRAPH.read_text(encoding="utf-8"))


def write_graph(graph: dict) -> None:
    with GRAPH.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(graph, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def affected_releases(graph: dict) -> set[str]:
    return {
        row["entityId"]
        for row in graph.get("entities", [])
        if row.get("entityType") == "card-release"
        and row.get("payload", {}).get("workMappingState") == "mapped"
        and row.get("payload", {}).get("work") is None
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the repair is applied")
    args = parser.parse_args()

    graph = read_graph()
    affected = affected_releases(graph)
    if args.check:
        if affected:
            raise SystemExit(f"issue #304 repair is incomplete: {sorted(affected)}")
        print("issue #304 work-mapping repair: OK")
        return 0

    if affected != EXPECTED_RELEASES:
        raise SystemExit(
            "issue #304 precondition changed; expected exactly the reviewed releases, "
            f"found {sorted(affected)}"
        )
    changed = 0
    for row in graph["entities"]:
        if row.get("entityType") == "card-release" and row.get("entityId") in EXPECTED_RELEASES:
            payload = row["payload"]
            if payload.get("work") is not None or payload.get("workMappingState") != "mapped":
                raise SystemExit(f"issue #304 precondition failed: {row['entityId']}")
            payload["workMappingState"] = "needs-explicit-equivalence"
            changed += 1
    graph["meta"]["generated"] = REVIEWED_AT
    write_graph(graph)
    print(f"issue #304 work-mapping repair: changed {changed} releases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

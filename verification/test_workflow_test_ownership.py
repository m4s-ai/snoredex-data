#!/usr/bin/env python3
"""Validate the single-owner test matrix and its gate boundaries."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "verification" / "workflow_test_ownership.json"
sys.path.insert(0, str(ROOT))
from scripts import regen  # noqa: E402


def main() -> int:
    document = json.loads(MATRIX.read_text(encoding="utf-8"))
    tests = document["tests"]
    commands = [tuple(row) for row in (test["command"] for test in tests)]
    expected = [tuple(row) for row in regen.TESTS]
    assert len(commands) == len(expected), (len(commands), len(expected))
    assert set(commands) == set(expected), "matrix and regen.TESTS command sets differ"
    assert len(commands) == len(set(commands)), "a core command has multiple ownership rows"
    assert len({test["id"] for test in tests}) == len(tests), "test IDs must be unique"
    assert all(isinstance(test["primaryOwner"], str) and test["primaryOwner"]
               for test in tests), "every test needs one primaryOwner"

    fixtures = document["fixtureRegistry"]
    fixture_ids = [fixture["id"] for fixture in fixtures]
    assert len(fixture_ids) == len(set(fixture_ids)), "fixture IDs must be unique"
    owners = {test["primaryOwner"] for test in tests}
    assert all(fixture["owner"] in owners for fixture in fixtures)
    for test in tests:
        assert set(test["fixtures"]).issubset(fixture_ids), test["id"]
        assert test["boundary"] in {"import", "projection", "cross-artifact"}, test["id"]
        assert test["gateLevel"] in {"L0", "L1", "L2"}, test["id"]
    assert "--check-only selected CHECK entries" in next(
        test["strategy"] for test in tests if test["id"] == "regen-readiness"
    )

    required_boundaries = {"import", "projection", "cross-artifact", "browser", "live", "publish"}
    assert set(document["gateBoundaries"]) == required_boundaries
    external = document["externalGates"]
    assert {gate["boundary"] for gate in external} == {"browser", "live", "publish"}
    assert len({gate["id"] for gate in external}) == len(external)

    counts = Counter(test["boundary"] for test in tests)
    print(f"workflow test ownership passed: {len(tests)} core tests, {len(fixtures)} shared fixtures, "
          f"boundaries={dict(sorted(counts.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

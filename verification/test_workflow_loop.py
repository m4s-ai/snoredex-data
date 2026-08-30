#!/usr/bin/env python3
"""Regression tests for bounded workflow-loop state and stop semantics."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "verification" / "workflow_loop_manifest.json"
LOOP = ROOT / "scripts" / "workflow_loop.py"


def remove_empty(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        pass


def main() -> int:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    loops = {loop["id"]: loop for loop in document["loops"]}
    assert set(loops) == {"physical", "evidence", "discovery", "news-promo", "tcgdex", "absence", "cardmarket"}
    assert document["loopContract"]["positiveEvidence"].startswith("No loop may turn")
    assert document["loopContract"]["mergeBoundary"].endswith("L3 merge gate.")
    for loop in loops.values():
        assert loop["initial"] in loop["states"]
        assert set(loop["terminal"]).issubset(loop["states"])
        assert loop["lane"] in {"physical-evidence", "correction", "source-discovery", "finish-refresh", "absence"}
        assert set(loop["dependsOn"]).issubset(loops)
        assert loop["gateLevel"] == "L0-L2 scoped lane; L3 merge gate"
        assert loop["retry"]

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(loop_id: str) -> None:
        assert loop_id not in visiting, f"workflow-loop dependency cycle at {loop_id}"
        if loop_id in visited:
            return
        visiting.add(loop_id)
        for dependency in loops[loop_id]["dependsOn"]:
            visit(dependency)
        visiting.remove(loop_id)
        visited.add(loop_id)

    for loop_id in loops:
        visit(loop_id)

    reports = [
        ROOT / "verification" / "cache" / "workflow-loops" / "test-loop-evidence.json",
        ROOT / "verification" / "cache" / "workflow-loops" / "test-loop-tcgdex.json",
        ROOT / "verification" / "cache" / "workflow-loops" / "test-loop-physical.json",
        ROOT / "verification" / "cache" / "workflow-loops" / "test-loop-discovery.json",
    ]
    for report in reports:
        report.unlink(missing_ok=True)
    try:
        evidence = subprocess.run([
            sys.executable, str(LOOP), "--loop", "evidence", "--run-id", "test-loop-evidence",
            "--out", str(reports[0]),
        ], cwd=ROOT, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert evidence.returncode == 0, evidence.stdout
        evidence_report = json.loads(reports[0].read_text(encoding="utf-8"))
        assert evidence_report["cycleCount"] == 0
        assert evidence_report["stateAfter"]["state"] == "needs-evidence"
        assert "requires external input" in evidence_report["stopReason"]

        tcgdex = subprocess.run([
            sys.executable, str(LOOP), "--loop", "tcgdex", "--include-live", "--dry-run",
            "--run-id", "test-loop-tcgdex", "--out", str(reports[1]),
        ], cwd=ROOT, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert tcgdex.returncode == 0, tcgdex.stdout
        tcgdex_report = json.loads(reports[1].read_text(encoding="utf-8"))
        assert tcgdex_report["cycleCount"] == 1
        assert tcgdex_report["cycles"][0]["lane"]["reason"] == "dry-run"
        assert tcgdex_report["stateAfter"] == tcgdex_report["stateBefore"]
        assert "L3 merge gate" in tcgdex_report["mergeBoundary"]

        physical = subprocess.run([
            sys.executable, str(LOOP), "--loop", "physical", "--dry-run",
            "--run-id", "test-loop-physical", "--out", str(reports[2]),
        ], cwd=ROOT, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert physical.returncode == 0, physical.stdout
        physical_report = json.loads(reports[2].read_text(encoding="utf-8"))
        assert physical_report["stateBefore"]["progress"]["activeSpecimenCount"] > 0
        assert physical_report["stateBefore"]["state"] == "observed"
        assert physical_report["cycleCount"] == 1
        assert physical_report["cycles"][0]["lane"]["reason"] == "dry-run"

        discovery = subprocess.run([
            sys.executable, str(LOOP), "--loop", "discovery", "--include-live", "--dry-run",
            "--run-id", "test-loop-discovery", "--out", str(reports[3]),
        ], cwd=ROOT, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert discovery.returncode == 0, discovery.stdout
        discovery_report = json.loads(reports[3].read_text(encoding="utf-8"))
        progress = discovery_report["stateBefore"]["progress"]
        if progress["blockedGaps"] and progress["needsSourceGaps"]:
            statuses = (progress["sourceStatus"], progress["cardStatus"])
            expected_state = (
                "retained" if any(status != "complete" for status in statuses)
                else "blocked-by-source"
            )
            assert discovery_report["stateBefore"]["state"] == expected_state
            assert discovery_report["cycleCount"] == 1
            assert discovery_report["cycles"][0]["lane"]["reason"] == "dry-run"
    finally:
        for report in reports:
            report.unlink(missing_ok=True)
        remove_empty(reports[0].parent)
        remove_empty(reports[0].parent.parent)

    print(f"workflow loop contract passed: {len(loops)} loops, bounded stop semantics and positive-evidence guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

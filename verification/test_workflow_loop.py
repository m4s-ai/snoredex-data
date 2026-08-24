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


def main() -> int:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    loops = {loop["id"]: loop for loop in document["loops"]}
    assert set(loops) == {"evidence", "discovery", "tcgdex", "absence"}
    assert document["loopContract"]["positiveEvidence"].startswith("No loop may turn")
    assert document["loopContract"]["mergeBoundary"].endswith("L3 merge gate.")
    for loop in loops.values():
        assert loop["initial"] in loop["states"]
        assert set(loop["terminal"]).issubset(loop["states"])
        assert loop["lane"] in {"correction", "source-discovery", "finish-refresh", "absence"}

    reports = [
        ROOT / "verification" / "cache" / "workflow-loops" / "test-loop-evidence.json",
        ROOT / "verification" / "cache" / "workflow-loops" / "test-loop-tcgdex.json",
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
    finally:
        for report in reports:
            report.unlink(missing_ok=True)

    print(f"workflow loop contract passed: {len(loops)} loops, bounded stop semantics and positive-evidence guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

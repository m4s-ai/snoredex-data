#!/usr/bin/env python3
"""Regression tests for manifest-defined scoped workflow lanes."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "verification" / "scoped_pipeline_manifest.json"
MATRIX = ROOT / "verification" / "workflow_gate_matrix.json"


def remove_empty(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        pass


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    lanes = {lane["id"]: lane for lane in manifest["lanes"]}
    assert set(lanes) == {"physical-evidence", "source-discovery", "finish-refresh", "correction", "absence"}
    assert manifest["fullGate"] == ["python", "scripts/regen.py", "--check"]
    assert manifest["runContract"]["defaultNetwork"] is False
    source_steps = {step["id"] for step in lanes["source-discovery"]["steps"]}
    assert {"source-registry-check", "source-capabilities-check"} <= source_steps

    # Lane dependencies are a DAG, and every command is an existing repository-owned script.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(lane_id: str) -> None:
        if lane_id in visiting:
            raise AssertionError(f"lane dependency cycle at {lane_id}")
        if lane_id in visited:
            return
        visiting.add(lane_id)
        for dependency in lanes[lane_id]["dependsOn"]:
            assert dependency in lanes or dependency in {"known-card-confirmation"}, dependency
            if dependency in lanes:
                visit(dependency)
        visiting.remove(lane_id)
        visited.add(lane_id)

    for lane_id, lane in lanes.items():
        visit(lane_id)
        for impact in lane["impactClasses"]:
            assert impact in matrix["impactClasses"], impact
        for step in lane["steps"]:
            command_path = ROOT / step["command"][0]
            assert command_path.is_file(), step["command"]
            assert step["gateLevel"] in {"L0", "L1", "L2"}
            if step.get("network"):
                assert "--refresh" in step["command"]

    report_path = ROOT / "verification" / "cache" / "scoped-test-lane.json"
    report_path.unlink(missing_ok=True)
    try:
        command = [
            sys.executable, str(ROOT / "scripts" / "scoped_regen.py"),
            "--lane", "finish-refresh", "--dry-run", "--run-id", "test-scoped-lane",
            "--out", str(report_path),
        ]
        first = subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8",
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert first.returncode == 0, first.stdout
        first_report = json.loads(report_path.read_text(encoding="utf-8"))
        second = subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8",
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert second.returncode == 0, second.stdout
        second_report = json.loads(report_path.read_text(encoding="utf-8"))
        for report in (first_report, second_report):
            assert report["runId"] == "test-scoped-lane"
            assert report["summary"] == {"steps": 4, "passed": 0, "failed": 0, "notRun": 4, "durationMs": 0.0}
            assert report["fullGate"] == manifest["fullGate"]
            assert any("dry-run" in reason for reason in report["skippedChecks"])
        first_report.pop("generatedAt")
        second_report.pop("generatedAt")
        assert first_report == second_report, "same pinned scoped run must be idempotent"
    finally:
        report_path.unlink(missing_ok=True)
        remove_empty(report_path.parent)
        remove_empty(report_path.parent.parent)

    print(f"scoped regen contract passed: {len(lanes)} lanes, {sum(len(lane['steps']) for lane in lanes.values())} steps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

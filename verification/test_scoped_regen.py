#!/usr/bin/env python3
"""Regression tests for manifest-defined scoped workflow lanes."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "verification" / "scoped_pipeline_manifest.json"
MATRIX = ROOT / "verification" / "workflow_gate_matrix.json"
sys.path.insert(0, str(ROOT))
from scripts import regen, scoped_regen


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    lanes = {lane["id"]: lane for lane in manifest["lanes"]}
    assert set(lanes) == {"physical-evidence", "source-discovery", "finish-refresh", "correction", "absence"}
    assert manifest["fullGate"] == ["python", "scripts/regen.py", "--check"]
    assert manifest["runContract"]["defaultNetwork"] is False
    # A checkpoint must materialize the reference consumers that used to require a full build.
    consumers = {"source_registry", "source_capabilities", "authoritative_graph", "artwork_review", "checklist", "collector_catalogue"}
    for lane in lanes.values():
        commands = [step["command"] for step in lane["steps"]]
        assert consumers <= {Path(cmd[0]).stem for cmd in commands}
        writes = [cmd for cmd in commands if cmd in regen.REGEN]
        assert writes == [cmd for cmd in regen.REGEN if cmd in writes], "reuse the normative dependency order"
        assert len({tuple(cmd) for cmd in commands}) == len(commands), "one execution per checkpoint"
        assert not any(Path(cmd[0]).stem in {"regen", "review_findings", "database", "site", "tracker"}
                       or "--refresh" in cmd for cmd in commands), "delivery/network work is not intake"
    source_commands = [step["command"] for step in lanes["source-discovery"]["steps"]]
    assert ["scripts/source_capabilities.py"] in source_commands
    assert ["scripts/card_discovery.py"] in source_commands

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

    with tempfile.TemporaryDirectory() as directory:
        report_path = Path(directory) / "scoped-test-lane.json"
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
            count = len(lanes["finish-refresh"]["steps"])
            assert report["summary"] == {"steps": count, "passed": 0, "failed": 0, "notRun": count, "durationMs": 0.0}
            assert report["fullGate"] == manifest["fullGate"]
            assert any("dry-run" in reason for reason in report["skippedChecks"])
        first_report.pop("generatedAt")
        second_report.pop("generatedAt")
        first_report.pop("wallDurationMs")
        second_report.pop("wallDurationMs")
        assert first_report == second_report, "same pinned scoped run must be idempotent"

        # A failed projection may not be concealed by green checks or consumers built afterward.
        with mock.patch.object(sys, "argv", ["scoped_regen.py", "--lane", "physical-evidence", "--out", str(report_path)]), \
                mock.patch.object(scoped_regen, "run_step", return_value={"status": "failed", "returnCode": 7}) as run, \
                mock.patch.object(scoped_regen, "tree_snapshot", return_value={}):
            assert scoped_regen.main() == 1
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert run.call_count == 1
        assert report["summary"]["failed"] == 1
        assert all(row["reason"] == "previous step failed" for row in report["steps"][1:])

    print(f"scoped regen contract passed: {len(lanes)} lanes, {sum(len(lane['steps']) for lane in lanes.values())} steps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

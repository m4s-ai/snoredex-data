#!/usr/bin/env python3
"""Regression tests for bounded workflow-loop state and stop semantics."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "verification" / "workflow_loop_manifest.json"
LOOP = ROOT / "scripts" / "workflow_loop.py"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow_loop import (  # noqa: E402
    _cycle_commands, _discovery_cycle_stop_reason, _discovery_refresh_command, _discovery_replay_command,
    _discovery_summary,
    _discovery_replay_commands, _discovery_state, _next_discovery_run_id, _next_replay_run_id,
    _completeness_matches_inputs, _should_skip_terminal_state, _staging_matches_inputs,
    _records_projection_matches, _read_staging, _source_staging_matches_inputs,
    _stale_discovery_run, _stale_source_run,
    latest_manifests,
)


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

    canonical = {"runId": "run-1", "status": "complete"}
    staging_meta = {
        "generatedFromRun": "run-1",
        "contractHash": "contract-1",
        "capabilityGraphHash": "capability-1",
        "authoritativeGraphHash": "graph-1",
    }
    assert _staging_matches_inputs(staging_meta, canonical, "contract-1", "capability-1", "graph-1")
    stale_hashes = (
        ("generatedFromRun", "run-2"),
        ("contractHash", "contract-2"),
        ("capabilityGraphHash", "capability-2"),
        ("authoritativeGraphHash", "graph-2"),
    )
    for field, value in stale_hashes:
        stale_meta = {**staging_meta, field: value}
        assert not _staging_matches_inputs(
            stale_meta, canonical, "contract-1", "capability-1", "graph-1"
        )
    with tempfile.TemporaryDirectory(dir=ROOT) as raw_records:
        records_path = Path(raw_records) / "records.jsonl"
        records_bytes = b'{"recordId":"record-1"}\n'
        records_path.write_bytes(records_bytes)
        records_hash = "sha256:" + hashlib.sha256(records_bytes).hexdigest()
        records_projection = {
            "recordsHash": records_hash,
        }
        assert _records_projection_matches(records_projection, records_path)
        source_canonical = {"runId": "source-run-1"}
        source_staging = {
            "meta": {
                "generatedFromRun": "source-run-1",
                "contractHash": "source-contract-1",
                "capabilityGraphHash": "source-capability-1",
            },
            "recordsHash": records_hash,
        }
        assert _source_staging_matches_inputs(
            source_staging, records_path, source_canonical,
            "source-contract-1", "source-capability-1",
        )
        for field, value in (
            ("generatedFromRun", "older-run"),
            ("contractHash", "changed-contract"),
            ("capabilityGraphHash", "changed-capabilities"),
        ):
            stale_staging = {
                **source_staging,
                "meta": {**source_staging["meta"], field: value},
            }
            assert not _source_staging_matches_inputs(
                stale_staging, records_path, source_canonical,
                "source-contract-1", "source-capability-1",
            )
        missing_staging_path = Path(raw_records) / "missing-staging.json"
        assert _read_staging(missing_staging_path) == {}
        missing_staging_path.write_text("{truncated", encoding="utf-8")
        assert _read_staging(missing_staging_path) == {}
        missing_staging_path.write_text("[]", encoding="utf-8")
        assert _read_staging(missing_staging_path) == {}
        records_path.write_bytes(b'{"recordId":"record-2"}\n')
        assert not _records_projection_matches(records_projection, records_path)
        assert _stale_discovery_run("discovery", {
            "progress": {
                "stagingMatchesCanonicalInputs": False,
                "cardRun": "older-canonical-run",
                "cardReplayRun": "newest-acquisition-run",
            },
        }) == "newest-acquisition-run"
        assert _stale_source_run("discovery", {
            "progress": {
                "sourceRecordsCurrent": False,
                "sourceRun": "canonical-source-run",
                "sourceReplayRun": "newest-source-acquisition-run",
            },
        }) == "newest-source-acquisition-run"
        assert _stale_source_run("discovery", {
            "progress": {"sourceRecordsCurrent": True},
        }) is None
        records_path.unlink()
        assert not _records_projection_matches(records_projection, records_path)
    expected_summary = {"meta": {"cardDiscoveryRun": "run-1"}}
    expected_text = json.dumps(expected_summary, ensure_ascii=False, indent=2) + "\n"
    assert _completeness_matches_inputs({}, [], expected_text, expected_summary)
    assert not _completeness_matches_inputs({}, [], "stale summary", expected_summary)
    assert not _completeness_matches_inputs({}, ["invalid locality reference"],
                                           expected_text, expected_summary)
    complete = [{"status": "complete"}]
    assert _discovery_state(complete, complete,
                            {"runId": "source-1", "status": "complete"}, canonical,
                            0, 0, 0, False, True) == "retained"
    assert _discovery_state(complete, complete,
                            {"runId": "source-1", "status": "complete"}, canonical,
                            1, 1, 41, True, True) == "needs-reconciliation"
    assert _discovery_state(complete, complete,
                            {"runId": "source-1", "status": "complete"}, canonical,
                            1, 1, 41, True, False) == "retained"
    assert _discovery_state(complete, complete,
                            {"runId": "source-1", "status": "complete"}, canonical,
                            1, 1, 41, True, True,
                            source_records_current=False) == "retained"
    assert _discovery_state(complete, complete,
                            {"runId": "source-1", "status": "complete"}, canonical,
                            1, 1, 41, True, True, source_records_current=False,
                            source_replay_available=False) == "needs-source"
    assert _discovery_state(complete, complete,
                            {"runId": "source-1", "status": "complete"}, canonical,
                            1, 1, 41, False, True,
                            card_replay_available=False) == "needs-source"
    failed_attempt = [{"runId": "attempt-2", "status": "failed"}]
    complete_canonical = {"runId": "run-1", "status": "complete"}
    assert _discovery_state(failed_attempt, failed_attempt, complete_canonical, canonical,
                            1, 1, 41, True, True) == "needs-reconciliation"
    assert _discovery_state([], failed_attempt, complete_canonical, canonical,
                            1, 1, 41, True, True) == "candidate"
    discovery_terminals = {"terminal", "needs-reconciliation", "needs-source", "blocked-by-source"}
    assert not _should_skip_terminal_state(
        "discovery", "needs-reconciliation", discovery_terminals, True,
    )
    assert _should_skip_terminal_state(
        "discovery", "blocked-by-source", discovery_terminals, False,
    )
    assert _should_skip_terminal_state(
        "discovery", "needs-source", discovery_terminals, False,
    )
    assert not _should_skip_terminal_state(
        "discovery", "needs-source", discovery_terminals, True,
    )
    assert not _should_skip_terminal_state("tcgdex", "needs-source", {"needs-source"}, True)
    replay_after = {"state": "needs-reconciliation", "progress": {"needsSourceGaps": 21}}
    assert _discovery_cycle_stop_reason(
        replay_after, replay_after, {"needs-reconciliation"},
    ) == "state=needs-reconciliation"
    now = dt.datetime(2026, 9, 24, 21, 0, tzinfo=dt.timezone.utc)
    latest = "20260925T000000Z"
    assert _next_replay_run_id(now, {latest}) == "20260925T000001Z"
    source_latest = "20260925T000003Z"
    card_latest = "20260925T000010Z"
    next_discovery = _next_discovery_run_id(now, {source_latest}, {card_latest})
    assert next_discovery == "20260925T000011Z"
    assert _discovery_refresh_command(now)[:3] == [
        "scripts/discovery_cycle.py", "--refresh", "--run-id"
    ]
    assert _discovery_replay_commands("20260909T171255Z", now)[-1] == [
        "scripts/completeness_gate.py"
    ]
    replay_commands = _cycle_commands(
        "discovery", "source-discovery", "cycle", True, "20260909T171255Z", False, now,
    )
    assert len(replay_commands) == 3
    assert replay_commands[0][:3] == [
        "scripts/card_discovery.py", "--replay-from-run", "20260909T171255Z"
    ]
    assert replay_commands[1] == ["scripts/completeness_gate.py"]
    assert replay_commands[2][:2] == ["scripts/discovery_cycle.py", "--refresh"]
    assert replay_commands[2][-1] > replay_commands[0][-1]
    unreplayable_source_live = _cycle_commands(
        "discovery", "source-discovery", "cycle", True, "card-acquisition-run", False, now,
        live_refresh_required=True,
    )
    assert len(unreplayable_source_live) == 1
    assert unreplayable_source_live[0][:2] == ["scripts/discovery_cycle.py", "--refresh"]
    both_replay_commands = _cycle_commands(
        "discovery", "source-discovery", "cycle", True,
        "card-acquisition-run", False, now,
        source_replay_from_run="source-acquisition-run",
    )
    assert [command[0] for command in both_replay_commands] == [
        "scripts/source_adapters.py", "scripts/card_discovery.py",
        "scripts/completeness_gate.py", "scripts/discovery_cycle.py",
    ]
    replay_ids = [both_replay_commands[index][-1] for index in (0, 1, 3)]
    assert replay_ids == sorted(replay_ids) and len(set(replay_ids)) == 3
    stale_completeness_live = _cycle_commands(
        "discovery", "source-discovery", "cycle", True, None, False, now,
    )
    assert len(stale_completeness_live) == 1
    assert stale_completeness_live[0][:2] == ["scripts/discovery_cycle.py", "--refresh"]
    assert _cycle_commands("discovery", "source-discovery", "cycle", False, None, False) == [
        ["scripts/completeness_gate.py"]
    ]
    assert _cycle_commands("discovery", "source-discovery", "cycle", True, None, True)[0][:2] == [
        "scripts/discovery_cycle.py", "--refresh"
    ]
    assert "action=live-acquisition-required" in _discovery_summary("discovery", {
        "sourceRecordsCurrent": False, "sourceReplayRun": None,
        "stagingMatchesCanonicalInputs": True, "newCandidateRecords": 0,
        "stagingCandidateRecords": 0,
    })
    assert "action=live-acquisition-required" in _discovery_summary("discovery", {
        "sourceRecordsCurrent": True,
        "stagingMatchesCanonicalInputs": False, "cardReplayRun": None,
        "newCandidateRecords": 0, "stagingCandidateRecords": 0,
    })
    replayable_source_summary = _discovery_summary("discovery", {
        "sourceRecordsCurrent": False, "sourceReplayRun": "source-run",
        "stagingMatchesCanonicalInputs": True, "newCandidateRecords": 0,
        "stagingCandidateRecords": 0,
    })
    assert "action=reproject-source-staging" in replayable_source_summary
    assert "review=verification/source_adapter_staging.json" in replayable_source_summary
    terminal_summary = _discovery_summary("discovery", {
        "sourceRecordsCurrent": True, "stagingMatchesCanonicalInputs": True,
        "completenessMatchesInputs": True, "newCandidateRecords": 0,
        "stagingCandidateRecords": 0, "blockedGaps": 0, "needsSourceGaps": 0,
    }, "terminal")
    assert "action=complete review=none" in terminal_summary
    failed_refresh_summary = _discovery_summary("discovery", {
        "sourceRecordsCurrent": True, "stagingMatchesCanonicalInputs": True,
        "completenessMatchesInputs": True, "newCandidateRecords": 0,
        "stagingCandidateRecords": 0, "blockedGaps": 0, "needsSourceGaps": 0,
    }, "terminal", "lane-failed")
    assert "action=inspect-failed-discovery-run" in failed_refresh_summary
    assert "review=verification/runs/source-adapters,verification/runs/card-discovery" in failed_refresh_summary
    assert _discovery_replay_command("20260909T171255Z", now)[1:4] == [
        "--replay-from-run", "20260909T171255Z", "--run-id"
    ]

    with tempfile.TemporaryDirectory(dir=ROOT) as raw_root:
        runs = Path(raw_root)
        older = runs / "20260101T000000Z"
        newer = runs / "20260102T000000Z"
        for path, run_id in ((older, older.name), (newer, newer.name)):
            path.mkdir()
            (path / "manifest.json").write_text(
                json.dumps({"runId": run_id, "status": "complete"}), encoding="utf-8"
            )
        # Filesystem mtimes are deliberately reversed; manifest run identity still wins.
        os.utime(older / "manifest.json", (200, 200))
        os.utime(newer / "manifest.json", (100, 100))
        assert latest_manifests(runs)[0]["runId"] == newer.name
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
        if progress["newCandidateRecords"]:
            assert progress["stagingMatchesCanonicalInputs"]
            assert progress["newCandidateRecords"] == progress["stagingCandidateRecords"]
            assert discovery_report["stateBefore"]["state"] == "needs-reconciliation"
        elif not progress["stagingMatchesCanonicalInputs"]:
            assert progress["newCandidateRecords"] == 0
            assert discovery_report["stateBefore"]["state"] == "retained"
        if progress["blockedGaps"] and progress["needsSourceGaps"]:
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

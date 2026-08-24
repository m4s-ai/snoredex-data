#!/usr/bin/env python3
"""Run one manifest-defined workflow lane without weakening the full PR gate.

The runner is deliberately small: the manifest owns lane order and graph impact, while each
existing generator/check remains the owner of its own contract. Network steps are opt-in and every
run records skipped checks rather than silently claiming coverage. Reports live in the ignored
scoped-run cache unless ``--out`` is supplied.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "verification" / "scoped_pipeline_manifest.json"
MATRIX = ROOT / "verification" / "workflow_gate_matrix.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True, encoding="utf-8",
        stdout=subprocess.PIPE,
    ).stdout.strip()


def tree_paths() -> set[str]:
    tracked = git("diff", "--name-only", "--", ".", ":(exclude)*.sqlite").splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    return set(tracked) | {path for path in untracked if not path.endswith(".sqlite")}


def graph_impact(matrix: dict[str, Any], graph: dict[str, Any], classes: list[str]) -> dict[str, Any]:
    entity_counts = collections.Counter(row["entityType"] for row in graph["entities"])
    relation_counts = collections.Counter(row["relation"] for row in graph["edges"])
    details: dict[str, Any] = {}
    projections: set[str] = set()
    stores: set[str] = set()
    for impact_id in classes:
        impact = matrix["impactClasses"][impact_id]
        projections.update(impact["projectionRoots"])
        stores.update(impact["canonicalStores"])
        details[impact_id] = {
            "entityCount": sum(entity_counts[name] for name in impact["graphEntityTypes"]),
            "edgeCount": sum(relation_counts[name] for name in impact["graphRelations"]),
            "graphEntityTypes": impact["graphEntityTypes"],
            "graphRelations": impact["graphRelations"],
            "projectionRoots": impact["projectionRoots"],
        }
    return {
        "classes": details,
        "canonicalStores": sorted(stores),
        "projectionRoots": sorted(projections),
        "graphTotals": {"entities": len(graph["entities"]), "edges": len(graph["edges"])},
    }


def make_run_id(lane: str, manifest: dict[str, Any], commit: str) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seed = f"{lane}\0{commit}\0{json.dumps(manifest, sort_keys=True)}"
    return f"{stamp}-{lane}-{hashlib.sha256(seed.encode()).hexdigest()[:10]}"


def run_step(step: dict[str, Any], include_live: bool, include_browser: bool,
             dry_run: bool, before: set[str]) -> dict[str, Any]:
    command = step["command"]
    if dry_run:
        return {"status": "not-run", "reason": "dry-run", "durationMs": 0.0}
    if step.get("network") and not include_live:
        return {"status": "not-run", "reason": "network disabled; pass --include-live", "durationMs": 0.0}
    if step.get("browser") and not include_browser:
        return {"status": "not-run", "reason": "browser disabled; pass --include-browser", "durationMs": 0.0}

    started = time.perf_counter()
    process = subprocess.run(
        [sys.executable, *command], cwd=ROOT,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    after = tree_paths()
    return {
        "status": "passed" if process.returncode == 0 else "failed",
        "returnCode": process.returncode,
        "durationMs": round((time.perf_counter() - started) * 1000, 1),
        "observedChangedPaths": sorted(after - before),
        "outputTail": process.stdout[-2000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True, choices=[lane["id"] for lane in read_json(MANIFEST)["lanes"]])
    parser.add_argument("--run-id", help="pin a run ID for a replay or test")
    parser.add_argument("--include-live", action="store_true", help="execute manifest steps marked network=true")
    parser.add_argument("--include-browser", action="store_true", help="execute manifest steps marked browser=true")
    parser.add_argument("--dry-run", action="store_true", help="emit the lane plan without executing steps")
    parser.add_argument("--out", type=pathlib.Path,
                        default=ROOT / "verification" / "cache" / "scoped-runs")
    args = parser.parse_args()

    manifest = read_json(MANIFEST)
    matrix = read_json(MATRIX)
    graph = read_json(GRAPH)
    lane = next(item for item in manifest["lanes"] if item["id"] == args.lane)
    commit = git("rev-parse", "HEAD")
    run_id = args.run_id or make_run_id(args.lane, manifest, commit)
    if not RUN_ID.fullmatch(run_id):
        parser.error("--run-id contains unsupported characters")
    report_path = args.out / f"{run_id}.json" if args.out.suffix != ".json" else args.out

    results: list[dict[str, Any]] = []
    skipped = list(lane["skippedChecks"])
    previous_failed = False
    for step in lane["steps"]:
        before = tree_paths()
        if previous_failed:
            result = {"status": "not-run", "reason": "previous step failed", "durationMs": 0.0}
        else:
            result = run_step(step, args.include_live, args.include_browser, args.dry_run, before)
        if result["status"] == "not-run":
            skipped.append(f"{step['id']}: {result['reason']}")
        if result["status"] == "failed":
            previous_failed = True
        results.append({
            "id": step["id"], "command": step["command"], "gateLevel": step["gateLevel"],
            "network": step.get("network", False), "browser": step.get("browser", False),
            "declaredWrites": step.get("writes", []), **result,
        })

    counts = collections.Counter(result["status"] for result in results)
    report = {
        "schema": "snoredex-scoped-run",
        "version": "1.0.0",
        "runId": run_id,
        "lane": lane["id"],
        "title": lane["title"],
        "commit": commit,
        "manifestVersion": manifest["version"],
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "entry": lane["entry"],
        "dependsOn": lane["dependsOn"],
        "gates": {key: lane[key] for key in ("minimumGate", "projectionGate", "mergeGate", "releaseGate")},
        "impact": graph_impact(matrix, graph, lane["impactClasses"]),
        "fullGate": manifest["fullGate"],
        "idempotenceContract": manifest["runContract"]["idempotence"],
        "skippedChecks": skipped,
        "summary": {
            "steps": len(results), "passed": counts["passed"], "failed": counts["failed"],
            "notRun": counts["not-run"], "durationMs": round(sum(row.get("durationMs", 0) for row in results), 1),
        },
        "steps": results,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"scoped workflow: runId={run_id} lane={lane['id']} "
          f"{counts['passed']} passed, {counts['not-run']} not-run, {counts['failed']} failed; "
          f"report={report_path.relative_to(ROOT) if report_path.is_relative_to(ROOT) else report_path}")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

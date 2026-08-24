#!/usr/bin/env python3
"""Measure offline workflow cost and graph fan-out without changing gate behavior.

The report deliberately separates declared reads from observed writes:

* workflow_gate_matrix.json declares the stores and projection roots a lane owns;
* git status before/after a step records files that the process actually changed;
* subprocess wall time measures the cost on the current machine.

Browser and live-network checks are recorded as skipped unless explicitly enabled.
This is a diagnostic baseline, not a merge gate and not a replacement for regen.py.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
from contextlib import ExitStack
import importlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import tempfile
import time
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent.parent
MATRIX_PATH = ROOT / "verification" / "workflow_gate_matrix.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True,
        encoding="utf-8", stdout=subprocess.PIPE,
    ).stdout


def tree_paths() -> set[str]:
    tracked = run_git("diff", "--name-only", "--", ".", ":(exclude)*.sqlite").splitlines()
    untracked = run_git("ls-files", "--others", "--exclude-standard").splitlines()
    return set(tracked) | {path for path in untracked if not path.endswith(".sqlite")}


def command_path(args: list[str]) -> str:
    return next((arg for arg in args if arg.endswith(".py")), "")


def python_command(args: list[str]) -> list[str]:
    return [sys.executable, *args]


def impact_metadata(command: str, matrix: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    impacts: list[str] = []
    stores: set[str] = set()
    projections: set[str] = set()
    for impact_id, impact in matrix["impactClasses"].items():
        if command not in impact["projectionRoots"]:
            continue
        impacts.append(impact_id)
        stores.update(impact["canonicalStores"])
        projections.update(impact["projectionRoots"])
    return sorted(impacts), sorted(stores), sorted(projections)


def graph_fanout(matrix: dict[str, Any]) -> dict[str, Any]:
    graph = json.loads((ROOT / "verification" / "authoritative_graph.json").read_text(encoding="utf-8"))
    entity_counts = collections.Counter(entity["entityType"] for entity in graph["entities"])
    relation_counts = collections.Counter(edge["relation"] for edge in graph["edges"])
    by_impact: dict[str, Any] = {}
    for impact_id, impact in matrix["impactClasses"].items():
        entity_count = sum(entity_counts[name] for name in impact["graphEntityTypes"])
        edge_count = sum(relation_counts[name] for name in impact["graphRelations"])
        by_impact[impact_id] = {
            "entityCount": entity_count,
            "edgeCount": edge_count,
            "graphEntityTypes": impact["graphEntityTypes"],
            "graphRelations": impact["graphRelations"],
            "projectionCount": len(impact["projectionRoots"]),
        }
    return {
        "entities": len(graph["entities"]),
        "edges": len(graph["edges"]),
        "entityCounts": dict(sorted(entity_counts.items())),
        "relationCounts": dict(sorted(relation_counts.items())),
        "impactClasses": by_impact,
    }


def ci_specs(temp_root: pathlib.Path, include_browser: bool, include_live: bool) -> list[dict[str, Any]]:
    syntax = (
        "import ast, pathlib; "
        "bad=[]; "
        "paths=[p for p in pathlib.Path('.').rglob('*.py') if not any(x in {'.git','cache','__pycache__'} for x in p.parts)]; "
        "[bad.append(f'{p}: {e}') for p in paths for e in ([None] if False else [])]; "
        "[ast.parse(p.read_text(encoding='utf-8')) for p in paths]; "
        "print(f'parsed {len(paths)} Python files')"
    )
    specs: list[dict[str, Any]] = [
        {"label": "ci-syntax", "phase": "ci", "args": ["-c", syntax]},
        {"label": "ci-live-finish-replay", "phase": "ci", "args": ["verification/verify_finish_sources.py", "--replay"]},
        {"label": "ci-publish-build", "phase": "ci", "args": ["scripts/publish.py", "--out", str(temp_root)]},
        {"label": "ci-publish-verify", "phase": "ci", "args": ["scripts/publish.py", "--out", str(temp_root), "--verify"]},
    ]
    specs.append({
        "label": "ci-browser",
        "phase": "ci",
        "args": ["verification/test_site.py"],
        "execute": include_browser,
        "skipReason": "browser disabled; use --include-browser on a runner with Chromium",
    })
    specs.append({
        "label": "ci-live-finish",
        "phase": "ci",
        "args": ["verification/verify_finish_sources.py"],
        "execute": include_live,
        "skipReason": "live network disabled; --replay measures the deterministic CI substitute",
    })
    return specs


def pages_specs(temp_root: pathlib.Path) -> list[dict[str, Any]]:
    commands = [
        ["scripts/finishes.py", "--reproject"],
        ["scripts/language_status.py"],
        ["scripts/confirmed_releases.py"],
        ["scripts/source_registry.py"],
        ["scripts/source_capabilities.py"],
        ["scripts/checklist.py"],
        ["scripts/collector_catalogue.py"],
        ["scripts/readme_stats.py"],
        ["scripts/issue_templates.py"],
        ["scripts/site.py"],
    ]
    specs = [
        {"label": f"pages-{args[0].split('/')[-1]}", "phase": "pages", "args": args}
        for args in commands
    ]
    site = temp_root
    deployment = site / "collector_deployment.json"
    artifact_commit = git_commit()
    specs.extend([
        {"label": "pages-publish-build", "phase": "pages", "args": ["scripts/publish.py", "--out", str(site)]},
        {
            "label": "pages-deployment-manifest",
            "phase": "pages",
            "args": [
                "scripts/collector_deployment.py", "--catalogue", str(site / "collector_catalogue.json"),
                "--out", str(deployment), "--artifact-commit", artifact_commit,
                "--published-at", "2000-01-01T00:00:00Z",
            ],
        },
        {"label": "pages-publish-verify", "phase": "pages", "args": ["scripts/publish.py", "--out", str(site), "--verify"]},
        {
            "label": "pages-deployment-verify",
            "phase": "pages",
            "args": [
                "scripts/collector_deployment.py", "--check", "--catalogue", str(site / "collector_catalogue.json"),
                "--out", str(deployment), "--artifact-commit", artifact_commit,
            ],
        },
    ])
    return specs


def run_spec(spec: dict[str, Any], matrix: dict[str, Any]) -> dict[str, Any]:
    args = spec["args"]
    command = command_path(args)
    impacts, stores, projections = impact_metadata(command, matrix)
    before = tree_paths()
    started = time.perf_counter()
    if spec.get("execute", True):
        process = subprocess.run(
            python_command(args), cwd=ROOT, env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
            text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        output = process.stdout
        return_code = process.returncode
        status = "passed" if return_code == 0 else "failed"
    else:
        output = spec.get("skipReason", "disabled")
        return_code = None
        status = "not-run"
    duration_ms = round((time.perf_counter() - started) * 1000, 1)
    after = tree_paths()
    return {
        "label": spec["label"],
        "phase": spec["phase"],
        "command": " ".join(args),
        "status": status,
        "returnCode": return_code,
        "durationMs": duration_ms,
        "impactClasses": impacts,
        "declaredReadStores": stores,
        "declaredProjectionRoots": projections,
        "observedChangedPaths": sorted(after - before),
        "treeDirtyAfter": sorted(after),
        "outputTail": output[-2000:] if output else "",
    }


def git_commit() -> str:
    return run_git("rev-parse", "HEAD").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("core", "ci", "pages", "all"), default="core")
    parser.add_argument("--include-browser", action="store_true", help="run the Playwright CI check")
    parser.add_argument("--include-live", action="store_true", help="run the live TCGCSV check")
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "verification" / "workflow_runtime_baseline.json")
    args = parser.parse_args()

    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    regen = importlib.import_module("scripts.regen")
    specs: list[dict[str, Any]] = []
    if args.profile in {"core", "all"}:
        specs.extend({"label": "core-check", "phase": "core", "args": command} for command in regen.CHECK)
        specs.extend({"label": "core-test", "phase": "core", "args": command} for command in regen.TESTS)

    with ExitStack() as stack:
        if args.profile in {"ci", "all"}:
            ci_root = pathlib.Path(stack.enter_context(
                tempfile.TemporaryDirectory(prefix="_site-measure-ci-", dir=ROOT)
            ))
            specs.extend(ci_specs(ci_root, args.include_browser, args.include_live))
        if args.profile in {"pages", "all"}:
            pages_root = pathlib.Path(stack.enter_context(
                tempfile.TemporaryDirectory(prefix="_site-measure-pages-", dir=ROOT)
            ))
            specs.extend(pages_specs(pages_root))

        results = [run_spec(spec, matrix) for spec in specs]

    totals = collections.Counter(result["status"] for result in results)
    report = {
        "schema": "snoredex-workflow-runtime-baseline",
        "version": "1.0.0",
        "measuredAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "commit": git_commit(),
        "profile": args.profile,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "methodology": {
            "declaredReads": "canonical stores from workflow_gate_matrix.json matched by projection root",
            "observedWrites": "git status delta before/after each subprocess; SQLite bytes excluded",
            "network": "live checks are skipped unless --include-live is supplied",
            "browser": "Playwright check is skipped unless --include-browser is supplied",
            "scope": "measurement is diagnostic and never changes merge-gate behavior",
        },
        "graph": graph_fanout(matrix),
        "summary": {
            "steps": len(results),
            "passed": totals["passed"],
            "failed": totals["failed"],
            "notRun": totals["not-run"],
            "durationMs": round(sum(result["durationMs"] for result in results), 1),
        },
        "steps": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"workflow measurement: {report['summary']['steps']} steps, "
        f"{report['summary']['passed']} passed, {report['summary']['notRun']} not-run, "
        f"{report['summary']['failed']} failed, {report['summary']['durationMs'] / 1000:.1f}s"
    )
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""One command to regenerate every derived artifact and verify nothing is stale.

Before opening a PR, run:

    python scripts/regen.py          # regenerate everything, then verify

or, when the derived artifacts are already regenerated:

    python scripts/regen.py --check  # verify artifacts and run the core regression gate

`--check` is what CI calls, so the local command and the gate share one source of
truth instead of the author guessing which script regenerates which file.

Exit code is non-zero if a generator, determinism check, or regression fails.

COVERAGE NOTE: this file must name every generator and core regression check. Add
new ones here, never to a prose list or a second workflow list. Browser, live-source,
syntax and publish checks remain separate because they are not regeneration concerns.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import pathlib
import subprocess
import sys
import time

sys.dont_write_bytecode = True
# Read-only Git commands must not refresh the index as a side effect.
os.environ["GIT_OPTIONAL_LOCKS"] = "0"
try:
    from scripts.workflow_observation import tree_snapshot
    from scripts import check_memo
except ModuleNotFoundError:
    from workflow_observation import tree_snapshot
    import check_memo

ROOT = pathlib.Path(__file__).resolve().parent.parent

REGEN = [
    ["scripts/legacy_baseline.py"],
    ["scripts/analyze.py"],
    ["scripts/evidence_semantics.py"],
    ["scripts/editions.py"],
    ["scripts/finishes.py", "--offline"],
    ["scripts/language_status.py"],
    ["scripts/source_registry.py"],
    ["scripts/confirmed_releases.py"],
    ["verification/report.py"],
    ["scripts/source_capabilities.py"],
    ["scripts/source_adapters.py"],
    ["scripts/authoritative_graph.py", "--write"],
    ["scripts/artwork_review.py"],
    ["scripts/card_discovery.py"],
    ["scripts/asia_locality_matrix.py"],
    ["scripts/locality_matrix.py"],
    ["scripts/completeness_gate.py"],
    ["scripts/checklist.py"],
    ["scripts/collector_catalogue.py"],
    ["scripts/malie_export.py", "--write"],
    ["scripts/readme_stats.py"],
    ["scripts/issue_templates.py"],
    ["scripts/open_items.py"],
    ["scripts/database.py", "--out", "snoredex.sqlite"],
    ["scripts/tracker.py", "--tracker", "snoredex-tracker-template.sqlite", "init", "--force"],
    ["scripts/site.py"],
]

CHECK = [
    ["scripts/legacy_baseline.py", "--check"],
    ["scripts/analyze.py", "--check"],
    ["scripts/evidence_semantics.py", "--check"],
    ["scripts/editions.py", "--check"],
    ["scripts/finishes.py", "--offline", "--check"],
    ["scripts/language_status.py", "--check"],
    ["scripts/source_registry.py", "--check"],
    ["scripts/confirmed_releases.py", "--check"],
    ["verification/report.py", "--check"],
    ["scripts/source_capabilities.py", "--check"],
    ["scripts/source_adapters.py", "--check"],
    ["scripts/authoritative_graph.py", "--check"],
    ["scripts/artwork_review.py", "--check"],
    ["scripts/card_discovery.py", "--check"],
    ["scripts/asia_locality_matrix.py", "--check"],
    ["scripts/locality_matrix.py", "--check"],
    ["scripts/completeness_gate.py", "--check"],
    ["scripts/checklist.py", "--check"],
    ["scripts/collector_catalogue.py", "--check"],
    ["scripts/malie_export.py", "--check"],
    ["scripts/readme_stats.py", "--check"],
    ["scripts/issue_templates.py", "--check"],
    ["scripts/open_items.py", "--check"],
    ["scripts/database.py", "--check"],
    ["scripts/tracker.py", "check-template"],
    ["scripts/site.py", "--check"],
]

TESTS = [
    ["verification/test_complexity.py"],
    ["verification/review_integrity.py"],
    ["verification/test_evidence_application.py"],
    ["verification/test_database_portability.py"],
    ["verification/test_tracker_state.py"],
    ["verification/test_owner_adjudications.py"],
    ["verification/test_source_adapters.py"],
    ["verification/test_card_discovery.py"],
    ["verification/test_metric_polarity.py"],
    ["verification/test_asia_locality_matrix.py"],
    ["verification/test_locality_matrix.py"],
    ["verification/test_authoritative_graph.py"],
    ["verification/test_authoritative_graph_replays.py"],
    ["verification/test_physical_evidence_workflow.py"],
    ["verification/test_fetch_attachment.py"],
    ["verification/test_tcgdex_snapshot.py"],
    ["verification/test_file_digest.py"],
    ["verification/fetch_attachment.py", "--evidence-check"],
    ["verification/test_collector_catalogue.py"],
    ["verification/test_card_content.py"],
    ["verification/test_malie_profile.py"],
    ["verification/test_malie_export.py"],
    ["verification/test_malie_integration.py"],
    ["verification/test_malie_package.py"],
    ["verification/test_retired_projections.py"],
    ["verification/test_artwork_review.py"],
    ["verification/test_gallery.py"],
    ["verification/test_korean_burning_confrontation.py"],
    ["verification/test_completeness_gate.py"],
    ["verification/test_workflow_gate_matrix.py"],
    ["verification/test_pipeline_documentation.py"],
    ["verification/test_gate_handoff.py"],
    ["verification/test_workflow_test_ownership.py"],
    ["verification/test_scoped_regen.py"],
    ["verification/test_workflow_loop.py"],
    ["verification/test_measure_workflow.py"],
    ["verification/test_findings_harness.py"],
    ["verification/test_sensitive_scan.py"],
    ["verification/test_check_memo.py"],
    ["verification/review_findings.py"],          # cross-artifact + publication
    ["verification/test_regen_readiness.py"],
]

CHILD_ENV = os.environ.copy()
CHILD_ENV["PYTHONUTF8"] = "1"
CHILD_ENV["PYTHONIOENCODING"] = "utf-8"
CHILD_ENV["PYTHONDONTWRITEBYTECODE"] = "1"


def run_step(session: check_memo.MemoSession, phase: str, cmd: list[str], capture: bool,
             quiet: bool = False) -> tuple[bool, str]:
    """Run one step through the verification memo; return (passed, printable block).

    An unchanged step (#460) reports a memo hit instead of running. Captured output is returned so
    parallel steps print in list order; `quiet` keeps a passing step's output out of the log.
    """
    label = " ".join(cmd)
    header = f"\n=== {label} ==="
    if not capture:
        print(header, flush=True)
    started = time.perf_counter()
    outcome = session.execute(phase, cmd, CHILD_ENV, capture=capture)
    if outcome.hit is not None:
        footer = check_memo.hit_line(label, outcome.hit)
    else:
        footer = f"--- {label}: {time.perf_counter() - started:.2f}s"
    passed = outcome.returncode == 0
    body = outcome.output or ""
    if quiet and passed:
        body = ""
    block = "\n".join(part for part in (header if capture else "", body.rstrip("\n"), footer) if part)
    return passed, block


def run_phase(session: check_memo.MemoSession, commands: list[list[str]], jobs: int) -> list[list[str]]:
    """Run observational steps in parallel, print their blocks in list order, return the failures."""
    def one(cmd: list[str]) -> tuple[bool, str]:
        return run_step(session, "check", cmd, capture=True, quiet=cmd[0].endswith("review_findings.py"))

    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        for cmd, (passed, block) in zip(commands, pool.map(one, commands)):
            print(block, flush=True)
            if not passed:
                failures.append(cmd)
    return failures


def tree_state() -> tuple[dict, dict, dict]:
    """Observe contents and metadata without comparing non-portable SQLite bytes."""
    paths = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "-z"], cwd=ROOT,
        check=True, stdout=subprocess.PIPE,
    ).stdout.split(b"\0")
    metadata = {}
    for relative in filter(None, paths):
        try:
            info = (ROOT / os.fsdecode(relative)).lstat()
            metadata[relative] = (info.st_size, info.st_mtime_ns, info.st_mode)
        except FileNotFoundError:
            metadata[relative] = None
    index_paths = subprocess.run(
        ["git", "rev-parse", "--git-path", "index", "--shared-index-path"], cwd=ROOT,
        check=True, stdout=subprocess.PIPE,
    ).stdout.splitlines()
    indexes = [ROOT / os.fsdecode(path) for path in index_paths]
    index_state = {path: path.read_bytes() if path.exists() else None for path in indexes}
    return tree_snapshot(ROOT, paths=[os.fsdecode(path) for path in metadata]), metadata, index_state


def verify(session: check_memo.MemoSession, check_commands: list[list[str]],
           tests: list[list[str]], jobs: int) -> bool:
    determinism_failures = run_phase(session, check_commands, jobs)
    if determinism_failures:
        print("\nFAILED determinism checks:", file=sys.stderr)
        for cmd in determinism_failures:
            print(f"  - {' '.join(cmd)}", file=sys.stderr)
        return False
    test_failures = run_phase(session, tests, jobs)
    for cmd in test_failures:
        print(f"\nFAILED {' '.join(cmd)}", file=sys.stderr)
    return not test_failures


def regenerate(session: check_memo.MemoSession) -> bool:
    for cmd in REGEN:
        passed, block = run_step(session, "write", cmd, capture=False)
        print(block, flush=True)
        if not passed:
            print(f"\nFAILED regenerating {' '.join(cmd)}", file=sys.stderr)
            return False
    return True


def shallow_clone_blocked(allow_shallow: bool) -> bool:
    """Stop before minutes of work that a shallow clone cannot pass (#460).

    collector_catalogue.py reconstructs predecessors from Git history and P6 audits it, so a
    shallow clone fails late. Diagnostic runs may continue with --allow-shallow.
    """
    shallow = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    ).stdout.strip() == "true"
    if shallow and not allow_shallow:
        print("regen.py: shallow clone. collector_catalogue.py and P6 need full Git history; run "
              "`git fetch --unshallow` once, or pass --allow-shallow for a diagnostic run.",
              file=sys.stderr)
    return shallow and not allow_shallow


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify artifacts and run the core regression gate")
    ap.add_argument("--check-only", action="append", metavar="SCRIPT",
                    help="run only selected CHECK entries (repeatable diagnostic hook)")
    ap.add_argument("--allow-shallow", action="store_true",
                    help="diagnostic only: run on a shallow clone (P6 still fails)")
    ap.add_argument("--memo", choices=check_memo.MODES, default="use",
                    help="use: skip steps whose observed inputs are unchanged (default); refresh: run "
                         "every step and rewrite the memo; off: reference run without any memo")
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1),
                    help="parallel CHECK/TESTS steps (REGEN stays serial); 1 = serial")
    args = ap.parse_args()

    if shallow_clone_blocked(args.allow_shallow):
        return 2
    if args.check_only and not args.check:
        ap.error("--check-only requires --check")
    check_commands = CHECK
    if args.check_only:
        known = {cmd[0] for cmd in CHECK}
        unknown = sorted(set(args.check_only) - known)
        if unknown:
            ap.error("unknown CHECK script(s): " + ", ".join(unknown))
        wanted = set(args.check_only)
        check_commands = [cmd for cmd in CHECK if cmd[0] in wanted]

    session = check_memo.MemoSession(ROOT, args.memo)
    CHILD_ENV[check_memo.MODE_VAR] = session.mode
    if not args.check and not regenerate(session):
        return 1

    before_check = tree_state()
    changed, valid = True, False
    try:
        valid = verify(session, check_commands, [] if args.check_only else TESTS, args.jobs)
    finally:
        changed = tree_state() != before_check
        if changed:
            print("\nRead-only gate changed working-tree files, metadata or Git index.", file=sys.stderr)
        else:  # a run that wrote nothing may keep what passed; generators only after a green run
            session.commit(full_success=valid and not args.check_only)
        print("\n" + session.summary())
    if changed or not valid:
        return 1

    status = subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, text=True, encoding="utf-8",
        check=True, stdout=subprocess.PIPE,
    ).stdout.strip()
    if status and not args.check:
        print("\nWorking tree changes to review and commit:\n" + status)
    if args.check_only:
        print("\nregen.py: OK. Selected determinism checks are current.")
    else:
        print("\nregen.py: OK. Generated artifacts and core regressions are current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

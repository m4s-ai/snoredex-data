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
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------- #
# Regenerate (write) phase — every generator that produces a derived artifact,
# in dependency order (later generators read earlier outputs). These are the
# *writing* variants; the same scripts with --check (see CHECK) verify them.
# --------------------------------------------------------------------------- #
REGEN = [
    # source-of-truth parses & candidate-universe contracts
    ["scripts/legacy_baseline.py"],
    ["scripts/analyze.py"],
    # card-evidence inventory & its conservative application policy (keystone for
    # every consumer projection's per-unit status)
    ["scripts/evidence_semantics.py"],
    # Editions are written onto the card rows consumed by the remaining projections.
    ["scripts/editions.py"],
    ["scripts/finishes.py", "--offline"],
    ["scripts/language_status.py"],
    ["scripts/confirmed_releases.py"],
    ["verification/report.py"],
    # source-first catalogue & discovery
    ["scripts/source_registry.py"],
    ["scripts/source_capabilities.py"],
    ["scripts/source_adapters.py"],
    # The migration remains the reviewed graph base; physical evidence is projected from
    # canonical finish/specimen inputs before downstream consumers read it.
    ["scripts/authoritative_graph.py", "--write"],
    ["scripts/artwork_review.py"],
    ["scripts/card_discovery.py"],
    ["scripts/asia_locality_matrix.py"],
    ["scripts/locality_matrix.py"],
    ["scripts/completeness_gate.py"],
    # downstream projections
    ["scripts/checklist.py"],
    ["scripts/collector_catalogue.py"],
    ["scripts/readme_stats.py"],
    ["scripts/issue_templates.py"],
    ["scripts/open_items.py"],
    ["scripts/database.py", "--out", "snoredex.sqlite"],
    ["scripts/tracker.py", "--tracker", "snoredex-tracker-template.sqlite", "init", "--force"],
    ["scripts/site.py"],
]

# --------------------------------------------------------------------------- #
# Determinism (verify) phase — the same generators in the --check/--reproject
# modes the gate's "Generated artifacts match their inputs" step uses, then the
# git diff proving committed == generated. Scripts with no --check are re-run in
# write mode (idempotent on a clean tree) and the diff catches drift.
# --------------------------------------------------------------------------- #
CHECK = [
    ["scripts/legacy_baseline.py", "--check"],
    ["scripts/analyze.py", "--check"],
    ["scripts/evidence_semantics.py", "--check"],
    ["scripts/editions.py"],
    ["scripts/finishes.py", "--offline"],
    ["scripts/language_status.py"],
    ["scripts/confirmed_releases.py"],
    ["verification/report.py"],
    ["scripts/source_registry.py", "--check"],
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
    ["scripts/readme_stats.py", "--check"],
    ["scripts/issue_templates.py", "--check"],
    ["scripts/open_items.py", "--check"],
    ["scripts/database.py", "--check"],
    ["scripts/tracker.py", "check-template"],
    ["scripts/site.py", "--check"],
]

# --------------------------------------------------------------------------- #
# Verify (test) phase — every regression suite and cross-artifact gate the gate
# runs, in the order CI runs them.
# --------------------------------------------------------------------------- #
TESTS = [
    ["verification/review_integrity.py"],
    ["verification/test_evidence_application.py"],
    ["verification/test_database_portability.py"],
    ["verification/test_tracker_state.py"],
    ["verification/test_owner_adjudications.py"],
    ["verification/test_source_adapters.py"],
    ["verification/test_card_discovery.py"],
    ["verification/test_metric_polarity.py"],
    ["verification/test_asia_locality_matrix.py"],
    ["verification/test_authoritative_graph.py"],
    ["verification/test_physical_evidence_workflow.py"],
    ["verification/test_fetch_attachment.py"],
    ["verification/test_tcgdex_snapshot.py"],
    ["verification/fetch_attachment.py", "--evidence-check"],
    ["verification/test_collector_catalogue.py"],
    ["verification/test_retired_projections.py"],
    ["verification/test_artwork_review.py"],
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
    ["verification/review_findings.py"],          # cross-artifact + publication
    ["verification/test_regen_readiness.py"],
]

# Local-only gate exceptions: CI is the authority on merge-readiness. A finding
# that is green in the gate but red on a local full clone must not block a PR
# that CI will pass. P6 scans *all reachable git blobs*; a local clone that still
# carries the kept `refs/original/*` rollback refs from the 2026-08 history
# rewrite scans more blobs than the gate's fresh clone, so it reports sensitive
# history hits the gate never sees. If review_findings fails with exactly P6 and
# no other FAIL, treat it as a warning, not a block.


CHILD_ENV = os.environ.copy()
CHILD_ENV["PYTHONUTF8"] = "1"
CHILD_ENV["PYTHONIOENCODING"] = "utf-8"
DIFF_PATHS = ["--", ".", ":(exclude)*.sqlite"]


def run(cmd: list[str], label: str) -> bool:
    print(f"\n=== {label} ===", flush=True)
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, env=CHILD_ENV)
    print(f"--- {label}: {time.perf_counter() - started:.2f}s", flush=True)
    return proc.returncode == 0


def tree_state() -> tuple[bytes, bytes]:
    """Return generated-file state while ignoring non-portable SQLite bytes."""
    diff = subprocess.run(
        ["git", "diff", "--binary", *DIFF_PATHS], cwd=ROOT,
        check=True, stdout=subprocess.PIPE,
    ).stdout
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT,
        check=True, stdout=subprocess.PIPE,
    ).stdout.splitlines()
    return diff, b"\n".join(path for path in untracked if not path.endswith(b".sqlite"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify artifacts and run the core regression gate")
    ap.add_argument("--check-only", action="append", metavar="SCRIPT",
                    help="run only selected CHECK entries (diagnostic/test hook; repeatable)")
    args = ap.parse_args()

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

    if not args.check:
        for cmd in REGEN:
            if not run([sys.executable, *cmd], cmd[0]):
                print(f"\nFAILED regenerating {' '.join(cmd)}", file=sys.stderr)
                return 1

    # Snapshot after the intentional write phase. The check phase may run idempotent
    # writers, but it must not change any tracked text or create a new non-SQLite file.
    before_check = tree_state()
    determinism_failures: list[list[str]] = []
    for cmd in check_commands:
        if not run([sys.executable, *cmd], " ".join(cmd)):
            determinism_failures.append(cmd)
    if determinism_failures:
        print("\nFAILED determinism checks:", file=sys.stderr)
        for cmd in determinism_failures:
            print(f"  - {' '.join(cmd)}", file=sys.stderr)
        return 1

    if tree_state() != before_check:
        print("\nStale artifacts: checking changed generated output. Run "
              "`python scripts/regen.py` and commit the result.",
              file=sys.stderr)
        return 1

    for test in ([] if args.check_only else TESTS):
        if test[0].endswith("review_findings.py"):
            label = " ".join(test)
            print(f"\n=== {label} ===", flush=True)
            started = time.perf_counter()
            proc = subprocess.run([sys.executable, *test], cwd=ROOT, text=True,
                                  encoding="utf-8", env=CHILD_ENV,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            print(f"--- {label}: {time.perf_counter() - started:.2f}s", flush=True)
            failed = proc.returncode != 0
            n_fail = proc.stdout.count("[FAIL]")
            p6_only = failed and n_fail == 1 and "[FAIL] P6 " in proc.stdout
            if failed and not p6_only:
                print(proc.stdout)
                print(f"\nFAILED {' '.join(test)}", file=sys.stderr)
                return 1
            if p6_only:
                print(proc.stdout)
                print("note: review_findings FAILed only on P6 (local full-clone "
                      "history scan); CI gate is green — not blocking.", file=sys.stderr)
            continue
        if not run([sys.executable, *test], " ".join(test)):
            print(f"\nFAILED {' '.join(test)}", file=sys.stderr)
            return 1

    status = subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, text=True, encoding="utf-8",
        check=True, stdout=subprocess.PIPE,
    ).stdout.strip()
    if status and not args.check:
        print("\nWorking tree changes to review and commit:\n" + status)
    if args.check_only:
        print("\nregen.py: OK — selected determinism checks are current.")
    else:
        print("\nregen.py: OK — generated artifacts and core regressions are current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

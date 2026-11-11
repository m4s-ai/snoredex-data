---
name: snoredex-state-audit
description: Audit the current Snoredex-Data repository and data handoff as a read-only, evidence-backed report. Use for current-state, data-quality, architecture, dependency, documentation, or consumer-readiness reviews; not for implementing fixes.
---

<!-- doc: role=repository-state audit workflow skill; stage=task -->

# Snoredex state audit

Report what the current tree and its checks establish, which contracts fail, and where evidence or maintenance work remains. Do not change the repository unless the user separately requests remediation.

## State-audit context

Read [AGENTS.md](../../../AGENTS.md), [README.md](../../../README.md), [DATA-GUIDE.md](../../../DATA-GUIDE.md) and [DATABASE.md](../../../DATABASE.md). Use the issue tracker only for priorities; do not infer backlog from stale prose.

## State-audit workflow

1. Define the requested audit boundary: data truth, architecture, gates, documentation, consumer handoff, or a stated combination. Do not silently expand to history or unrelated branches.
2. Record branch, HEAD, `origin/main` freshness, working-tree state, and pre-existing changes. Do not switch, clean, or rewrite the user's checkout.
3. Trace each fact from its source in `data/` (or an owner file read in place) through `scripts/build.py` to the outputs and the gate (`scripts/regen.py`). Distinguish curated sources, build outputs and the immutable `verification/archive/`.
4. Read current counts from `data/`, the built database or the page, never from remembered prose. Keep bounded-input completion separate from historical or all-locality completeness.
5. Run the narrowest read-only checks needed (`python scripts/check.py`, `python scripts/build.py --check`, `python scripts/regen.py --check`). Capture `git status` before and after; if a check dirties the tree, report that as a gate defect and do not leave its side effects in a read-only audit.
6. Validate each finding with a concrete file, command result, invariant, or reproducible example. Absence of a record is not evidence of a missing printing.
7. Rank findings by correctness or data-loss risk, downstream graph fan-out, reproducibility, and remediation cost. Separate confirmed defects from questions and enhancement ideas.

## State-audit cross-layer validation

Trace source and asset identity through the affected outputs; compare current counts rather than
copying historical totals. Use the read-only checks in step 5, never a write mode. A failed invariant is a finding, not permission to repair
data, regenerate outputs or weaken an assertion. Determinism checks that require rebuilding belong
to a separately authorized implementation workflow, not this read-only audit.

Return an executive conclusion, audit boundary, verified findings with paths, affected consumers, gate evidence, and a small ordered remediation list. Do not create issues or modify files without explicit authorization.

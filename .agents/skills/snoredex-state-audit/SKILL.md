---
name: snoredex-state-audit
description: Audit the current Snoredex-Data repository and data handoff as a read-only, evidence-backed report. Use for current-state, data-quality, architecture, dependency, documentation, or consumer-readiness reviews; not for implementing fixes.
---

# Snoredex state audit

Report what the current tree and generated audits establish, which contracts fail, and where evidence or maintenance work remains. Do not change the repository unless the user separately requests remediation.

## Required context

Read [CLAUDE.md](../../../CLAUDE.md), [HANDOVER.md](../../../HANDOVER.md), [README.md](../../../README.md), [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md), and the current generated [DATA-HANDOFF-AUDIT.md](../../../verification/DATA-HANDOFF-AUDIT.md). Use the issue tracker only for priorities; do not infer backlog from stale prose.

## Workflow

1. Define the requested audit boundary: data truth, architecture, gates, documentation, consumer handoff, or a stated combination. Do not silently expand to history or unrelated branches.
2. Record branch, HEAD, `origin/main` freshness, working-tree state, and pre-existing changes. Do not switch, clean, or rewrite the user's checkout.
3. Trace canonical inputs through graph edges, projections, consumers, and gates using `WORKFLOW-MAP.md`. Distinguish reviewed stores, immutable runs, generated views, and historical archives.
4. Read current counts from generated audits or data, never from remembered prose. Keep bounded-input completion separate from historical or all-locality completeness.
5. Run the narrowest read-only checks needed. When running `python scripts/regen.py --check`, capture status before and after; if the check dirties generated files, report that as a gate defect and do not leave its side effects in a read-only audit.
6. Validate each finding with a concrete file, command result, invariant, or reproducible example. Absence of a record is not evidence of a missing printing.
7. Rank findings by correctness or data-loss risk, downstream graph fan-out, reproducibility, and remediation cost. Separate confirmed defects from questions and enhancement ideas.

Return an executive conclusion, audit boundary, verified findings with paths, affected consumers, gate evidence, and a small ordered remediation list. Do not create issues or modify files without explicit authorization.

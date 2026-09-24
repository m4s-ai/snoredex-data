---
name: snoredex-issue-delivery
description: Deliver one Snoredex-Data issue through implementation and verification to a review-ready branch or pull request. Use for implementing or fixing a specific issue; not for review-only remediation or broad backlog planning.
---

<!-- doc: role=issue-delivery workflow skill; stage=task -->

# Snoredex issue delivery

Complete one issue without mixing unrelated work or weakening the repository's evidence and gate contracts.

## Issue-delivery context

Work from the repository root. Read [AGENTS.md](../../../AGENTS.md), [HANDOVER.md](../../../HANDOVER.md), and [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md). Read the full issue, every comment, linked issue and relevant pull request before planning. If the issue changes evidence, read the domain document required by `AGENTS.md` before editing.

## Issue-delivery workflow

1. Confirm the complete requested scope and existing session authorization. For work spanning several targets, start the completion record below. Use [issue triage](../snoredex-issue-triage/SKILL.md) when the task is choosing or reconciling issues. Do not infer permission to merge, publish or expand the scope; carry out already-authorized issue maintenance without asking again.
2. Fetch `origin` and start from current `origin/main`. Reuse an existing branch only when it belongs exclusively to this issue and its work is understood; otherwise create one isolated issue branch.
3. Run `python scripts/regen.py --check` before editing. Preserve and report any pre-existing failure instead of folding it into the issue.
4. Trace the issue from canonical input through graph edges, projections, consumers, and gates using `WORKFLOW-MAP.md`. Identify generated and archived files that must not be edited.
5. Implement the smallest complete change at the canonical owner. Add the narrowest meaningful regression check when behavior changes.
6. Use `python scripts/scoped_regen.py --lane <lane>` for fast feedback when a manifest lane matches. Treat its Run-ID and skipped checks as partial evidence only.
7. Reconcile the completion record before the final gate. For canonical-input or generator changes run `python scripts/regen.py`; for other changes use `python scripts/regen.py --check`. Inspect the complete diff and preserve unrelated user changes. L3 remains required before merge.
8. Commit and push only when authorized. After any commit and push, rerun `python verification/review_findings.py` so the history-sensitive checks see the actual commit.
9. Create or update the requested pull request. Rewrite its title and description around the final scope, link the issue, and report canonical inputs, graph impact and verification accurately. For authorized issue maintenance, synchronize the title, checkboxes and related references from the same completion record; close only when the issue's criteria are met.

Finish with the issue state, branch or PR, files changed, verification results, known pre-existing failures, and any required owner or source input. Merge only on explicit instruction.

## Issue-delivery completion and handoff

For multipart work, keep one task-local record with these columns:
`Target/evidence | accepted fields | canonical integration | affected consumers verified |
commit/PR | remaining`. Derive it from the whole authorized scope and all accepted evidence,
including additional image views and re-keyed targets. Retained bytes, integrated references,
pushed changes and completed issue criteria are different milestones. Reconcile every row
before reporting completion; a newly handled photo does not discharge the rest of the batch.

Reuse this record for a handoff with branch, full HEAD SHA, pre-existing changes/failures, open
review IDs and the next executable step. Verify it against the checkout when resuming; do not
create another durable backlog database. Bundle related fixes, run focused checks during that
batch, then the required full gate. Repeat the gate for changed inputs, failures or new concerns,
not for unchanged state. Use existing [workflow measurements](../../../scripts/measure_workflow.py)
when timing is needed; keep mandatory L3/L4 requirements intact.

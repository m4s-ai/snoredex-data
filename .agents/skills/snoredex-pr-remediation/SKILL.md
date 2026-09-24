---
name: snoredex-pr-remediation
description: Remediate an existing Snoredex-Data pull request until actionable review findings and PR-caused CI failures are resolved at the exact head. Use when explicitly asked to address existing PR findings, failing checks, conflicts, or babysit a PR; not for review-only inspection or new feature scope.
---

<!-- doc: role=pull-request remediation workflow skill; stage=task -->

# Snoredex PR remediation

Make the smallest justified repair to the current pull-request head and leave an auditable clean-review result.

## PR-remediation context

Read [AGENTS.md](../../../AGENTS.md), [HANDOVER.md](../../../HANDOVER.md), and [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md). Inspect the complete PR, its base and head SHAs, commits, checks, annotations, review summaries, inline threads, and linked issue. Treat old summaries as stale until checked against the live head.

## PR-remediation workflow

1. Record the exact PR head SHA and determine whether the PR is draft, mergeable, conflicted, or already closed.
2. Build or refresh the complete finding inventory below. Classify each finding as actionable, outdated, already fixed, unrelated, infrastructure failure, or requiring user input. Explain disagreements with evidence; resolved/outdated UI state alone does not establish that the current head is correct.
3. Work in the PR branch or a safe isolated worktree without disturbing another checkout. Preserve unrelated changes.
4. Trace each valid finding to the earliest responsible canonical input or decision and all affected consumers. For specimen/reference findings, use the [acceptance contract](../../../verification/RESUME.md#specimen-and-reference-acceptance-contract) across the affected corpus. If a related finding recurs, reopen the causal model and inspect sibling cases before patching another symptom. Apply the minimum complete fix; for nontrivial behavior, exercise the violated invariant with the reported case and a relevant sibling/boundary case.
5. Run the narrowest useful checks. If the fix changes a canonical input or generator, run `python scripts/regen.py` to materialize every projection; otherwise run `python scripts/regen.py --check`. Review the complete diff before committing.
6. Commit and push to the PR branch only when authorized. Rerun `python verification/review_findings.py` after the pushed commit so P6/P7 inspect the real history.
7. Reply to actionable or newly assessed review threads with the disposition, fix commit and check evidence; retain existing adequate replies. Request review of the current exact head and verify the resulting review actually covers that SHA. If the head moves, reassess from step 1; pending or unavailable review is not a clean review.
8. When asked to monitor, continue until checks and the exact-head review are clean, the PR closes, or a concrete blocker requires user input. Honor the user's polling cadence or the configured watcher cadence; back off on unchanged state. Do not replace a requested multi-minute interval with a tight loop. Before declaring completion, refresh the full finding inventory and head again.

Merge only on explicit instruction, with expected-head protection and after confirming required checks and unresolved-thread count again. Report the final head SHA, fixes, replies, checks, merge state, and remaining blockers.

## PR-remediation finding inventory

At startup, resume and final verification, exhaust pagination for review summaries, issue comments,
inline comments and review threads, including each thread's nested comment pages. Inspect check
annotations too. A latest-N response or `first: 100` with `hasNextPage=true` is incomplete; report
an inaccessible page rather than claiming zero findings. Keep review/comment/thread IDs and URLs
so repeated reports map to the same finding without dropping distinct concerns.

Maintain one compact task-local ledger:
`Finding ID | disposition | violated invariant/root cause | fix commit | validation | reply ID`.
Record why an outdated or resolved finding stays closed at the current head. Validate evidence
against that head, including older findings whose original code disappeared. Report concrete
coverage and remaining gaps; self-awarded quality scores are not acceptance evidence.

Batch fixes with a shared cause, run focused checks while iterating and the required gate after
the batch. Recheck changed inputs or new failures; do not repeat expensive checks for unchanged
state. This workflow is usable on its own; an installed global PR watcher is optional and may
orchestrate it without creating a second ledger or weakening the exact-head boundary.

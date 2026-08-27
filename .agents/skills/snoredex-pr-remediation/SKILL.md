---
name: snoredex-pr-remediation
description: Remediate an existing Snoredex-Data pull request until actionable review findings and PR-caused CI failures are resolved at the exact head. Use for PR reviews, failing checks, conflicts, or babysitting; not for new feature scope.
---

<!-- doc: role=pull-request remediation workflow skill; stage=task -->

# Snoredex PR remediation

Make the smallest justified repair to the current pull-request head and leave an auditable clean-review result.

## PR-remediation context

Read [CLAUDE.md](../../../CLAUDE.md), [HANDOVER.md](../../../HANDOVER.md), and [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md). Inspect the complete PR, its base and head SHAs, commits, checks, annotations, review summaries, inline threads, and linked issue. Treat old summaries as stale until checked against the live head.

## PR-remediation workflow

1. Record the exact PR head SHA and determine whether the PR is draft, mergeable, conflicted, or already closed.
2. Classify every unresolved finding as actionable, outdated, already fixed, unrelated, infrastructure failure, or requiring user input. Explain disagreements with evidence; do not change code merely to silence a reviewer.
3. Work in the PR branch or a safe isolated worktree without disturbing another checkout. Preserve unrelated changes.
4. Trace each valid finding to its shared root cause and all affected consumers. Apply the minimum complete fix and a focused regression check.
5. Run the narrowest useful checks, then `python scripts/regen.py --check`. Review the diff before committing.
6. Commit and push to the PR branch only when authorized. Rerun `python verification/review_findings.py` after the pushed commit so P6/P7 inspect the real history.
7. Reply to each review thread with the disposition and evidence. Request a new review only for the unchanged exact head; if the head moves, reassess from step 1.
8. When asked to monitor, continue until checks and the exact-head review are clean, the PR closes, or a concrete blocker requires user input. Do not spin on unchanged pending state.

Merge only on explicit instruction, with expected-head protection and after confirming required checks and unresolved-thread count again. Report the final head SHA, fixes, replies, checks, merge state, and remaining blockers.

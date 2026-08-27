---
name: snoredex-issue-delivery
description: Deliver one Snoredex-Data issue through implementation and verification to a review-ready branch or pull request. Use for implementing or fixing a specific issue; not for review-only remediation or broad backlog planning.
---

<!-- doc: role=issue-delivery workflow skill; stage=task -->

# Snoredex issue delivery

Complete one issue without mixing unrelated work or weakening the repository's evidence and gate contracts.

## Issue-delivery context

Work from the repository root. Read [CLAUDE.md](../../../CLAUDE.md), [HANDOVER.md](../../../HANDOVER.md), and [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md). Read the full issue, every comment, linked issue and relevant pull request before planning. If the issue changes evidence, read the domain document required by `CLAUDE.md` before editing.

## Issue-delivery workflow

1. Confirm the requested issue and authorization boundary. Do not infer permission to merge, publish, close other issues, or expand the task.
2. Fetch `origin` and start from current `origin/main`. Reuse an existing branch only when it belongs exclusively to this issue and its work is understood; otherwise create one isolated issue branch.
3. Run `python scripts/regen.py --check` before editing. Preserve and report any pre-existing failure instead of folding it into the issue.
4. Trace the issue from canonical input through graph edges, projections, consumers, and gates using `WORKFLOW-MAP.md`. Identify generated and archived files that must not be edited.
5. Implement the smallest complete change at the canonical owner. Add the narrowest meaningful regression check when behavior changes.
6. Use `python scripts/scoped_regen.py --lane <lane>` for fast feedback when a manifest lane matches. Treat its Run-ID and skipped checks as partial evidence only.
7. Run `python scripts/regen.py`, inspect the complete diff, and verify that unrelated user changes remain untouched.
8. Commit and push only when authorized. After any commit and push, rerun `python verification/review_findings.py` so the history-sensitive checks see the actual commit.
9. Create or update a pull request only when requested. Link the issue, describe canonical inputs and graph impact, and report scoped plus L3 verification accurately.

Finish with the issue state, branch or PR, files changed, verification results, known pre-existing failures, and any required owner or source input. Merge only on explicit instruction.

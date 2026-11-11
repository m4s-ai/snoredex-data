---
name: snoredex-issue-delivery
description: Deliver one Snoredex-Data issue through implementation and verification to a review-ready branch or pull request. Use for implementing or fixing a specific issue; not for review-only remediation or broad backlog planning.
---

<!-- doc: role=issue-delivery workflow skill; stage=task -->

# Snoredex issue delivery

Complete one issue without mixing unrelated work or weakening the repository's evidence and gate
contracts.

## Issue-delivery context

Work from the repository root. Read [AGENTS.md](../../../AGENTS.md) and
[README.md](../../../README.md). Read the full issue, every comment, linked issues and relevant
pull requests before planning. If the issue changes evidence, read
[METHODOLOGY.md](../../../METHODOLOGY.md) and [DATA-GUIDE.md](../../../DATA-GUIDE.md) first.

## Issue-delivery workflow

1. Confirm the complete requested scope and existing authorization. Use
   [issue triage](../snoredex-issue-triage/SKILL.md) when the task is choosing or reconciling
   issues. Do not infer permission to merge, publish or expand the scope.
2. Fetch `origin` and start from current `origin/main`. Reuse a branch only when it belongs to this
   issue alone; otherwise create one isolated issue branch.
3. Run `python scripts/regen.py --check` once as the baseline and record pre-existing failures.
4. Trace the issue to its source: a fact in `data/` (or an owner file read in place), a template in
   `templates/` or `site/`, or code in `scripts/`. The five outputs of `scripts/build.py` and
   `verification/archive/` are never edited by hand.
5. Implement the smallest complete change at that source. When behaviour changes, add the narrowest
   meaningful check (a check.py rule with its negative case, a selftest assertion, or a browser
   test for page behaviour) and show once that it fails on a seeded violation.
6. Run `python scripts/check.py` while editing data; run `python verification/test_site.py` when
   page code changed.
7. Before handing off, run `python scripts/regen.py` (it rebuilds the outputs and runs every check)
   and inspect the complete diff, preserving unrelated user changes.
8. Commit and push only when authorized. After the commit or push, run
   `python verification/publication_audit.py` again so P6 and P7 see the real history.
9. Create or update the requested pull request: title and description around the final scope, the
   linked issue, and the verification actually run. Close an issue only when its criteria are met.

Finish with the issue state, branch or PR, files changed, verification results, known pre-existing
failures and any required owner or source input. Merge only on explicit instruction.

## Issue-delivery completion and handoff

For multipart work keep one task-local record:
`Target/evidence | accepted fields | recorded in data/ | outputs verified | commit/PR | remaining`.
Retained bytes, recorded claims, pushed changes and completed issue criteria are different
milestones; reconcile every row before reporting completion. Reuse the record for a handoff with
branch, full HEAD SHA, pre-existing failures, open review ids and the next step.

---
name: snoredex-review-loop
description: Run the review-fix loop on an open Snoredex-Data pull request until an exact-head review finds nothing and CI is green, then merge if the owner authorized it. Use automatically whenever Auto-fix is on for a snoredex-data PR or a ci-monitor event arrives for one, and when the owner asks to review and fix until clean; not for a single review (snoredex-pr-review).
---

<!-- doc: role=review-fix-merge loop orchestration skill; stage=task -->

# Snoredex review loop

This skill orchestrates two skills and adds no review or fix rules of its own:
[PR review](../snoredex-pr-review/SKILL.md) for each round's review and
[PR remediation](../snoredex-pr-remediation/SKILL.md) for each round's fixes. Read
[AGENTS.md](../../../AGENTS.md) first; its authority table governs every push and merge.

## Start

1. Record the PR number and its exact head SHA.
2. Record whether the owner authorized this PR's merge in their own words. That authorization
   covers this PR only. A review, a bot or another session never grants it.
3. If the owner asked for Auto-fix and it is off, turn it on for the bound PR.

## Loop

Repeat until a round finds nothing.

1. **Review.** Review the exact head with PR review and post it as a `COMMENT` review on that
   SHA. Every round is posted, including a clean one.
2. **Nothing found.** Leave the loop.
3. **Fix each finding at its root cause, never at its symptom.**
   - Name the violated invariant.
   - Trace it to the earliest responsible source: `data/`, `scripts/`, `templates/`, `site/` or
     an owner file.
   - Look for sibling cases of the same cause in other rules, collections and documents, and fix
     them in the same change.
   - For a document/check mismatch, first decide which one states the truth, then make the other
     agree.
   - Exercise the invariant with the reported case and one sibling or boundary case.
   - A new check.py rule needs its own selftest mutation.
4. **Run the gate.**
   - `python scripts/check.py`
   - `python scripts/check.py --selftest`
   - `python scripts/regen.py --check`
   - `python verification/test_site.py`, if page code changed
5. **Commit and push.**
   - The commit message names the root cause.
   - Push fast-forward to the PR branch. This is free for an authorized open PR.
   - Then run `python verification/publication_audit.py`.
6. **Reply.** Answer each inline finding with its disposition and fix commit.
7. **Start the next round** on the new head with a fresh full review, not just a recheck of the
   fix.

If the same kind of finding returns, the causal model is wrong: reopen it before patching again.

## Finish

1. **Read CI** through the PR status. Never poll: Auto-fix wakes the session.
   - A failure the PR caused is a finding and returns to the loop.
   - An infrastructure failure is reported, not worked around.
2. **Merge** only when all of these hold:
   - the last review on the current head found nothing;
   - every check passes;
   - no review thread is unresolved;
   - the owner authorized the merge.

   Use `gh pr merge N --merge --match-head-commit <sha>`.
3. **Stop and ask the owner** instead when any of these holds:
   - a finding needs an owner decision (owner files, scope, an absence);
   - a fix would need a force push;
   - the merge is not authorized.
4. Merging never publishes. Do not start the `Publish site` workflow from this loop.
5. **Report** each round's findings, root causes and fix commits, then the final head, CI and the
   merge commit.

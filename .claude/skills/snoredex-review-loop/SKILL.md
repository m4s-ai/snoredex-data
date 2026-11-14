---
name: snoredex-review-loop
description: Run the review-fix loop on an open Snoredex-Data pull request until an exact-head review finds nothing and CI is green, then merge if the owner authorized it. Use automatically whenever Auto-fix is on for a snoredex-data PR or a ci-monitor event arrives for one, and when the owner asks to review and fix until clean; not for a single review (snoredex-pr-review).
---

<!-- doc: role=Claude Code discovery shim for the snoredex-review-loop skill; stage=task -->

# Snoredex review loop (shim)

Read and follow [the canonical skill](../../../.agents/skills/snoredex-review-loop/SKILL.md) with the
arguments given. Keep this file a pointer; the procedure lives only in the canonical skill.

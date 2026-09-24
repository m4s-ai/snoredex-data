---
name: snoredex-issue-triage
description: Reconcile Snoredex issues with current evidence, identify remaining fields and dependencies, and rank the next executable work. Use for backlog planning, progress reconciliation or authorized issue maintenance; not for implementing a selected issue or a repository-only state audit.
---

<!-- doc: role=issue-triage workflow skill; stage=task -->

# Snoredex issue triage

Establish what remains before choosing work. Report-only requests leave issues and data unchanged.

## Issue-triage context

Read [AGENTS.md](../../../AGENTS.md), [HANDOVER.md](../../../HANDOVER.md) and
[WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md). Read the evidence/finish contracts named there
when assessing those fields; a tracker checkbox is not evidence.

## Issue-triage workflow

1. Read the requested issues' complete bodies, all comment pages, linked PRs and dependencies.
   Record the repository SHA and retrieval time. Inspect current stores and retained evidence;
   distinguish committed, PR-only and merely proposed work. Do not execute imports or refreshes.
2. Recover each issue's original target cohort and completion criteria. Keep that denominator
   separate from today's catalogue. Count unique targets at the issue's stated granularity;
   parent/child overlap, duplicate release references and extra photos do not add completed cards.
3. For each target, reconcile identity, language/locality, finish, date, image/provenance and
   reference integration separately. Verify the relevant downstream consumers using the
   [reference acceptance contract](../../../verification/RESUME.md#specimen-and-reference-acceptance-contract).
   Reuse retained evidence before proposing another search. Distinguish missing evidence,
   evidence awaiting integration and stale tracker text; do not treat uncertainty as absence.
4. Identify dependency order and blockers. Rank by the user's requested criterion, such as fewest
   remaining cards, effort or downstream impact; if none is given, prioritize unblocked work with
   retained evidence and state that assumption. A low remaining count does not erase a blocker.
5. Return one compact table: `Issue | verified state | missing fields | blockers/dependencies |
   next step/skill`. Include supporting IDs/links and cohort-qualified counts; flag contradictions
   or unavailable inputs instead of manufacturing a precise progress figure.
6. Route targeted searches to [card search](../card-search/SKILL.md), supplied assertions to
   [claim evidence](../snoredex-claim-evidence/SKILL.md), photos to
   [specimen intake](../snoredex-specimen-intake/SKILL.md), and implementation to
   [issue delivery](../snoredex-issue-delivery/SKILL.md). Provider registration belongs to
   [source onboarding](../snoredex-source-onboarding/SKILL.md). Selecting work is not doing it.

## Issue-triage maintenance

When issue maintenance is already authorized, reconcile title counts, body checkboxes and relevant
parent/child references from the same verified snapshot. Preserve unrelated text and reread before
writing to avoid overwriting concurrent edits. A progress comment alone does not repair a stale
title. Close an issue only when its own completion criteria are met and closure is within the
authorized scope; partial evidence or an unmerged delivery is not automatically completion.
Report actual edits and remaining work. Do not request the same authorization again or create
another persistent backlog store.

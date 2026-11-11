---
name: snoredex-issue-triage
description: Reconcile Snoredex issues with current evidence, identify remaining fields and dependencies, and rank the next executable work. Use for backlog planning, progress reconciliation or authorized issue maintenance; not for implementing a selected issue or a repository-only state audit.
---

<!-- doc: role=issue-triage workflow skill; stage=task -->

# Snoredex issue triage

Establish what remains before choosing work. Report-only requests leave issues and data unchanged.

## Issue-triage context

Read [AGENTS.md](../../../AGENTS.md), [METHODOLOGY.md](../../../METHODOLOGY.md) and
[DATA-GUIDE.md](../../../DATA-GUIDE.md) when assessing evidence or finish fields; a tracker
checkbox is not evidence.

## Issue-triage workflow

1. Read the requested issues' complete bodies, all comment pages, linked PRs and dependencies.
   Record the repository SHA and retrieval time. Inspect the current records in `data/`,
   `verification/specimens.json` and retained evidence under `verification/evidence/`; distinguish
   committed, PR-only and merely proposed work. Do not edit data.
2. Recover each issue's original target cohort and completion criteria. Keep that denominator
   separate from today's catalogue; parent/child overlap, duplicate references and extra photos do
   not add completed cards.
3. For each target, reconcile identity, language and locality, finish, date, image and provenance
   separately. Reuse retained evidence before proposing another search. Distinguish missing
   evidence, evidence awaiting recording and stale tracker text; uncertainty is not absence.
4. Identify dependency order and blockers. Rank by the user's criterion; if none is given,
   prioritize unblocked work with retained evidence and state that assumption.
5. Return one compact table: `Issue | verified state | missing fields | blockers/dependencies |
   next step/skill`, with supporting ids and links. Flag contradictions or unavailable inputs
   instead of manufacturing a precise progress figure.
6. Route targeted searches to [card search](../card-search/SKILL.md), supplied assertions to
   [claim evidence](../snoredex-claim-evidence/SKILL.md), photos to
   [specimen intake](../snoredex-specimen-intake/SKILL.md), and implementation to
   [issue delivery](../snoredex-issue-delivery/SKILL.md). Selecting work is not doing it.

## Issue-triage maintenance

When issue maintenance is authorized, reconcile title counts, body checkboxes and parent/child
references from the same verified snapshot. Preserve unrelated text and reread before writing. Close
an issue only when its own criteria are met and closure is within the authorized scope. Report the
actual edits and the remaining work.

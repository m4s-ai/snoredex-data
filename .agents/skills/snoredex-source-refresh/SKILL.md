---
name: snoredex-source-refresh
description: Refresh and reconcile Snoredex source-first set and card discovery runs. Use for scheduled, release-triggered, provider-change, or manual catalogue discovery; not for applying evidence to an already-known unit.
---

# Snoredex source refresh

Create one immutable provider refresh and reconcile every result to a visible terminal state without turning source failure or silence into a verdict.

## Required context

Read [CLAUDE.md](../../../CLAUDE.md), [HANDOVER.md](../../../HANDOVER.md), [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md), and [RECURRENCE.md](../../../verification/RECURRENCE.md). Treat the adapter and discovery manifests as reviewed contracts and their generated staging files as review surfaces, not truth stores.

## Workflow

1. Confirm whether the request is offline validation or an authorized live refresh. Network access and scheduling do not authorize commits, merges, publication, or canonical verdict changes.
2. Run `python scripts/discovery_cycle.py --check` for retained-run validation. For a live refresh, create a unique UTC run ID and run `python scripts/discovery_cycle.py --refresh --run-id <YYYYMMDDTHHMMSSZ>`.
3. Verify request/checkpoint manifests, raw bytes, hashes, provider errors, pagination, and source-capability boundaries before interpreting records.
4. Review every added, changed, disappeared, re-keyed, ambiguous, unmapped, `needsEvidence`, and gap record. Preserve provider-native locality and identifiers.
5. Reconcile records through the reviewed adapter/card-discovery inputs. A candidate cannot directly mutate language, finish, set, or absence verdicts.
6. Run `python scripts/workflow_loop.py --loop discovery --max-cycles 3` and `python scripts/scoped_regen.py --lane source-discovery`. Stop when the source or owner input named by the runner is required.
7. Run `python scripts/regen.py`, inspect completeness and graph changes, and report run IDs, hashes, provider failures, reconciliation counts, explicit gaps, and remaining blockers.

Never rewrite an immutable run, the legacy Cardmarket baseline, or an archived pass. Zero rows and unreachable providers are failures or gaps, not empty catalogues.

---
name: snoredex-finish-refresh
description: Refresh, review, accept, and project the versioned TCGdex finish snapshot for Snoredex. Use for monthly drift review, pre-release checks, or known upstream changes; not for specimen or curated finish corrections.
---

# Snoredex finish refresh

Perform the explicit TCGdex candidate-to-snapshot workflow while keeping ordinary regeneration offline and reproducible.

## Required context

Read [CLAUDE.md](../../../CLAUDE.md), [HANDOVER.md](../../../HANDOVER.md), [FINISH_SOURCES.md](../../../verification/FINISH_SOURCES.md), and the finish-refresh path in [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md).

## Workflow

1. Establish a clean baseline with `python scripts/regen.py --check` and record pre-existing failures.
2. Stage one live candidate with `python scripts/finishes.py --refresh`. Treat exit code 2 as a source or transport failure; retry later rather than interpreting it as finish evidence.
3. Review the staged candidate's source URL set, payload hashes, added URLs, changed payloads, removed URLs, and affected finish units. TCGdex `true` may confirm a printing; `false` cannot refute one.
4. Report the candidate and stop for explicit owner acceptance when committed snapshot bytes would change. Do not refetch between review and acceptance.
5. After acceptance is authorized, run `python scripts/finishes.py --refresh --accept-refresh` to consume that exact staged candidate.
6. Run `python scripts/workflow_loop.py --loop tcgdex --max-cycles 3`, then `python scripts/regen.py` for the offline projection and full gate.
7. Review the snapshot, finish units, checklist, graph, collector, database, and site diffs. Report accepted hashes, affected URLs and units, gate results, and remaining finish gaps.

Do not edit the transport cache as truth, accept an unreviewed candidate, or infer a physical finish from language confirmation.

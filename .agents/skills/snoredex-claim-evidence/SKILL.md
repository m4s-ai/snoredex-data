---
name: snoredex-claim-evidence
description: Apply positive external-source or collection-owner evidence to an existing Snoredex card-language-variant claim. Use for confirmations, contradictions, and adjudication inputs; not for photographs, source-first discovery, or TCGdex refreshes.
---

<!-- doc: role=claim-evidence workflow skill; stage=task -->

# Snoredex claim evidence

Bring one already-identified claim to the strongest state justified by the supplied evidence while preserving its provenance and uncertainty.

## Claim-evidence context

Work from the repository root. Read [CLAUDE.md](../../../CLAUDE.md), [HANDOVER.md](../../../HANDOVER.md), and the complete [verification playbook](../../../verification/RESUME.md) before changing evidence. Read [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md) to identify downstream impact. If the claim concerns finish, foil, stamp, marking, or size, also read [FINISH_SOURCES.md](../../../verification/FINISH_SOURCES.md).

## Claim-evidence workflow

1. Identify the exact `(setCode, number, variant, language)` unit and separate language existence, locality, finish, edition, and distribution claims.
2. Establish a clean baseline with `python scripts/regen.py --check`. Record any pre-existing failure; do not hide it in the evidence change.
3. Classify what the source positively establishes. Provider silence, missing rows, zero results, and TCGdex `false` are not negative evidence.
4. Resolve the provider and its capability in the reviewed source registry. Attribute the claim to the source it would fail without; mark corroboration only when a second provider supports this same unit.
5. Follow `RESUME.md` to update the canonical store and append the observation journal. Never edit generated projections, reuse a neighbour's evidence, or invent a source reference.
6. Treat an explicit collection-owner absence decision as adjudication input. A scoped source may support the rationale but cannot itself produce `not-printed`; otherwise leave the claim pending or disputed.
7. Run the smallest relevant check while iterating:
   - ordinary claim change: `python scripts/scoped_regen.py --lane correction`
   - owner absence adjudication: `python scripts/scoped_regen.py --lane absence`
   - state-machine diagnosis: `python scripts/workflow_loop.py --loop evidence --max-cycles 3` or `--loop absence`
8. Run `python scripts/regen.py`, review every changed canonical and generated artifact, and report the evidence, provider, status transition, graph impact, and remaining uncertainty.

Stop without changing the claim when identity, locality, source capability, or owner intent is unresolved.

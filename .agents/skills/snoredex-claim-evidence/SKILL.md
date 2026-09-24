---
name: snoredex-claim-evidence
description: Apply positive external-source or collection-owner evidence to an existing Snoredex card-language-variant claim. Use for confirmations, contradictions, and adjudication inputs; not for photographs, source-first discovery, or TCGdex refreshes.
---

<!-- doc: role=claim-evidence workflow skill; stage=task -->

# Snoredex claim evidence

Bring one already-identified claim to the strongest state justified by the supplied evidence while preserving its provenance and uncertainty.

## Claim-evidence context

Work from the repository root. Read [AGENTS.md](../../../AGENTS.md), [HANDOVER.md](../../../HANDOVER.md), and the complete [verification playbook](../../../verification/RESUME.md) before changing evidence. Read [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md) to identify downstream impact. If the claim concerns finish, foil, stamp, marking, or size, also read [FINISH_SOURCES.md](../../../verification/FINISH_SOURCES.md).

## Claim-evidence workflow

1. Identify the exact `(setCode, number, variant, language)` unit and separate language existence, locality, finish, edition, and distribution claims.
2. Establish a clean baseline with `python scripts/regen.py --check`. Record any pre-existing failure; do not hide it in the evidence change.
3. Classify what the source positively establishes. Provider silence, missing rows, zero results, and TCGdex `false` are not negative evidence.
4. Resolve the provider and its capability in the reviewed source registry. Attribute the claim to the source it would fail without; mark corroboration only when a second provider supports this same unit.
5. Follow `RESUME.md` to update the canonical store and append the observation journal. For specimen-backed claims or changed references, apply its [specimen and reference acceptance contract](../../../verification/RESUME.md#specimen-and-reference-acceptance-contract). Never edit generated projections, reuse a neighbour's evidence, or invent a source reference.
6. Treat an explicit collection-owner absence decision as adjudication input. A scoped source may support the rationale but cannot itself produce `not-printed`; otherwise leave the claim pending or disputed.
7. Run the smallest relevant check while iterating:
   - ordinary claim change: `python scripts/scoped_regen.py --lane correction`
   - owner absence adjudication: `python scripts/scoped_regen.py --lane absence`
   - state-machine diagnosis: `python scripts/workflow_loop.py --loop evidence --max-cycles 3` or `--loop absence`
8. Run `python scripts/regen.py`, review every changed canonical and generated artifact, and report the evidence, provider, status transition, graph impact, and remaining uncertainty.

## Claim-evidence source-recovery

For a source link that is bot-gated (Cloudflare/CAPTCHA/403/JS), do **not** reinvent retrieval:
follow the acquisition and retention steps in
[source-refresh bot-gated retrieval](../snoredex-source-refresh/SKILL.md#source-refresh-bot-gated-retrieval),
then classify here what the recovered source positively establishes for this exact unit. Retrieval
is never evidence on its own; the determination that the source proves (or does not prove) a claim
is this workflow's task.

For localized set-code research, inspect the exact TCGCollector card page and preserve its native
set code, number and language in the retained research snapshot. Resolve its provider/surface
against the current inventory. If the needed capability is missing and registration is authorized, use
[source onboarding](../snoredex-source-onboarding/SKILL.md); otherwise keep the result as a lead
until its source contract is reviewed, without changing a verdict or marking corroboration. Check
`verification/source_first_prints.json` and the reviewed
identity/source stores before calling a find new. If an official source already establishes that
same field for that same release, evaluate the page as possible corroboration under the provider's
capabilities; never assign corroboration merely because the page exists. Catalogue metadata is not
specimen evidence and cannot establish physical finish. Source silence proves neither absence nor
first release; keep catch-up/reprint identities separate from the original set.

Stop without changing the claim when identity, locality, source capability, or owner intent is unresolved.

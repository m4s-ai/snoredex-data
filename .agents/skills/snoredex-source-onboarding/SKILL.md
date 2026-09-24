---
name: snoredex-source-onboarding
description: Review and register a new Snoredex provider or source surface and its positive field and locality capabilities. Use when adding a source or extending its reviewed authority; not for refreshing an established adapter, applying one known-source claim or importing photos.
---

<!-- doc: role=source-onboarding workflow skill; stage=task -->

# Snoredex source onboarding

Make a source usable for the fields it actually supports through the existing owners.
Review-only requests produce a proposed contract; authorized onboarding implements it.

## Source-onboarding context

Read [AGENTS.md](../../../AGENTS.md), [HANDOVER.md](../../../HANDOVER.md),
[WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md),
[ADR-0003](../../../verification/ADR-0003-source-capability-coverage.md) and the complete
[verification playbook](../../../verification/RESUME.md). For physical treatments also read
[FINISH_SOURCES.md](../../../verification/FINISH_SOURCES.md).

## Source-onboarding workflow

1. Inspect the current provider, capability and adapter inventories before adding anything.
   Identify the operator, exact surface, source-native identifiers, access/retention constraints
   and intended use. A new URL on an existing surface may need no new provider or adapter.
2. Retain a real positive example with source URL, actual observation/retrieval date, content or
   precise excerpt, its hash and field attribution. Use the existing
   [retrieval and retention path](../snoredex-source-refresh/SKILL.md#source-refresh-bot-gated-retrieval).
   Record supported fields and locality, language, product and time bounds, plus an example outside
   that capability. A failed fetch is an access gap, not proof of no coverage.
3. Apply the owner's explicit source-use decision and the repository evidence rules together.
   Do not invent a discovery-only restriction contrary to an authorized positive capability.
   Equally, approval does not manufacture fields: preserve native values, keep unreviewed
   normalized mappings null and never transfer language, rarity or finish between releases.
   An external provider cannot establish absence or close a finish list.
4. Before authorized writes, establish `python scripts/regen.py --check`. Update the canonical
   `PROVIDERS` declarations in [source_registry.py](../../../scripts/source_registry.py) and the
   reviewed [source capabilities](../../../verification/source_capabilities.json) as needed.
   The generated `verification/source_registry.json` and `verification/SOURCES.md` are outputs.
   Reconcile contradictory active guidance, affected mappings and consumers in the same change.
5. Add or extend an adapter only for a requested automated acquisition need. Use the existing
   [source adapter inventory](../../../verification/source_adapters.json) or
   [card discovery inventory](../../../verification/card_discovery_adapters.json) and ADR-0003's
   retained positive/boundary fixtures. Manual evidence use does not require an automated adapter;
   registering a provider alone does not make an adapter active.
6. Exercise the positive example and the unsupported boundary through the relevant existing
   checks. If application is authorized, route it to [claim evidence](../snoredex-claim-evidence/SKILL.md),
   [specimen intake](../snoredex-specimen-intake/SKILL.md) or
   [source reconciliation](../snoredex-source-refresh/SKILL.md) and verify its affected consumers.
   Otherwise validate the contract without accepting a claim. A native rarity label alone cannot
   establish a physical finish; a missing language row cannot disprove a printing.
7. Run the relevant scoped source-discovery checks while iterating, then `python scripts/regen.py`
   and the required L3 check before delivery. Inspect source grading, provenance and consumer
   changes. Follow [issue delivery](../snoredex-issue-delivery/SKILL.md) for the authorized PR work.

Report the provider/surface, supported fields and explicit limits, retained examples, manual versus
automated use, checks and any remaining access or mapping gaps. Do not create a parallel registry.

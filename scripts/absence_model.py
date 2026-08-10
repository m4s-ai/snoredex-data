#!/usr/bin/env python3
"""When a contradiction is a final absence decision, and when it is only a disagreement (#66).

`contradicted` in `verification/units.json` means an outside source disagrees with Cardmarket's
language claim. It does *not* mean the printing has been shown not to exist, and the two are
different enough that consumers must be able to tell them apart:

    not-printed   an explicit collection-owner adjudication has settled the question
    disputed      a source disagrees and no adjudication has settled it

`scripts/database.py` has drawn that line correctly since the clean-handoff work, and `DATABASE.md`
tells applications "do not turn [disputed] into a hard 'does not exist'". But the line lived only
inside the database, so `snorlax_cards.json`, the checklist and the site went on presenting all 85
contradictions as one settled block of "refuted claims" — 73 of which are a single uncorroborated
source's disagreement.

The rule is one rule, so it is written once here and imported by both generators rather than
implemented twice and left to drift. Two independent computations of one fact is exactly the shape
of #64, where `providerId` and `source_registry.py` disagreed for weeks with nothing comparing them.

The absence scopes come from `verification/source_registry.json`, where a provider may declare
`absenceScopes` — specific URLs whose contents are complete manifests. They record evidence the
owner may weigh; they never settle a claim by themselves. Authority tier alone is never enough: a
tier-1 provider's blog post proves nothing about absence, while a published set checklist can
support an adjudication only within its own scope.
"""

from __future__ import annotations

from typing import Any, Iterable


def absence_scope_urls(providers: Iterable[dict[str, Any]]) -> set[str]:
    """Every URL a provider has declared to be a complete, absence-capable manifest."""
    return {
        url.rstrip("/")
        for provider in providers
        if provider.get("supportsAbsence")
        for url in provider.get("absenceScopes") or []
    }


def absence_decision(status: str, adjudicated: bool) -> str:
    """Classify one resolved language unit for consumers.

    Returns `exists`, `not-printed`, `disputed` or `unresolved`.

    `not-printed` requires an explicit collection-owner adjudication — always, with no exception
    (owner decision, 2026-08-03). A declared absence scope is recorded rationale, never a
    mechanism: it strengthens the case the owner weighs, and consumers expose that capability
    separately, but it cannot settle anything by itself.

    The reasoning is the owner's: converging evidence from dependable sources is *Indizien*, and
    deciding which way it points — printed, or not printed — is the collector's job rather than a
    property any single page can assert. This is stricter than the rule it replaces, which settled
    a claim on a scoped source alone. No row moves: every scoped-source row already carries an
    adjudication.

    `not-printed` means **no regular release**. A proof copy or an error card is a different
    category and does not falsify the decision.
    """
    if status == "confirmed":
        return "exists"
    if status == "contradicted":
        return "not-printed" if adjudicated else "disputed"
    return "unresolved"

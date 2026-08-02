#!/usr/bin/env python3
"""When a contradiction is a final absence decision, and when it is only a disagreement (#66).

`contradicted` in `verification/units.json` means an outside source disagrees with Cardmarket's
language claim. It does *not* mean the printing has been shown not to exist, and the two are
different enough that consumers must be able to tell them apart:

    not-printed   an explicit collection-owner adjudication, or a source whose scope is a complete
                  official manifest, has settled the question within that scope
    disputed      a source disagrees and nothing has settled it

`scripts/database.py` has drawn that line correctly since the clean-handoff work, and `DATABASE.md`
tells applications "do not turn [disputed] into a hard 'does not exist'". But the line lived only
inside the database, so `snorlax_cards.json`, the checklist and the site went on presenting all 85
contradictions as one settled block of "refuted claims" — 73 of which are a single uncorroborated
source's disagreement.

The rule is one rule, so it is written once here and imported by both generators rather than
implemented twice and left to drift. Two independent computations of one fact is exactly the shape
of #64, where `providerId` and `source_registry.py` disagreed for weeks with nothing comparing them.

The absence scopes come from `verification/source_registry.json`, where a provider may declare
`absenceScopes` — specific URLs whose contents are complete manifests. Authority tier alone is
never enough: a tier-1 provider's blog post proves nothing about absence, while a tier-1 provider's
published set checklist does, and only within its own scope.
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


def source_settles_absence(source_url: str | None, scope_urls: set[str]) -> bool:
    """True when this exact source is one of the declared complete manifests.

    Keyed on the URL, not the provider. A provider "supporting absence" means it has published at
    least one complete manifest somewhere, which says nothing about the page a given claim cites.
    """
    return bool(source_url) and source_url.rstrip("/") in scope_urls


def absence_decision(status: str, source_url: str | None, scope_urls: set[str],
                     adjudicated: bool) -> str:
    """Classify one resolved language unit for consumers.

    Returns `exists`, `not-printed`, `disputed` or `unresolved`. `not-printed` is deliberately the
    narrow case: it requires someone to have taken responsibility for the decision — the collection
    owner in writing, or a publisher's own complete manifest — because absence is the one claim
    this project treats as harder to make than presence.
    """
    if status == "confirmed":
        return "exists"
    if status == "contradicted":
        if adjudicated or source_settles_absence(source_url, scope_urls):
            return "not-printed"
        return "disputed"
    return "unresolved"

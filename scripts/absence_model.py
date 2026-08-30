#!/usr/bin/env python3
"""Project raw language verdicts into final consumer states."""

from __future__ import annotations

def absence_decision(status: str, adjudicated: bool) -> str:
    """Classify one resolved language unit for consumers.

    Returns `exists`, `not-printed`, `disputed` or `unresolved`.

    `not-printed` requires an explicit collection-owner adjudication. External sources provide
    positive evidence or disagreement, never the final absence decision.
    """
    if status == "confirmed":
        return "exists"
    if status == "contradicted":
        return "not-printed" if adjudicated else "disputed"
    return "unresolved"

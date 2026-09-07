"""Shared semantic identity for physical printing projections."""

from __future__ import annotations

import hashlib
import json
from typing import Any

FOIL_PATTERN_ALIASES = {
    "poke ball mirror": "poke-ball",
    "poké ball mirror": "poke-ball",
    "master ball mirror": "master-ball",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalized_foil_pattern(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return FOIL_PATTERN_ALIASES.get(value.strip().casefold(), value)


def normalized_markings(value: Any) -> list[dict[str, Any]] | Any | None:
    """Copy and sort marking records so list order is not part of identity."""
    if not value:
        return None
    if not isinstance(value, list):
        return value
    return sorted((dict(row) for row in value), key=canonical_bytes)


def printing_semantic_key(scope: Any, printing: dict[str, Any]) -> bytes:
    return canonical_bytes(_semantic_payload(scope, printing, include_edition=True))


def printing_semantic_core_key(scope: Any, printing: dict[str, Any]) -> bytes:
    return canonical_bytes(_semantic_payload(scope, printing, include_edition=False))


def _semantic_payload(scope: Any, printing: dict[str, Any], *, include_edition: bool) -> dict[str, Any]:
    payload = {
        "scope": str(scope or ""),
        "finish": printing.get("finish"),
        "foilPattern": normalized_foil_pattern(printing.get("foilPattern")),
        "markings": normalized_markings(printing.get("markings")),
        "distribution": printing.get("distribution") or None,
        "cardSize": printing.get("cardSize") or "unknown",
    }
    if include_edition:
        payload["edition"] = printing.get("edition")
    return payload


def stable_printing_id(semantic_key: bytes) -> str:
    return "PRINTING:" + hashlib.sha256(semantic_key).hexdigest()[:24]

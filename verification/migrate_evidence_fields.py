#!/usr/bin/env python3
"""One-shot: split evidence identity out of the two overloaded fields (#32).

    python verification/migrate_evidence_fields.py [--dry-run]

`sourceUrl` carried either a URL or a sentence, and `sourceType` carried both the provider and,
for some units, the fact that a second source agreed. Neither could be queried. This promotes
what `scripts/source_registry.py` already derives into the store itself:

  providerId    which declared provider the evidence comes from, from the 18-provider registry
  sourceRef     the prose that used to sit in `sourceUrl`, for evidence that has no URL
  corroborated  whether more than one provider is named for the claim
  sourceUrl     now a URL or null, never a sentence

`sourceType` stays as it is. It carries the detail that makes each citation checkable — which
table, which article section, which field — and no enum reproduces that.

Only resolved units are touched. Unresolved ones have no evidence, and `corroborated: false` on a
pending unit would assert something about evidence that does not exist.

The script is idempotent: rerunning it produces the same file. It is kept in the tree rather than
deleted because it documents how the fields were derived, and because the derivation is the thing
a reviewer would want to re-check.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from checks import VERIFICATION, read_json, write_json  # noqa: E402
from source_registry import (  # noqa: E402
    PROVIDER_BY_ID, SOURCE_TYPE_PATTERNS, resolve_provider,
)

RESOLVED = ("confirmed", "contradicted")
# Field order within a unit, so the evidence block reads as a block.
AFTER = "sourceType"


def providers_named(unit: dict) -> list[str]:
    """Every provider the citation names, primary first.

    Corroboration was recorded inconsistently — sometimes in `sourceType` ("corroborated for
    DE/PT"), sometimes in the `sourceUrl` sentence ("corroborated by LigaPokemon + photographed
    specimens"). Both are read, which is the whole reason this field is worth materialising.
    """
    url = unit.get("sourceUrl")
    is_url = bool(url) and str(url).startswith("http")
    # `sourceRef` is where the prose lands once this migration has run. Reading it as well as the
    # pre-migration prose `sourceUrl` is what makes a second run agree with the first, rather than
    # quietly dropping the corroboration recorded only in that sentence.
    prose = " ".join(str(v) for v in ((None if is_url else url), unit.get("sourceRef")) if v)
    text = f"{unit.get('sourceType') or ''} {prose}"

    cited = resolve_provider(url, None) if is_url else None

    named: list[str] = []
    for pattern, provider_id in SOURCE_TYPE_PATTERNS:
        if pattern.search(text) and provider_id != cited and provider_id not in named:
            named.append(provider_id)

    if cited:
        # A URL is the citation; whatever else the prose mentions corroborates it.
        return [cited, *named]
    # Otherwise the strongest class present is the primary one. Pattern order is an artefact of
    # how the registry lists providers, so ranking by authority keeps this from depending on it —
    # a photographed specimen (tier 1) outranks bare attestation (tier 2) whichever is matched
    # first. Registry order breaks ties so the result stays stable.
    return sorted(named, key=lambda p: (PROVIDER_BY_ID[p]["authorityTier"], named.index(p)))


def migrate(unit: dict) -> dict:
    url = unit.get("sourceUrl")
    is_url = bool(url) and str(url).startswith("http")
    names = providers_named(unit)

    fields = {
        "providerId": names[0] if names else None,
        # Already-migrated units keep the ref they have; only a pre-migration prose `sourceUrl`
        # supplies a new one. Deriving it from `sourceUrl` alone would erase it on a rerun.
        "sourceRef": unit.get("sourceRef") or (None if is_url else (url or None)),
        "corroborated": len(names) > 1,
    }

    rebuilt: dict = {}
    for key, value in unit.items():
        if key in fields:
            continue
        rebuilt[key] = None if key == "sourceUrl" and not is_url else value
        if key == AFTER:
            rebuilt.update(fields)
    for key, value in fields.items():  # units lacking sourceType keep the fields anyway
        rebuilt.setdefault(key, value)
    return rebuilt


def main() -> int:
    dry = "--dry-run" in sys.argv
    units = read_json(VERIFICATION / "units.json")

    changed = 0
    out = []
    for unit in units:
        if unit.get("status") not in RESOLVED:
            out.append(unit)
            continue
        new = migrate(unit)
        changed += new != unit
        out.append(new)

    resolved = [u for u in out if u.get("status") in RESOLVED]
    unresolvable = [u["unitId"] for u in resolved if not u.get("providerId")]
    single_source = [u for u in resolved
                     if u.get("providerId")
                     and PROVIDER_BY_ID[u["providerId"]]["category"] == "non-url-evidence"
                     and not u["corroborated"]]

    print(f"resolved units: {len(resolved)}, rewritten: {changed}")
    print(f"prose moved out of sourceUrl: {sum(1 for u in resolved if u.get('sourceRef'))}")
    print(f"corroborated by more than one provider: {sum(1 for u in resolved if u['corroborated'])}")
    print(f"resting on a single non-URL source: {len(single_source)}")
    for provider in sorted({u["providerId"] for u in single_source}):
        n = sum(1 for u in single_source if u["providerId"] == provider)
        print(f"    {n:3}  {provider} (authority tier "
              f"{PROVIDER_BY_ID[provider]['authorityTier']})")
    if unresolvable:
        print(f"UNRESOLVABLE providerId: {len(unresolvable)} -> {unresolvable[:5]}")
        return 1

    if dry:
        print("\n--dry-run: nothing written")
        return 0
    write_json(VERIFICATION / "units.json", out)
    print("\nwrote verification/units.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Derived analyses of the main dataset (#50 Wave 4, closing #28 and #30).

    python scripts/analyze.py
    python scripts/analyze.py --check    # fail if regeneration would change any output

Ported from `verification/archive/scripts/analyze.ps1`, the last step that required PowerShell. Produces the four
artifacts nothing else generates:

    analysis_language_drift.json   languages a printing has beyond, or short of, its market baseline
    analysis_shared_cards.json     the same card text across releases, grouped by Cardmarket cardKey
    analysis_artists.json          illustrator to printings
    analysis_variants.json         one set number carrying several Cardmarket products

**Reads `snorlax_cards.json` and nothing else.** The PowerShell preferred `_cards_stage3.json`,
then `_cards_stage2.json`, then the committed dataset. Those stage files are intermediate outputs
of a harvest that cannot be re-run (#28), so preferring them meant the canonical input depended on
what happened to be lying in the working directory. One documented canonical node is #30's
remaining acceptance criterion, and this is it.

Every record is byte-identical to what the PowerShell produced. Two ordering behaviours were
measured against the committed artifacts rather than assumed:

  * `Group-Object` orders groups by key, case-insensitively — not by first appearance, and not
    ordinally. This shows through wherever a later sort has ties.
  * `Select-Object -Unique` keeps first-appearance order rather than sorting.

**Ties are ordered differently, deliberately.** `Sort-Object -Descending` is unstable, so in
`analysis_artists.json` and `analysis_shared_cards.json` the order of equal-count groups was
whatever .NET's introsort happened to produce — not first-appearance, not alphabetical, not the
reverse of either. Reproducing it would mean emulating an unstable sort to preserve an accident.
Ties are broken by key instead, so the output is deterministic and explainable. The records and
their contents are unchanged; only the position of equal-count groups moves, once.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CARDS_PATH = ROOT / "snorlax_cards.json"

WEST = ("English", "French", "German", "Spanish", "Italian", "Portuguese")
ASIA = ("Japanese", "Korean", "T-Chinese")

OUTPUTS = ("analysis_language_drift.json", "analysis_shared_cards.json",
           "analysis_artists.json", "analysis_variants.json")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def dumps(payload: Any) -> str:
    """PowerShell's `ConvertTo-Json | Set-Content -Encoding utf8NoBOM`, byte for byte."""
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def market(languages: list[str]) -> str:
    """Keep the marketplace claim from verification/archive/passes/finalize.ps1."""
    if "English" in languages:
        return "Western"
    if "Japanese" in languages:
        return "Japanese"
    if "S-Chinese" in languages and len(languages) == 1:
        return "Simplified Chinese"
    if "Indonesian" in languages or "Thai" in languages:
        return "SEA promo"
    if "T-Chinese" in languages:
        return "Traditional Chinese"
    return "Other"


def unique(values: list[Any]) -> list[Any]:
    """`Select-Object -Unique`: first-appearance order, not sorted."""
    seen, out = set(), []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def ps_sorted(values: list[str]) -> list[str]:
    """`Sort-Object` on strings: case-insensitive, which ordinal sorting is not."""
    return sorted(values, key=lambda v: (str(v).casefold(), str(v)))


def group_by(cards: list[dict], key) -> dict[Any, list[dict]]:
    """`Group-Object`: groups ordered by key, case-insensitively.

    Measured against the committed artifacts rather than assumed — first-appearance order and
    ordinal sorting both disagree with them, case-insensitive sorting matches exactly. It matters
    beyond this function: the count sorts below are stable, so this ordering is what shows through
    wherever two groups have the same number of printings.
    """
    groups: dict[Any, list[dict]] = {}
    for card in cards:
        groups.setdefault(key(card), []).append(card)
    return {k: groups[k] for k in sorted(groups, key=lambda v: (str(v).casefold(), str(v)))}


def language_drift(cards: list[dict]) -> list[dict]:
    """Languages a printing carries beyond, or lacks against, its market baseline.

    Code cards are excluded (#31): drift measures a printing's language coverage, and a code card
    is a redemption slip whose language list follows the online client, not any print run.
    """
    rows = []
    for card in cards:
        if card.get("isCodeCard"):
            continue
        languages = card.get("languages") or []
        baseline = {"Western": WEST, "Japanese": ASIA}.get(card["market"])
        if baseline is None:
            continue
        missing = [lang for lang in baseline if lang not in languages]
        extra = [lang for lang in languages if lang not in baseline]
        if not missing and not extra:
            continue
        rows.append({
            "card": f"{card.get('name')} ({card.get('setCode')} {card.get('number')})",
            "setName": card.get("setName"),
            "market": card["market"],
            "languages": ", ".join(languages),
            # Field names say "Western" for both markets. Kept: they are the committed schema, and
            # renaming them would be a consumer-visible change unrelated to this port.
            "missingVsWesternBaseline": ", ".join(missing),
            "extraVsWesternBaseline": ", ".join(extra),
        })
    return rows


def shared_cards(cards: list[dict]) -> list[dict]:
    groups = group_by([c for c in cards if c.get("cardKey")], lambda c: c["cardKey"])
    multi = [(key, members) for key, members in groups.items() if len(members) > 1]
    # Count descending, then key — an explicit tie-break rather than an inherited accident.
    multi.sort(key=lambda item: (-len(item[1]), str(item[0]).casefold(), str(item[0])))
    rows = []
    for key, members in multi:
        artists = unique([m["artist"] for m in members if m.get("artist")])
        rows.append({
            "cardKey": key,
            "printings": len(members),
            "distinctSets": len(unique([m.get("setName") for m in members])),
            "markets": ", ".join(ps_sorted(unique([m["market"] for m in members]))),
            "knownArtists": ", ".join(artists),
            "artistCount": len(artists),
            "rarities": ", ".join(ps_sorted(unique([m.get("rarity") for m in members]))),
            "releases": [{
                "set": m.get("setName"),
                "code": f"{m.get('setCode')} {m.get('number')}",
                "rarity": m.get("rarity"),
                "variant": m.get("variantToken"),
                "artist": m.get("artist"),
                "market": m["market"],
                "image": m.get("imageFile"),
            } for m in members],
        })
    return rows


def artists(cards: list[dict]) -> list[dict]:
    groups = group_by([c for c in cards if c.get("artist")], lambda c: c["artist"])
    ordered = sorted(groups.items(),
                     key=lambda item: (-len(item[1]), str(item[0]).casefold(), str(item[0])))
    return [{
        "artist": name,
        "printings": len(members),
        "cards": [f"{m.get('name')} ({m.get('setCode')} {m.get('number')}) [{m.get('setName')}]"
                  for m in members],
    } for name, members in ordered]


def variants(cards: list[dict]) -> list[dict]:
    groups = group_by(cards, lambda c: f"{c.get('setCode')}|{c.get('number')}")
    return [{
        "setAndNumber": key,
        "count": len(members),
        "products": [{
            "variant": m.get("variantToken"),
            "rarity": m.get("rarity"),
            "name": m.get("name"),
            "url": m.get("productUrl"),
            "image": m.get("imageFile"),
        } for m in members],
    } for key, members in groups.items() if len(members) > 1]


def build() -> dict[str, str]:
    document = read_json(CARDS_PATH)
    cards = document["cards"] if isinstance(document, dict) and "cards" in document else document
    for card in cards:
        card["market"] = market(card.get("languages") or [])
    return {
        "analysis_language_drift.json": dumps(language_drift(cards)),
        "analysis_shared_cards.json": dumps(shared_cards(cards)),
        "analysis_artists.json": dumps(artists(cards)),
        "analysis_variants.json": dumps(variants(cards)),
    }


def main() -> int:
    rendered = build()

    if "--check" in sys.argv:
        stale = [name for name, body in rendered.items()
                 if not (ROOT / name).exists()
                 or (ROOT / name).read_text(encoding="utf-8") != body]
        if stale:
            print(f"stale: {', '.join(stale)}; run python scripts/analyze.py")
            return 1
        print(f"analyses are current ({len(rendered)} artifacts)")
        return 0

    for name, body in rendered.items():
        (ROOT / name).write_text(body, encoding="utf-8", newline="\n")

    counts = {name: len(json.loads(body)) for name, body in rendered.items()}
    print(f"drift rows      : {counts['analysis_language_drift.json']}")
    print(f"shared groups   : {counts['analysis_shared_cards.json']}")
    print(f"artists         : {counts['analysis_artists.json']}")
    print(f"variant clusters: {counts['analysis_variants.json']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

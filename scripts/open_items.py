#!/usr/bin/env python3
"""Generate the open-items page from the verification store (#37).

    python scripts/open_items.py            # rewrite the generated blocks
    python scripts/open_items.py --check    # fail if regeneration would change the page

`verification/open-items.html` listed the open and manual-review claims as two hand-written
JavaScript arrays. They were correct when written and they matched the store when this generator
replaced them — but nothing kept them that way. Resolving a unit meant remembering to edit a page
that no check ever read, and a page that is wrong about what is unresolved is worse than no page,
because it is the one a contributor reads to decide what to work on.

Only the data blocks are generated. The layout, CSS and rendering JavaScript stay hand-written,
because they are design rather than data, and regenerating them would mean moving 300 lines of
presentation into Python to no benefit.

The section a row belongs to is derived from its market and set, not stored: the page groups
Western gaps, Japanese decks and Japanese promos, and that grouping follows from the data.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "verification" / "open-items.html"

UNRESOLVED = ("pending", "needs-manual-review")
MONTHS = ("January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def section_for(unit: dict) -> str:
    """Which of the page's three sections a row belongs under.

    Western products are the Spanish/Portuguese gap; everything else is a Japanese-market product,
    split by whether it is a deck/collection or a promo, which is what the set code records.
    """
    if unit.get("market") == "Western":
        return "sec-west"
    return "sec-promo" if "-P" in str(unit.get("setCode", "")) else "sec-deck"


def display_code(set_code: str, number: Any) -> str:
    """Render the collector code without repeating the source-set token.

    Promo and championship products carry a compound setCode whose last token is also the prefix
    of the number — setCode "WCD23 LOR" with number "LOR 143". Joining them gives
    "WCD23 LOR LOR 143". The page has always shown these as "WCD23 · LOR 143", separating the
    product from the set the card was reprinted out of, so that reading is preserved here.
    """
    set_code, number = str(set_code).strip(), str(number).strip()
    head, _, tail = set_code.partition(" ")
    if tail and number.startswith(tail):
        return f"{head} · {number}"
    return f"{set_code} {number}".strip()


def js_string(value: str) -> str:
    """A JS double-quoted literal. The page is static, but the store is not, so escape properly."""
    return json.dumps(str(value), ensure_ascii=False)


def row_literal(unit_group: list[dict], card: dict | None, with_reason: bool) -> str:
    first = unit_group[0]
    gaps = sorted({u["language"] for u in unit_group})
    have = sorted({lang for lang in (card.get("languages") if card else []) or []
                   if lang not in gaps})

    code = display_code(first["setCode"], first["number"])
    fields = [f"n:{js_string(first['cardName'])}",
              f"c:{js_string(code)}"]
    if first.get("variant") and first["variant"] != "base":
        fields.append(f"v:{js_string(first['variant'])}")
    fields += [f"s:{js_string(first.get('setName') or '')}",
               f"r:{js_string(first.get('rarity') or '')}",
               f"g:[{','.join(js_string(g) for g in gaps)}]",
               f"h:[{','.join(js_string(h) for h in have)}]"]
    if with_reason:
        reasons = sorted({u.get("manualReason") or "" for u in unit_group if u.get("manualReason")})
        fields.append(f"why:{js_string('; '.join(reasons) or 'awaiting a decision')}")
    fields.append(f"u:{js_string(first.get('cmUrl') or '')}")
    if not with_reason:
        fields.append(f"sec:{js_string(section_for(first))}")
    return "    {" + ", ".join(fields) + "}"


def group(units: list[dict], status: str) -> list[list[dict]]:
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for unit in units:
        if unit["status"] != status:
            continue
        buckets[(unit["setCode"], str(unit["number"]), unit.get("variant") or "base")].append(unit)
    return [buckets[key] for key in sorted(buckets)]


def replace_block(text: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- generated:{re.escape(name)}[^>]*-->\n).*?(\n\s*<!-- /generated:{re.escape(name)} -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"open-items.html has no generated:{name} block")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text)


def main() -> int:
    units = read_json(ROOT / "verification" / "units.json")
    cards = read_json(ROOT / "snorlax_cards.json")["cards"]
    by_card = {(c["setCode"], str(c.get("number") or ""),
                c.get("variantToken") or "base"): c for c in cards}

    def card_for(unit_group: list[dict]) -> dict | None:
        first = unit_group[0]
        return by_card.get((first["setCode"], str(first["number"]),
                            first.get("variant") or "base"))

    open_groups = group(units, "pending")
    manual_groups = group(units, "needs-manual-review")

    open_body = ("  const OPEN = [\n"
                 + ",\n".join(row_literal(g, card_for(g), False) for g in open_groups)
                 + "\n  ];")
    manual_body = ("  const MANUAL = [\n"
                   + ",\n".join(row_literal(g, card_for(g), True) for g in manual_groups)
                   + "\n  ];")

    # Resolution progress, over card-variants that actually carry units.
    per_variant: dict[tuple, set[str]] = defaultdict(set)
    for unit in units:
        per_variant[(unit["setCode"], str(unit["number"]),
                     unit.get("variant") or "base")].add(unit["status"])
    total = len(per_variant)
    resolved = sum(1 for statuses in per_variant.values()
                   if not statuses & set(UNRESOLVED))

    # Derived from the evidence rather than the clock, for the same reason as
    # scripts/confirmed_releases.py: this page is regenerated and diffed by the release gate.
    stamp = max(u["checkedAt"][:10] for u in units if u.get("checkedAt"))
    year, month, day = (int(part) for part in stamp.split("-"))
    footer_body = (
        f"    Generated {day} {MONTHS[month - 1]} {year} from <code>verification/units.json</code>.\n"
        f"    Full evidence per claim in <code>confirmed_sources.json</code>,\n"
        f"    refuted claims in <code>CONTRADICTED.json</code>.\n"
        f"    {resolved} of {total} card variants are now fully resolved across all their languages."
    )

    original = PAGE.read_text(encoding="utf-8")
    updated = replace_block(original, "open", open_body)
    updated = replace_block(updated, "manual", manual_body)
    updated = replace_block(updated, "footer", footer_body)

    if "--check" in sys.argv:
        if updated != original:
            print("verification/open-items.html is stale; run python scripts/open_items.py")
            return 1
        print(f"open-items.html is current ({len(open_groups)} open, {len(manual_groups)} manual)")
        return 0

    if updated != original:
        PAGE.write_text(updated, encoding="utf-8", newline="")
        print(f"verification/open-items.html updated "
              f"({len(open_groups)} open, {len(manual_groups)} manual)")
    else:
        print("verification/open-items.html already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())

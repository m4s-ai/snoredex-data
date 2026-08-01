#!/usr/bin/env python3
"""Audit every represented expansion against Bulbapedia release fields.

The expansion pages commonly describe two differently named products in one infobox.  For
example, ``Gym Challenge (TCG)`` contains both ``enrelease`` for Gym Challenge and ``jarelease``
for Challenge from the Darkness.  Matching only the article title therefore misses the Japanese
set, even though the date is present on the same page.

This pass downloads every page in Bulbapedia's expansion category, indexes the English and
translated set names, adds the product/Asian pages already cited by this repository, and compares
their exact release fields with ``analysis_confirmed_releases.json``.  It is deliberately
read-only: applying a fetched date remains a reviewed source change.

    python verification/passes/audit_bulbapedia_release_dates.py
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
API = "https://bulbapedia.bulbagarden.net/w/api.php"
CATEGORY = "Category:Pokémon Trading Card Game expansions"
USER_AGENT = "Snoredex-Data Bulbapedia release-date audit/1.0"

# Cardmarket sometimes translates or shortens the published expansion/product name.  These
# mappings are not guesses: every page below is already cited by a confirmed unit in units.json,
# or is the English-counterpart expansion page whose own infobox names the set held here.
PAGE_OVERRIDES = {
    "151C": "Collection 151 (ATCG)",
    "20th": "Generations (TCG)",
    "BA20": "Battle Academy 2020 (TCG)",
    "BW7": "Plasma Storm (TCG)",
    "CLF": "Pokémon Trading Card Game Classic (TCG)",
    "CLV": "Pokémon Trading Card Game Classic (TCG)",
    "CS1DC": "Dynamax Clash V Starter Deck (ATCG)",
    "CS1aC": "Dynamax Clash (ATCG)",
    "CS2aC": "Vivid Portrayals (ATCG)",
    "CS3DC": "Primordial Arts V Starter Deck (ATCG)",
    "CS5DC": "Gallant Galaxy V Starter Deck (ATCG)",
    "CS5aC": "Gallant Galaxy (ATCG)",
    "CS6bC": "Marine Shadow (ATCG)",
    "CSAC": "Dynamax Clash Deck Building Gift Box (ATCG)",
    "CSM1cC": "Storming Emergence (ATCG)",
    "CSM2.1C": "Golden Energy (ATCG)",
    "CSM2DC": "Shining Synergy GX Starter Deck (ATCG)",
    "CSM2bC": "Shining Synergy (ATCG)",
    "CSM2cC": "Shining Synergy (ATCG)",
    "CSMPC": "Battle Party Set (ATCG)",
    "CSUC": "Pokémon Card Display Set Gift Box Vol. 3 (ATCG)",
    "CSVE1C": "Battle Party: Shared Dream (ATCG)",
    "CSVE2C": "Battle Party: Shining Dream (ATCG)",
    "CSV10C": "Together in Pursuit of Glory (ATCG)",
    "CSV5C": "Ardent Obsidian (ATCG)",
    "CSV7C": "Blade Awakening (ATCG)",
    "CSVH1C": "Pikachu & Clefairy & Turtwig & Gimmighoul Happy Set (ATCG)",
    "CSVH4C": "Decidueye & Melmetal & Koraidon & Miraidon Happy Set (ATCG)",
    "CSVL1C": "Journey Theme Pack (ATCG)",
    "CSZC": "Peripheral Collection Gift Box: Variety Treasure Box (ATCG)",
    "EC5": "Skyridge (TCG)",
    "HXY": "Kalos Starter Set (TCG)",
    "HSZ": "National Beginning Set (TCG)",
    "KSS": "Kalos Starter Set (TCG)",
    "LL": "Lost Link (TCG)",
    "PCG1": "EX FireRed & LeafGreen (TCG)",
    "PCG3": "EX Team Rocket Returns (TCG)",
    "PCG9": "EX Dragon Frontiers (TCG)",
    "PJU": "Jungle (TCG)",
    "Pt2": "Rising Rivals (TCG)",
    "PPS1 VIV": "Play! Pokémon Prize Pack Series One (TCG)",
    "PPS3 LOR": "Play! Pokémon Prize Pack Series Three (TCG)",
    "PPS7 JTG": "Play! Pokémon Prize Pack Series Seven (TCG)",
    "PPS8 JTG": "Play! Pokémon Prize Pack Series Eight (TCG)",
    "SSH": "Sword & Shield (TCG)",
    "s10a": "Dark Phantasma (TCG)",
    "s10b": "Pokémon GO (TCG)",
    "s1H": "Sword & Shield (TCG)",
    "s4": "Vivid Voltage (TCG)",
    "s5a": "Peerless Fighters (TCG)",
    "sH": "Sword & Shield Family Pokémon Card Game (TCG)",
    "sI100": "Start Deck 100 (TCG)",
    "sN": "Start Deck 100 CoroCoro Comic Version (TCG)",
    "smL": "Sun & Moon Family Pokémon Card Game (TCG)",
    "sv2a": "151 (TCG)",
    "sv4K": "Paradox Rift (TCG)",
    "sv4a": "Paldean Fates (TCG)",
    "sv5a": "Crimson Haze (TCG)",
    "sv9": "Battle Partners (TCG)",
    "svG": "Venusaur & Charizard & Blastoise Special Deck Set ex (TCG)",
    "svIba": "Pokémon Card Game Battle Academy (TCG)",
    "svLN": "Stellar Tera Type Starter Sets (TCG)",
    "svM": "Generations Start Decks (TCG)",
    "XY10": "Fates Collide (TCG)",
    "XY2": "Flashfire (TCG)",
    "m3": "Nihil Zero (TCG)",
    "m2a": "MEGA Dream ex (TCG)",
    "mC": "Start Deck 100 Battle Collection (TCG)",
    "mP1": "Start Deck 100 Battle Collection CoroCiao Version (TCG)",
    "xm2a": "MEGA Dream ex (TCG)",
    "xsv2a": "151 (TCG)",
}

# An override page can describe the counterpart market or use a generic product infobox.  Pick
# the documented field explicitly rather than relying on whether the article title happens to
# match Cardmarket's spelling.
FIELD_OVERRIDES = {
    "20th": "jarelease",
    "BW7": "jarelease",
    "EC5": "jarelease",
    "HXY": "jarelease",
    "KSS": "enrelease",
    "PCG1": "jarelease",
    "PCG3": "jarelease",
    "PCG9": "jarelease",
    "PJU": "jarelease",
    "Pt2": "jarelease",
    "XY10": "jarelease",
    "XY2": "jarelease",
    "SSH": "enrelease",
    "s10b": "jarelease",
    "s1H": "jarelease",
    "s4": "jarelease",
    "sv2a": "jarelease",
    "sv4K": "jarelease",
    "sv4a": "jarelease",
    "xsv2a": "jarelease",
    "m3": "jarelease",
}

# A split Japanese expansion can share one field with the year printed only once.  The selected
# date is still taken verbatim from that field, but cannot be recovered by a generic first-date
# parser.  Mysterious Mountains is the second of Skyridge's two Japanese component sets.
EXPECTED_DATE_OVERRIDES = {
    "CLV": "2023-11-17",
    "EC5": "2002-10-04",
}

MANUAL_REVIEW_CODES = {"CLF"}


@dataclass(frozen=True)
class Page:
    title: str
    fields: dict[str, str]


def request_json(params: dict[str, str]) -> dict[str, Any]:
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def category_titles() -> list[str]:
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": CATEGORY,
        "cmnamespace": "0",
        "cmlimit": "500",
        "format": "json",
    }
    titles: list[str] = []
    while True:
        payload = request_json(params)
        titles.extend(row["title"] for row in payload["query"]["categorymembers"])
        if "continue" not in payload:
            return titles
        params.update({key: str(value) for key, value in payload["continue"].items()})


def fetch_pages(titles: list[str]) -> dict[str, Page]:
    pages: dict[str, Page] = {}
    for offset in range(0, len(titles), 50):
        payload = request_json({
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "redirects": "1",
            "titles": "|".join(titles[offset:offset + 50]),
            "format": "json",
            "formatversion": "2",
        })
        for item in payload["query"]["pages"]:
            if item.get("missing"):
                continue
            wikitext = (
                item.get("revisions", [{}])[0]
                .get("slots", {}).get("main", {}).get("content", "")
            )
            fields = {
                match.group(1).strip().lower(): match.group(2).strip()
                for match in re.finditer(r"^\|\s*([^=\n]+?)\s*=(.*)$", wikitext, re.MULTILINE)
            }
            # DeckInfobox is sometimes written on one line (``release=... |``) rather than one
            # field per line.  Capture its two date-bearing keys without trying to parse every
            # pipe in every set-list template on the page.
            for match in re.finditer(
                r"(?:^|\|)\s*(release|date)\s*=\s*([^|\n}]+)", wikitext,
                re.MULTILINE | re.IGNORECASE,
            ):
                fields.setdefault(match.group(1).lower(), match.group(2).strip())
            page = Page(item["title"], fields)
            pages[item["title"]] = page
            for redirect in item.get("redirects", []):
                pages[redirect["from"]] = page
    return pages


def plain(value: str | None) -> str:
    value = re.sub(r"<!--.*?-->", "", value or "")
    value = re.sub(r"\{\{j\|([^{}]*)\}\}", r"\1", value)
    value = re.sub(r"\{\{tt\|([^|{}]*)\|[^{}]*\}\}", r"\1", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"'{2,}", "", value)
    return re.sub(r"\s+", " ", value).strip()


def normalized(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", plain(value)).casefold().replace("&", "and")
    return "".join(char for char in value if char.isalnum())


def first_iso_date(value: str | None) -> str | None:
    """Return the first full calendar date from a release field.

    Some products have several waves or regions in one field.  The chronological export's
    historical scalar date means the first release of that set; the raw field remains visible in
    the report so a reviewer can see when multiple releases exist.
    """
    value = plain(value)
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2}),\s+(\d{4})",
        value,
    )
    if not match:
        return None
    # Do not skip over an earlier month-only release and accidentally select the next language's
    # full date (for example Japanese "March 2022" followed by Korean "May 27, 2022").
    first_month = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)",
        value,
    )
    if first_month and first_month.start() < match.start():
        return None
    return datetime.strptime(match.group(0), "%B %d, %Y").date().isoformat()


def release_rows() -> dict[tuple[str, str], dict[str, Any]]:
    with (ROOT / "analysis_confirmed_releases.json").open(encoding="utf-8-sig") as handle:
        variants = json.load(handle)["variants"]
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for row in variants:
        rows.setdefault((row["setCode"], row["setName"]), row)
    return rows


def choose_field(code: str, name: str, page: Page, matched_as: str | None) -> str | None:
    if code in FIELD_OVERRIDES:
        return FIELD_OVERRIDES[code]
    fields = page.fields
    if matched_as == "transsetname" and fields.get("jarelease"):
        return "jarelease"
    if fields.get("enrelease"):
        return "enrelease"
    if fields.get("release"):
        return "release"
    if fields.get("date"):
        return "date"
    if fields.get("jarelease") and normalized(name) == normalized(fields.get("setname")):
        return "jarelease"
    return None


def main() -> int:
    try:
        category = category_titles()
        wanted = sorted(set(category) | set(PAGE_OVERRIDES.values()))
        pages = fetch_pages(wanted)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        print(f"Bulbapedia audit failed: {error}", file=sys.stderr)
        return 2

    index: dict[str, list[tuple[Page, str]]] = {}
    for title in category:
        page = pages.get(title)
        if not page:
            continue
        values = {
            "title": re.sub(r" \([^()]*(?:TCG)\)$", "", page.title),
            "setname": page.fields.get("setname"),
            "transsetname": page.fields.get("transsetname"),
            "altname": page.fields.get("altname"),
        }
        for kind, value in values.items():
            if value:
                index.setdefault(normalized(value), []).append((page, kind))

    rows = release_rows()
    same = 0
    differences: list[tuple[str, str, str, str, str, str]] = []
    unparsable: list[tuple[str, str, str, str]] = []
    uncovered: list[tuple[str, str]] = []

    for (code, name), row in sorted(rows.items()):
        matched_as: str | None = None
        if code in PAGE_OVERRIDES:
            page = pages.get(PAGE_OVERRIDES[code])
        else:
            candidates = index.get(normalized(name), [])
            languages = set(row.get("confirmedLanguages") or [])

            def candidate_score(candidate: tuple[Page, str]) -> tuple[int, int, int]:
                candidate_page, candidate_kind = candidate
                fields = candidate_page.fields
                if "English" in languages:
                    market = 2 if fields.get("enrelease") else 0
                elif "S-Chinese" in languages:
                    market = 2 if candidate_page.title.endswith("(ATCG)") else 0
                elif "Japanese" in languages:
                    market = 2 if fields.get("jarelease") else 0
                else:
                    market = 1
                global_page = 1 if candidate_page.title.endswith("(TCG)") else 0
                exact_name = 1 if candidate_kind in ("setname", "transsetname") else 0
                return market, global_page, exact_name

            if candidates:
                page, matched_as = max(candidates, key=candidate_score)
            else:
                page, matched_as = None, None
        if not page:
            uncovered.append((code, name))
            continue
        field = choose_field(code, name, page, matched_as)
        raw = page.fields.get(field or "")
        expected = (
            None if code in MANUAL_REVIEW_CODES
            else EXPECTED_DATE_OVERRIDES.get(code) or first_iso_date(raw)
        )
        if not expected:
            unparsable.append((code, name, page.title, f"{field or 'none'}={raw or ''}"))
            continue
        current = str(row["date"])
        if current == expected and not row.get("dateApproximate"):
            same += 1
        else:
            differences.append((code, name, current, expected, page.title, field or ""))

    print(f"Bulbapedia category pages: {len(category)}")
    print(f"Represented set code/name pairs: {len(rows)}")
    print(f"Exact matches: {same}")
    print(f"Differences: {len(differences)}")
    print(f"Matched pages without one parseable full date: {len(unparsable)}")
    print(f"No directly matched expansion/product page: {len(uncovered)}")

    if differences:
        print("\n== Differences ==")
        for code, name, current, expected, title, field in differences:
            print(f"{code:10} {name[:42]:42} {current:10} -> {expected}  {title} [{field}]")
    if unparsable:
        print("\n== Manual review: multi-date or partial-date field ==")
        for code, name, title, raw in unparsable:
            print(f"{code:10} {name[:42]:42} {title}: {raw}")
    if uncovered:
        print("\n== No directly matched Bulbapedia release page ==")
        for code, name in uncovered:
            print(f"{code:10} {name}")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())

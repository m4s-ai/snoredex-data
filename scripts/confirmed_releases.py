# -*- coding: utf-8 -*-
"""Build a chronological list of every card-variant with its CONFIRMED languages.

Date sources, in precedence order:
  1. Reviewed Bulbapedia expansion/product release fields in
     verification/bulbapedia_release_dates.json. One article commonly carries both English and
     Japanese dates, so the reviewed record identifies the matching field as well as the page.
  2. DATES table below - dates verified during the verification sessions
     (official DB entries, Bulbapedia infobox release fields, campaign dates)
  3. artists_pokemontcg.io releaseDate (English-market fallback)
  4. Approximate dates carry exact=False and render as "~YYYY".
Outputs: analysis_confirmed_releases.json + .csv (the HTML page is built by scripts/site.py)
"""
import json, io, html, os, re
from pathlib import Path
from urllib.parse import quote, urlencode

B = Path(__file__).resolve().parent.parent
cards = json.load(io.open(os.path.join(B, "snorlax_cards.json"), encoding="utf-8"))["cards"]
units = json.load(io.open(os.path.join(B, "verification", "units.json"), encoding="utf-8"))
artists = json.load(io.open(os.path.join(B, "artists_pokemontcgio.json"), encoding="utf-8"))
finish_document = json.load(
    io.open(os.path.join(B, "verification", "finish_units.json"), encoding="utf-8")
)
finish_units = finish_document["units"]
finish_counts = finish_document["meta"]["counts"]
finish_lookup = {
    (u["setCode"], str(u.get("number") or ""), u["language"]): u for u in finish_units
}
bulbapedia_document = json.load(
    io.open(os.path.join(B, "verification", "bulbapedia_release_dates.json"), encoding="utf-8")
)
bulbapedia_dates = {record["setCode"]: record for record in bulbapedia_document["records"]}


def bulbapedia_url(page):
    return "https://bulbapedia.bulbagarden.net/wiki/" + quote(page.replace(" ", "_"))

# --- 1. exact EN set dates from pokemontcg.io ---
en_dates = {}
for a in artists:
    if a.get("releaseDate") and a.get("setName"):
        en_dates[a["setName"]] = a["releaseDate"].replace("/", "-")

# map Cardmarket setName -> pokemontcg.io setName where they differ
EN_NAME_MAP = {
    "151": "151", "Jungle": "Jungle", "Base Set 2": "Base Set 2",
    "Legendary Collection": "Legendary Collection", "Skyridge": "Skyridge",
    "EX FireRed & LeafGreen": "FireRed & LeafGreen", "EX Team Rocket Returns": "Team Rocket Returns",
    "EX Dragon Frontiers": "Dragon Frontiers", "Diamond & Pearl": "Diamond & Pearl",
    "Rising Rivals": "Rising Rivals", "Call of Legends": "Call of Legends",
    "Boundaries Crossed": "Boundaries Crossed", "Plasma Storm": "Plasma Storm",
    "XY Kalos Starter Set": "Kalos Starter Set", "Flashfire": "Flashfire",
    "BREAKthrough": "BREAKthrough", "Generations": "Generations", "Fates Collide": "Fates Collide",
    "Team Up": "Team Up", "Unbroken Bonds": "Unbroken Bonds", "Hidden Fates": "Hidden Fates",
    "Sword & Shield": "Sword & Shield", "Rebel Clash": "Rebel Clash",
    "Vivid Voltage": "Vivid Voltage", "Chilling Reign": "Chilling Reign",
    "Fusion Strike": "Fusion Strike", "Pokémon GO": "Pokémon GO", "Lost Origin": "Lost Origin",
    "Crown Zenith": "Crown Zenith", "Paradox Rift": "Paradox Rift",
    "Paldean Fates": "Paldean Fates", "Twilight Masquerade": "Twilight Masquerade",
    "Surging Sparks": "Surging Sparks", "Prismatic Evolutions": "Prismatic Evolutions",
    "Journey Together": "Journey Together", "Perfect Order": "Perfect Order",
    "Gym Heroes": "Gym Heroes",
}

# --- 2. dates verified in-session or approximations (exact: full ISO; approx: year or year-month) ---
# key: setCode or (setCode, number)
DATES = {
    # Japanese classics
    "PJU": ("1997-03", False), "UNP": ("1997-12", True),  # Hungry Snorlax N64 campaign Dec 1997
    "EXS": ("1998-03-23", True),  # Expansion Sheet 1; later Quick Starter printing is dated per checklist item
    "G2": ("1999", False), "EC5": ("2002", False),
    "PCG1": ("2004", False), "PCG3": ("2004", False), "PCG9": ("2006", False),
    "DP1": ("2006-10", False),
    ("DP-P", "126"): ("2008-10", True),   # Domino's Pizza Oct-Dec 2008
    ("DP-P", "127"): ("2008-12", True),   # Domino's Pizza Dec 2008-Jan 2009
    "Pt2": ("2009-03", False), "LL": ("2010", False), "BW7": ("2012", False),
    ("BW-P", "207"): ("2013-02", True),   # CoroCoro Ichiban! March 2013 issue insert
    "HSZ": ("2012", False), "HXY": ("2013-12", False), "XY2": ("2014-03", False),
    ("XY-P", "149"): ("2015-07", True),   # Marumiya promotion July 2015
    ("XY-P", "261"): ("2016-09-01", True),# Daiichi Pan Sep 1 2016
    "XY10": ("2016-03", False), "20th": ("2016-09", False),
    # Wizards/EN promos with card-specific dates
    ("WP", "49"): ("2002-08", True),      # Pokemon League August 2002
    ("XYPR", "179"): ("2016-12-14", True),# Snorlax-GX Box
    ("SM", "05"): ("2016-12-14", True),   # same box
    ("SM-P", "1"): ("2016-12", False),
    "smL": ("2018", False),
    "sm9": ("2018-12-07", True),
    ("SM-P", "297"): ("2018-12", True),   # Tag Bolt booster box campaign
    ("SM", "169"): ("2019-02", False),
    "sm10": ("2019-03-01", True),
    "sA": ("2019-11-29", True),           # V Starter Sets infobox
    "s1H": ("2019-12-06", True),          # Shield
    "s2": ("2020-03-06", True),
    "BA20": ("2020-06", True),            # Battle Academy 2020
    ("SWSH", "032"): ("2020-05", False), ("SWSH", "068"): ("2020-11", False),
    "s4": ("2020-09-18", True),           # Amazing Volt Tackle
    ("S-P", "156"): ("2021-01-21", True), # CoroCoro Ichiban! March 2021 issue insert
    "s5a": ("2021-03-19", True),
    "sH": ("2021-07-09", True),           # Family Card Game infobox
    ("SWSH", "119"): ("2021-07", False),
    ("PKMTCH S-P", "S-P 145"): ("2021-10", False),
    "s8b": ("2021-12-03", True),
    "sI100": ("2021-12-17", True),        # Start Deck 100 infobox
    "sN": ("2022-03", True),              # CoroCoro Comic Version infobox
    "s10a": ("2022-05-13", True), "s10b": ("2022-06-17", True),
    "PPS1 VIV": ("2022-11-09", True),     # Prize Pack Series One
    ("SVP", "051"): ("2023", False),
    "CS1aC": ("2023-05-19", True),        # Dynamax Clash (ATCG article)
    "CS1DC": ("2023", False), "CSAC": ("2023", False),
    "sv2a": ("2023-06-16", True), "xsv2a": ("2023-06-16", True),
    "PPS3 LOR": ("2023-06", False),
    "sv4K": ("2023-10-27", True),
    "svG": ("2023-11-10", True),          # Special Deck Set ex infobox
    "CLV": ("2023-11-17", True), "CLF": ("2023-11", False),
    "WCD23 LOR": ("2023-11", False),
    "sv4a": ("2023-12-01", True),
    ("SVP", "122"): ("2024", False),
    "svIba": ("2024-03-08", True),        # Battle Academy JP infobox
    "sv5a": ("2024-03-22", True),
    ("SV-P/ID", "117"): ("2024-06-28", True),  # Monthly Promo Card
    "svLN": ("2024", False),
    "svM": ("2024-11-22", True),          # Generations Start Decks infobox
    ("SV-P/TH", "082"): ("2024", False),
    ("S-P/CS", "061"): ("2023", False),
    "151C": ("2025-01-17", True),         # Collection 151 (ATCG article)
    "sv9": ("2025-01-24", True),
    "xPRE": ("2025-02", False),           # Snorlax ex & Blissey ex Special Collection
    "CSVE1C": ("2025-02-28", True),       # Battle Party: Shared Dream
    ("SVP", "184"): ("2025-03", False),
    "xJTG": ("2025-04", False),
    ("SV-P/ID", "278"): ("2025-07-25", True),  # Gym Promo Card Pack 11
    "CSVE2C": ("2025-07-18", True),       # Battle Party: Shining Dream
    "PPS7 JTG": ("2025-08-14", True),     # Prize Pack Series Seven
    "m2a": ("2025-11-28", True), "xm2a": ("2025-11-28", True),
    "mC": ("2025-12", False),
    "mP1": ("2025-12-19", True),          # CoroCiao Version infobox
    "PPS8 JTG": ("2026-01-01", True),     # Prize Pack Series Eight
    ("SV-P/ID", "286"): ("2026-01", True),# Taro promotion Jan-Feb 2026
    "m3": ("2026-01", False),
    ("SV-P/CS", "277"): ("2025", False),
    # Simplified Chinese sets without pinned dates
    "CS2aC": ("2024", False), "CS3DC": ("2024", False), "CS5aC": ("2025", False),
    "CS5DC": ("2025", False), "CS6bC": ("2025", False), "CSV5C": ("2024", False),
    "CSV7C": ("2025", False), "CSV10C": ("2025-12", False),
    "CSM1cC": ("2025", False), "CSM2bC": ("2025", False), "CSM2cC": ("2025", False),
    "CSM2.1C": ("2025", False), "CSM2DC": ("2025", False), "CSMPC": ("2025", False),
    "CSZC": ("2025", False), "CSUC": ("2025", False), "CSVL1C": ("2025", False),
    "CSVH1C": ("2025", False), "CSVH4C": ("2025-26", False),
}

def get_date(c):
    num = c.get("number") or ""
    specific = (c["setCode"], num)
    if specific in DATES:
        d, exact = DATES[specific]
        return d, exact, None
    sourced = bulbapedia_dates.get(c["setCode"])
    if sourced:
        return sourced["date"], True, {
            "provider": "Bulbapedia",
            "url": bulbapedia_url(sourced["page"]),
            "page": sourced["page"],
            "field": sourced["field"],
        }
    if c["setCode"] in DATES:
        d, exact = DATES[c["setCode"]]
        return d, exact, None
    en = EN_NAME_MAP.get(c["setName"])
    if en and en in en_dates:
        return en_dates[en], True, None
    return ("9999", False, None)

# --- collect confirmed languages per card-variant ---
conf = {}
for u in units:
    if u["status"] != "confirmed":
        continue
    key = (u["setCode"], str(u.get("number") or ""), u.get("variant") or "base")
    conf.setdefault(key, []).append(u["language"])

LANG_ORDER = ["English","French","German","Italian","Spanish","Portuguese","Dutch","Polish",
              "Russian","Japanese","Korean","T-Chinese","S-Chinese","Indonesian","Thai"]

def order(ls):
    return [l for l in LANG_ORDER if l in ls]

rows = []
skipped = []
for c in cards:
    if c.get("isCodeCard"):
        continue
    vt = c.get("variantToken") or "base"
    key = (c["setCode"], str(c.get("number") or ""), vt)
    langs = order(conf.get(key, []))
    if not langs:
        skipped.append(key)
        continue
    d, exact, date_source = get_date(c)
    ed = c.get("editions") or {}
    base = {
        "date": d, "dateExact": exact, "dateSource": date_source,
        "name": c["name"], "setCode": c["setCode"], "number": c.get("number"),
        "setName": c["setName"], "variant": vt,
        "variantName": c.get("variantName"), "rarity": c.get("rarity"),
        "artist": c.get("artist"), "cardmarketUrl": c["productUrl"], "image": c["imageFile"],
        "finishByLanguage": (c.get("finishAvailability") or {}).get("byLanguage", []),
        "finishCompletenessByLanguage": {
            language: finish_lookup.get((c["setCode"], str(c.get("number") or ""), language), {}).get(
                "completenessStatus", "pending"
            )
            for language in langs
        },
    }
    if ed.get("hasFirstEdition"):
        fe = order([l for l in ed.get("firstEditionLanguages", []) if l in langs])
        # 1st Edition run (edord=0 so it sorts before Unlimited), then Unlimited run
        rows.append({**base, "edition": "1st Edition", "edord": 0, "confirmedLanguages": fe})
        rows.append({**base, "edition": "Unlimited",   "edord": 1, "confirmedLanguages": langs})
    elif ed.get("system") in ("WOTC-unlimited-only", "JP-unlimited-only"):
        rows.append({**base, "edition": "Unlimited", "edord": 1, "confirmedLanguages": langs})
    else:
        rows.append({**base, "edition": "—", "edord": 1, "confirmedLanguages": langs})

# --- stable identity and typed date fields -------------------------------------------------
# Identity must not be the sort position: filtering and sorting reorder rows, and correction
# links, checklist scope and deep links all have to survive that. (setCode, number, variant,
# edition) is unique across every row, so it is the natural key.
EDITION_SLUG = {"1st Edition": "1e", "Unlimited": "unl", "—": "none"}

def row_id(r):
    parts = [r["setCode"], str(r["number"] or "no-number"), r["variant"],
             EDITION_SLUG.get(r["edition"], r["edition"])]
    slug = "-".join(re.sub(r"[^A-Za-z0-9]+", "", p) or "x" for p in parts)
    return slug.lower()

def date_precision(d):
    """Classify a date value by validating it, not by measuring its length.

    Length alone is wrong: "2025-26" is a year *range* (CSVH4C), not a month, and would be
    mistaken for month precision and then normalized into the invalid month 26.
    """
    d = str(d)
    if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", d):
        return "day"
    if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", d):
        return "month"
    return "year"

def date_sort_key(d):
    """Normalize a mixed-precision date to a full ISO date for typed ordering.

    Missing components resolve to the start of the period, so a year-precision row sorts at
    the head of its year rather than lexicographically among that year's dated rows.
    """
    d = str(d)
    precision = date_precision(d)
    if precision == "day":
        return d
    if precision == "month":
        return f"{d}-01"
    return f"{d[:4]}-01-01"

for r in rows:
    r["rowId"] = row_id(r)
    # `dateExact` conflated two things: how precise the value is, and whether it is trusted at
    # that precision. Both are now explicit. `datePrecision` is derived from the value, so it
    # can never contradict it; `dateApproximate` carries the confidence judgement alone.
    r["datePrecision"] = date_precision(r["date"])
    r["dateApproximate"] = not r["dateExact"]
    r["dateSort"] = date_sort_key(r["date"])

_dupe_ids = {i for i in (r["rowId"] for r in rows) if list(r["rowId"] for r in rows).count(i) > 1}
if _dupe_ids:
    raise SystemExit(f"rowId collision, identity is not stable: {sorted(_dupe_ids)}")

rows.sort(key=lambda r: (r["dateSort"], r["setName"], str(r["number"]), r["variant"], r["edord"]))

json.dump({"generated": "2026-07-31",
           "note": "One row per card-variant-edition; confirmedLanguages holds only externally confirmed printings. finishByLanguage is product-mapped positive finish evidence and does not distinguish First Edition from Unlimited. Cards with a 1st-edition run appear twice (edition '1st Edition' then 'Unlimited'). rowId is the stable identity (setCode-number-variant-edition) and is independent of sort order; use it for correction links, checklist scope and deep links, never the generated row number. datePrecision (year|month|day) is derived from the date value, dateApproximate says the value is not trusted at that precision, and dateSource identifies the reviewed source field when available. dateSort is the normalized full date for typed ordering. dateExact is retained as the deprecated inverse of dateApproximate. For '1st Edition' rows confirmedLanguages lists only the languages that received a 1st-edition run.",
           "variants": rows},
          io.open(os.path.join(B, "analysis_confirmed_releases.json"), "w", encoding="utf-8", newline="\n"),
          ensure_ascii=False, indent=1)

# --- shared formatting ---
def fmt_date(r):
    d = r["date"]
    if not r["dateExact"]:
        return "~" + d[:4] if len(d) >= 4 else "~" + d
    p = d.split("-")
    M = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    if len(p) == 3: return f"{p[0]}-{p[1]}-{p[2]}"
    if len(p) == 2: return f"{p[0]}-{p[1]}"
    return d

# compact 2-letter language codes, in the fixed column order of the matrix
LANG_CODE = {"English":"EN","French":"FR","German":"DE","Italian":"IT","Spanish":"ES",
             "Portuguese":"PT","Dutch":"NL","Polish":"PL","Russian":"RU","Japanese":"JA",
             "Korean":"KO","T-Chinese":"ZH-T","S-Chinese":"ZH-S","Indonesian":"ID","Thai":"TH"}
LANG_COLS = [LANG_CODE[l] for l in LANG_ORDER]
# canonical count: each confirmed card x language once (Unlimited / no-edition rows carry all langs)
total_langs = sum(len(r["confirmedLanguages"]) for r in rows if r["edition"] != "1st Edition")
fe_langs = sum(len(r["confirmedLanguages"]) for r in rows if r["edition"] == "1st Edition")

# --- CSV (Excel-friendly matrix: one column per language, X = confirmed) ---
import csv
with io.open(os.path.join(B, "analysis_confirmed_releases.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter=";", lineterminator="\n")
    w.writerow(["#","Release","Date exact","Release source","Card","Set code","Number","Edition","Variant","Variant name",
                "Set / expansion","Rarity","Artist","Known finishes","Finish evidence","Langs"] + LANG_COLS + ["Cardmarket URL"])
    for i, r in enumerate(rows, 1):
        have = {LANG_CODE[l] for l in r["confirmedLanguages"]}
        finish_rows = [
            item for item in r["finishByLanguage"] if item["language"] in r["confirmedLanguages"]
        ]
        known_finishes = [
            finish
            for finish in ("non-holo", "holo", "reverse-holo", "mirror-holo")
            if any(finish in item.get("availableFinishes", []) for item in finish_rows)
        ]
        finish_evidence = sorted({item.get("status", "pending") for item in finish_rows})
        w.writerow([i, fmt_date(r), "yes" if r["dateExact"] else "approx",
                    (r.get("dateSource") or {}).get("url", ""),
                    r["name"], r["setCode"], r["number"] or "", r["edition"], r["variant"],
                    r.get("variantName") or "", r["setName"], r.get("rarity") or "",
                    r.get("artist") or "", ", ".join(known_finishes), ", ".join(finish_evidence),
                    len(r["confirmedLanguages"])]
                   + ["X" if c in have else "" for c in LANG_COLS]
                   + [r["cardmarketUrl"]])


# The HTML page used to be generated here, from ~430 lines of CSS, JavaScript and markup
# embedded in Python string literals. scripts/site.py is now the single page generator and the
# styles and behaviour live in site/app.css and site/app.js, so that block has been removed
# rather than left to rot beside a second implementation of the same page.
# verification/confirmed-releases.html is a redirect to the site root, written by site.py.
print(f"variants: {len(rows)}  confirmed language printings: {total_langs}")
print(f"skipped (no confirmed lang): {len(skipped)} -> {skipped}")
approx = sum(1 for r in rows if not r["dateExact"])
print(f"approx dates: {approx} / {len(rows)}")
print("wrote: analysis_confirmed_releases.csv, analysis_confirmed_releases.json")

# -*- coding: utf-8 -*-
"""Build a chronological list of every card-variant with its CONFIRMED languages.

Date sources, in precedence order:
  1. artists_pokemontcgio.json releaseDate (exact, English-market sets)
  2. DATES table below - dates verified during the verification sessions
     (official DB entries, Bulbapedia infobox release fields, campaign dates)
  3. Approximate dates carry exact=False and render as "~YYYY".
Outputs: verification/confirmed-releases.html + analysis_confirmed_releases.json
"""
import json, io, html, os
from pathlib import Path
from urllib.parse import urlencode

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
    "EXS": ("1998", False), "G2": ("1999", False), "EC5": ("2002", False),
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
    for key in ((c["setCode"], num), c["setCode"]):
        if key in DATES:
            d, exact = DATES[key]
            return d, exact
    en = EN_NAME_MAP.get(c["setName"])
    if en and en in en_dates:
        return en_dates[en], True
    return ("9999", False)

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
    d, exact = get_date(c)
    ed = c.get("editions") or {}
    base = {
        "date": d, "dateExact": exact,
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

rows.sort(key=lambda r: (r["date"], r["setName"], str(r["number"]), r["variant"], r["edord"]))

json.dump({"generated": "2026-07-23",
           "note": "One row per card-variant-edition; confirmedLanguages holds only externally confirmed printings. finishByLanguage is product-mapped positive finish evidence and does not distinguish First Edition from Unlimited. Cards with a 1st-edition run appear twice (edition '1st Edition' then 'Unlimited'). dateExact=false means the date is approximate (year-level). For '1st Edition' rows confirmedLanguages lists only the languages that received a 1st-edition run.",
           "variants": rows},
          io.open(os.path.join(B, "analysis_confirmed_releases.json"), "w", encoding="utf-8"),
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
with io.open(os.path.join(B, "analysis_confirmed_releases.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["#","Release","Date exact","Card","Set code","Number","Edition","Variant","Variant name",
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
                    r["name"], r["setCode"], r["number"] or "", r["edition"], r["variant"],
                    r.get("variantName") or "", r["setName"], r.get("rarity") or "",
                    r.get("artist") or "", ", ".join(known_finishes), ", ".join(finish_evidence),
                    len(r["confirmedLanguages"])]
                   + ["X" if c in have else "" for c in LANG_COLS]
                   + [r["cardmarketUrl"]])

# --- HTML table ---
def cell_langs(r):
    have = {LANG_CODE[l] for l in r["confirmedLanguages"]}
    return "".join(f'<td class="L{" on" if c in have else ""}">{c if c in have else ""}</td>' for c in LANG_COLS)


FINISH_DISPLAY = (
    ("non-holo", "NH", "Non-holo"),
    ("holo", "H", "Holo"),
    ("reverse-holo", "RH", "Reverse holo"),
    ("mirror-holo", "MH", "Mirror holo"),
)


def cell_finishes(r):
    relevant = [
        item for item in r["finishByLanguage"] if item["language"] in r["confirmedLanguages"]
    ]
    finish_values = []
    evidence_values = {item.get("status", "pending") for item in relevant}
    badges = []
    details = []

    for finish, short, label in FINISH_DISPLAY:
        occurrences = []
        patterns = set()
        for item in relevant:
            if finish not in item.get("availableFinishes", []):
                continue
            status = (item.get("finishStatus") or {}).get(finish, "pending")
            occurrences.append((item["language"], status))
            for printing in item.get("printings") or []:
                if printing.get("finish") == finish and printing.get("foilPattern"):
                    patterns.add(printing["foilPattern"])
        if not occurrences:
            continue

        finish_values.append(finish)
        statuses = {status for _, status in occurrences}
        if statuses == {"confirmed"}:
            strength = "verified"
        elif statuses <= {"confirmed", "owner-attested"}:
            strength = "attested"
        else:
            strength = "claimed"
        evidence_values.update(statuses)
        language_detail = "; ".join(
            f"{LANG_CODE.get(language, language)}: {status}" for language, status in occurrences
        )
        pattern_detail = f"; pattern: {', '.join(sorted(patterns))}" if patterns else ""
        badges.append(
            f'<span class="fb f-{finish} {strength}" title="{html.escape(label)} — '
            f'{html.escape(language_detail + pattern_detail)}" '
            f'aria-label="{html.escape(label)}: {html.escape(language_detail + pattern_detail)}">'
            f'{html.escape(label)}</span>'
        )
        if patterns:
            details.append(f'{short}: {", ".join(sorted(patterns))}')

    pending_languages = [
        LANG_CODE.get(item["language"], item["language"])
        for item in relevant
        if item.get("status") == "pending"
    ]
    if pending_languages:
        finish_values.append("pending")
        badges.append(
            f'<span class="fb pending" title="No positive product-mapped finish evidence: '
            f'{html.escape(", ".join(pending_languages))}">?</span>'
        )

    markings = set()
    sizes = set()
    for item in relevant:
        for printing in item.get("printings") or []:
            if printing.get("cardSize") and printing["cardSize"] != "unknown":
                sizes.add(printing["cardSize"])
            for marking in printing.get("markings") or []:
                text = marking.get("text") or marking.get("kind")
                if text:
                    markings.add(str(text))
    if markings:
        details.append("mark: " + ", ".join(sorted(markings)))
    if "jumbo" in sizes:
        details.append("size: " + " + ".join(sorted(sizes)))

    manifest_languages = [
        LANG_CODE.get(language, language)
        for language in r["confirmedLanguages"]
        if r["finishCompletenessByLanguage"].get(language) == "complete-manifest"
    ]
    if manifest_languages:
        details.append("complete manifest: " + ", ".join(manifest_languages))
        evidence_values.add("complete-manifest")

    evidence_values.discard("not-applicable")
    detail_html = f'<div class="fdetail">{html.escape(" · ".join(details))}</div>' if details else ""
    return (
        f'<td class="finish"><div class="fbadges">{"".join(badges)}</div>{detail_html}</td>',
        " ".join(finish_values),
        " ".join(sorted(evidence_values)),
        " ".join(details),
    )


lang_head = "".join(f'<th class="L" title="{html.escape(l)}">{LANG_CODE[l]}</th>' for l in LANG_ORDER)
n_cards = len({(r["setCode"], str(r["number"]), r["variant"]) for r in rows})
fe_count = len({(r["setCode"], str(r["number"]), r["variant"]) for r in rows if r["edition"] == "1st Edition"})


def correction_issue_url(r, row_number, finish_values):
    title = f'[Correction] {r["name"]} — {r["setCode"]} {r["number"] or "unnumbered"} ({r["variant"]})'
    release = r["date"] if r["dateExact"] else f'{r["date"]} (approximate)'
    body_lines = [
        "A correction was requested from `verification/confirmed-releases.html`.",
        "",
        "## Row to correct",
        f'- Generated row: {row_number}',
        f'- Card: {r["name"]}',
        f'- Set: {r["setName"]} ({r["setCode"]})',
        f'- Collector number: {r["number"] or "unnumbered"}',
        f'- Variant: {r["variant"]}',
        f'- Variant description: {r.get("variantName") or "none"}',
        f'- Edition: {r["edition"]}',
        f'- Release: {release}',
        f'- Finishes displayed: {finish_values.replace(" ", ", ") or "none confirmed"}',
        f'- Confirmed languages: {", ".join(r["confirmedLanguages"])}',
        f'- Cardmarket product: {r["cardmarketUrl"]}',
        "",
        "## Suggested correction",
        "Describe what is wrong and, if possible, include a source, link, or photograph:",
        "",
    ]
    query = urlencode({"title": title, "body": "\n".join(body_lines)})
    return f"https://github.com/m4s-ai/snoredex-data/issues/new?{query}"


trs = []
prev_year = None
for i, r in enumerate(rows, 1):
    y = r["date"][:4]
    if y != prev_year:
        trs.append(f'<tr class="yr"><td colspan="{9+len(LANG_COLS)+2}">{y}</td></tr>')
        prev_year = y
    variant = html.escape(r["variant"]) if r["variant"] != "base" else '<span class="dim">base</span>'
    if r.get("variantName"):
        variant += f'<div class="vn" title="{html.escape(r["variantName"])}">{html.escape(r["variantName"])}</div>'
    num = html.escape(str(r["number"])) if r["number"] else ""
    dcls = "d" if r["dateExact"] else "d approx"
    ed = r["edition"]
    edcls = "ed1" if ed == "1st Edition" else ("edu" if ed == "Unlimited" else "edn")
    edtxt = "1st Ed." if ed == "1st Edition" else ed
    finish_cell, finish_values, evidence_values, finish_details = cell_finishes(r)
    search_value = " ".join(
        str(value or "")
        for value in (
            r["name"], r["setCode"], r["number"], r["setName"], r["variant"],
            r.get("variantName"), r.get("rarity"), r.get("artist"), finish_values, finish_details,
        )
    ).casefold()
    image_src = "../" + str(r["image"]).replace("\\", "/")
    artist = html.escape(r.get("artist") or "")
    artist_html = f'<span class="artist">{artist}</span>' if artist else ""
    correction_url = correction_issue_url(r, i, finish_values)
    trs.append(f'''<tr class="card-row" data-search="{html.escape(search_value)}" data-finishes="{finish_values}" data-evidence="{evidence_values}">
<td class="n">{i}</td>
<td class="{dcls}">{fmt_date(r)}</td>
<td class="nm"><div class="card"><img src="{html.escape(image_src)}" alt="" loading="lazy"><div><a href="{html.escape(r["cardmarketUrl"])}" target="_blank" rel="noopener">{html.escape(r["name"])}</a>{artist_html}</div></div></td>
<td class="code">{html.escape(r["setCode"])}</td>
<td class="code num">{num}</td>
<td class="ed"><span class="{edcls}">{edtxt}</span></td>
<td class="var">{variant}</td>
<td class="set">{html.escape(r["setName"])}<span class="rar">{html.escape(r.get("rarity") or "")}</span></td>
{finish_cell}
{cell_langs(r)}
<td class="ct">{len(r["confirmedLanguages"])}</td>
<td class="corr"><a href="{html.escape(correction_url)}" target="_blank" rel="noopener" aria-label="Report a correction for row {i}: {html.escape(r['name'])}">Correction?</a></td>
</tr>''')

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Snorlax — confirmed printings, chronological</title>
<style>
  :root {{ --paper:#E9EDEF; --surface:#FFFFFF; --zebra:#F4F7F8; --head:#E4EAEC; --yr:#DCE6E3;
    --ink:#111A21; --ink-soft:#4C5D68; --ink-faint:#7A8B96; --rule:#CFD8DD; --rule-soft:#E5EBEE;
    --accent:#23606E; --have:#2F7D5B; --have-bg:#DCEEE4; --nh:#4D6572; --h:#A55B17;
    --rh:#6D4EA1; --mh:#24758B; --pending:#8B5C65;
    --serif:Georgia,"Iowan Old Style",serif; --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --paper:#0D1317; --surface:#141C22; --zebra:#18222A;
    --head:#1F2A31; --yr:#243530; --ink:#DFE7EB; --ink-soft:#9DAEB8; --ink-faint:#74868F;
    --rule:#2A363E; --rule-soft:#212C33; --accent:#74B4C2; --have:#7FC7A0; --have-bg:#183026; }} }}
  :root[data-theme="dark"] {{ --paper:#0D1317; --surface:#141C22; --zebra:#18222A; --head:#1F2A31;
    --yr:#243530; --ink:#DFE7EB; --ink-soft:#9DAEB8; --ink-faint:#74868F; --rule:#2A363E;
    --rule-soft:#212C33; --accent:#74B4C2; --have:#7FC7A0; --have-bg:#183026; }}
  :root[data-theme="light"] {{ --paper:#E9EDEF; --surface:#FFFFFF; --zebra:#F4F7F8; --head:#E4EAEC;
    --yr:#DCE6E3; --ink:#111A21; --ink-soft:#4C5D68; --ink-faint:#7A8B96; --rule:#CFD8DD;
    --rule-soft:#E5EBEE; --accent:#23606E; --have:#2F7D5B; --have-bg:#DCEEE4; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink); font-family:var(--sans); }}
  .wrap {{ max-width:112rem; margin:0 auto; padding:2rem 1rem 4rem; }}
  .eyebrow {{ font-family:var(--mono); font-size:.7rem; letter-spacing:.14em; text-transform:uppercase; color:var(--ink-faint); }}
  h1 {{ font-family:var(--serif); font-weight:600; font-size:clamp(1.5rem,3vw,2.1rem); margin:.35rem 0 .4rem; }}
  .lede {{ color:var(--ink-soft); max-width:70ch; margin:0 0 1rem; font-size:.92rem; line-height:1.5; }}
  .legend {{ display:flex; flex-wrap:wrap; gap:.4rem 1.1rem; font-size:.78rem; color:var(--ink-soft); margin:0 0 1.25rem; }}
  .legend b {{ font-family:var(--mono); font-weight:600; color:var(--ink); }}
  .summary {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(8.5rem,1fr)); gap:.45rem; margin:0 0 .75rem; }}
  .metric {{ padding:.55rem .65rem; background:var(--surface); border:1px solid var(--rule); border-radius:4px; }}
  .metric strong {{ display:block; font:700 1rem/1.1 var(--mono); color:var(--ink); }}
  .metric span {{ display:block; margin-top:.18rem; color:var(--ink-faint); font-size:.68rem; }}
  .controls {{ display:flex; flex-wrap:wrap; align-items:center; gap:.55rem; padding:.7rem;
    margin:0 0 .75rem; background:var(--surface); border:1px solid var(--rule); border-radius:4px; }}
  .controls input, .controls select, .controls button {{ font:inherit; color:var(--ink); background:var(--surface);
    border:1px solid var(--rule); border-radius:3px; padding:.42rem .55rem; }}
  .controls input {{ flex:1 1 18rem; min-width:12rem; }}
  .controls button {{ cursor:pointer; }}
  .shown {{ margin-left:auto; color:var(--ink-faint); font-family:var(--mono); font-size:.75rem; }}
  .scroll {{ overflow-x:auto; border:1px solid var(--rule); border-radius:4px; }}
  table {{ border-collapse:collapse; width:100%; font-size:.8rem; }}
  thead th {{ position:sticky; top:0; z-index:2; background:var(--head); color:var(--ink-soft);
    font-weight:600; text-align:left; padding:.5rem .55rem; border-bottom:2px solid var(--rule);
    white-space:nowrap; font-size:.72rem; letter-spacing:.02em; }}
  th.L {{ text-align:center; padding:.5rem .2rem; font-family:var(--mono); color:var(--ink-faint);
    border-left:1px solid var(--rule-soft); }}
  tbody td {{ padding:.4rem .55rem; border-bottom:1px solid var(--rule-soft); vertical-align:top; }}
  tbody tr:nth-child(even of :not(.yr)) td {{ background:var(--zebra); }}
  tbody tr:hover td {{ background:var(--have-bg); }}
  tbody tr[hidden] {{ display:none; }}
  tr.yr td {{ background:var(--yr); font-family:var(--mono); font-weight:700; font-size:.82rem;
    letter-spacing:.05em; color:var(--ink); position:sticky; top:1.95rem; z-index:1;
    padding:.3rem .55rem; border-bottom:1px solid var(--rule); }}
  tr.yr:hover td {{ background:var(--yr); }}
  td.n {{ font-family:var(--mono); color:var(--ink-faint); font-variant-numeric:tabular-nums; text-align:right; }}
  td.d {{ font-family:var(--mono); color:var(--ink-soft); white-space:nowrap; font-variant-numeric:tabular-nums; }}
  td.d.approx {{ color:var(--ink-faint); font-style:italic; }}
  td.nm {{ font-weight:600; min-width:11rem; }}
  td.nm a {{ color:inherit; text-decoration:none; }}
  td.nm a:hover {{ color:var(--accent); text-decoration:underline; }}
  .card {{ display:flex; align-items:flex-start; gap:.5rem; }}
  .card img {{ width:2.3rem; height:3.2rem; flex:0 0 auto; object-fit:cover; border-radius:2px;
    box-shadow:0 1px 4px #0003; background:var(--head); }}
  .artist {{ display:block; margin-top:.15rem; color:var(--ink-faint); font-size:.68rem; font-weight:400; }}
  td.code {{ font-family:var(--mono); color:var(--accent); white-space:nowrap; }}
  td.num {{ color:var(--ink-soft); }}
  td.ed {{ white-space:nowrap; }}
  td.ed span {{ font-family:var(--mono); font-size:.68rem; padding:.1rem .35rem; border-radius:2px; letter-spacing:.02em; }}
  .ed1 {{ background:#B9761722; color:#9C5417; border:1px solid #9C541766; font-weight:700; }}
  .edu {{ color:var(--ink-faint); }}
  .edn {{ color:var(--ink-faint); opacity:.5; }}
  @media (prefers-color-scheme: dark) {{ .ed1 {{ background:#DC9B5722; color:#DC9B57; border-color:#DC9B5766; }} }}
  :root[data-theme="dark"] .ed1 {{ background:#DC9B5722; color:#DC9B57; border-color:#DC9B5766; }}
  td.var {{ font-family:var(--mono); font-size:.76rem; color:var(--ink-soft); }}
  td.var .dim {{ color:var(--ink-faint); }}
  td.var .vn {{ font-family:var(--sans); font-style:italic; font-size:.72rem; color:var(--ink-faint);
    max-width:14rem; white-space:normal; margin-top:.15rem; }}
  td.set {{ min-width:11rem; }}
  td.set .rar {{ display:block; color:var(--ink-faint); font-size:.72rem; }}
  td.finish {{ min-width:17rem; max-width:24rem; }}
  .fbadges {{ display:flex; flex-wrap:wrap; gap:.4rem; }}
  .fb {{ display:inline-flex; align-items:center; justify-content:center; padding:.34rem .58rem;
    border:2px solid currentColor; border-radius:999px; font:800 .76rem/1 var(--sans);
    letter-spacing:.035em; text-transform:uppercase; white-space:nowrap; box-shadow:0 1px 2px #0002; }}
  .f-non-holo {{ color:var(--nh); background:color-mix(in srgb,var(--nh) 13%,var(--surface)); }}
  .f-holo {{ color:var(--h); background:color-mix(in srgb,var(--h) 13%,var(--surface)); }}
  .f-reverse-holo {{ color:var(--rh); background:color-mix(in srgb,var(--rh) 16%,var(--surface)); }}
  .f-mirror-holo {{ color:var(--mh); background:color-mix(in srgb,var(--mh) 13%,var(--surface)); }}
  .fb.claimed {{ border-style:dashed; }} .fb.attested {{ border-style:dotted; }}
  .fb.pending {{ color:var(--pending); border-style:dashed; }}
  .fdetail {{ margin-top:.22rem; color:var(--ink-faint); font-size:.65rem; line-height:1.28; }}
  td.L {{ text-align:center; padding:.4rem .2rem; border-left:1px solid var(--rule-soft);
    font-family:var(--mono); font-size:.68rem; color:transparent; }}
  td.L.on {{ color:var(--have); font-weight:700; background:var(--have-bg); }}
  td.ct {{ font-family:var(--mono); text-align:center; color:var(--ink-soft); font-variant-numeric:tabular-nums;
    border-left:1px solid var(--rule); }}
  th.corr, td.corr {{ position:sticky; right:0; border-left:2px solid var(--rule); text-align:center; }}
  th.corr {{ z-index:3; }}
  td.corr a {{ display:inline-block; padding:.3rem .48rem; border:1px solid var(--accent); border-radius:3px;
    color:var(--accent); background:var(--surface); font-size:.7rem; font-weight:700; text-decoration:none;
    white-space:nowrap; }}
  td.corr a:hover, td.corr a:focus-visible {{ color:var(--surface); background:var(--accent); outline:none; }}
  footer {{ margin-top:1.5rem; color:var(--ink-faint); font-size:.82rem; }}
  footer code {{ font-family:var(--mono); }}
  @media (max-width:700px) {{ .wrap {{ padding:1rem .5rem 3rem; }} .shown {{ width:100%; margin-left:0; }} }}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">Snorlax · visual collection · source verification</div>
  <h1>Confirmed printings — chronological collection</h1>
  <p class="lede">{n_cards} card-variants, 1997–2026, carrying {total_langs} externally confirmed
  card×language printings. A language cell is filled only where an outside source confirmed that
  printing — contradicted and still-open claims are blank. The {n_cards} variants render as
  {len(rows)} rows because the {fe_count} cards with a 1st-edition run appear twice —
  <span class="ed1" style="padding:.05rem .3rem;border-radius:2px">1st Ed.</span> (the {fe_langs}
  languages that got a first-edition run) then Unlimited (all confirmed languages). Finish badges
  are scoped to each Cardmarket product and confirmed language; hover a badge for evidence detail.</p>
  <div class="summary">
    <div class="metric"><strong>{finish_counts["withConfirmedFinish"]}</strong><span>finish units externally confirmed</span></div>
    <div class="metric"><strong>{finish_counts["withOnlyMarketplaceClaim"]}</strong><span>marketplace-only finish units</span></div>
    <div class="metric"><strong>{finish_counts["pendingFinish"]}</strong><span>applicable finish units pending</span></div>
    <div class="metric"><strong>{finish_counts["notApplicableFinish"]}</strong><span>false-language units not applicable</span></div>
    <div class="metric"><strong>{finish_counts["withCompleteManifest"]}</strong><span>complete official manifests</span></div>
    <div class="metric"><strong>{finish_counts["withAnyUnresolvedDetail"]}</strong><span>rows in finish review queue</span></div>
  </div>
  <div class="legend">
    <span><b>Edition</b> from Bulbapedia + Elite Fourum: WOTC 1st ed = Base Set→Neo Destiny (not Base Set 2); Japanese 1st ed = ADV/e-Card→XY (none since Sun &amp; Moon); Korean/Chinese never</span>
    <span><b>Date</b> ISO; <b><i>~YYYY</i></b> italic = approximate</span>
    <span><b>EN FR DE IT ES PT</b> European · <b>NL PL RU</b> · <b>JA KO ZH-T ZH-S ID TH</b> Asian. ES = European Spanish (LATAM-ES not listed by Cardmarket)</span>
    <span><b>Finish pills</b> show every available version in full. Solid border = externally confirmed; dashed = marketplace claim; <b>?</b> = pending for at least one confirmed language</span>
  </div>
  <div class="controls" aria-label="Collection filters">
    <input id="query" type="search" placeholder="Search card, set, number, artist, pattern…" autocomplete="off">
    <select id="finish-filter" aria-label="Filter by finish">
      <option value="">Any finish</option><option value="non-holo">Non-holo</option>
      <option value="holo">Holo</option><option value="reverse-holo">Reverse holo</option>
      <option value="mirror-holo">Mirror holo</option><option value="pending">Finish pending</option>
    </select>
    <select id="evidence-filter" aria-label="Filter by evidence">
      <option value="">Any evidence</option><option value="confirmed">Externally confirmed</option>
      <option value="marketplace-claimed">Marketplace-claimed</option><option value="pending">Pending</option>
      <option value="complete-manifest">Complete official manifest</option>
    </select>
    <button id="theme" type="button" title="Toggle light/dark theme">Theme</button>
    <span class="shown"><span id="shown-count">{len(rows)}</span> / {len(rows)} rows</span>
  </div>
  <div class="scroll">
    <table>
      <thead><tr>
        <th>#</th><th>Release</th><th>Card</th><th>Set</th><th>No.</th><th>Edition</th><th>Variant</th><th>Expansion</th><th>Finish / treatment</th>
        {lang_head}<th class="L" title="confirmed language count">Σ</th><th class="corr">Report</th>
      </tr></thead>
      <tbody>
      {"".join(trs)}
      </tbody>
    </table>
  </div>
  <footer>Generated 23 July 2026 by <code>scripts/confirmed_releases.py</code> from
  <code>verification/units.json</code> + <code>verification/finish_units.json</code> +
  <code>snorlax_cards.json</code>. Finish evidence is product- and language-mapped but currently
  edition-agnostic. Downloads:
  <code>analysis_confirmed_releases.csv</code> (Excel, semicolon-separated) and
  <code>analysis_confirmed_releases.json</code>.</footer>
</div>
<script>
  const query = document.getElementById('query');
  const finishFilter = document.getElementById('finish-filter');
  const evidenceFilter = document.getElementById('evidence-filter');
  const cardRows = [...document.querySelectorAll('tr.card-row')];
  const yearRows = [...document.querySelectorAll('tr.yr')];
  const shownCount = document.getElementById('shown-count');

  function applyFilters() {{
    const needle = query.value.trim().toLocaleLowerCase();
    const finish = finishFilter.value;
    const evidence = evidenceFilter.value;
    let shown = 0;
    for (const row of cardRows) {{
      const matches = (!needle || row.dataset.search.includes(needle)) &&
        (!finish || row.dataset.finishes.split(' ').includes(finish)) &&
        (!evidence || row.dataset.evidence.split(' ').includes(evidence));
      row.hidden = !matches;
      if (matches) shown++;
    }}
    for (const yearRow of yearRows) {{
      let sibling = yearRow.nextElementSibling;
      let hasVisibleCard = false;
      while (sibling && !sibling.classList.contains('yr')) {{
        if (sibling.classList.contains('card-row') && !sibling.hidden) {{ hasVisibleCard = true; break; }}
        sibling = sibling.nextElementSibling;
      }}
      yearRow.hidden = !hasVisibleCard;
    }}
    shownCount.textContent = shown;
  }}

  query.addEventListener('input', applyFilters);
  finishFilter.addEventListener('change', applyFilters);
  evidenceFilter.addEventListener('change', applyFilters);
  document.getElementById('theme').addEventListener('click', () => {{
    const root = document.documentElement;
    const dark = root.dataset.theme
      ? root.dataset.theme === 'dark'
      : window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.dataset.theme = dark ? 'light' : 'dark';
  }});
</script>
</body>
</html>'''

io.open(os.path.join(B, "verification", "confirmed-releases.html"), "w", encoding="utf-8").write(page)
print(f"variants: {len(rows)}  confirmed language printings: {total_langs}")
print(f"skipped (no confirmed lang): {len(skipped)} -> {skipped}")
approx = sum(1 for r in rows if not r["dateExact"])
print(f"approx dates: {approx} / {len(rows)}")
print("wrote: confirmed-releases.html, analysis_confirmed_releases.csv, analysis_confirmed_releases.json")

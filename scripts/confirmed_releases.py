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

B = r"C:\Users\marku\Claude\snorlax-cardmarket"
cards = json.load(io.open(os.path.join(B, "snorlax_cards.json"), encoding="utf-8"))["cards"]
units = json.load(io.open(os.path.join(B, "verification", "units.json"), encoding="utf-8"))
artists = json.load(io.open(os.path.join(B, "artists_pokemontcgio.json"), encoding="utf-8"))

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

rows = []
skipped = []
for c in cards:
    if c.get("isCodeCard"):
        continue
    vt = c.get("variantToken") or "base"
    key = (c["setCode"], str(c.get("number") or ""), vt)
    langs = conf.get(key, [])
    langs = [l for l in LANG_ORDER if l in langs]
    if not langs:
        skipped.append(key)
        continue
    d, exact = get_date(c)
    rows.append({
        "date": d, "dateExact": exact,
        "name": c["name"], "setCode": c["setCode"], "number": c.get("number"),
        "setName": c["setName"], "variant": vt,
        "variantName": c.get("variantName"), "rarity": c.get("rarity"),
        "artist": c.get("artist"), "confirmedLanguages": langs,
        "cardmarketUrl": c["productUrl"], "image": c["imageFile"],
    })

rows.sort(key=lambda r: (r["date"], r["setName"], str(r["number"]), r["variant"]))

json.dump({"generated": "2026-07-23",
           "note": "One row per card-variant; confirmedLanguages holds only externally confirmed printings. dateExact=false means the date is approximate (year-level).",
           "variants": rows},
          io.open(os.path.join(B, "analysis_confirmed_releases.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# --- HTML ---
def fmt_date(r):
    d = r["date"]
    if not r["dateExact"]:
        return "~" + d[:4] if len(d) >= 4 else "~" + d
    p = d.split("-")
    M = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    if len(p) == 3: return f"{int(p[2])} {M[int(p[1])]} {p[0]}"
    if len(p) == 2: return f"{M[int(p[1])]} {p[0]}"
    return d

years = {}
for r in rows:
    years.setdefault(r["date"][:4], []).append(r)

total_langs = sum(len(r["confirmedLanguages"]) for r in rows)
body = []
for y in sorted(years):
    body.append(f'<section><h2>{y}<span class="ycount">{len(years[y])} printings</span></h2><div class="rows">')
    for r in years[y]:
        chips = "".join(f'<span class="chip">{html.escape(l)}</span>' for l in r["confirmedLanguages"])
        vname = f'<div class="vname">{html.escape(r["variantName"])}</div>' if r.get("variantName") else ""
        variant = f'<span class="sep">·</span>{r["variant"]}' if r["variant"] != "base" else ""
        num = f' {html.escape(str(r["number"]))}' if r["number"] else ""
        artist = f'<span class="sep">·</span>Illus. {html.escape(r["artist"])}' if r.get("artist") else ""
        dcls = "date" if r["dateExact"] else "date approx"
        body.append(f'''<div class="row">
  <div class="{dcls}">{fmt_date(r)}</div>
  <div class="ident">
    <div class="cardname"><a href="{html.escape(r["cardmarketUrl"])}" target="_blank" rel="noopener">{html.escape(r["name"])}</a>
      <span class="sep">·</span><span class="code">{html.escape(r["setCode"])}{num}</span>{variant}</div>
    <div class="meta">{html.escape(r["setName"])}<span class="sep">·</span>{html.escape(r.get("rarity") or "")}{artist}</div>
    {vname}
  </div>
  <div class="langs">{chips}</div>
</div>''')
    body.append("</div></section>")

page = f'''<title>Snorlax — confirmed printings, chronological</title>
<style>
  :root {{ --paper:#E9EDEF; --surface:#FFFFFF; --surface-2:#F3F6F7; --ink:#111A21; --ink-soft:#4C5D68;
    --ink-faint:#7A8B96; --rule:#D0D9DE; --accent:#23606E; --have:#3F6E58; --have-bg:#E7EFEA;
    --serif:Georgia,"Iowan Old Style",serif; --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --paper:#0D1317; --surface:#161E24; --surface-2:#1B252C;
    --ink:#DFE7EB; --ink-soft:#9DAEB8; --ink-faint:#74868F; --rule:#29363E; --accent:#74B4C2;
    --have:#7FAF95; --have-bg:#1A2721; }} }}
  :root[data-theme="dark"] {{ --paper:#0D1317; --surface:#161E24; --surface-2:#1B252C; --ink:#DFE7EB;
    --ink-soft:#9DAEB8; --ink-faint:#74868F; --rule:#29363E; --accent:#74B4C2; --have:#7FAF95; --have-bg:#1A2721; }}
  :root[data-theme="light"] {{ --paper:#E9EDEF; --surface:#FFFFFF; --surface-2:#F3F6F7; --ink:#111A21;
    --ink-soft:#4C5D68; --ink-faint:#7A8B96; --rule:#D0D9DE; --accent:#23606E; --have:#3F6E58; --have-bg:#E7EFEA; }}
  body {{ margin:0; background:var(--paper); color:var(--ink); font-family:var(--sans); line-height:1.5; }}
  .wrap {{ max-width:64rem; margin:0 auto; padding:3rem 1.25rem 5rem; }}
  .eyebrow {{ font-family:var(--mono); font-size:.72rem; letter-spacing:.14em; text-transform:uppercase; color:var(--ink-faint); }}
  h1 {{ font-family:var(--serif); font-weight:600; font-size:clamp(1.7rem,3.2vw,2.4rem); margin:.4rem 0 .5rem; text-wrap:balance; }}
  .lede {{ color:var(--ink-soft); max-width:62ch; margin:0 0 2rem; }}
  h2 {{ font-family:var(--serif); font-size:1.3rem; font-weight:600; margin:2.2rem 0 .6rem; display:flex; align-items:baseline; gap:.7rem; }}
  .ycount {{ font-family:var(--mono); font-size:.72rem; color:var(--ink-faint); letter-spacing:.06em; }}
  .rows {{ display:flex; flex-direction:column; gap:1px; background:var(--rule); border:1px solid var(--rule); border-radius:3px; overflow:hidden; }}
  .row {{ background:var(--surface); padding:.75rem 1rem; display:grid; grid-template-columns:6.2rem minmax(0,1fr) auto; gap:.4rem 1.2rem; align-items:start; }}
  .row:hover {{ background:var(--surface-2); }}
  .date {{ font-family:var(--mono); font-size:.78rem; color:var(--ink-soft); font-variant-numeric:tabular-nums; padding-top:.15rem; }}
  .date.approx {{ color:var(--ink-faint); font-style:italic; }}
  .cardname {{ font-weight:600; font-size:.95rem; }}
  .cardname a {{ color:inherit; text-decoration:none; }}
  .cardname a:hover {{ color:var(--accent); }}
  .code {{ font-family:var(--mono); font-size:.8rem; color:var(--accent); }}
  .meta {{ font-size:.82rem; color:var(--ink-faint); }}
  .vname {{ font-size:.8rem; color:var(--ink-soft); font-style:italic; margin-top:.1rem; }}
  .sep {{ opacity:.5; padding:0 .3rem; }}
  .langs {{ display:flex; flex-wrap:wrap; gap:.28rem; justify-content:flex-end; max-width:20rem; }}
  .chip {{ font-family:var(--mono); font-size:.7rem; padding:.13rem .4rem; border-radius:2px;
    background:var(--have-bg); color:var(--have); border:1px solid var(--have); white-space:nowrap; }}
  footer {{ margin-top:3rem; padding-top:1.2rem; border-top:1px solid var(--rule); color:var(--ink-faint); font-size:.84rem; }}
  @media (max-width:44rem) {{ .row {{ grid-template-columns:1fr; }} .langs {{ justify-content:flex-start; max-width:none; }} }}
</style>
<div class="wrap">
  <header>
    <div class="eyebrow">Cardmarket · Snorlax · source verification</div>
    <h1>Every confirmed printing, in release order</h1>
    <p class="lede">{len(rows)} card-variants spanning 1997–2026, carrying {total_langs} externally
    confirmed language printings. Dates in italics with a tilde are approximate (set-level, not
    pinned to a source); all others come from pokemontcg.io release data or dates verified during
    the source checks. Chips list only <em>confirmed</em> languages — contradicted and unresolved
    claims are excluded.</p>
  </header>
  {"".join(body)}
  <footer>Generated 23 July 2026 from <code>verification/units.json</code> and
  <code>snorlax_cards.json</code> by <code>scripts/confirmed_releases.py</code>.
  Machine-readable copy: <code>analysis_confirmed_releases.json</code>.</footer>
</div>'''

io.open(os.path.join(B, "verification", "confirmed-releases.html"), "w", encoding="utf-8").write(page)
print(f"variants: {len(rows)}  confirmed language printings: {total_langs}")
print(f"skipped (no confirmed lang): {len(skipped)} -> {skipped}")
approx = sum(1 for r in rows if not r["dateExact"])
print(f"approx dates: {approx} / {len(rows)}")

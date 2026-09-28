# -*- coding: utf-8 -*-
"""Build a chronological list of every card-variant with its CONFIRMED languages.

Date sources, in precedence order:
  1. Exact card overrides in verification/confirmed_release_overrides.json.
  2. Reviewed Bulbapedia expansion/product release fields, with page and field provenance.
  3. Set-level fallback dates in the override file, then artists_pokemontcg.io English fallback.
  4. Approximate dates carry exact=False and render as "~YYYY".
Outputs: analysis_confirmed_releases.json + .csv (the HTML page is built by scripts/site.py)
"""
import csv, json, io, os, re, sys
from pathlib import Path
from urllib.parse import quote

B = Path(__file__).resolve().parent.parent
cards = json.load(io.open(os.path.join(B, "snorlax_cards.json"), encoding="utf-8"))["cards"]
units = json.load(io.open(os.path.join(B, "verification", "units.json"), encoding="utf-8"))
evidence_semantics = {
    row["unitId"]: row
    for row in json.load(io.open(
        os.path.join(B, "verification", "evidence_semantics.json"), encoding="utf-8"
    ))["units"]
}
if set(evidence_semantics) != {unit["unitId"] for unit in units}:
    raise SystemExit("evidence semantics must classify every language unit exactly once")
artists = json.load(io.open(os.path.join(B, "artists_pokemontcgio.json"), encoding="utf-8"))
finish_document = json.load(
    io.open(os.path.join(B, "verification", "finish_units.json"), encoding="utf-8")
)
finish_units = finish_document["units"]
finish_lookup = {
    (u["setCode"], str(u.get("number") or ""), u["language"]): u for u in finish_units
}
bulbapedia_document = json.load(
    io.open(os.path.join(B, "verification", "bulbapedia_release_dates.json"), encoding="utf-8")
)
bulbapedia_dates = {record["setCode"]: record for record in bulbapedia_document["records"]}


def bulbapedia_url(page):
    return "https://bulbapedia.bulbagarden.net/wiki/" + quote(page.replace(" ", "_"))

en_dates = {}
for a in artists:
    if a.get("releaseDate") and a.get("setName"):
        en_dates[a["setName"]] = a["releaseDate"].replace("/", "-")

OVERRIDES = json.load(io.open(
    os.path.join(B, "verification", "confirmed_release_overrides.json"), encoding="utf-8"
))
if OVERRIDES.get("meta", {}).get("schema") != "snoredex-confirmed-release-overrides":
    raise SystemExit("invalid verification/confirmed_release_overrides.json schema")
EN_NAME_MAP = OVERRIDES["setNameAliases"]
DATES = {
    row["setCode"]: (row["date"], row["exact"])
    for row in OVERRIDES["releaseDates"]["sets"]
}
DATES.update({
    (row["setCode"], row["number"]): (row["date"], row["exact"])
    for row in OVERRIDES["releaseDates"]["cards"]
})

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

source_registry = json.load(
    io.open(os.path.join(B, "verification", "source_registry.json"), encoding="utf-8")
)
TIER_BY_PROVIDER = {p["providerId"]: p["authorityTier"] for p in source_registry["providers"]}
NAME_BY_PROVIDER = {p["providerId"]: p["displayName"] for p in source_registry["providers"]}

conf = {}
strength = {}
for u in units:
    if evidence_semantics[u["unitId"]]["applicationStatus"] != "exists":
        continue
    key = (u["setCode"], str(u.get("number") or ""), u.get("variant") or "base")
    conf.setdefault(key, []).append(u["language"])
    provider = u.get("providerId")
    strength.setdefault(key, {})[u["language"]] = {
        "providerId": provider,
        "provider": NAME_BY_PROVIDER.get(provider),
        "authorityTier": TIER_BY_PROVIDER.get(provider),
        "corroborated": bool(u.get("corroborated")),
        "checkable": bool(u.get("sourceUrl")),
    }

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
    finish_by_language = (c.get("finishAvailability") or {}).get("byLanguage", [])
    product_printings = [
        printing
        for cell in finish_by_language
        for printing in cell.get("printings") or []
        if printing.get("productMapping") == "mapped"
    ]
    if product_printings and all(
        "releaseDate" in printing and printing.get("releaseDate") is None
        for printing in product_printings
    ):
        d, exact, date_source = "9999", False, None
    else:
        d, exact, date_source = get_date(c)
    ed = c.get("editions") or {}
    base = {
        "date": d, "dateExact": exact, "dateSource": date_source,
        "name": c["name"], "setCode": c["setCode"], "number": c.get("number"),
        "setName": c["setName"], "variant": vt,
        "variantName": c.get("variantName"), "rarity": c.get("rarity"),
        "artist": c.get("artist"), "cardmarketUrl": c["productUrl"], "image": c["imageFile"],
        "finishByLanguage": finish_by_language,
        "finishCompletenessByLanguage": {
            language: finish_lookup.get((c["setCode"], str(c.get("number") or ""), language), {}).get(
                "completenessStatus", "pending"
            )
            for language in langs
        },
        "languageEvidence": {language: strength.get(key, {}).get(language)
                             for language in langs},
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
    # can never contradict it. `dateApproximate` carries the confidence judgement alone.
    r["datePrecision"] = date_precision(r["date"])
    r["dateApproximate"] = not r["dateExact"]
    r["dateSort"] = date_sort_key(r["date"])

_dupe_ids = {i for i in (r["rowId"] for r in rows) if list(r["rowId"] for r in rows).count(i) > 1}
if _dupe_ids:
    raise SystemExit(f"rowId collision, identity is not stable: {sorted(_dupe_ids)}")

rows.sort(key=lambda r: (r["dateSort"], r["setName"], str(r["number"]), r["variant"], r["edord"]))

generated = max(
    max(u["checkedAt"][:10] for u in units if u.get("checkedAt")),
    finish_document["meta"]["generated"][:10],
)

output_document = {"schema": "snoredex-confirmed-releases",
           # 1.x while `dateExact` is still emitted. It is the deprecated inverse of
           # `dateApproximate` and is scheduled for removal at 2.0.0 (#37). Consumers that
           # read it should move to `datePrecision` + `dateApproximate` before then. The
           # file previously carried no schema at all, so there was no way to announce a
           # removal rather than spring it.
           "schemaVersion": "1.0.0",
           "generated": generated,
           "note": "One row per card-variant-edition. confirmedLanguages holds only externally confirmed printings. finishByLanguage is product-mapped positive finish evidence and does not distinguish First Edition from Unlimited. Cards with a 1st-edition run appear twice (edition '1st Edition' then 'Unlimited'). rowId is the stable identity (setCode-number-variant-edition) and is independent of sort order. Use it for correction links, checklist scope and deep links, never the generated row number. datePrecision (year|month|day) is derived from the date value, dateApproximate says the value is not trusted at that precision, and dateSource identifies the reviewed source field when available. dateSort is the normalized full date for typed ordering. dateExact is retained as the deprecated inverse of dateApproximate. For '1st Edition' rows confirmedLanguages lists only the languages that received a 1st-edition run.",
           "variants": rows}

def fmt_date(r):
    d = r["date"]
    if not r["dateExact"]:
        return "~" + d[:4] if len(d) >= 4 else "~" + d
    p = d.split("-")
    M = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    if len(p) == 3: return f"{p[0]}-{p[1]}-{p[2]}"
    if len(p) == 2: return f"{p[0]}-{p[1]}"
    return d

LANG_CODE = {"English":"EN","French":"FR","German":"DE","Italian":"IT","Spanish":"ES",
             "Portuguese":"PT","Dutch":"NL","Polish":"PL","Russian":"RU","Japanese":"JA",
             "Korean":"KO","T-Chinese":"ZH-T","S-Chinese":"ZH-S","Indonesian":"ID","Thai":"TH"}
LANG_COLS = [LANG_CODE[l] for l in LANG_ORDER]
total_langs = sum(len(r["confirmedLanguages"]) for r in rows if r["edition"] != "1st Edition")

csv_buffer = io.StringIO(newline="")
w = csv.writer(csv_buffer, delimiter=";", lineterminator="\n")
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

outputs = {
    B / "analysis_confirmed_releases.json": json.dumps(
        output_document, ensure_ascii=False, indent=1
    ),
    B / "analysis_confirmed_releases.csv": csv_buffer.getvalue(),
}
if "--check" in sys.argv:
    stale = [
        path.name for path, body in outputs.items()
        if not path.exists() or path.read_text(encoding="utf-8") != body
    ]
    if stale:
        print(f"stale: {', '.join(stale)}")
        sys.exit(1)
else:
    for path, body in outputs.items():
        path.write_text(body, encoding="utf-8", newline="\n")


print(f"variants: {len(rows)}  confirmed language printings: {total_langs}")
print(f"skipped (no confirmed lang): {len(skipped)} -> {skipped}")
approx = sum(1 for r in rows if not r["dateExact"])
print(f"approx dates: {approx} / {len(rows)}")
print(
    "checked: analysis_confirmed_releases.csv, analysis_confirmed_releases.json"
    if "--check" in sys.argv
    else "wrote: analysis_confirmed_releases.csv, analysis_confirmed_releases.json"
)

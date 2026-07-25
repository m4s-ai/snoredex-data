#!/usr/bin/env python3
"""Generate the public root index.html (#7), with the filterable table (#10) and checklist UI (#9).

Design constraints, all from the epic:

* **One implementation.** `verification/confirmed-releases.html` becomes a redirect to this page
  rather than a second page maintained in parallel.
* **Static and dependency-free.** No CDN, no analytics, no cookies, no runtime API. The page is
  usable if every external source site is down; only the outbound evidence links would fail.
* **Works from `file://` and from `/snoredex-data/`.** All asset paths are project-relative, and
  row data is embedded as JSON rather than fetched, because `fetch` of a sibling file is blocked
  under `file://`.
* **Statistics are generated**, never typed into prose, so the page cannot drift from the data
  the way the README did.

    python scripts/site.py
    python scripts/site.py --check    # fail if regeneration would change the output
"""

from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "index.html"
ALIAS_PATH = ROOT / "verification" / "confirmed-releases.html"

LANG_CODE = {
    "English": "EN", "French": "FR", "German": "DE", "Italian": "IT", "Spanish": "ES",
    "Portuguese": "PT", "Dutch": "NL", "Polish": "PL", "Russian": "RU", "Japanese": "JA",
    "Korean": "KO", "T-Chinese": "ZH-T", "S-Chinese": "ZH-S", "Indonesian": "ID", "Thai": "TH",
}
LANG_ORDER = list(LANG_CODE)

FINISH_LABEL = {
    "non-holo": "non-holo", "holo": "holo",
    "reverse-holo": "reverse", "mirror-holo": "mirror",
}

# `secondary` columns are dropped when printing: 34 columns cannot fit A4 or US Letter, and a
# print stylesheet that lets the table overflow silently truncates the right-hand side.
COLUMNS = [
    ("", None, "img"), ("Release", "release", ""), ("Card", "name", ""),
    ("Set", "setCode", ""), ("Expansion", "setName", "secondary"),
    ("No.", "number", ""), ("Variant", "variant", "secondary"),
    ("Rarity", "rarity", "secondary"), ("Artist", "artist", "secondary"),
    ("Edition", "edition", ""), ("Finish", "finish", ""),
    ("Pattern", "pattern", "secondary"), ("Stamp", "marking", "secondary"),
    ("Stamp role", "markingRole", "secondary"), ("Size", "size", "secondary"),
    ("Distribution", "distribution", "secondary"), ("Evidence", "evidence", "secondary"),
    ("Langs", "langCount", ""),
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def correction_url(row: dict[str, Any]) -> str:
    title = f'[Correction] {row["name"]} — {row["setCode"]} {row["number"] or "unnumbered"} ({row["variant"]})'
    body = "\n".join([
        "A correction was requested from the Snoredex collection page.",
        "",
        "## Row to correct",
        f'- Row ID: `{row["rowId"]}`  (stable; survives sorting and filtering)',
        f'- Card: {row["name"]}',
        f'- Set: {row["setName"]} ({row["setCode"]})',
        f'- Collector number: {row["number"] or "unnumbered"}',
        f'- Variant: {row["variant"]}',
        f'- Edition: {row["edition"]}',
        f'- Release: {row["date"]}{"" if not row.get("dateApproximate") else " (approximate)"}',
        f'- Confirmed languages: {", ".join(row["confirmedLanguages"])}',
        f'- Cardmarket product: {row["cardmarketUrl"]}',
        "",
        "## Suggested correction",
        "Describe what is wrong and, if possible, include a source, link, or photograph:",
        "",
    ])
    return "https://github.com/m4s-ai/snoredex-data/issues/new?" + urlencode({"title": title, "body": body})


def display_date(row: dict[str, Any]) -> str:
    if row.get("dateApproximate"):
        return "~" + str(row["date"])[:4]
    return str(row["date"])


def build_rows(releases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in releases:
        finishes: set[str] = set()
        patterns: set[str] = set()
        markings: set[str] = set()
        marking_roles: set[str] = set()
        sizes: set[str] = set()
        distributions: set[str] = set()
        evidence: set[str] = set()
        # Best status per finish across the row's languages, so the pill says how strong the
        # evidence is rather than merely that something exists.
        best: dict[str, str] = {}
        rank = {"pending": 0, "other-product": 1, "unmapped": 2,
                "marketplace-claimed": 3, "owner-attested": 4, "confirmed": 5}
        for cell in row.get("finishByLanguage") or []:
            for finish, status in (cell.get("finishStatus") or {}).items():
                if status in ("pending", "not-applicable"):
                    continue
                if rank.get(status, 0) > rank.get(best.get(finish, "pending"), 0):
                    best[finish] = status
            for printing in cell.get("printings") or []:
                if printing.get("finish") in FINISH_LABEL:
                    finishes.add(printing["finish"])
                if printing.get("foilPattern"):
                    patterns.add(printing["foilPattern"])
                for marking in printing.get("markings") or []:
                    if isinstance(marking, dict):
                        if marking.get("text"):
                            markings.add(marking["text"])
                        if marking.get("role"):
                            marking_roles.add(marking["role"])
                if printing.get("cardSize"):
                    sizes.add(printing["cardSize"])
                dist = printing.get("distribution")
                if dist and dist.get("kind"):
                    distributions.add(dist["kind"])
            evidence.add(cell.get("status") or "pending")
        finishes |= set(best)

        completeness = set((row.get("finishCompletenessByLanguage") or {}).values())
        evidence |= completeness

        lang_codes = [LANG_CODE[l] for l in row["confirmedLanguages"] if l in LANG_CODE]
        search = " ".join(str(v).lower() for v in [
            row["name"], row["setCode"], row["setName"], row["number"], row["variant"],
            row.get("variantName") or "", row.get("rarity") or "", row.get("artist") or "",
            row["edition"], " ".join(sorted(finishes)), " ".join(sorted(patterns)),
            " ".join(sorted(markings)), " ".join(lang_codes), display_date(row),
        ])
        rows.append({
            "rowId": row["rowId"],
            "name": row["name"],
            "setCode": row["setCode"],
            "setName": row["setName"],
            "number": row["number"] or "",
            "variant": row["variant"],
            "variantName": row.get("variantName"),
            "rarity": row.get("rarity"),
            "artist": row.get("artist"),
            "edition": row["edition"],
            "dateSort": row["dateSort"],
            "dateDisplay": display_date(row),
            "image": row.get("image"),
            "finishes": sorted(finishes),
            "finishDisplay": [
                {"label": FINISH_LABEL[f], "status": best.get(f, "pending")}
                for f in ("non-holo", "holo", "reverse-holo", "mirror-holo") if f in finishes
            ],
            "patterns": sorted(patterns),
            "markings": sorted(markings),
            "markingRoles": sorted(marking_roles),
            "sizes": sorted(sizes) or ["standard"],
            "distributions": sorted(distributions),
            "evidence": sorted(e for e in evidence if e),
            "confirmedLanguages": row["confirmedLanguages"],
            "langCodes": lang_codes,
            "correctionUrl": correction_url(row),
            "search": search,
        })
    return rows


def build_checklist(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact projection of the canonical export — only what the builder UI needs."""
    compact = []
    for item in items:
        marking = None
        for entry in item.get("markings") or []:
            if isinstance(entry, dict) and entry.get("text"):
                marking = entry["text"]
                break
        compact.append({
            "checklistId": item["checklistId"],
            "rowId": item.get("rowId"),
            "cardName": item["cardName"],
            "setCode": item["setCode"],
            "setName": item["setName"],
            "number": item["number"],
            "language": item["language"],
            "edition": item["edition"],
            "finish": item["finish"],
            "foilPattern": item.get("foilPattern"),
            "marking": marking,
            "cardSize": item.get("cardSize"),
            "releaseDate": item.get("releaseDate"),
            "image": item.get("image"),
        })
    return compact


def json_block(element_id: str, payload: Any) -> str:
    # `</script>` inside JSON would terminate the block early; escaping the slash is the
    # standard defence and stays valid JSON.
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="{element_id}">{text}</script>'


def multiselect(field: str, label: str) -> str:
    return (
        f'<div class="field"><label for="f-{field}">{html.escape(label)}</label>'
        f'<select id="f-{field}" multiple size="4" aria-label="Filter by {html.escape(label)}"></select></div>'
    )


def main() -> int:
    releases_doc = read_json(ROOT / "analysis_confirmed_releases.json")
    checklist_doc = read_json(ROOT / "analysis_checklist.json")
    finish_counts = read_json(ROOT / "analysis_finishes.json")["counts"]
    dataset = read_json(ROOT / "snorlax_cards.json")
    registry = read_json(ROOT / "verification" / "source_registry.json")
    units = read_json(ROOT / "verification" / "units.json")

    rows = build_rows(releases_doc["variants"])
    checklist = build_checklist(checklist_doc["items"])
    verification = dataset["meta"]["verification"]
    generated = date.today().isoformat()

    confirmed_pairs = sum(len(r["confirmedLanguages"]) for r in releases_doc["variants"]
                          if r["edition"] != "1st Edition")

    stats = [
        (f"{len(rows)}", "card-variant rows"),
        (f"{verification['confirmed']}", "confirmed language claims"),
        (f"{verification['contradicted']}", "refuted claims"),
        (f"{finish_counts['totalFinishUnits']}", "finish units"),
        (f"{finish_counts['withConfirmedFinish']}", "externally confirmed finishes"),
        (f"{checklist_doc['meta']['counts']['items']}", "checklist items"),
        (f"{registry['meta']['counts']['evidenceRecords']}", "distinct sources"),
        (f"{confirmed_pairs}", "confirmed card×language pairs"),
    ]

    languages_meta = [{"code": LANG_CODE[l], "name": l} for l in LANG_ORDER]

    head_cells = []
    for label, key, cls in COLUMNS:
        if key is None:
            head_cells.append(f'<th scope="col" class="{cls}"><span class="sr">Image</span></th>')
        else:
            head_cells.append(
                f'<th scope="col" class="{cls}" data-key="{key}" aria-sort="none">'
                f'<button type="button" class="sort" data-key="{key}">{html.escape(label)}</button></th>'
            )
    for lang in LANG_ORDER:
        head_cells.append(
            f'<th scope="col" class="langcell" data-key="lang-{LANG_CODE[lang]}" '
            f'title="{html.escape(lang)}">{LANG_CODE[lang]}</th>'
        )
    head_cells.append('<th scope="col" class="corr">Report</th>')

    providers_rows = "\n".join(
        f"<tr><td><strong>{html.escape(p['displayName'])}</strong></td>"
        f"<td>{html.escape(p['category'])}</td><td>{p['authorityTier']}</td>"
        f"<td>{'yes' if p['supportsAbsence'] else 'no'}</td>"
        f"<td>{p['uniqueSources']}</td><td>{p['claimsSupported']}</td>"
        f"<td>{html.escape(p['coverage'])}</td></tr>"
        for p in sorted(registry["providers"], key=lambda p: (p["authorityTier"], p["displayName"]))
    )

    source_items = "\n".join(
        f'<li><a href="{html.escape(e["canonicalUrl"])}" target="_blank" rel="noopener nofollow">'
        f'{html.escape(e["canonicalUrl"])}</a> <small>({html.escape(e["providerId"])}, '
        f'{e["usageCount"]}×)</small></li>'
        if e["canonicalUrl"] else
        f'<li><em>{html.escape(e["nonUrlEvidenceId"])}</em> <small>({html.escape(e["providerId"])}, '
        f'{e["usageCount"]}×)</small></li>'
        for e in registry["evidence"]
    )

    open_units = sum(1 for u in units if u["status"] in ("pending", "needs-manual-review"))

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Snoredex — documented Snorlax TCG printings</title>
<meta name="description" content="An auditable catalogue of physical Snorlax Pokemon TCG printings across variants, editions, languages, finishes, patterns, stamps, distribution and card size. Every claim carries an external source.">
<link rel="stylesheet" href="site/app.css">
<style>.sr{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}</style>
</head>
<body>
<header class="masthead">
  <div class="wrap">
    <h1>Snoredex — documented Snorlax TCG printings</h1>
    <p class="tagline">An auditable catalogue of <strong>physical</strong> Snorlax Pok&eacute;mon TCG
    printings: variants, editions, languages, finishes, foil patterns, stamps, distribution and card
    size. Every claim carries a source outside the marketplace it came from.</p>
    <nav class="sections" aria-label="Sections">
      <ul>
        <li><a href="#about">About</a></li>
        <li><a href="#collection">Collection</a></li>
        <li><a href="#checklist">Checklist</a></li>
        <li><a href="#methodology">Methodology</a></li>
        <li><a href="#sources">Sources</a></li>
        <li><a href="#license">License</a></li>
      </ul>
    </nav>
  </div>
</header>

<main class="wrap">

<section id="about">
  <h2>What this is</h2>
  <p>A complete catalogue of every Snorlax product listed on Cardmarket, plus a verification layer
  that answers a different question for each one: <em>does a source outside Cardmarket confirm this
  printing actually exists?</em></p>
  <p>The goal is to let a collector tell three things apart that catalogues routinely blur:
  <strong>documented printings</strong>, <strong>unresolved claims</strong>, and
  <strong>confirmed absences</strong> — and to keep every one of them auditable back to a source.</p>

  <div class="stats">
    {"".join(f'<div class="stat"><span class="n">{n}</span><span class="k">{html.escape(k)}</span></div>' for n, k in stats)}
  </div>

  <div class="callout">
    <strong>Scope limits — read these before relying on anything here.</strong>
    <ul>
      <li><strong>Physical cards only.</strong> Online and live code cards are excluded.</li>
      <li><strong>A marketplace filter is not a print manifest.</strong> Cardmarket's language
      filter over-claims: {verification['contradicted']} claims here are refuted by outside sources.
      The clearest is <code>KSS 26</code>, advertised in 17 languages for an expansion printed in 7.</li>
      <li><strong>Pending means unresolved, never absent.</strong> No finish is ever marked
      unavailable because a catalogue failed to list it.</li>
      <li><strong>Finish evidence is positive-only</strong> except under a complete official
      manifest — currently {finish_counts['withCompleteManifest']} units.</li>
      <li><strong>&ldquo;Spanish&rdquo; means European Spanish.</strong> Latin-American Spanish is a
      physically distinct edition from Journey Together (2025) onward and is out of scope here.</li>
      <li><strong>{open_units} claims remain open.</strong> They are shown as unresolved rather than
      quietly dropped.</li>
    </ul>
  </div>
</section>

<section id="collection">
  <h2>Collection</h2>
  <p>Every meaningful column is sortable and filterable. Filters combine with AND between fields and
  OR within a field. Your filter and sort state is stored in the page URL, so a filtered view can be
  shared or bookmarked.</p>

  <div class="controls">
    <div class="row">
      <div class="field" style="flex:1 1 260px">
        <label for="f-q">Search</label>
        <input id="f-q" type="search" placeholder="card, set, artist, stamp, language…" style="width:100%">
      </div>
      <div class="field"><label for="f-yearFrom">Year from</label><input id="f-yearFrom" type="number" min="1996" max="2030"></div>
      <div class="field"><label for="f-yearTo">Year to</label><input id="f-yearTo" type="number" min="1996" max="2030"></div>
      <div class="field"><label for="f-langMin">Min langs</label><input id="f-langMin" type="number" min="0" max="17"></div>
      <div class="field"><label for="f-langMax">Max langs</label><input id="f-langMax" type="number" min="0" max="17"></div>
      <button type="button" class="ghost" id="reset">Reset all</button>
    </div>
    <details class="morefilters">
      <summary>Column filters</summary>
      <div class="row" style="margin-top:8px">
        {multiselect("setCode", "Set")}
        {multiselect("edition", "Edition")}
        {multiselect("rarity", "Rarity")}
        {multiselect("artist", "Artist")}
        {multiselect("finish", "Finish")}
        {multiselect("pattern", "Foil pattern")}
        {multiselect("markingRole", "Stamp role")}
        {multiselect("size", "Card size")}
        {multiselect("distribution", "Distribution")}
        {multiselect("evidence", "Evidence")}
      </div>
    </details>
    <details class="morefilters">
      <summary>Language filters (any / present / absent)</summary>
      <div class="langgrid" id="langfilters"></div>
    </details>
    <div class="chips" id="chips"></div>
    <div class="count" id="count"></div>
  </div>

  <div class="tablewrap">
    <table id="collection">
      <caption class="sr">Chronological list of documented Snorlax card printings</caption>
      <thead><tr>{"".join(head_cells)}</tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </div>
</section>

<section id="checklist">
  <h2>Checklist</h2>
  <p>Generate a printable ownership checklist from the canonical export. It lists what has been
  <em>documented</em>, and marks items whose finish is unresolved so they cannot be mistaken for
  confirmed physical versions.</p>
  <div class="builder">
    <div class="row">
      <div class="field"><label for="cl-scope">Scope</label>
        <select id="cl-scope">
          <option value="all">All documented items</option>
          <option value="filtered">Current filtered rows only</option>
        </select></div>
      <div class="field"><label for="cl-langs">Languages</label>
        <select id="cl-langs" multiple size="4" aria-label="Checklist languages"></select></div>
      <div class="field"><label for="cl-editions">Editions</label>
        <select id="cl-editions" multiple size="4" aria-label="Checklist editions"></select></div>
      <div class="field"><label for="cl-finishes">Finishes</label>
        <select id="cl-finishes" multiple size="4" aria-label="Checklist finishes"></select></div>
      <div class="field"><label for="cl-group">Group by</label>
        <select id="cl-group">
          <option value="release">Release</option><option value="set">Set</option>
          <option value="card">Card</option><option value="language">Language</option>
        </select></div>
      <div class="field"><label for="cl-layout">Layout</label>
        <select id="cl-layout">
          <option value="compact">Compact (text only)</option>
          <option value="images">With images</option>
        </select></div>
      <div class="field"><label for="cl-unresolved">Unresolved</label>
        <span><input type="checkbox" id="cl-unresolved" checked> include placeholders</span></div>
    </div>
    <div class="preview" id="cl-preview"></div>
    <p style="margin-top:12px">
      <button type="button" class="primary" id="cl-download">Generate checklist</button>
      <small style="margin-left:8px">Downloads a standalone HTML file that works offline and prints
      to A4 or US Letter. Use your browser's <em>Save as PDF</em> from its print dialog.</small>
    </p>
  </div>
</section>

<section id="methodology">
  <h2>Methodology</h2>
  <p>Every card &times; language &times; variant claim is checked against a source
  <em>outside</em> the marketplace that made the claim. A seller's photograph of a physical card is
  evidence; the marketplace's own language filter is not.</p>
  <h3>Evidence is graded, and absence is treated carefully</h3>
  <ul>
    <li>Source strength is recorded explicitly: photographed specimen &gt; official database /
    marketplace listing / fan wiki &gt; owner attestation.</li>
    <li><strong>Absence is never a finding on its own.</strong> A source only counts against a claim
    once it is shown to cover that category. This rule exists because an absence argument once
    produced a false contradiction here, which had to be reverted.</li>
    <li>Only a complete official checklist may establish that an alternative does <em>not</em>
    exist, and only within its stated scope.</li>
  </ul>
  <h3>Finish, pattern, stamp, distribution and size are separate dimensions</h3>
  <p>A stamp does not make a card reverse holo. EX-era set logos that are part of the reverse
  treatment are recorded as <code>reverse-holo-treatment</code>; later prerelease, Staff, retailer
  and Pok&eacute;mon Center marks are <code>distribution-promo</code> and imply nothing about finish.</p>
  <h3>Two finish layers, deliberately</h3>
  <p>A card row shows what evidence attributes to <em>that Cardmarket product</em>. The finish store
  records what is known for the <em>set number and language</em>, whichever product carries it.
  Product attribution is necessarily the weaker view, so a finish can read <code>unmapped</code>
  (known, but not yet attributable to this listing) or <code>other-product</code> (attributed to a
  different listing) rather than being silently downgraded to <code>pending</code>.</p>
  <h3>Data downloads</h3>
  <ul>
    <li><a href="snorlax_cards.json">snorlax_cards.json</a> — main dataset</li>
    <li><a href="analysis_checklist.json">analysis_checklist.json</a> — canonical checklist items</li>
    <li><a href="analysis_confirmed_releases.json">analysis_confirmed_releases.json</a> — chronological rows</li>
    <li><a href="analysis_confirmed_releases.csv">analysis_confirmed_releases.csv</a> — spreadsheet export</li>
    <li><a href="verification/finish_units.json">verification/finish_units.json</a> — finish state store</li>
    <li><a href="verification/units.json">verification/units.json</a> — language state store</li>
    <li><a href="verification/source_registry.json">verification/source_registry.json</a> — source registry</li>
  </ul>
  <p><a href="https://github.com/m4s-ai/snoredex-data">Repository</a> ·
  <a href="https://github.com/m4s-ai/snoredex-data/issues">Issue tracker</a> ·
  <a href="README.md">Dataset documentation</a> ·
  <a href="verification/RESUME.md">Verification playbook</a></p>
</section>

<section id="sources">
  <h2>Sources</h2>
  <p>{registry['meta']['counts']['claimsAttributed']} claims are attributed across
  {registry['meta']['counts']['evidenceRecords']} distinct sources
  ({registry['meta']['counts']['uniqueUrls']} unique URLs and
  {registry['meta']['counts']['nonUrlEvidenceClasses']} non-URL evidence classes). This section is
  generated from the registry, so it cannot drift from the evidence stores.</p>
  <p><strong>The &ldquo;Absence?&rdquo; column is the one that matters.</strong> Only a complete
  official manifest may establish that a printing does not exist. For every other provider, a
  missing row is a coverage gap and never a finding.</p>
  <div class="tablewrap">
    <table class="sources">
      <thead><tr><th scope="col">Provider</th><th scope="col">Category</th><th scope="col">Tier</th>
      <th scope="col">Absence?</th><th scope="col">Sources</th><th scope="col">Claims</th>
      <th scope="col">Coverage</th></tr></thead>
      <tbody>{providers_rows}</tbody>
    </table>
  </div>
  <details class="sourcelist">
    <summary>Every individual source ({registry['meta']['counts']['evidenceRecords']})</summary>
    <ol>{source_items}</ol>
  </details>
  <p><a href="verification/source_registry.json">Download the machine-readable registry</a> ·
  <a href="verification/SOURCES.md">Readable provider summary</a></p>
</section>

<section id="license">
  <h2>License and notices</h2>
  <p>This repository is a mixed work; no single licence covers all of it. Original software is under
  <strong>PolyForm Noncommercial 1.0.0</strong>; the original data selection and arrangement,
  verification annotations, documentation and site copy are under
  <strong>CC BY-NC-SA 4.0</strong>. This is noncommercial source-available, not OSI open source.</p>
  <p><strong>Excluded:</strong> Pok&eacute;mon card artwork and images, names, logos and trademarks,
  illustrator credits and the underlying illustrations, quoted provider content, and third-party
  photographs. The licences above grant nothing in respect of any of it.</p>
  <p>Pok&eacute;mon and all related names are trademarks of Nintendo, Creatures Inc. and GAME FREAK
  inc. &copy; Pok&eacute;mon / Nintendo / Creatures / GAME FREAK. Card images are served from
  Cardmarket and are included for identification only.</p>
  <p><strong>This is an unofficial fan project.</strong> It is not affiliated with, endorsed by,
  sponsored by, or associated with Nintendo, Creatures Inc., GAME FREAK inc., The Pok&eacute;mon
  Company, Cardmarket, or any other rights holder or data provider named here.</p>
  <p><strong>No warranty.</strong> This records evidence and its strength. It is not a print manifest
  and is not guaranteed complete. Do not rely on it for purchase, grading, insurance or valuation
  decisions without independent verification.</p>
  <p><a href="LICENSE.md">Full licensing scope</a> ·
  <a href="THIRD_PARTY_NOTICES.md">Third-party notices</a></p>
</section>

<footer class="sitefoot">
  <p>Generated {generated} from the repository data. No analytics, no cookies, no trackers, no
  runtime API dependency — this page works offline once loaded.</p>
</footer>

</main>

{json_block("data-rows", rows)}
{json_block("data-checklist", checklist)}
{json_block("data-meta", {"languages": languages_meta, "generated": generated})}
<script src="site/app.js"></script>
</body>
</html>
"""

    alias = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moved — Snoredex collection</title>
<meta http-equiv="refresh" content="0; url=../index.html">
<link rel="canonical" href="../index.html">
</head>
<body>
<p>The collection page is now the site root, so there is only one page to maintain.</p>
<p><a href="../index.html">Continue to the collection &rarr;</a></p>
</body>
</html>
"""

    if "--check" in sys.argv:
        stale = []
        if not INDEX_PATH.exists() or INDEX_PATH.read_text(encoding="utf-8") != page:
            stale.append("index.html")
        if not ALIAS_PATH.exists() or ALIAS_PATH.read_text(encoding="utf-8") != alias:
            stale.append("verification/confirmed-releases.html")
        if stale:
            print(f"stale: {', '.join(stale)}; run python scripts/site.py")
            return 1
        print("site is current")
        return 0

    INDEX_PATH.write_text(page, encoding="utf-8", newline="\n")
    ALIAS_PATH.write_text(alias, encoding="utf-8", newline="\n")
    print(f"index.html: {len(rows)} rows, {len(checklist)} checklist items, "
          f"{registry['meta']['counts']['evidenceRecords']} sources "
          f"({INDEX_PATH.stat().st_size // 1024} KB)")
    print("verification/confirmed-releases.html: redirect to the site root")
    return 0


if __name__ == "__main__":
    sys.exit(main())

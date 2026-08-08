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
import re
import sys
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

FINISH_FAMILY = {
    "non-holo": "non-holo",
    "holo": "holo",
    "reverse-holo": "reverse-holo",
    "mirror-holo": "reverse-holo",
}
FINISH_LABEL = {
    "non-holo": "Non-Holo",
    "holo": "Holo",
    "reverse-holo": "Reverse Holo",
}

# `secondary` columns are dropped when printing: 34 columns cannot fit A4 or US Letter, and a
# print stylesheet that lets the table overflow silently truncates the right-hand side.
COLUMNS = [
    # Identity block first and contiguous: app.css pins these five to the left edge while the rest
    # scrolls, and a sticky column can only start from the left edge with every column before it
    # pinned too. "No." used to sit behind "Expansion", which would have forced the 10rem expansion
    # column into the frozen pane to reach it. Set and number belong together anyway (#124).
    ("", None, "img"), ("Release", "release", "col-release"), ("Card", "name", "col-card"),
    ("Set", "setCode", "col-set"), ("No.", "number", "col-number"),
    ("Expansion", "setName", "secondary col-expansion"),
    ("Variant", "variant", "secondary col-variant"),
    ("Rarity", "rarity", "secondary col-rarity"),
    ("Artist", "artist", "secondary col-artist"),
    ("Edition", "edition", ""), ("Finish", "finish", ""),
    ("Pattern", "pattern", "secondary col-pattern"),
    ("Stamp / marking", "marking", "secondary col-marking"),
    ("Marking role", "markingRole", "secondary col-marking-role"),
    ("Size", "size", "secondary col-size"),
    ("Distribution", "distribution", "secondary col-distribution"),
    ("Evidence", "evidence", "secondary col-evidence"),
    ("Langs", "langCount", "langcount"),
]


def read_json(path: Path) -> Any:
    # Tolerate historical PowerShell 5.1 BOM output; all active writers now emit UTF-8 no-BOM.
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def current_state_summary(row: dict[str, Any]) -> str:
    """Compact description of what the page shows for this row, for the form's prefill.

    Kept terse on purpose: it travels in a URL query string, and GitHub rejects issue-creation
    URLs beyond roughly 8 KB. The reporter needs enough to confirm we are looking at the same
    row, not a full dump — the row ID already carries exact identity.
    """
    finishes: dict[str, str] = {}
    patterns: set[str] = set()
    stamps: set[str] = set()
    sizes: set[str] = set()
    rank = {"pending": 0, "other-product": 1, "unmapped": 2,
            "marketplace-claimed": 3, "owner-attested": 4, "confirmed": 5}
    for cell in row.get("finishByLanguage") or []:
        for technical_finish, status in (cell.get("finishStatus") or {}).items():
            if status in ("pending", "not-applicable"):
                continue
            finish = FINISH_FAMILY.get(technical_finish, technical_finish)
            if rank.get(status, 0) > rank.get(finishes.get(finish, "pending"), 0):
                finishes[finish] = status
        for printing in cell.get("printings") or []:
            if printing.get("foilPattern"):
                patterns.add(printing["foilPattern"])
            for marking in printing.get("markings") or []:
                if isinstance(marking, dict) and marking.get("text"):
                    stamps.add(marking["text"])
            if printing.get("cardSize"):
                sizes.add(printing["cardSize"])

    release = str(row["date"]) + (" (approximate)" if row.get("dateApproximate") else "")
    release_source = row.get("dateSource") or {}
    finish_text = ", ".join(
        f"{FINISH_LABEL.get(f, f)} = {s}" for f, s in sorted(finishes.items())
    ) or "none recorded"
    return "\n".join([
        f"Edition: {row['edition']}",
        f"Release: {release}",
        f"Release source: {release_source.get('url') or 'not recorded'}",
        f"Confirmed languages: {', '.join(row['confirmedLanguages']) or 'none'}",
        f"Finishes: {finish_text}",
        f"Foil patterns: {', '.join(sorted(patterns)) or 'none recorded'}",
        f"Markings: {', '.join(sorted(stamps)) or 'none recorded'}",
        f"Card size: {', '.join(sorted(sizes)) or 'unknown'}",
        f"Cardmarket: {row['cardmarketUrl']}",
        "",
        "(pending = not yet established, never proven absent)",
    ])


def correction_url(row: dict[str, Any]) -> str:
    """Deep-link into the generated issue form with the row's identity already filled in.

    Only `input` and `textarea` fields are prefilled. GitHub keys issue-form prefill on each
    field's `id`, and support is most reliable for those two types — so the fields the site must
    fill are exactly the ones with dependable prefill, and the dropdowns and checkboxes the
    reporter sets by hand never need it. If prefill were to fail entirely the form still works;
    the reporter would just retype the row ID.
    """
    params = {
        "template": "printing-correction.yml",
        "title": f'[Correction] {row["name"]} — {row["setCode"]} '
                 f'{row["number"] or "unnumbered"} ({row["variant"]})',
        "row-id": row["rowId"],
        "card-name": row["name"],
        "set-code": f'{row["setCode"]} — {row["setName"]}',
        "card-number": row["number"] or "unnumbered",
        "current-state": current_state_summary(row),
    }
    return "https://github.com/m4s-ai/snoredex-data/issues/new?" + urlencode(params)


def display_date(row: dict[str, Any]) -> str:
    if row.get("dateApproximate"):
        return "~" + str(row["date"])[:4]
    return str(row["date"])


def release_sort(value: str) -> str:
    """Normalize a printing-level release date for chronological presentation."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return value + "-01"
    return value[:4] + "-01-01"


def expand_dated_printings(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Split one catalogue row when it contains separately dated physical printings.

    Cardmarket can catalogue multiple physical versions as one product. The canonical finish
    layer keeps those versions separate, but the collection table historically flattened them
    back into one row and displayed only the catalogue row's first release date. When every
    logical printing is dated and there is more than one date, expose one chronological variant
    per date. Undated or single-date products retain the established one-row projection.
    """
    cells = row.get("finishByLanguage") or []
    printings = [printing for cell in cells for printing in (cell.get("printings") or [])]
    dated = [printing for printing in printings if printing.get("releaseDate")]
    dates = sorted({str(printing["releaseDate"]) for printing in dated})
    if len(dates) <= 1 or len(dated) != len(printings):
        return [row]

    expanded = []
    for index, date in enumerate(dates, 1):
        projected_cells = []
        distributions = set()
        printing_ids = set()
        explicit_images = []
        for cell in cells:
            matching = [
                printing for printing in (cell.get("printings") or [])
                if str(printing.get("releaseDate") or "") == date
            ]
            if not matching:
                continue
            projected_cell = dict(cell)
            projected_cell["printings"] = matching
            matching_finishes = {printing.get("finish") for printing in matching}
            projected_cell["availableFinishes"] = sorted(
                finish for finish in matching_finishes if finish in FINISH_FAMILY
            )
            projected_cell["finishStatus"] = {
                finish: status if finish in matching_finishes else "pending"
                for finish, status in (cell.get("finishStatus") or {}).items()
            }
            projected_cells.append(projected_cell)
            for printing in matching:
                if printing.get("printingId"):
                    printing_ids.add(printing["printingId"])
                distribution = printing.get("distribution") or {}
                if distribution.get("name"):
                    distributions.add(distribution["name"])
                if "image" in printing:
                    explicit_images.append(printing["image"])

        projected = dict(row)
        projected["date"] = date
        projected["dateExact"] = True
        projected["datePrecision"] = (
            "day" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)
            else "month" if re.fullmatch(r"\d{4}-\d{2}", date)
            else "year"
        )
        projected["dateApproximate"] = False
        projected["dateSort"] = release_sort(date)
        projected["variant"] = f"V{index}" if row["variant"] == "base" else f'{row["variant"]}.{index}'
        projected["variantName"] = " / ".join(sorted(distributions)) or row.get("variantName")
        projected["finishByLanguage"] = projected_cells
        projected["confirmedLanguages"] = [cell["language"] for cell in projected_cells]
        projected["rowId"] = f'{row["rowId"]}-{date.replace("-", "")}'
        projected["sourceRowId"] = row["rowId"]
        projected["printingIds"] = sorted(printing_ids)
        projected["splitPhysicalPrinting"] = True
        if explicit_images:
            unique_images = {image for image in explicit_images}
            if len(unique_images) == 1:
                projected["image"] = unique_images.pop()
        expanded.append(projected)
    return expanded


def build_rows(releases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    expanded_releases = [
        row for source_row in releases for row in expand_dated_printings(source_row)
    ]
    for row in expanded_releases:
        finishes: set[str] = set()
        technical_finishes: set[str] = set()
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
            for technical_finish, status in (cell.get("finishStatus") or {}).items():
                if status in ("pending", "not-applicable"):
                    continue
                finish = FINISH_FAMILY.get(technical_finish, technical_finish)
                if rank.get(status, 0) > rank.get(best.get(finish, "pending"), 0):
                    best[finish] = status
            for printing in cell.get("printings") or []:
                technical_finish = printing.get("finish")
                if technical_finish in FINISH_FAMILY:
                    technical_finishes.add(technical_finish)
                    finishes.add(FINISH_FAMILY[technical_finish])
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
        # Evidence strength per confirmed language, keyed by the same code the cells use so
        # the renderer can look it up without a second mapping (#32).
        lang_evidence = {
            LANG_CODE[language]: {
                "tier": (info or {}).get("authorityTier"),
                "provider": (info or {}).get("provider"),
                "corroborated": bool((info or {}).get("corroborated")),
                "checkable": bool((info or {}).get("checkable")),
            }
            for language, info in (row.get("languageEvidence") or {}).items()
            if language in LANG_CODE
        }
        search = " ".join(str(v).lower() for v in [
            row["name"], row["setCode"], row["setName"], row["number"], row["variant"],
            row.get("variantName") or "", row.get("rarity") or "", row.get("artist") or "",
            row["edition"], " ".join(sorted(finishes)), " ".join(sorted(technical_finishes)),
            " ".join(sorted(patterns)),
            " ".join(sorted(markings)), " ".join(lang_codes), display_date(row),
        ])
        rows.append({
            "rowId": row["rowId"],
            "sourceRowId": row.get("sourceRowId", row["rowId"]),
            "printingIds": row.get("printingIds", []),
            "splitPhysicalPrinting": bool(row.get("splitPhysicalPrinting")),
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
            "dateStatus": "approximate" if row.get("dateApproximate") else "exact",
            "dateSource": row.get("dateSource"),
            "image": row.get("image"),
            "finishes": sorted(finishes),
            "technicalFinishes": sorted(technical_finishes),
            "finishDisplay": [
                {"label": FINISH_LABEL[f], "status": best.get(f, "pending")}
                for f in ("non-holo", "holo", "reverse-holo") if f in finishes
            ],
            "patterns": sorted(patterns),
            "markings": sorted(markings),
            "markingRoles": sorted(marking_roles),
            "sizes": sorted(sizes) or ["standard"],
            "distributions": sorted(distributions),
            "evidence": sorted(e for e in evidence if e),
            "confirmedLanguages": row["confirmedLanguages"],
            "langCodes": lang_codes,
            "langEvidence": lang_evidence,
            "correctionUrl": correction_url(row),
            "search": search,
        })
    return rows


def build_checklist(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact projection of the canonical export — only what the builder UI needs."""
    compact = []
    for item in items:
        markings = []
        for entry in item.get("markings") or []:
            if isinstance(entry, dict) and entry.get("text"):
                markings.append(entry["text"])
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
            "finishFamily": item["finishFamily"],
            "finishGroupId": item["finishGroupId"],
            "printingId": item.get("printingId"),
            "foilPattern": item.get("foilPattern"),
            "marking": markings[0] if markings else None,
            "markings": markings,
            "distribution": item.get("distribution"),
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
    # The licensor is an owner decision, so the page reads it rather than hardcoding a name that
    # could drift from the record the publication gate actually enforces.
    decisions = read_json(ROOT / "publication-decisions.json")
    licensor = str(decisions.get("licensor") or "undecided")
    licensor_contact = "https://www.instagram.com/" + licensor.lower() + "/"
    # Licence status is an owner decision too. Deriving the sentence from the record means the
    # published page cannot claim a grant the owner has not made, or deny one they have.
    grants_state = (
        f"<strong>in force</strong>, granted by {html.escape(licensor)}"
        if decisions.get("licenseGrantsApproved") is True
        else "<strong>not yet operative</strong> until the owner records approval"
    )

    rows = build_rows(releases_doc["variants"])
    checklist = build_checklist(checklist_doc["items"])
    verification = dataset["meta"]["verification"]
    # A refuted claim is not automatically a settled absence, and the page used to present all of
    # them as one block of "refuted claims" (#66). Only an owner adjudication or a complete
    # official manifest settles the question; the rest are one source's disagreement, and
    # DATABASE.md tells applications not to read those as "does not exist". Counted from the cards
    # rather than restated, so the two numbers cannot drift apart from the store.
    not_printed = sum(len(c.get("languagesNotPrinted") or []) for c in dataset["cards"])
    disputed = sum(len(c.get("languagesDisputed") or []) for c in dataset["cards"])
    # The page is a projection of committed inputs. A wall-clock date made an unchanged checkout
    # stale as soon as CI ran in a different timezone or on the next day. Reuse the checklist
    # snapshot date so identical inputs always produce identical bytes.
    generated = str(checklist_doc.get("meta", {}).get("generated") or "unknown")

    confirmed_pairs = sum(len(r["confirmedLanguages"]) for r in releases_doc["variants"]
                          if r["edition"] != "1st Edition")

    stats = [
        (f"{len(rows)}", "card-variant rows"),
        (f"{verification['confirmed']}", "confirmed language claims"),
        (f"{not_printed}", "adjudicated not printed"),
        (f"{disputed}", "disputed claims"),
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
            f'aria-sort="none" title="{html.escape(lang)}">'
            f'<button type="button" class="sort" data-key="lang-{LANG_CODE[lang]}" '
            f'aria-label="Sort by {html.escape(lang)} availability">{LANG_CODE[lang]}</button></th>'
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
    # A scope limit is a warning about what the reader must not assume. With the language queue
    # closed this rendered as "0 claims remain open. They are shown as unresolved rather than
    # quietly dropped." — a caveat about nothing, in the list a reader is told to read first (#68).
    # It returns by itself if a claim is ever reopened, which is when it means something again.
    open_claims_note = (
        f"<li><strong>{open_units} claims remain open.</strong> They are shown as unresolved "
        f"rather than quietly dropped.</li>" if open_units else ""
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Snoredex — documented Snorlax TCG printings</title>
<meta name="description" content="An auditable catalogue of physical Snorlax Pokemon TCG printings across variants, editions, languages, finishes, patterns, stamps, distribution and card size. Every claim carries an external source.">
<script>
(function () {{
  var root = document.documentElement;
  var saved = null;
  try {{ saved = localStorage.getItem("snoredex-theme"); }} catch (error) {{ /* storage may be unavailable */ }}
  var systemDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  var theme = saved === "light" || saved === "dark" ? saved : (systemDark ? "dark" : "light");
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
}})();
</script>
<link rel="stylesheet" href="site/app.css">
<style>.sr{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}</style>
</head>
<body>
<header class="masthead">
  <div class="wrap">
    <div class="masthead-row">
      <div class="masthead-copy">
        <h1>Snoredex — documented Snorlax TCG printings</h1>
        <p class="tagline">An auditable catalogue of <strong>physical</strong> Snorlax Pok&eacute;mon TCG
        printings: variants, editions, languages, finishes, foil patterns, stamps, distribution and card
        size. Every claim carries a source outside the marketplace it came from.</p>
      </div>
      <button type="button" class="theme-toggle" id="theme-toggle" aria-pressed="false"
        aria-label="Change color theme">
        <span class="theme-toggle-icon" aria-hidden="true">&#9680;</span>
        <span class="theme-toggle-text">Theme</span>
      </button>
    </div>
    <nav class="sections" id="section-nav" aria-label="Sections">
      <button type="button" class="nav-toggle" id="nav-toggle"
        aria-expanded="false" aria-controls="section-nav-list">
        <span class="nav-toggle-icon" aria-hidden="true">&#9776;</span>
        <span class="nav-toggle-text">Sections</span>
      </button>
      <ul id="section-nav-list">
        <li><a href="#about">About</a></li>
        <li><a href="#collection">Collection</a></li>
        <li><a href="#checklist">Checklist</a></li>
        <li><a href="#methodology">Methodology</a></li>
        <li><a href="#contribute">Help correct this</a></li>
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
  <strong>final application absence decisions</strong> — and to keep every one of them auditable
  back to its evidence and decision authority.</p>

  <div class="stats">
    {"".join(f'<div class="stat"><span class="n">{n}</span><span class="k">{html.escape(k)}</span></div>' for n, k in stats)}
  </div>

  <div class="callout">
    <strong>Scope limits — read these before relying on anything here.</strong>
    <ul>
      <li><strong>Physical cards only.</strong> Online and live code cards are excluded.</li>
      <li><strong>A marketplace filter is not a print manifest.</strong> Cardmarket's language
      filter over-claims: {verification['contradicted']} claims here are contradicted by outside
      sources. The clearest is <code>KSS 26</code>, advertised in 17 languages for an expansion
      printed in 7.</li>
      <li><strong>Contradicted is not the same as proven absent.</strong> Only
      {not_printed} of those claims are settled — by an explicit collection-owner adjudication or a
      complete official manifest. The other {disputed} are <strong>disputed</strong>: a source
      disagrees and nothing has settled it. They are excluded from the checklist so that nobody
      hunts a card the evidence points away from, but they are not a claim that the card does not
      exist, and a photograph of one would overturn the row.</li>
      <li><strong>Pending means unresolved, never absent.</strong> No finish is ever marked
      unavailable because a catalogue failed to list it.</li>
      <li><strong>Finish evidence is positive-only</strong> except under a complete official
      manifest — currently {finish_counts['withCompleteManifest']} units.</li>
      <li><strong>&ldquo;Spanish&rdquo; means European Spanish.</strong> Latin-American Spanish is a
      physically distinct edition from Journey Together (2025) onward and is out of scope here.</li>
      {open_claims_note}
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
        {multiselect("dateStatus", "Release status")}
        {multiselect("name", "Card")}
        {multiselect("setCode", "Set")}
        {multiselect("setName", "Expansion")}
        {multiselect("number", "Collector number")}
        {multiselect("edition", "Edition")}
        {multiselect("variant", "Variant")}
        {multiselect("variantName", "Variant description")}
        {multiselect("rarity", "Rarity")}
        {multiselect("artist", "Artist")}
        {multiselect("finish", "Finish")}
        {multiselect("pattern", "Foil pattern")}
        {multiselect("marking", "Stamp / marking")}
        {multiselect("markingRole", "Marking role")}
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
    <div class="count" id="count" role="status" aria-live="polite" aria-atomic="true"></div>
  </div>

  <p class="language-legend" id="collection-table-legend">
    <strong>Language availability:</strong>
    <span><span class="yes" aria-hidden="true">&#10003;</span> present</span>
    <span><span class="no" aria-hidden="true">&mdash;</span> absent</span>
    <span><span class="yes legend-unverifiable" aria-hidden="true">&#10003;</span> present, but on a
      single source with no public URL &mdash; hover any tick for its provider and evidence tier</span>
    <span>Ellipsized values can be selected to expand.</span>
  </p>

  <div class="tableframe" id="collection-table-frame">
    <div class="table-scroll-tools" id="collection-scroll-tools" hidden>
      <span class="scroll-hint" id="collection-scroll-hint" aria-live="polite">
        <span class="scroll-icon" aria-hidden="true">&#8596;</span><span class="scroll-hint-text">More columns are available</span>
      </span>
      <span class="scroll-actions">
        <button type="button" class="scroll-button" id="collection-scroll-left"
          aria-controls="collection-table-scroll" aria-label="Scroll collection table left">&#8592;</button>
        <button type="button" class="scroll-button" id="collection-scroll-right"
          aria-controls="collection-table-scroll" aria-label="Scroll collection table right">&#8594;</button>
      </span>
    </div>
    <span class="table-edge left" aria-hidden="true"></span>
    <div class="tablewrap" id="collection-table-scroll" tabindex="0"
      aria-describedby="collection-scroll-hint collection-table-legend">
      <table id="collection-table">
        <caption class="sr">Chronological list of documented Snorlax card printings</caption>
        <thead><tr>{"".join(head_cells)}</tr></thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
    <span class="table-edge right" aria-hidden="true"></span>
  </div>
</section>

<section id="checklist">
  <h2>Checklist</h2>
  <p>Generate a printable ownership checklist from the canonical export. It lists what has been
  <em>documented</em>, and marks items whose finish is unresolved so they cannot be mistaken for
  confirmed physical versions. Patterned reverse and mirror treatments are grouped under
  <strong>Reverse Holo</strong>, while each distinct physical treatment keeps its own checkbox.</p>
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
      <div class="field"><label for="cl-paper">Paper</label>
        <select id="cl-paper">
          <option value="A4">A4</option>
          <option value="Letter">US Letter</option>
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
    exist, and only within its stated scope. Other final absence decisions are explicit
    collection-owner adjudications after reviewing all cited claims; they are not attributed to a
    single provider.</li>
  </ul>
  <h3>Finish family, treatment, marking, distribution and size are separate dimensions</h3>
  <p>The collector-facing <strong>Reverse Holo</strong> family includes technical
  <code>reverse-holo</code> and <code>mirror-holo</code> printings. Exact treatments such as
  Pok&eacute; Ball, Master Ball, energy patterns and EX-era set-logo reverse treatments stay visible
  and independently traceable. Printed identity features such as rarity symbols and contest
  credits use <code>print-identity</code>. A later prerelease, Staff, retailer or Pok&eacute;mon
  Center <code>distribution-promo</code> stamp does not imply a reverse-holo finish.</p>
  <h3>Two evidence scopes, deliberately</h3>
  <p>A card row shows what evidence attributes to <em>that Cardmarket product</em>. The finish store
  records what is known for the <em>set number and language</em>, whichever product carries it.
  Product attribution is necessarily the weaker view, so a finish can read <code>unmapped</code>
  (known, but not yet attributable to this listing) or <code>other-product</code> (attributed to a
  different listing) rather than being silently downgraded to <code>pending</code>. When one
  Cardmarket product contains multiple physical printings with distinct release dates, the
  chronological table gives each printing its own dated variant row.</p>
  <h3>Release dates follow the matching market</h3>
  <p>Bulbapedia commonly records English and Japanese counterpart releases on the same article.
  The set's published or translated name selects <code>enrelease</code> or <code>jarelease</code>;
  the article title alone does not. Reviewed Bulbapedia dates take precedence over the generic API
  fallback, and linked dates in the table open the exact source page used.</p>
  <h3>Data downloads</h3>
  <ul>
    <li><a href="snoredex.sqlite">snoredex.sqlite</a> — normalized current-state application database</li>
    <li><a href="snoredex-tracker-template.sqlite">snoredex-tracker-template.sqlite</a> — blank have/have-not tracker</li>
    <li><a href="DATABASE.md">DATABASE.md</a> — schema, status rules and example queries</li>
    <li><a href="snorlax_cards.json">snorlax_cards.json</a> — main dataset</li>
    <li><a href="analysis_checklist.json">analysis_checklist.json</a> — canonical checklist items</li>
    <li><a href="analysis_confirmed_releases.json">analysis_confirmed_releases.json</a> — chronological rows</li>
    <li><a href="analysis_confirmed_releases.csv">analysis_confirmed_releases.csv</a> — spreadsheet export</li>
    <li><a href="verification/finish_units.json">verification/finish_units.json</a> — finish state store</li>
    <li><a href="verification/units.json">verification/units.json</a> — language state store</li>
    <li><a href="verification/owner_adjudications.json">verification/owner_adjudications.json</a> — collection-owner application decisions</li>
    <li><a href="verification/bulbapedia_release_dates.json">verification/bulbapedia_release_dates.json</a> — reviewed release-date sources</li>
    <li><a href="verification/history/BULBAPEDIA-RELEASE-DATE-AUDIT.md">verification/history/BULBAPEDIA-RELEASE-DATE-AUDIT.md</a> — full date-difference audit</li>
    <li><a href="verification/source_registry.json">verification/source_registry.json</a> — source registry</li>
  </ul>
  <p><a href="https://github.com/m4s-ai/snoredex-data">Repository</a> ·
  <a href="https://github.com/m4s-ai/snoredex-data/issues">Issue tracker</a> ·
  <a href="README.md">Dataset documentation</a> ·
  <a href="verification/RESUME.md">Verification playbook</a></p>
</section>

<section id="contribute">
  <h2>Help correct this</h2>
  <p>Every row above ends in a <strong>Correction?</strong> link. It opens a pre-filled form with
  the row identity and everything this page currently records, so reporting an error is usually a
  matter of ticking a box and saying what is wrong. You need no account beyond GitHub, and no
  knowledge of how any of this is built.</p>

  <div class="callout">
    <strong>One rule decides whether a report can be acted on: positive evidence only.</strong>
    <ul>
      <li><strong>A card in your hands counts.</strong> Say so — it is recorded as an owner
      attestation and graded accordingly.</li>
      <li><strong>A photo, a listing, or an official checklist entry counts.</strong></li>
      <li><strong>&ldquo;It is not listed anywhere&rdquo; does not.</strong> A source failing to
      mention a printing is a gap in that source, not proof of absence. An absence argument once
      produced a false correction here that had to be reverted.</li>
      <li><strong>Nothing to correct on a <span class="pill pending">pending</span> finish</strong>
      unless you have seen the printing. Pending means not yet established — never unavailable.</li>
    </ul>
  </div>

  <p>Corrections are graded against the source ladder in
  <a href="verification/FINISH_SOURCES.md">FINISH_SOURCES.md</a>, applied with their source recorded
  in the evidence registry, or closed with the reason stated in the issue. Specimen reports have
  already overturned three databases at once here.</p>
  <p><a href="https://github.com/m4s-ai/snoredex-data/issues/new?template=printing-correction.yml">Report
  a printing correction</a> · <a href="CONTRIBUTING.md">How contributions are handled</a> ·
  <a href="verification/open-items.html">Open questions we would most like answered</a></p>
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
  <p>This repository is a mixed work; no single licence covers all of it. The intended terms are
  <strong>PolyForm Noncommercial 1.0.0</strong> for original software and
  <strong>CC BY-NC-SA 4.0</strong> for the original data selection and arrangement, verification
  annotations, documentation and site copy. The verbatim texts are included, and the grants are
  {grants_state}. This is noncommercial source-available, not OSI open source.</p>
  <p><strong>Licensor: {html.escape(licensor)}.</strong> That is the name CC BY-NC-SA attribution
  must credit, and the party from whom a commercial exception is sought. Both licences here are
  noncommercial; neither permits commercial use without a separate
  grant. Licensing and commercial-use enquiries:
  <a href="{html.escape(licensor_contact)}" rel="noopener">@{html.escape(licensor)} on Instagram</a>.
  That is a licensing contact, not a corrections channel — corrections belong in the
  <a href="#contribute">issue tracker</a>, where they are recorded with their evidence.</p>
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

    with INDEX_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(page)
    with ALIAS_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(alias)
    print(f"index.html: {len(rows)} rows, {len(checklist)} checklist items, "
          f"{registry['meta']['counts']['evidenceRecords']} sources "
          f"({INDEX_PATH.stat().st_size // 1024} KB)")
    print("verification/confirmed-releases.html: redirect to the site root")
    return 0


if __name__ == "__main__":
    sys.exit(main())

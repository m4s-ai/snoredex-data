#!/usr/bin/env python3
"""Browser tests for the public site (#7, #9, #10).

These drive the real page in Chromium rather than asserting on the generator's output, because
the behaviours the epic asks for — filtering, sorting, URL round-trip, year headings, print and review
proposal downloads — only exist at runtime.

Run against a temporary local HTTP server, as for a served checkout:

    python verification/test_site.py

Requires the pinned `playwright` dependency and its Chromium build. Missing prerequisites are a
test failure: a release gate that silently skips its browser contract is not a release gate.
"""

from __future__ import annotations

import json
import importlib.util
import os
import re
import shutil
import sys
import tempfile
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
CANONICAL_ITEMS = [item for item in json.loads((ROOT / "collector_catalogue.json").read_text(encoding="utf-8"))["items"]
                   if item["active"] and item["itemKind"] == "verified-printing"]
EXPECTED_ROWS = len(CANONICAL_ITEMS)

# Every surface #43 enumerates, measured in both themes: (label, selector, property, mode,
# threshold). "text" measures the property against the element's own composited backdrop;
# "boundary" measures it against the backdrop behind the element, which is what a border or a
# focus ring actually sits on.
#
# Thresholds follow WCAG 2.2 AA: 4.5:1 for text (nothing here is large text — the biggest is the
# 26px masthead heading, asserted at the stricter figure anyway), 3:1 for the boundaries and state
# indicators of user interface components. Decorative separators — panel edges, row rules, chip and
# treatment borders, the masthead and footer lines — are deliberately absent: 1.4.11 covers what
# identifies a component or a state, and raising every divider to 3:1 would draw a heavy grid over a
# 204-row table. A chip is identified by its text and fill, a row by its content.
#
# Floating previews and pinned columns need visible boundaries against the content beneath them.
THEME_SURFACES = [
    ("masthead heading", ".masthead h1", "color", "text", 4.5),
    ("masthead tagline", ".masthead .tagline", "color", "text", 4.5),
    ("navigation link", "nav.sections a", "color", "text", 4.5),
    ("section heading", "#about h2", "color", "text", 4.5),
    ("body text", "#about p", "color", "text", 4.5),
    ("body link", "#methodology a", "color", "text", 4.5),
    ("statistic value", ".stat .n", "color", "text", 4.5),
    ("statistic label", ".stat .k", "color", "text", 4.5),
    ("callout text", ".callout", "color", "text", 4.5),
    ("callout rule", ".callout", "borderLeftColor", "boundary", 3.0),
    ("filter label", ".field label", "color", "text", 4.5),
    ("filter input text", "#f-q", "color", "text", 4.5),
    ("filter input border", "#f-q", "borderTopColor", "boundary", 3.0),
    ("filter select text", ".field select", "color", "text", 4.5),
    ("filter select border", ".field select", "borderTopColor", "boundary", 3.0),
    ("disclosure summary", "details.morefilters > summary", "color", "text", 4.5),
    ("active filter chip", ".chip", "color", "text", 4.5),
    ("ghost button text", "button.ghost", "color", "text", 4.5),
    ("ghost button edge", "button.ghost", "borderTopColor", "boundary", 3.0),
    ("result count", "#count", "color", "text", 4.5),
    ("column heading", "#collection-table thead th button.sort", "color", "text", 4.5),
    ("table cell", "#rows tr td:nth-child(3)", "color", "text", 4.5),
    ("clipped cell", "#rows .cell-clip", "color", "text", 4.5),
    ("year separator", "tr.yearsep td", "color", "text", 4.5),
    ("frozen column heading", "#collection-table th.corr", "color", "text", 4.5),
    ("frozen column link", "#rows td.corr a", "color", "text", 4.5),
    ("frozen column edge", "#rows td.corr", "borderLeftColor", "boundary", 3.0),
    ("card preview edge", ".card-preview", "borderTopColor", "boundary", 3.0),
    ("confirmed pill", ".pill.confirmed", "color", "text", 4.5),
    ("not-applicable pill", ".pill.not-applicable", "color", "text", 4.5),
    ("treatment badge", "#rows .treatment", "color", "text", 4.5),
    ("language present", "td.langcell.yes", "color", "text", 4.5),
    ("language absent", "td.langcell.no", "color", "text", 4.5),
    ("language count", "td.langcount", "color", "text", 4.5),
    ("legend text", ".language-legend", "color", "text", 4.5),
    ("legend present state", ".language-legend .yes", "color", "text", 4.5),
    ("legend absent state", ".language-legend .no", "color", "text", 4.5),
    ("sources link", "#sources a", "color", "text", 4.5),
    ("footer text", "footer.sitefoot", "color", "text", 4.5),
]

# Composite transparent backgrounds before measuring contrast.
MEASURE_SURFACES = """(surfaces) => {
  const parse = (value) => {
    const parts = (value.match(/[\\d.]+/g) || []).map(Number);
    if (value.startsWith('color(')) {
      return {r: parts[0] * 255, g: parts[1] * 255, b: parts[2] * 255,
              a: parts.length > 3 ? parts[3] : 1};
    }
    return {r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1};
  };
  const over = (top, bottom) => ({
    r: top.r * top.a + bottom.r * (1 - top.a),
    g: top.g * top.a + bottom.g * (1 - top.a),
    b: top.b * top.a + bottom.b * (1 - top.a),
    a: 1,
  });
  const rgb = (c) => 'rgb(' + [c.r, c.g, c.b].map((v) => Math.round(v)).join(', ') + ')';
  const backdrop = (element) => {
    let colour = {r: 255, g: 255, b: 255, a: 0};
    const stack = [];
    for (let node = element; node; node = node.parentElement) {
      stack.push(parse(getComputedStyle(node).backgroundColor));
    }
    stack.push(parse(getComputedStyle(document.documentElement).backgroundColor));
    stack.push({r: 255, g: 255, b: 255, a: 1});
    for (let index = stack.length - 1; index >= 0; index -= 1) colour = over(stack[index], colour);
    return rgb(colour);
  };
  return surfaces.map(([label, selector, property, mode]) => {
    const element = document.querySelector(selector);
    if (!element) return {label, missing: true};
    const behind = mode === 'boundary' ? element.parentElement || document.body : element;
    return {label, value: rgb(parse(getComputedStyle(element)[property])), against: backdrop(behind)};
  });
}"""

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def check_catalogue_evidence(embedded):
    spec = importlib.util.spec_from_file_location("site_projection", ROOT / "scripts/site.py")
    projection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(projection)
    load = lambda path: json.loads((ROOT / path).read_text(encoding="utf-8"))
    graph = load("verification/authoritative_graph.json")
    records = projection.catalogue_source_records(graph, load("verification/source_first_prints.json"))
    strengths = projection.catalogue_language_evidence(records, load("analysis_checklist.json"),
        load("analysis_confirmed_releases.json"), graph)
    localizations = {row["localizationId"]:row for row in load("collector_catalogue.json")["localizations"]}
    check("every confirmed table language has a registered provider and authority tier",
          all(row["langEvidence"][code]["provider"] and row["langEvidence"][code]["tier"] in (1, 2, 3)
              for row in embedded for code in row["langCodes"]))
    check("claim and predecessor ordering cannot change language evidence",
          all(projection.catalogue_language(item, localizations[item["localizationId"]], strengths) ==
              projection.catalogue_language(dict(item, sourceClaimRefs=list(reversed(item["sourceClaimRefs"])),
                  legacyChecklistIds=list(reversed(item["legacyChecklistIds"]))),
                  localizations[item["localizationId"]], strengths) for item in CANONICAL_ITEMS))
    expected_artists = {item["itemId"]:records[ref]["illustrator"] for item in CANONICAL_ITEMS
                        for ref in item["sourceClaimRefs"] if records.get(ref, {}).get("illustrator")}
    check("source-native illustrator credits survive for every supported table item",
          all(row["artist"] == expected_artists.get(row["rowId"], row["artist"]) for row in embedded))
    check_catalogue_boundaries(embedded, projection, localizations, strengths, load("collector_catalogue.json"))
    check_exact_provider_agreement(embedded, projection)


def check_catalogue_boundaries(rows, projection, localizations, strengths, catalogue):
    chinese = next(row for row in rows if row["setCode"] == "30thC" and row["number"] == "095/103")
    check("historical source-first alias resolves to registered photograph authority",
          chinese["langEvidence"]["ZH-S"]["tier"] == 1
          and chinese["langEvidence"]["ZH-S"]["provider"] == "Inspected physical specimen")
    indonesian = next(row for row in rows if row["setCode"] == "S8b I" and row["number"] == "126/184")
    check("exact predecessor corroboration survives source-first attachment",
          indonesian["langEvidence"]["ID"]["corroborated"])
    promo = next(item for item in catalogue["items"] if item["localSetCode"] == "FLF"
                 and any(mark.get("text") == "Build-A-Bear Workshop" for mark in item["markings"]))
    grade = projection.catalogue_language(promo, localizations[promo["localizationId"]], strengths)
    check("retailer candidate keeps its own grade without borrowing a sibling variant",
          grade["languageEvidence"]["English"]["provider"] == "Cardmarket exact product image"
          and not grade["languageEvidence"]["English"]["corroborated"])
    check("unconfirmed retailer finish stays outside the table while its positive date is retained",
          promo["releaseDate"] == "2019-08-29" and promo["itemId"] not in {row["rowId"] for row in rows})


def check_exact_provider_agreement(rows, projection):
    korean = next(row for row in rows if row["setCode"] == "20th" and "KO" in row["langCodes"])
    check("independent exact Korean checklist and photograph evidence is corroborated",
          korean["langEvidence"]["KO"]["corroborated"])
    item = dict(sourceClaimRefs=["one", "two"], legacyChecklistIds=[], itemKind="verified-printing")
    localization = dict(language="Korean", locality="KR")
    grade = dict(language="Korean", provider="Bulbapedia", authorityTier=3, corroborated=False, checkable=True)
    fields = projection.catalogue_language(item, localization, {"one":grade, "two":dict(grade)})
    check("two references to the same provider are not independent corroboration",
          not fields["languageEvidence"]["Korean"]["corroborated"])


def check_desktop_sources(page):
    for width in (1280, 2560):
        page.set_viewport_size({"width": width, "height": 900})
        button = page.locator("#rows .rowmore").first
        button.click()
        open_label = button.inner_text()
        open_overflow = page.locator("#collection-table-scroll").evaluate("e => e.scrollWidth - e.clientWidth")
        panel = page.locator("#" + button.get_attribute("aria-controls"))
        check(f"row sources are reachable on desktop at {width}px",
              panel.is_visible() and panel.locator("dt", has_text="Sources").count() == 1
              and panel.locator("a[href]").count() > 0)
        button.click()
        check(f"row disclosure retains its compact label after toggling at {width}px",
              button.inner_text() == open_label == "Info")
        if width == 2560:
            closed_overflow = page.locator("#collection-table-scroll").evaluate("e => e.scrollWidth - e.clientWidth")
            check("desktop source disclosure fits before and after closing",
                  open_overflow <= 1 and closed_overflow <= 1,
                  f"open={open_overflow}, closed={closed_overflow}")
    page.set_viewport_size({"width": 1280, "height": 900})


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the WCAG contrast ratio for computed rgb()/rgba() colors."""
    def luminance(color: str) -> float:
        channels = [int(value) / 255 for value in re.findall(r"\d+", color)[:3]]
        linear = [
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            for value in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = luminance(foreground), luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


@contextmanager
def serve_site(directory: Path = ROOT):
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(directory))) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join()


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed; run: pip install -r requirements.txt", file=sys.stderr)
        return 1

    with serve_site() as origin, sync_playwright() as p:
        url = origin + "/index.html"
        try:
            # Playwright resolves both its default cache and PLAYWRIGHT_BROWSERS_PATH itself.
            # Contributors may instead select an installed Playwright channel (for example
            # ``chrome``) without baking a machine-specific executable path into the suite.
            channel = os.environ.get("SNOREDEX_BROWSER_CHANNEL") or None
            browser = p.chromium.launch(channel=channel)
        except Exception as error:  # pragma: no cover - environment dependent
            print(f"chromium unavailable: {error}", file=sys.stderr)
            return 1

        page = browser.new_page()
        artwork_requests = []
        page.on("request", lambda request: artwork_requests.append(request.url)
                if "artwork_review_projection" in request.url else None)
        page.add_init_script("localStorage.setItem('snoredex-artwork-review-proposals-v1', 'retained-draft')")
        console_errors: list[str] = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))
        page.goto(url)
        page.wait_for_selector("#rows tr")
        # Column and language filters live in collapsed <details>; open them as a user would.
        page.eval_on_selector_all("details.morefilters", "els => els.forEach(d => d.open = true)")

        total = page.evaluate("JSON.parse(document.getElementById('data-rows').textContent).length")
        check("page loads with no console errors", not console_errors, "; ".join(console_errors[:3]))
        check("all rows render", total == EXPECTED_ROWS, f"data has {total} rows")
        embedded = page.evaluate("() => JSON.parse(document.getElementById('data-rows').textContent)")
        check_catalogue_evidence(embedded)
        expected = {item["itemId"]: item for item in CANONICAL_ITEMS}
        check("main table represents every active canonical item exactly once",
              len(embedded) == len(expected) and {row["rowId"] for row in embedded} == set(expected),
              f"canonical={len(expected)} table={len(embedded)}")
        check("canonical evidence states and correction identities survive rendering",
              all(row["itemKind"] == expected[row["rowId"]]["itemKind"]
                  and row["edition"] == (expected[row["rowId"]]["edition"] or
                      {"not-applicable":"none"}.get(expected[row["rowId"]]["editionAssignmentStatus"], "unknown"))
                  and row["correctionUrl"] == expected[row["rowId"]]["correctionLink"]
                  and expected[row["rowId"]]["finishVerificationStatus"] in row["evidence"]
                  for row in embedded), "no candidate is promoted to verified")
        check("canonical field values and date precision survive the main table projection",
              all(row["dateDisplay"] == ("Undated" if not (item := expected[row["rowId"]])["releaseDate"]
                      else ("~" if item["releaseApproximate"] else "") + item["releaseDate"])
                  and row["rarity"] == item["rarity"]["display"]
                  and row["sourceLinks"] == item["sourceLinks"]
                  and row["number"] == (item["collectorNumber"] or "") +
                      ("/" + item["collectorNumberDenominator"] if item["collectorNumberDenominator"] else "")
                  for row in embedded), "dates, numbers, rarity and sources match canonical items")


        check("page advertises the concise LLM entry point",
              page.locator('head link[rel="describedby"][href="llms.txt"]').count() == 1
              and (ROOT / "llms.txt").read_text(encoding="utf-8").startswith("# Snoredex Data\n"),
              "missing describedby relation or llms.txt H1")

        check("retired artwork review has no controls, metadata or navigation",
              page.locator('#artwork-review, #artwork-review-app, #ar-load, #ar-export, '
                           '#data-artwork-review-meta, a[href="#artwork-review"]').count() == 0)
        check("removing the review UI preserves existing draft storage and performs no artwork fetch",
              page.evaluate("localStorage.getItem('snoredex-artwork-review-proposals-v1')") == "retained-draft"
              and not artwork_requests)


        exs_rows = page.evaluate("""() => JSON.parse(
          document.getElementById('data-rows').textContent
        ).filter(r => r.setCode === 'EXS')""")
        check("both dated EXS physical variants appear in 1998",
              len(exs_rows) == 2
              and [row["dateDisplay"] for row in exs_rows] == ["1998-03-23", "1998-12-04"]
              and [row["distributions"] for row in exs_rows] == [["vending-sheet"], ["fixed-deck"]]
              and [row["image"] is not None for row in exs_rows] == [False, True]
              and len({row["rowId"] for row in exs_rows}) == 2,
              f"EXS rows: {exs_rows}")

        # --- complete light/dark themes (#43) ---
        check("removed UI features leave no controls or embedded checklist",
              page.locator('#theme-toggle, #cl-download, #data-checklist, '
                           '#collection-sticky-header, #collection-scroll-tools').count() == 0)

        for scheme in ("light", "dark"):
            theme_context = browser.new_context(color_scheme=scheme)
            prior_scheme = "dark" if scheme == "light" else "light"
            theme_context.add_init_script(f"localStorage.setItem('snoredex-theme', '{prior_scheme}');")
            theme_context.add_init_script("""
              window.__snoredexThemeAtFirstFrame = new Promise((resolve) => {
                requestAnimationFrame(() => resolve(getComputedStyle(document.documentElement).colorScheme));
              });
            """)
            theme_page = theme_context.new_page()
            theme_page.goto(url)
            theme_page.wait_for_selector("#rows tr")
            first_frame_theme = theme_page.evaluate("window.__snoredexThemeAtFirstFrame")
            # Chips and treatment badges exist only once a filter narrows the table, and the
            # language filters live in a collapsed disclosure.
            theme_page.eval_on_selector_all("details", "els => els.forEach(d => d.open = true)")
            theme_page.fill("#f-q", "holo")
            theme_page.wait_for_timeout(150)
            theme_metrics = theme_page.evaluate("""() => {
              const primary = getComputedStyle(document.querySelector('button.ghost'));
              const control = getComputedStyle(document.querySelector('.field select'));
              const panel = getComputedStyle(document.querySelector('.controls'));
              const absent = getComputedStyle(document.querySelector('td.langcell.no'));
              const body = getComputedStyle(document.body);
              return {
                colorScheme: getComputedStyle(document.documentElement).colorScheme,
                primaryForeground: primary.color,
                primaryBackground: primary.backgroundColor,
                controlBorder: control.borderTopColor,
                panelBackground: panel.backgroundColor,
                absentForeground: absent.color,
                bodyBackground: body.backgroundColor,
              };
            }""")
            check(f"{scheme} mode follows the initial system preference before first paint",
                  first_frame_theme == scheme
                  and theme_metrics["colorScheme"] == scheme,
                  f"firstFrame={first_frame_theme} metrics={theme_metrics}")
            check(f"{scheme} mode meets representative WCAG contrast thresholds",
                  contrast_ratio(theme_metrics["primaryForeground"],
                                 theme_metrics["primaryBackground"]) >= 4.5
                  and contrast_ratio(theme_metrics["controlBorder"],
                                     theme_metrics["panelBackground"]) >= 3
                  and contrast_ratio(theme_metrics["absentForeground"],
                                     theme_metrics["bodyBackground"]) >= 4.5,
                  str(theme_metrics))
            # The representative sample above is a smoke test; #43 asks for the whole interface.
            # Exercise the reserved treatment style even when no active item uses it.
            theme_page.evaluate("""() => {
              if (!document.querySelector('.pill.not-applicable')) {
                document.querySelector('#rows .col-finish').insertAdjacentHTML(
                  'beforeend', '<span class="pill not-applicable">not applicable</span>');
              }
            }""")
            surfaces = theme_page.evaluate(MEASURE_SURFACES, THEME_SURFACES)
            surface_failures = []
            for surface, (label, _selector, _property, _mode, threshold) in zip(
                    surfaces, THEME_SURFACES):
                if surface.get("missing"):
                    surface_failures.append(f"{label}: not rendered")
                    continue
                ratio = contrast_ratio(surface["value"], surface["against"])
                if ratio < threshold:
                    surface_failures.append(
                        f"{label}: {ratio:.2f}:1 needs {threshold}:1 "
                        f"({surface['value']} on {surface['against']})")
            check(f"every {scheme}-mode surface meets its WCAG 2.2 AA contrast threshold",
                  not surface_failures,
                  f"{len(surface_failures)}/{len(THEME_SURFACES)} failing: "
                  f"{'; '.join(surface_failures[:6])}")

            theme_page.fill("#f-q", "")
            theme_page.wait_for_timeout(150)
            focus_target = theme_page.locator("#rows td.corr a").nth(20)
            focus_target.focus()
            focus_geometry = focus_target.evaluate("""element => {
              const box = element.getBoundingClientRect();
              return {focused: document.activeElement === element,
                      visible: box.top >= 0 && box.bottom <= innerHeight};
            }""")
            check(f"keyboard focus in the table is visible in {scheme} mode",
                  focus_geometry["focused"] and focus_geometry["visible"], str(focus_geometry))
            theme_page.emulate_media(color_scheme="dark" if scheme == "light" else "light")
            check("system preference changes apply without a persisted override",
                  theme_page.evaluate("getComputedStyle(document.documentElement).colorScheme") != scheme)
            theme_context.close()

        # Sort affordances must render as glyphs, not as the literal CSS escape text. A
        # double-escaped content string printed "\\2195" in every heading and passed every
        # functional assertion, so this is checked explicitly.
        indicator = page.evaluate(
            "() => getComputedStyle(document.querySelector('th[data-key=\"name\"] button.sort'),"
            "'::after').content")
        check("sort indicators render as arrow glyphs, not literal escapes",
              "2195" not in indicator and "2191" not in indicator, f"content={indicator}")

        # Rows must not blow up from text wrapping. With 34 columns squeezed into the page
        # shell, cells wrapped to six lines and rows reached 173px; nowrap plus a scrolling
        # wrapper fixed it. The budget allows a 64px thumbnail plus a two-line variant cell.
        max_row = page.evaluate(
            "() => Math.max(...[...document.querySelectorAll('#rows tr:not(.yearsep)')]"
            ".map(r => r.getBoundingClientRect().height))")
        check("table rows do not blow up from text wrapping", max_row <= 120,
              f"tallest row {max_row}px")

        # The site used to clamp every monitor to a 1,200px content shell while the table itself
        # needed 3,711px. A wide display must now be used, and the compact column treatment should
        # fit the complete matrix at 2560px without manufacturing a horizontal-scroll problem.
        page.set_viewport_size({"width": 2560, "height": 1000})
        wide_layout = page.evaluate("""() => {
          const wrap = document.querySelector('.wrap');
          const scroller = document.querySelector('#collection-table-scroll');
          return {
            wrap: Math.round(wrap.getBoundingClientRect().width),
            overflow: scroller.scrollWidth - scroller.clientWidth,
          };
        }""")
        check("wide monitors use the available viewport width", wide_layout["wrap"] >= 2500,
              f"content shell is only {wide_layout['wrap']}px at a 2560px viewport")
        check("the complete collection matrix fits a 2560px viewport",
              wide_layout["overflow"] <= 1,
              f"overflow={wide_layout['overflow']}")

        page.set_viewport_size({"width": 3072, "height": 1200})
        page.wait_for_timeout(120)
        clipping = page.evaluate("""() => {
          const cells = [...document.querySelectorAll('.cell-clip')].map((cell) => {
            const parent = cell.parentElement;
            const style = getComputedStyle(parent);
            const available = parent.clientWidth - parseFloat(style.paddingLeft)
              - parseFloat(style.paddingRight);
            const clipped = cell.scrollWidth > cell.clientWidth + 1;
            return {
              clipped,
              avoidable: clipped && available >= cell.scrollWidth - 1,
              ratio: cell.scrollWidth ? cell.clientWidth / cell.scrollWidth : 1,
              disclosed: cell.dataset.clipped === 'true'
                && cell.getAttribute('role') === 'button'
                && cell.tabIndex === 0,
            };
          });
          return {
            clipped: cells.filter((cell) => cell.clipped).length,
            avoidable: cells.filter((cell) => cell.avoidable).length,
            underHalf: cells.filter((cell) => cell.clipped && cell.ratio < .5).length,
            undisclosed: cells.filter((cell) => cell.clipped && !cell.disclosed).length,
          };
        }""")
        # Bound clipping density rather than a tally tied to the retired 204-row table.
        check("wide cells use allocated table width instead of avoidably clipping",
              clipping["avoidable"] == 0 and clipping["clipped"] / EXPECTED_ROWS < 1.25,
              str(clipping))
        check("severely clipped values are reduced and expose a disclosure control",
              clipping["underHalf"] < 60 and clipping["undisclosed"] == 0,
              str(clipping))

        disclosure = page.locator('.cell-clip[data-clipped="true"]').first
        collapsed_height = disclosure.evaluate("element => element.getBoundingClientRect().height")
        disclosure.focus()
        disclosure.press("Enter")
        expanded_state = disclosure.evaluate("""element => ({
          expanded: element.getAttribute('aria-expanded'),
          whiteSpace: getComputedStyle(element).whiteSpace,
          height: element.getBoundingClientRect().height,
          label: element.getAttribute('aria-label'),
        })""")
        disclosure.press("Escape")
        check("clipped values expand and collapse from the keyboard",
              expanded_state["expanded"] == "true"
              and expanded_state["whiteSpace"] == "normal"
              and expanded_state["height"] > collapsed_height
              and "Hide full value" in expanded_state["label"]
              and disclosure.get_attribute("aria-expanded") == "false",
              f"collapsed={collapsed_height} expanded={expanded_state}")

        page.set_viewport_size({"width": 1280, "height": 900})
        scroller = page.locator("#collection-table-scroll")
        scroller.focus()
        scroller.press("ArrowRight")
        page.wait_for_timeout(150)
        check("native table overflow is keyboard-scrollable",
              scroller.evaluate("element => element.scrollLeft") > 0)
        scroller.evaluate("element => { element.scrollLeft = 0; }")

        # Thumbnails visibly react and render their large preview outside the clipped table.
        image_trigger = page.locator(".card-preview-trigger").first
        image_trigger.hover()
        page.wait_for_timeout(120)
        preview_geometry = page.evaluate("""() => {
          const trigger = document.querySelector('.card-preview-trigger').getBoundingClientRect();
          const preview = document.querySelector('.card-preview');
          const box = preview.getBoundingClientRect();
          return {hidden: preview.hidden, triggerWidth: trigger.width, previewWidth: box.width};
        }""")
        check("hovering a card thumbnail opens a substantially larger preview",
              not preview_geometry["hidden"]
              and preview_geometry["previewWidth"] >= preview_geometry["triggerWidth"] * 4,
              str(preview_geometry))
        page.keyboard.press("Escape")
        check("the enlarged card preview closes with Escape",
              page.locator(".card-preview").evaluate("element => element.hidden"),
              "preview remained open")

        count_text = page.text_content("#count")
        check("shown/total count is displayed", str(EXPECTED_ROWS) in (count_text or ""), count_text or "")
        count_status = page.evaluate("""() => {
          const count = document.querySelector('#count');
          return {role: count.getAttribute('role'), live: count.getAttribute('aria-live'),
                  atomic: count.getAttribute('aria-atomic')};
        }""")
        check("filter result count is announced to assistive technology",
              count_status == {"role": "status", "live": "polite", "atomic": "true"},
              str(count_status))

        sourced_dates = page.evaluate("""() => {
          const rows = JSON.parse(document.getElementById('data-rows').textContent);
          return Object.fromEntries(['G2', 'PCG9', 'DF', 'CS2aC'].map(code => {
            const row = rows.find(candidate => candidate.setCode === code);
            return [code, {date: row.dateDisplay, source: row.dateSource}];
          }));
        }""")
        expected_dates = {"G2": "1999-06-25", "PCG9": "2006-06-29",
                          "DF": "2006-11-08", "CS2aC": "2023-08-18"}
        release_projection_ok = all(
            sourced_dates[code]["date"] == date
            for code, date in expected_dates.items()
        )
        check("Bulbapedia market-specific release dates reach the site projection",
              release_projection_ok, str(sourced_dates))

        page.fill("#f-q", "challenge from the darkness")
        page.wait_for_timeout(120)
        release_link = page.locator("#rows tr:not(.yearsep) .release-source")
        check("sourced release dates link to the reviewed Bulbapedia page",
              release_link.count() > 0
              and release_link.first.text_content() == "1999-06-25"
              and "Gym_Challenge" in (release_link.first.get_attribute("href") or ""),
              f"links={release_link.count()}")
        page.fill("#f-q", "")
        page.wait_for_timeout(120)

        # --- filtering ---
        page.fill("#f-q", "jungle")
        page.wait_for_timeout(120)
        filtered = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        check("global search filters rows", 0 < filtered < EXPECTED_ROWS, f"{filtered} rows for 'jungle'")

        page.fill("#f-q", "")
        page.wait_for_timeout(120)

        localized = page.evaluate("""() => JSON.parse(document.getElementById('data-rows').textContent)
          .filter(row => ['30C EN','30C LA','30thC','M6a'].includes(row.setCode))""")
        check("source-first anniversary releases reach the main table with distinct localities",
              {row['setCode'] for row in localized} == {'30C EN','30C LA','30thC','M6a'}
              and all(row['image'] and row['dateSort'] == '2026-09-16' for row in localized)
              and next(row for row in localized if row['setCode'] == '30C LA')['langCodes'] == ['ES-LA'],
              f"Localized anniversary rows: {localized}")

        required_filters = [
            "dateStatus", "name", "setCode", "setName", "number", "edition", "variant",
            "variantName", "rarity", "artist", "finish", "pattern", "marking",
            "markingRole", "size", "distribution", "evidence",
        ]
        missing_filters = [
            field for field in required_filters if page.locator("#f-" + field).count() != 1
        ]
        check("every semantic field has a dedicated filter", not missing_filters,
              f"missing controls: {missing_filters}")

        finish_options = page.eval_on_selector_all(
            "#f-finish option", "els => els.map(e => [e.value, e.textContent])")
        check("public finish filter exposes one Reverse Holo family",
              ["reverse-holo", "Reverse Holo"] in finish_options
              and not any(value == "mirror-holo" or label == "Mirror Holo"
                          for value, label in finish_options),
              f"finish options: {finish_options}")
        technical_mirror_rows = page.evaluate("""() => JSON.parse(
          document.getElementById('data-rows').textContent
        ).filter(r => r.technicalFinishes.includes('mirror-holo'))""")
        # The property, not the tally. This asserted `== 4` and broke the moment TCGdex began
        # reporting a mirror finish for SV-P/ID 117 Indonesian — genuine new evidence, arriving at a
        # check that treated the then-current count as the specification. Nothing about the
        # behaviour had moved: all six rows kept the technical value and presented Reverse Holo.
        # The named sets stay pinned, because losing *those* would be the real regression.
        mirror_row_ids = {row["rowId"] for row in technical_mirror_rows}
        known_mirror_rows = {item["itemId"] for item in CANONICAL_ITEMS
                             if item["finish"] == "mirror-holo"}
        check("technical mirror-holo evidence remains in the embedded audit projection",
              known_mirror_rows <= mirror_row_ids
              and all("reverse-holo" in row["finishes"] and "mirror-holo" not in row["finishes"]
                      for row in technical_mirror_rows),
              f"missing={sorted(known_mirror_rows - mirror_row_ids)}; "
              f"technical mirror rows: {[(r['rowId'], r['finishes']) for r in technical_mirror_rows]}")

        page.select_option("#f-finish", ["reverse-holo"])
        page.wait_for_timeout(120)
        visible_mirrors = page.eval_on_selector_all(
            "#rows .rowmore", "els => els.map(e => e.dataset.rowId)")
        check("Reverse Holo filter includes every canonical mirror printing",
              known_mirror_rows <= set(visible_mirrors),
              f"missing={sorted(known_mirror_rows - set(visible_mirrors))}")
        page.select_option("#f-finish", [])
        page.wait_for_timeout(120)

        page.select_option("#f-dateStatus", ["approximate"])
        page.wait_for_timeout(120)
        approximate = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        check("exact/approximate release status is filterable", 0 < approximate < EXPECTED_ROWS,
              f"{approximate} approximate rows")
        page.select_option("#f-dateStatus", [])
        page.wait_for_timeout(120)

        first_name = page.evaluate(
            "JSON.parse(document.getElementById('data-rows').textContent)[0].name"
        )
        page.select_option("#f-name", [first_name])
        page.wait_for_timeout(120)
        named = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        check("card name has an exact field filter", 0 < named < EXPECTED_ROWS,
              f"{named} rows for {first_name}")
        page.select_option("#f-name", [])
        page.wait_for_timeout(120)

        # URL values stay compatible; the complement of confirmed does not assert absence.
        page.select_option("#f-lang-JA", "present")
        page.wait_for_timeout(120)
        present = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        page.select_option("#f-lang-JA", "absent")
        page.wait_for_timeout(120)
        absent = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        check("language confirmation filter partitions the rows",
              present + absent == EXPECTED_ROWS and present > 0 and absent > 0,
              f"present={present} absent={absent} total={EXPECTED_ROWS}")

        page.select_option("#f-lang-JA", "")
        page.wait_for_timeout(120)

        present_cell = page.locator("#rows td.langcell.yes").first
        absent_cell = page.locator("#rows td.langcell.no").first
        language_accessibility = {
            "presentLabel": present_cell.get_attribute("aria-label"),
            "absentLabel": absent_cell.get_attribute("aria-label"),
            "presentSnapshot": present_cell.aria_snapshot(),
            "absentSnapshot": absent_cell.aria_snapshot(),
            "legend": page.locator("#collection-table-legend").inner_text(),
        }
        check("language cells expose confirmation without asserting absence",
              language_accessibility["presentLabel"].endswith(": confirmed")
              and language_accessibility["absentLabel"].endswith(": not confirmed")
              and "confirmed" in language_accessibility["presentSnapshot"]
              and "not confirmed" in language_accessibility["absentSnapshot"],
              str(language_accessibility))
        check("language symbols have a visible non-color legend",
              "✓ confirmed" in language_accessibility["legend"]
              and "— not confirmed" in language_accessibility["legend"]
              and "not proof of absence" in language_accessibility["legend"],
              language_accessibility["legend"])

        evidence_trigger = page.locator(".lang-evidence-trigger").first
        evidence_label = evidence_trigger.get_attribute("aria-label") or ""
        evidence_trigger.focus()
        evidence_trigger.press("Enter")
        page.wait_for_timeout(80)
        evidence_popover = page.evaluate("""() => {
          const popover = document.querySelector('#collection-language-evidence');
          const trigger = document.querySelector('.lang-evidence-trigger[aria-expanded="true"]');
          return {hidden: popover.hidden, text: popover.textContent,
                  describedBy: trigger && trigger.getAttribute('aria-describedby')};
        }""")
        check("language evidence opens from a keyboard/touch-capable control",
              not evidence_popover["hidden"]
              and evidence_label.split(" — ", 1)[-1] in evidence_popover["text"]
              and evidence_popover["describedBy"] == "collection-language-evidence",
              str(evidence_popover))
        page.keyboard.press("Escape")
        check("language evidence detail closes with Escape",
              page.locator("#collection-language-evidence").evaluate("element => element.hidden"),
              "language evidence popover remained open")

        # --- no-results state ---
        page.fill("#f-q", "zzzzzznotacard")
        page.wait_for_timeout(120)
        check("no-results state appears", page.locator("#rows .empty").count() == 1,
              "expected a single empty-state cell")
        page.fill("#f-q", "")
        page.wait_for_timeout(120)

        # --- sorting ---
        page.click('th[data-key="number"] button.sort')
        page.wait_for_timeout(150)
        aria = page.get_attribute('th[data-key="number"]', "aria-sort")
        check("sorting sets aria-sort", aria == "ascending", f"aria-sort={aria}")

        numbers = page.eval_on_selector_all(
            "#rows tr:not(.yearsep) .col-number", "els => els.map(e => e.textContent)")
        numeric = [n for n in numbers if n.isdigit()]
        check("collector numbers sort naturally, not lexicographically",
              numeric == sorted(numeric, key=int),
              f"first 12: {numeric[:12]}")

        # Year separators must not survive a non-chronological sort.
        seps = page.eval_on_selector_all("#rows tr.yearsep", "els => els.length")
        check("year headings are hidden outside chronological order", seps == 0,
              f"{seps} year separator rows while sorted by collector number")

        page.click('th[data-key="lang-JA"] button.sort')
        page.wait_for_timeout(150)
        ja_ends = page.evaluate("""() => {
          const headers = [...document.querySelectorAll('thead th')];
          const column = headers.findIndex((th) => th.dataset.key === 'lang-JA') + 1;
          const cells = [...document.querySelectorAll(
            `#rows tr:not(.yearsep) td:nth-child(${column})`
          )];
          return [cells[0].className, cells[cells.length - 1].className];
        }""")
        check("language columns are sortable by absence/presence",
              "no" in ja_ends[0] and "yes" in ja_ends[1],
              f"first/last classes={ja_ends}")

        page.click('th[data-key="release"] button.sort')
        page.wait_for_timeout(150)
        seps = page.eval_on_selector_all("#rows tr.yearsep", "els => els.length")
        check("year headings return under release sort", seps > 0, f"{seps} separators")

        # --- URL round-trip ---
        page.select_option("#f-edition", ["1st Edition"])
        page.click('th[data-key="name"] button.sort')
        page.wait_for_timeout(150)
        identity_mismatches = page.evaluate("""() => {
          const rows = new Map(JSON.parse(document.querySelector('#data-rows').textContent)
            .map(row => [row.rowId, row]));
          const languages = JSON.parse(document.querySelector('#data-meta').textContent).languages;
          return [...document.querySelectorAll('#rows tr:not(.yearsep)')].filter(element => {
            const row = rows.get(element.querySelector('.rowmore').dataset.rowId);
            return !row || element.querySelector('.col-card').textContent !== row.name
              || element.querySelector('.col-number').textContent !== (row.number || '—')
              || element.querySelector('td.corr a').getAttribute('href') !== row.correctionUrl
              || [...element.querySelectorAll('.langcell')].some((cell, i) =>
                cell.classList.contains('yes') !== row.langCodes.includes(languages[i].code)
                || (cell.dataset.tier && Number(cell.dataset.tier)
                  !== row.langEvidence[languages[i].code].tier));
          }).length;
        }""")
        check("filtered and sorted rows keep their correction and language evidence identity",
              identity_mismatches == 0 and page.locator('#rows .rowmore').count() > 0,
              f"{identity_mismatches} mismatched rows")
        before = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        shared_url = page.url
        check("filter state is written to the URL", "edition=" in shared_url, shared_url[-80:])

        page2 = browser.new_page()
        page2.goto(shared_url)
        page2.wait_for_selector("#rows tr")
        page2.eval_on_selector_all("details.morefilters", "els => els.forEach(d => d.open = true)")
        after = page2.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        check("URL state restores the same filtered view", before == after,
              f"{before} rows before, {after} after reload")
        page2.close()

        # --- reset ---
        page.click("#reset")
        page.wait_for_timeout(150)
        reset_rows = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        check("reset restores the unfiltered chronological view", reset_rows == EXPECTED_ROWS,
              f"{reset_rows} rows after reset")

        # --- correction links are stable, one per row ---
        links = page.eval_on_selector_all(
            "#rows td.corr a", "els => els.map(e => e.getAttribute('href'))")
        check("exactly one correction link per row", len(links) == EXPECTED_ROWS, f"{len(links)} links")
        # Links now deep-link into the generated issue form (#20) with the row identity in
        # query parameters, rather than pasting a prose body. Identity must still be the stable
        # rowId, never the rendered position.
        check("every correction link targets the correction issue form",
              all("template=printing-correction.yml" in href for href in links),
              "correction links must open the generated form")
        check("every correction link prefills the stable row id",
              all("row-id=" in href for href in links),
              "correction links must carry rowId, not the generated row number")

        # Short guidance links the authoritative contracts instead of duplicating them.
        contribute_text = " ".join((page.text_content("#contribute") or "").lower().split())
        contribute_links = page.eval_on_selector_all(
            "#contribute a", "els => els.map(e => e.getAttribute('href'))")
        check("correction guidance retains the positive-evidence boundary and domain links",
              "positive evidence" in contribute_text and "not proof of absence" in contribute_text
              and "never unavailable" in contribute_text
              and {"CONTRIBUTING.md", "verification/FINISH_SOURCES.md",
                   "verification/open-items.html"} <= set(contribute_links), contribute_text)
        check("entries outside the confirmed table have a visible general correction route",
              page.locator('#contribute a[href="https://github.com/m4s-ai/snoredex-data/issues/new/choose"]').is_visible()
              and "blank_issues_enabled: true" in (ROOT / ".github/ISSUE_TEMPLATE/config.yml").read_text(encoding="utf-8"))

        # Native printing uses the current filter without building another document.
        page.fill("#f-q", "EXS")
        page.wait_for_timeout(150)
        page.evaluate("window.print = () => { window.__printRequested = true; }")
        page.get_by_role("button", name="Print filtered view").click()
        check("print action uses the browser on the current filtered view",
              page.evaluate("window.__printRequested === true")
              and page.locator("#rows tr:not(.yearsep)").count() == 2)

        # --- print smoke tests on both paper sizes ---
        # A4 is 794 CSS px at 96dpi, US Letter 816. Emulating print media and clamping the
        # viewport to the paper width is what catches a table that silently truncates on paper.
        PAPER = {"A4": 794, "Letter": 816}
        for paper, width in PAPER.items():
            page.emulate_media(media="print", color_scheme="dark")
            page.set_viewport_size({"width": width, "height": 1000})
            page.wait_for_timeout(120)
            overflow = page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"collection page prints without horizontal overflow ({paper})",
                  overflow <= 1, f"overflow {overflow}px at {width}px")
            print_geometry = page.evaluate("""() => {
              const table = document.querySelector('#collection-table');
              const row = [...table.tBodies[0].rows].find((candidate) =>
                !candidate.classList.contains('yearsep'));
              const cells = [...row.cells].filter((cell) => getComputedStyle(cell).display !== 'none');
              const tableBox = table.getBoundingClientRect();
              const usedRight = Math.max(...cells.map((cell) => cell.getBoundingClientRect().right));
              const body = getComputedStyle(document.body);
              return {
                visibleColumns: cells.length,
                usedPercent: (usedRight - tableBox.left) / tableBox.width * 100,
                widths: cells.map((cell) => cell.getBoundingClientRect().width),
                rowHeight: row.getBoundingClientRect().height,
                bodyBackground: body.backgroundColor,
                bodyColor: body.color,
              };
            }""")
            check(f"collection print columns use the printable width ({paper})",
                  print_geometry["visibleColumns"] == 7
                  and print_geometry["usedPercent"] >= 98
                  and min(print_geometry["widths"]) >= 50
                  and print_geometry["rowHeight"] <= 80,
                  str(print_geometry))
            check(f"collection print remains light when screen theme is dark ({paper})",
                  print_geometry["bodyBackground"] == "rgb(255, 255, 255)"
                  and print_geometry["bodyColor"] == "rgb(0, 0, 0)",
                  str(print_geometry))

        # Adversarial fixture: future source text must remain text, never active markup or an
        # attribute breakout. This drives the generated page with the production JavaScript.
        scratch = Path(tempfile.mkdtemp(prefix="snoredex-site-test-"))
        hostile_root = scratch / "hostile"
        hostile_root.mkdir()
        shutil.copytree(ROOT / "site", hostile_root / "site")
        hostile_html = INDEX.read_text(encoding="utf-8")
        pattern = re.compile(
            r'(<script type="application/json" id="data-rows">)(.*?)(</script>)', re.S
        )
        match = pattern.search(hostile_html)
        hostile_rows = json.loads(match.group(2)) if match else []
        payload = '<img id="xss-probe" src=x onerror="window.__snoredexXss=1">'
        hostile_rows[0]["name"] = payload
        hostile_rows[0]["image"] = 'x" onerror="window.__snoredexXss=1'
        encoded = json.dumps(
            hostile_rows, ensure_ascii=False, separators=(",", ":")
        ).replace("</", "<\\/")
        hostile_html = pattern.sub(
            lambda found: found.group(1) + encoded + found.group(3), hostile_html, count=1
        )
        (hostile_root / "index.html").write_text(hostile_html, encoding="utf-8")
        hostile_page = browser.new_page()
        hostile_page.goto((hostile_root / "index.html").as_uri())
        hostile_page.wait_for_selector("#rows tr")
        hostile_executed = hostile_page.evaluate("window.__snoredexXss === 1")
        hostile_markup = hostile_page.locator("#xss-probe").count()
        check("source-derived row values cannot inject DOM markup",
              not hostile_executed and hostile_markup == 0,
              f"executed={hostile_executed} injected_nodes={hostile_markup}")

        hostile_page.close()

        page.emulate_media(media="screen", color_scheme="light")
        page.click("#reset")
        page.wait_for_timeout(150)
        page.set_viewport_size({"width": 1280, "height": 900})

        # --- mobile layout ---
        page.set_viewport_size({"width": 481, "height": 800})
        page.wait_for_timeout(120)
        breakpoint_edge = page.evaluate("""() => ({
          rowDisplay: getComputedStyle(document.querySelector('#rows tr:not(.yearsep)')).display,
          sortDisplay: getComputedStyle(document.querySelector('#collection-mobile-sort')).display,
          overflow: document.querySelector('#collection-table-scroll').scrollWidth
            - document.querySelector('#collection-table-scroll').clientWidth,
        })""")
        check("the reduced table remains active above the 480px card breakpoint",
              breakpoint_edge["rowDisplay"] == "table-row"
              and breakpoint_edge["sortDisplay"] == "none"
              and breakpoint_edge["overflow"] > 0, str(breakpoint_edge))

        page.set_viewport_size({"width": 320, "height": 700})
        page.wait_for_timeout(120)
        narrow_mobile = page.evaluate("""() => ({
          bodyOverflow: document.documentElement.scrollWidth
            - document.documentElement.clientWidth,
          tableOverflow: document.querySelector('#collection-table-scroll').scrollWidth
            - document.querySelector('#collection-table-scroll').clientWidth,
          cardDisplay: getComputedStyle(document.querySelector('#rows tr:not(.yearsep)')).display,
          sortDisplay: getComputedStyle(document.querySelector('#collection-mobile-sort')).display,
        })""")
        check("320px layout replaces the table with cards without horizontal overflow",
              narrow_mobile["bodyOverflow"] <= 1
              and narrow_mobile["tableOverflow"] <= 1
              and narrow_mobile["cardDisplay"] == "grid"
              and narrow_mobile["sortDisplay"] == "flex",
              str(narrow_mobile))

        page.set_viewport_size({"width": 390, "height": 844})
        page.evaluate("() => { document.querySelector('#collection-table-scroll').scrollLeft = 0; }")
        page.wait_for_timeout(120)
        body_overflow = page.evaluate(
            "() => document.body.scrollWidth - document.body.clientWidth")
        mobile_offenders = page.evaluate("""() => [...document.querySelectorAll('body *')]
          .map((element) => {
            const box = element.getBoundingClientRect();
            return {
              selector: element.tagName.toLowerCase()
                + (element.id ? '#' + element.id : '')
                + (element.className && typeof element.className === 'string'
                  ? '.' + element.className.trim().replace(/\\s+/g, '.') : ''),
              right: Math.round(box.right), width: Math.round(box.width),
              scrollWidth: element.scrollWidth, clientWidth: element.clientWidth,
            };
          })
          .filter((item) => item.right > document.body.clientWidth + 1
            && item.right <= document.body.scrollWidth + 1)
          .sort((a, b) => b.right - a.right)
          .slice(0, 10)""")
        check("mobile layout does not scroll the page body horizontally", body_overflow <= 1,
              f"body overflow {body_overflow}px at 390px wide; offenders={mobile_offenders}")

        mobile_cards = page.evaluate("""() => {
          const card = document.querySelector('#rows tr:not(.yearsep)');
          const image = card.querySelector('td.img').getBoundingClientRect();
          const name = card.querySelector('.col-card').getBoundingClientRect();
          const finish = card.querySelector('.col-finish').getBoundingClientRect();
          const evidence = card.querySelector('.col-evidence').getBoundingClientRect();
          return {
            cardRight: card.getBoundingClientRect().right,
            viewportRight: document.documentElement.clientWidth,
            imageLeftOfName: image.right <= name.left + 1,
            finishBelowIdentity: finish.top >= name.bottom,
            evidenceBelowFinish: evidence.top >= finish.bottom,
          };
        }""")
        check("mobile cards place image, identity, finish and evidence in reading order",
              mobile_cards["cardRight"] <= mobile_cards["viewportRight"] + 1
              and mobile_cards["imageLeftOfName"]
              and mobile_cards["finishBelowIdentity"]
              and mobile_cards["evidenceBelowFinish"], str(mobile_cards))

        page.select_option("#mobile-sort-key", "name")
        mobile_names = page.locator("#rows tr:not(.yearsep):not(.rowdetail) .col-card").all_text_contents()
        check("the mobile sort control replaces sortable column headings",
              mobile_names == sorted(mobile_names, key=str.lower)
              and page.locator("#mobile-sort-direction").get_attribute("aria-label") == "Sort ascending",
              str(mobile_names[:5]))
        page.click("#mobile-sort-direction")
        mobile_names_desc = page.locator(
            "#rows tr:not(.yearsep):not(.rowdetail) .col-card").all_text_contents()
        check("the mobile sort control changes direction",
              mobile_names_desc == sorted(mobile_names_desc, key=str.lower, reverse=True)
              and page.locator("#mobile-sort-direction").get_attribute("aria-label") == "Sort descending",
              str(mobile_names_desc[:5]))
        page.select_option("#mobile-sort-key", "release")

        mobile_trigger = page.locator(".card-preview-trigger").first
        mobile_trigger.click()
        page.wait_for_timeout(120)
        mobile_preview = page.evaluate("""() => {
          const preview = document.querySelector('.card-preview');
          const box = preview.getBoundingClientRect();
          return {hidden: preview.hidden, left: box.left, right: box.right, width: box.width};
        }""")
        check("tapping a card opens a preview that fits the mobile viewport",
              not mobile_preview["hidden"] and mobile_preview["left"] >= 0
              and mobile_preview["right"] <= 390,
              str(mobile_preview))
        mobile_trigger.click()
        check("tapping the active card closes its preview",
              page.locator(".card-preview").evaluate("element => element.hidden"),
              "preview remained open after the second tap")

        # --- #121/#128: the card keeps the core cells and restates the rest per row ---
        narrow_columns = page.evaluate("""() => {
          const shown = (sel) => {
            const cell = document.querySelector('#rows tr:not(.rowdetail) ' + sel);
            return cell ? getComputedStyle(cell).display !== 'none' : null;
          };
          return {
            core: ['td.img', '.col-card', '.col-set', '.col-number', '.col-variant',
                   '.col-finish', '.col-evidence'].map(shown),
            withdrawn: ['.col-release', '.col-expansion', '.col-rarity', '.col-artist',
                        '.col-edition', '.col-pattern', '.col-marking', '.col-marking-role',
                        '.col-size', '.col-distribution', '.langcount', '.langcell'].map(shown),
            more: shown('.col-more'),
            detailRows: document.querySelectorAll('#rows tr.rowdetail').length,
          };
        }""")
        check("mobile cards keep only the core identity and evidence cells",
              all(narrow_columns["core"]) and not any(narrow_columns["withdrawn"])
              and narrow_columns["more"], str(narrow_columns))
        # Built on demand: a panel per row would double the table's rows for every reader.
        check("row detail panels are not rendered until they are opened",
              narrow_columns["detailRows"] == 0,
              f"{narrow_columns['detailRows']} detail rows existed before any disclosure was used")

        first_more = page.locator("#rows .rowmore").first
        first_more.click()
        page.wait_for_timeout(120)
        detail_open = page.evaluate("""() => {
          const button = document.querySelector('#rows .rowmore');
          const panel = document.getElementById(button.getAttribute('aria-controls'));
          const terms = panel ? [...panel.querySelectorAll('dt')].map((dt) => dt.textContent) : [];
          return {
            expanded: button.getAttribute('aria-expanded'),
            visible: panel ? !panel.hidden && getComputedStyle(panel).display !== 'none' : false,
            terms: terms,
            hasLanguages: terms.includes('Confirmed languages'),
            rowAfter: panel ? panel.previousElementSibling.contains(button) : false,
          };
        }""")
        check("opening a row disclosure reveals the withdrawn values beneath that row",
              detail_open["expanded"] == "true" and detail_open["visible"]
              and detail_open["hasLanguages"] and detail_open["rowAfter"]
              and len(detail_open["terms"]) >= 10, str(detail_open))

        first_more.click()
        page.wait_for_timeout(120)
        check("closing a row disclosure hides it again",
              page.evaluate("""() => {
                const button = document.querySelector('#rows .rowmore');
                return button.getAttribute('aria-expanded') === 'false'
                  && document.getElementById(button.getAttribute('aria-controls')).hidden;
              }"""),
              "the panel stayed open after the second press")

        # --- #122/#128: filters stack on a phone ---
        page.evaluate("scrollTo(0, 0)")
        page.wait_for_timeout(120)
        narrow_controls = page.evaluate("""() => {
          const fields = [...document.querySelectorAll('#collection .controls .row > .field')];
          const boxes = fields.map((field) => field.getBoundingClientRect());
          return {
            fields: boxes.length,
            // Stacked means every field starts at the same x and none share a line.
            sameLeft: boxes.every((box) => Math.abs(box.left - boxes[0].left) <= 1),
            distinctRows: new Set(boxes.map((box) => Math.round(box.top))).size === boxes.length,
          };
        }""")
        check("narrow viewport stacks the collection filter fields",
              narrow_controls["fields"] > 1 and narrow_controls["sameLeft"]
              and narrow_controls["distinctRows"], str(narrow_controls))
        # --- #123: section navigation collapses behind a disclosure on a phone ---
        nav_collapsed = page.evaluate("""() => ({
          toggleShown: getComputedStyle(document.querySelector('#nav-toggle')).display !== 'none',
          listShown: getComputedStyle(document.querySelector('#section-nav-list')).display !== 'none',
          open: document.querySelector('#section-nav-disclosure').open,
        })""")
        check("narrow viewport collapses the section navigation behind a toggle",
              nav_collapsed["toggleShown"] and not nav_collapsed["listShown"]
              and not nav_collapsed["open"], str(nav_collapsed))

        page.locator("#nav-toggle").click()
        page.wait_for_timeout(80)
        nav_opened = page.evaluate("""() => ({
          listShown: getComputedStyle(document.querySelector('#section-nav-list')).display !== 'none',
          open: document.querySelector('#section-nav-disclosure').open,
        })""")
        check("the section-navigation toggle opens the list and reports its state",
              nav_opened["listShown"] and nav_opened["open"], str(nav_opened))

        page.locator('#section-nav-list a[href="#methodology"]').click()
        page.wait_for_timeout(80)
        check("following a section link closes the navigation again",
              page.evaluate(
                  "() => document.querySelector('#section-nav-disclosure').open")
              is False,
              "the panel stayed open, so the target scrolled under it")

        # Leaving the breakpoint must restore the plain list — the toggle is display:none there and
        # could not undo a collapsed state.
        check_desktop_sources(page)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(120)
        nav_wide = page.evaluate("""() => ({
          toggleShown: getComputedStyle(document.querySelector('#nav-toggle')).display !== 'none',
          listShown: getComputedStyle(document.querySelector('#section-nav-list')).display !== 'none',
          open: document.querySelector('#section-nav-disclosure').open,
          links: document.querySelectorAll('#section-nav-list a').length,
        })""")
        check("a wide viewport restores the full section navigation",
              not nav_wide["toggleShown"] and nav_wide["listShown"] and nav_wide["open"]
              and nav_wide["links"] == 6,
              str(nav_wide))

        page.locator('#section-nav-list a[href="#about"]').click()
        page.wait_for_timeout(80)
        check("a desktop section link keeps the navigation open",
              page.evaluate("""() => {
                const disclosure = document.querySelector('#section-nav-disclosure');
                return disclosure.open
                  && getComputedStyle(document.querySelector('#section-nav-list')).display !== 'none';
              }"""),
              "the desktop section link closed the always-visible navigation")

        # --- #125: raw export of the current view ---
        page.evaluate("""() => {
          document.querySelector('#f-q').value = 'Jungle';
          document.querySelector('#f-q').dispatchEvent(new Event('input', {bubbles: true}));
        }""")
        page.wait_for_timeout(200)
        with page.expect_download() as download_info:
            page.locator("#export-tsv").click()
        download = download_info.value
        export_path = scratch / "export.tsv"
        download.save_as(export_path)
        exported = export_path.read_text(encoding="utf-8-sig")
        export_lines = [line for line in exported.splitlines() if line.strip()]
        export_header = export_lines[0].split("\t") if export_lines else []
        visible_after_filter = page.evaluate(
            "() => document.querySelectorAll('#rows tr:not(.yearsep):not(.rowdetail)').length")
        check("the export downloads a dated TSV of the filtered view",
              download.suggested_filename.startswith("snoredex-collection-")
              and download.suggested_filename.endswith(".tsv")
              and len(export_lines) - 1 == visible_after_filter,
              f"{download.suggested_filename}, {len(export_lines) - 1} data lines "
              f"for {visible_after_filter} visible rows")
        # Tabs are the whole reason this is TSV rather than CSV; a value containing one would
        # silently shift every later column of that row.
        check("the export is tab-separated with one column per language and no ragged rows",
              export_header[:4] == ["Release", "Card", "Set", "No."]
              and all(name in export_header for name in ("English", "Japanese"))
              and all(len(line.split("\t")) == len(export_header) for line in export_lines[1:]),
              f"header={export_header[:6]}… width={len(export_header)}")
        check("the export starts with a UTF-8 BOM so spreadsheets read the accents",
              export_path.read_bytes().startswith(b"\xef\xbb\xbf"),
              "no BOM; a double-clicked file falls back to the local codepage")

        browser.close()
        shutil.rmtree(scratch, ignore_errors=True)

    failures = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"[{'ok ' if ok else 'FAIL'}] {name}" + (f"\n       {detail}" if not ok and detail else ""))
    print(f"\n{len(results) - len(failures)}/{len(results)} browser checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

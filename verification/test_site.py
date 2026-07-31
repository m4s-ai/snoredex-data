#!/usr/bin/env python3
"""Browser tests for the public site (#7, #9, #10).

These drive the real page in Chromium rather than asserting on the generator's output, because
the behaviours the epic asks for — filtering, sorting, URL round-trip, year headings, checklist
download — only exist at runtime.

Run against the local file, exactly as a reader with a checkout would:

    python verification/test_site.py

Requires the pinned `playwright` dependency and its Chromium build. Missing prerequisites are a
test failure: a release gate that silently skips its browser contract is not a release gate.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
EXPECTED_ROWS = 204

# Every surface #43 enumerates, measured in both themes: (label, selector, property, mode,
# threshold). "text" measures the property against the element's own composited backdrop;
# "boundary" measures it against the backdrop behind the element, which is what a border or a
# focus ring actually sits on.
#
# Thresholds follow WCAG 2.2 AA: 4.5:1 for text (nothing here is large text — the biggest is the
# 26px masthead heading, asserted at the stricter figure anyway), 3:1 for the boundaries and state
# indicators of user interface components. Decorative separators — panel edges, row rules, the
# footer line — are deliberately absent: 1.4.11 covers what identifies a component or a state, and
# raising every divider to 3:1 would draw a heavy grid over a 204-row table. The frozen-pane edge
# is listed because it carries meaning; it tells the reader the column is pinned rather than cut.
THEME_SURFACES = [
    ("masthead heading", ".masthead h1", "color", "text", 4.5),
    ("masthead tagline", ".masthead .tagline", "color", "text", 4.5),
    ("theme toggle label", "#theme-toggle", "color", "text", 4.5),
    ("theme toggle border", "#theme-toggle", "borderTopColor", "boundary", 3.0),
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
    ("primary button text", "button.primary", "color", "text", 4.5),
    ("primary button edge", "button.primary", "borderTopColor", "boundary", 3.0),
    ("ghost button text", "button.ghost", "color", "text", 4.5),
    ("ghost button edge", "button.ghost", "borderTopColor", "boundary", 3.0),
    ("result count", "#count", "color", "text", 4.5),
    ("scroll hint", "#collection-scroll-hint", "color", "text", 4.5),
    ("scroll hint icon", ".scroll-hint .scroll-icon", "color", "text", 3.0),
    ("scroll button glyph", "#collection-scroll-right", "color", "text", 4.5),
    ("scroll button edge", "#collection-scroll-right", "borderTopColor", "boundary", 3.0),
    ("column heading", "#collection-table thead th button.sort", "color", "text", 4.5),
    ("table cell", "#rows tr td:nth-child(3)", "color", "text", 4.5),
    ("clipped cell", "#rows .cell-clip", "color", "text", 4.5),
    ("year separator", "tr.yearsep td", "color", "text", 4.5),
    ("frozen column heading", "#collection-table th.corr", "color", "text", 4.5),
    ("frozen column link", "#rows td.corr a", "color", "text", 4.5),
    ("frozen column edge", "#rows td.corr", "borderLeftColor", "boundary", 3.0),
    ("confirmed pill", ".pill.confirmed", "color", "text", 4.5),
    ("marketplace pill", ".pill.marketplace-claimed", "color", "text", 4.5),
    ("pending pill", ".pill.pending", "color", "text", 4.5),
    ("not-applicable pill", ".pill.not-applicable", "color", "text", 4.5),
    ("treatment badge", "#rows .treatment", "color", "text", 4.5),
    ("language present", "td.langcell.yes", "color", "text", 4.5),
    ("language absent", "td.langcell.no", "color", "text", 4.5),
    ("language count", "td.langcount", "color", "text", 4.5),
    ("legend text", ".language-legend", "color", "text", 4.5),
    ("legend present state", ".language-legend .yes", "color", "text", 4.5),
    ("legend absent state", ".language-legend .no", "color", "text", 4.5),
    ("checklist preview", ".builder .preview", "color", "text", 4.5),
    ("sources table text", "table.sources td", "color", "text", 4.5),
    ("sources list link", "details.sourcelist li a", "color", "text", 4.5),
    ("footer text", "footer.sitefoot", "color", "text", 4.5),
]

# Computed backgrounds are frequently transparent or semi-transparent — the overflow toolbar uses
# color-mix over the panel — so the backdrop is composited down to an opaque rgb() rather than
# handing a partially transparent colour to the ratio calculation.
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


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed; run: pip install -r requirements.txt", file=sys.stderr)
        return 1

    url = INDEX.as_uri()
    with sync_playwright() as p:
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

        exs_rows = page.evaluate("""() => JSON.parse(
          document.getElementById('data-rows').textContent
        ).filter(r => r.setCode === 'EXS')""")
        check("both dated EXS physical variants appear in 1998",
              len(exs_rows) == 2
              and [row["dateDisplay"] for row in exs_rows] == ["1998-03-23", "1998-12-04"]
              and [row["variant"] for row in exs_rows] == ["V1", "V2"]
              and [row["image"] is not None for row in exs_rows] == [False, True]
              and len({row["rowId"] for row in exs_rows}) == 2,
              f"EXS rows: {exs_rows}")

        # --- complete light/dark themes (#43) ---
        source_html = INDEX.read_text(encoding="utf-8")
        check("theme selection runs before the stylesheet loads",
              source_html.find('localStorage.getItem("snoredex-theme")')
              < source_html.find('<link rel="stylesheet"'),
              "the theme bootstrap must precede CSS to avoid an opposite-theme flash")

        for scheme in ("light", "dark"):
            theme_context = browser.new_context(color_scheme=scheme)
            theme_context.add_init_script("""
              window.__snoredexThemeAtFirstFrame = new Promise((resolve) => {
                requestAnimationFrame(() => resolve(document.documentElement.dataset.theme));
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
              const primary = getComputedStyle(document.querySelector('button.primary'));
              const control = getComputedStyle(document.querySelector('.field select'));
              const panel = getComputedStyle(document.querySelector('.controls'));
              const absent = getComputedStyle(document.querySelector('td.langcell.no'));
              const body = getComputedStyle(document.body);
              const toggle = document.querySelector('#theme-toggle');
              const toggleBox = toggle.getBoundingClientRect();
              return {
                theme: document.documentElement.dataset.theme,
                colorScheme: getComputedStyle(document.documentElement).colorScheme,
                pressed: toggle.getAttribute('aria-pressed'),
                label: toggle.getAttribute('aria-label'),
                toggleWidth: toggleBox.width,
                toggleHeight: toggleBox.height,
                primaryForeground: primary.color,
                primaryBackground: primary.backgroundColor,
                controlBorder: control.borderTopColor,
                panelBackground: panel.backgroundColor,
                absentForeground: absent.color,
                bodyBackground: body.backgroundColor,
              };
            }""")
            check(f"{scheme} mode follows the initial system preference before first paint",
                  theme_metrics["theme"] == scheme and first_frame_theme == scheme
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

            # 2.4.11: a focus ring that lands under the sticky furniture is not visible focus.
            # The filtered table is too short to scroll into, so restore the full list first.
            theme_page.fill("#f-q", "")
            theme_page.wait_for_timeout(150)
            theme_page.evaluate("""() => {
              document.querySelector('#collection-table-frame').scrollIntoView();
              scrollBy(0, 600);
            }""")
            theme_page.wait_for_timeout(150)
            obscured = theme_page.evaluate("""() => {
              const overlay = document.querySelector('#collection-sticky-header');
              const tools = document.querySelector('#collection-scroll-tools');
              const band = overlay.classList.contains('is-visible')
                ? overlay.getBoundingClientRect()
                : tools.getBoundingClientRect();
              const covers = (box) => box.top < band.bottom && box.bottom > band.top;
              const targets = [...document.querySelectorAll(
                '#rows td.corr a, #rows .cell-clip[data-clipped="true"]')];
              // Start from something the furniture is already covering, so the assertion measures
              // the scroll adjustment rather than a row that happened to sit clear of it.
              const start = targets.find((element) => covers(element.getBoundingClientRect()));
              if (!start) return {missing: true};
              start.focus();
              const box = start.getBoundingClientRect();
              return {
                covered: covers(box),
                inViewport: box.top >= 0 && box.bottom <= innerHeight,
                focusTop: box.top, bandTop: band.top, bandBottom: band.bottom,
              };
            }""")
            check(f"keyboard focus in the table clears the sticky furniture in {scheme} mode",
                  not obscured.get("missing")
                  and not obscured["covered"] and obscured["inViewport"],
                  str(obscured))
            theme_page.evaluate("scrollTo(0, 0)")

            check(f"theme toggle exposes state and an adequate target in {scheme} mode",
                  theme_metrics["pressed"] == str(scheme == "dark").lower()
                  and scheme in theme_metrics["label"]
                  and theme_metrics["toggleWidth"] >= 44
                  and theme_metrics["toggleHeight"] >= 44,
                  str(theme_metrics))

            if scheme == "dark":
                toggle = theme_page.locator("#theme-toggle")
                toggle.focus()
                toggle.press("Enter")
                toggled = theme_page.evaluate("""() => ({
                  theme: document.documentElement.dataset.theme,
                  saved: localStorage.getItem('snoredex-theme'),
                  pressed: document.querySelector('#theme-toggle').getAttribute('aria-pressed'),
                })""")
                restored_page = theme_context.new_page()
                restored_page.goto(url)
                restored = restored_page.evaluate("""() => ({
                  theme: document.documentElement.dataset.theme,
                  saved: localStorage.getItem('snoredex-theme'),
                })""")
                check("keyboard theme toggle persists an explicit user preference",
                      toggled == {"theme": "light", "saved": "light", "pressed": "false"}
                      and restored == {"theme": "light", "saved": "light"},
                      f"toggled={toggled} restored={restored}")
                restored_page.close()
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
        page.wait_for_timeout(120)
        wide_layout = page.evaluate("""() => {
          const wrap = document.querySelector('.wrap');
          const scroller = document.querySelector('#collection-table-scroll');
          const tools = document.querySelector('#collection-scroll-tools');
          return {
            wrap: Math.round(wrap.getBoundingClientRect().width),
            overflow: scroller.scrollWidth - scroller.clientWidth,
            toolsHidden: tools.hidden,
          };
        }""")
        check("wide monitors use the available viewport width", wide_layout["wrap"] >= 2500,
              f"content shell is only {wide_layout['wrap']}px at a 2560px viewport")
        check("the complete collection matrix fits a 2560px viewport",
              wide_layout["overflow"] <= 1 and wide_layout["toolsHidden"],
              f"overflow={wide_layout['overflow']} toolsHidden={wide_layout['toolsHidden']}")

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
        check("wide cells use allocated table width instead of avoidably clipping",
              clipping["avoidable"] == 0 and clipping["clipped"] < 250,
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

        # At narrower widths some overflow is unavoidable. It must be announced at the top of the
        # table, with working controls, instead of exposing only a scrollbar after 203 rows.
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(120)
        overflow_start = page.evaluate("""() => ({
          overflow: document.querySelector('#collection-table-scroll').scrollWidth
            - document.querySelector('#collection-table-scroll').clientWidth,
          toolsHidden: document.querySelector('#collection-scroll-tools').hidden,
          rightDisabled: document.querySelector('#collection-scroll-right').disabled,
          hint: document.querySelector('.scroll-hint-text').textContent,
        })""")
        check("horizontal overflow is clearly indicated above the table",
              overflow_start["overflow"] > 0 and not overflow_start["toolsHidden"]
              and not overflow_start["rightDisabled"] and "right" in overflow_start["hint"],
              str(overflow_start))
        page.click("#collection-scroll-right")
        page.wait_for_timeout(500)
        overflow_after_click = page.evaluate("""() => ({
          left: document.querySelector('#collection-table-scroll').scrollLeft,
          leftDisabled: document.querySelector('#collection-scroll-left').disabled,
        })""")
        check("overflow controls scroll the table in both directions",
              overflow_after_click["left"] > 0 and not overflow_after_click["leftDisabled"],
              str(overflow_after_click))
        page.eval_on_selector("#collection-table-scroll", "element => { element.scrollLeft = 0; }")
        page.wait_for_timeout(80)

        page.set_viewport_size({"width": 1440, "height": 900})
        table_start = page.eval_on_selector(
            "#collection-table-frame", "element => element.getBoundingClientRect().top + scrollY"
        )
        page.evaluate("position => scrollTo(0, position + 180)", table_start)
        page.wait_for_timeout(120)
        sticky_header = page.evaluate("""() => {
          const overlay = document.querySelector('#collection-sticky-header');
          const overlayBox = overlay.getBoundingClientRect();
          const toolbarBox = document.querySelector('#collection-scroll-tools').getBoundingClientRect();
          const scrollerBox = document.querySelector('#collection-table-scroll').getBoundingClientRect();
          return {
            visible: getComputedStyle(overlay).display !== 'none',
            top: overlayBox.top,
            bottom: overlayBox.bottom,
            left: overlayBox.left,
            right: overlayBox.right,
            toolbarBottom: toolbarBox.bottom,
            scrollerLeft: scrollerBox.left,
            scrollerRight: scrollerBox.right,
            release: overlay.querySelector('th:nth-child(2)').innerText.trim(),
          };
        }""")
        check("collection headers remain visible below the sticky overflow toolbar",
              sticky_header["visible"]
              and abs(sticky_header["top"] - sticky_header["toolbarBottom"]) <= 1
              and abs(sticky_header["left"] - sticky_header["scrollerLeft"]) <= 1
              and abs(sticky_header["right"] - sticky_header["scrollerRight"]) <= 1
              and sticky_header["release"] == "Release",
              str(sticky_header))
        page.eval_on_selector("#collection-table-scroll", "element => { element.scrollLeft = 500; }")
        page.wait_for_timeout(80)
        sticky_scroll = page.evaluate("""() => ({
          transform: getComputedStyle(document.querySelector('#collection-sticky-header table')).transform,
          reportRight: document.querySelector('.table-sticky-correction').getBoundingClientRect().right,
          overlayRight: document.querySelector('#collection-sticky-header').getBoundingClientRect().right,
        })""")
        check("sticky headings follow horizontal scrolling and retain the Report heading",
              "-500" in sticky_scroll["transform"]
              and abs(sticky_scroll["reportRight"] - sticky_scroll["overlayRight"]) <= 1,
              str(sticky_scroll))
        page.eval_on_selector("#collection-table-scroll", "element => { element.scrollLeft = 0; }")
        page.wait_for_timeout(80)

        # A heading that covers the table owes the user the interactions it hides. Sorting from the
        # sticky copy must sort, and a click anywhere on it must not reach the row underneath —
        # otherwise aiming at a column heading expands a cell or opens a card preview instead.
        sticky_sort = page.evaluate("""() => {
          const overlay = document.querySelector('#collection-sticky-header');
          const button = overlay.querySelector('th[data-key="name"] button.sort');
          const box = button.getBoundingClientRect();
          const point = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
          return {
            reaches: overlay.contains(point),
            x: box.x + box.width / 2,
            y: box.y + box.height / 2,
            hit: point ? point.tagName + '.' + point.className : null,
          };
        }""")
        check("sticky headings receive their own clicks instead of passing them through",
              sticky_sort["reaches"], str(sticky_sort))
        page.mouse.click(sticky_sort["x"], sticky_sort["y"])
        page.wait_for_timeout(120)
        sticky_sorted = page.evaluate("""() => ({
          aria: document.querySelector('#collection-table thead th[data-key="name"]')
            .getAttribute('aria-sort'),
          overlayAria: document.querySelector('#collection-sticky-header th[data-key="name"]')
            .getAttribute('aria-sort'),
          names: [...document.querySelectorAll('#rows tr td:nth-child(3)')]
            .slice(0, 12).map((cell) => cell.innerText.trim()),
          expanded: document.querySelectorAll('.cell-clip.is-expanded').length,
          preview: !document.querySelector('.card-preview').hidden,
        })""")
        check("sorting from the sticky heading sorts the table and mirrors its state",
              sticky_sorted["aria"] == "ascending"
              and sticky_sorted["overlayAria"] == "ascending"
              and sticky_sorted["names"] == sorted(sticky_sorted["names"], key=str.lower)
              and sticky_sorted["expanded"] == 0
              and not sticky_sorted["preview"],
              str(sticky_sorted))
        page.click('th[data-key="release"] button.sort')
        page.wait_for_timeout(120)
        page.evaluate("scrollTo(0, 0)")
        page.eval_on_selector("#collection-table-scroll", "element => { element.scrollLeft = 0; }")
        page.wait_for_timeout(80)

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

        sourced_dates = page.evaluate("""() => {
          const rows = JSON.parse(document.getElementById('data-rows').textContent);
          return Object.fromEntries(['G2', 'PCG9', 'DF', 'CS2aC'].map(code => {
            const row = rows.find(candidate => candidate.setCode === code);
            return [code, {date: row.dateDisplay, source: row.dateSource}];
          }));
        }""")
        expected_dates = {
            "G2": ("1999-06-25", "Gym Challenge (TCG)", "jarelease"),
            "PCG9": ("2006-06-29", "EX Dragon Frontiers (TCG)", "jarelease"),
            "DF": ("2006-11-08", "EX Dragon Frontiers (TCG)", "enrelease"),
            "CS2aC": ("2023-08-18", "Vivid Portrayals (ATCG)", "release"),
        }
        release_projection_ok = all(
            sourced_dates[code]["date"] == date
            and sourced_dates[code]["source"]["page"] == source_page
            and sourced_dates[code]["source"]["field"] == field
            for code, (date, source_page, field) in expected_dates.items()
        )
        check("Bulbapedia market-specific release dates reach the site projection",
              release_projection_ok, str(sourced_dates))

        page.fill("#f-q", "challenge from the darkness")
        page.wait_for_timeout(120)
        release_link = page.locator("#rows tr:not(.yearsep) .release-source")
        check("sourced release dates link to the reviewed Bulbapedia page",
              release_link.count() == 1
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
        check("technical mirror-holo evidence remains in the embedded audit projection",
              len(technical_mirror_rows) == 4
              and all("reverse-holo" in row["finishes"] and "mirror-holo" not in row["finishes"]
                      for row in technical_mirror_rows),
              f"technical mirror rows: {[(r['rowId'], r['finishes']) for r in technical_mirror_rows]}")

        page.select_option("#f-finish", ["reverse-holo"])
        page.wait_for_timeout(120)
        mirror_family_rows = page.locator("#rows tr:not(.yearsep)").filter(has_text="xsv2a")
        check("Reverse Holo filter includes Poké Ball and Master Ball product rows",
              mirror_family_rows.count() == 2
              and all("Reverse Holo" in text for text in mirror_family_rows.all_text_contents()),
              f"xsv2a rows under Reverse Holo: {mirror_family_rows.all_text_contents()}")
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

        # Language tri-state: absent must be the complement of present.
        page.select_option("#f-lang-JA", "present")
        page.wait_for_timeout(120)
        present = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        page.select_option("#f-lang-JA", "absent")
        page.wait_for_timeout(120)
        absent = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        check("language tri-state present/absent partitions the rows",
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
        check("language cells expose named present and absent states",
              language_accessibility["presentLabel"].endswith(": present")
              and language_accessibility["absentLabel"].endswith(": absent")
              and "present" in language_accessibility["presentSnapshot"]
              and "absent" in language_accessibility["absentSnapshot"],
              str(language_accessibility))
        check("language symbols have a visible non-color legend",
              "✓ present" in language_accessibility["legend"]
              and "— absent" in language_accessibility["legend"],
              language_accessibility["legend"])

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
            "#rows tr:not(.yearsep) td:nth-child(6)", "els => els.map(e => e.textContent)")
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
        page.wait_for_timeout(150)
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

        # --- the contribute section is the front door for public reviewers ---
        check("a contribute section explains how to report a correction",
              page.locator("#contribute").count() == 1
              and page.locator('nav.sections a[href="#contribute"]').count() == 1,
              "the site must state how corrections are reported, not only link them per row")
        contribute_text = (page.text_content("#contribute") or "").lower()
        check("the contribute section states the positive-evidence rule",
              "positive evidence" in contribute_text
              and "not proof of absence" in contribute_text
              and "never unavailable" in contribute_text,
              "a reviewer must learn the evidence rule before filing, not after being rejected")
        contribute_links = page.eval_on_selector_all(
            "#contribute a", "els => els.map(e => e.getAttribute('href'))")
        check("the contribute section links the guide, the ladder and the open questions",
              {"CONTRIBUTING.md", "verification/FINISH_SOURCES.md",
               "verification/open-items.html"} <= set(contribute_links),
              f"contribute links: {contribute_links}")

        # --- checklist builder ---
        preview = page.text_content("#cl-preview")
        check("checklist preview reports an item count", "checklist items" in (preview or ""),
              preview or "")
        checklist_finish_options = page.eval_on_selector_all(
            "#cl-finishes option", "els => els.map(e => [e.value, e.textContent])")
        check("checklist selector aggregates mirror treatments under Reverse Holo",
              ["reverse-holo", "Reverse Holo"] in checklist_finish_options
              and not any(value == "mirror-holo" for value, _ in checklist_finish_options)
              and "Reverse Holo treatments" in (preview or ""),
              f"options={checklist_finish_options}; preview={preview}")

        # A filtered physical variant must select only its own checklist item, even though both
        # EXS versions share one canonical Cardmarket product row.
        page.fill("#f-q", "EXS")
        page.select_option("#f-marking", ["Uncommon rarity symbol"])
        page.select_option("#cl-scope", "filtered")
        page.wait_for_timeout(150)
        exs_scoped = page.text_content("#cl-preview") or ""
        check("filtered EXS V1 scope selects only its physical checklist item",
              int(exs_scoped.split()[0]) == 1, exs_scoped)
        page.click("#reset")
        page.select_option("#cl-scope", "all")
        page.wait_for_timeout(150)

        # Scope must follow the *filtered* rows, so filter first, then switch scope.
        page.select_option("#f-edition", ["1st Edition"])
        page.wait_for_timeout(150)
        page.select_option("#cl-scope", "filtered")
        page.wait_for_timeout(150)
        scoped = page.text_content("#cl-preview")
        scoped_n = int(scoped.split()[0].replace(",", ""))
        all_n = int(preview.split()[0].replace(",", ""))
        check("checklist scope follows the filtered rows", 0 < scoped_n < all_n,
              f"all={all_n} filtered={scoped_n}")

        # And it must key on stable row IDs, so sorting the table cannot change the selection.
        page.click('th[data-key="name"] button.sort')
        page.wait_for_timeout(150)
        after_sort = page.text_content("#cl-preview")
        check("checklist scope is unaffected by sorting", after_sort == scoped,
              f"before={scoped!r} after={after_sort!r}")

        page.click("#reset")
        page.wait_for_timeout(150)
        page.select_option("#cl-scope", "all")
        page.wait_for_timeout(150)

        with page.expect_download() as download_info:
            page.click("#cl-download")
        download = download_info.value
        scratch = Path(tempfile.mkdtemp(prefix="snoredex-site-test-"))
        target = scratch / "checklist-A4.html"
        download.save_as(target)
        content = target.read_text(encoding="utf-8")
        check("checklist downloads with a dated filename",
              download.suggested_filename.startswith("snoredex-checklist-"),
              download.suggested_filename)
        check("checklist is standalone with no external requests",
              "http://" not in content.replace("http://www.w3.org", "")
              and "<script src" not in content,
              "generated checklist must work offline")
        check("checklist marks unresolved items as not confirmed",
              "finish unresolved" in content, "unresolved placeholders must be visibly marked")
        check("checklist carries the licence and evidence caveat",
              "CC BY-NC-SA" in content and "not operative" in content
              and "never that a printing does not exist" in content,
              "notice block missing")
        checkbox_count = content.count('class="cb"')
        check("checklist has an ownership checkbox per item",
              checkbox_count > 100, f"{checkbox_count} checkboxes")
        checklist_id_count = content.count('data-checklist-id="')
        check("every printed line carries its stable checklist ID",
              checklist_id_count == checkbox_count,
              f"{checklist_id_count} IDs for {checkbox_count} checkboxes")
        check("downloaded checklist labels patterned mirror treatments as Reverse Holo",
              "Reverse Holo" in content and "Poké Ball" in content and "Master Ball" in content,
              "Reverse Holo family or its named treatments are missing")
        check("downloaded checklist retains deterministic finish-family grouping",
              content.count('data-finish-group-id="') == checkbox_count,
              "every physical line must keep both its stable item ID and family group ID")
        check("checklist repeats semantic headings when printing",
              "<thead>" in content and "Checklist ID</th>" in content
              and "thead{display:table-header-group}" in content,
              "repeatable table headings missing")
        check("checklist sets the selected A4 page size",
              "@page{size:A4;" in content, "A4 print CSS missing")

        page.select_option("#cl-paper", "Letter")
        with page.expect_download() as letter_download_info:
            page.click("#cl-download")
        letter_download = letter_download_info.value
        letter_target = scratch / "checklist-Letter.html"
        letter_download.save_as(letter_target)
        letter_content = letter_target.read_text(encoding="utf-8")
        check("checklist sets the selected US Letter page size",
              "@page{size:Letter;" in letter_content, "Letter print CSS missing")

        # --- print smoke tests on both paper sizes ---
        # A4 is 794 CSS px at 96dpi, US Letter 816. Emulating print media and clamping the
        # viewport to the paper width is what catches a table that silently truncates on paper.
        PAPER = {"A4": 794, "Letter": 816}
        for paper, width in PAPER.items():
            page.evaluate("""() => {
              document.documentElement.dataset.theme = 'dark';
              document.documentElement.style.colorScheme = 'dark';
            }""")
            page.emulate_media(media="print")
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

        for paper, width in PAPER.items():
            checklist_page = browser.new_page()
            checklist_page.goto((target if paper == "A4" else letter_target).as_uri())
            checklist_page.emulate_media(media="print")
            checklist_page.set_viewport_size({"width": width, "height": 1000})
            checklist_page.wait_for_timeout(120)
            overflow = checklist_page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"downloaded checklist prints without horizontal overflow ({paper})",
                  overflow <= 1, f"overflow {overflow}px at {width}px")
            checklist_page.close()

        # Adversarial fixture: future source text must remain text, never active markup or an
        # attribute breakout. This drives the generated page with the production JavaScript.
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
        checklist_pattern = re.compile(
            r'(<script type="application/json" id="data-checklist">)(.*?)(</script>)', re.S
        )
        checklist_match = checklist_pattern.search(hostile_html)
        hostile_checklist = json.loads(checklist_match.group(2)) if checklist_match else []
        checklist_payload = (
            '<img id="xss-checklist-probe" src=x onerror="window.__snoredexXss=1">'
        )
        hostile_checklist[0]["edition"] = checklist_payload
        hostile_checklist[0]["image"] = 'x" onerror="window.__snoredexXss=1'
        checklist_encoded = json.dumps(
            hostile_checklist, ensure_ascii=False, separators=(",", ":")
        ).replace("</", "<\\/")
        hostile_html = checklist_pattern.sub(
            lambda found: found.group(1) + checklist_encoded + found.group(3),
            hostile_html,
            count=1,
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

        with hostile_page.expect_download() as hostile_download_info:
            hostile_page.click("#cl-download")
        hostile_target = scratch / "hostile-checklist.html"
        hostile_download_info.value.save_as(hostile_target)
        hostile_checklist_page = browser.new_page()
        hostile_checklist_page.goto(hostile_target.as_uri())
        checklist_executed = hostile_checklist_page.evaluate("window.__snoredexXss === 1")
        checklist_markup = hostile_checklist_page.locator("#xss-checklist-probe").count()
        check("source-derived checklist values cannot inject DOM markup",
              not checklist_executed and checklist_markup == 0,
              f"executed={checklist_executed} injected_nodes={checklist_markup}")
        hostile_checklist_page.close()
        hostile_page.close()

        page.emulate_media(media="screen")
        page.evaluate("""() => {
          document.documentElement.dataset.theme = 'light';
          document.documentElement.style.colorScheme = 'light';
        }""")
        page.set_viewport_size({"width": 1280, "height": 900})

        # --- mobile layout ---
        page.set_viewport_size({"width": 320, "height": 700})
        page.wait_for_timeout(120)
        narrow_mobile = page.evaluate("""() => ({
          bodyOverflow: document.documentElement.scrollWidth
            - document.documentElement.clientWidth,
          tableOverflow: document.querySelector('#collection-table-scroll').scrollWidth
            - document.querySelector('#collection-table-scroll').clientWidth,
          toolsHidden: document.querySelector('#collection-scroll-tools').hidden,
          toggleWidth: document.querySelector('#theme-toggle').getBoundingClientRect().width,
          toggleHeight: document.querySelector('#theme-toggle').getBoundingClientRect().height,
        })""")
        check("320px layout reflows without body overflow and retains table affordances",
              narrow_mobile["bodyOverflow"] <= 1
              and narrow_mobile["tableOverflow"] > 0
              and not narrow_mobile["toolsHidden"]
              and narrow_mobile["toggleWidth"] >= 44
              and narrow_mobile["toggleHeight"] >= 44,
              str(narrow_mobile))

        page.set_viewport_size({"width": 390, "height": 844})
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

        mobile_overflow = page.evaluate("""() => ({
          overflow: document.querySelector('#collection-table-scroll').scrollWidth
            - document.querySelector('#collection-table-scroll').clientWidth,
          toolsHidden: document.querySelector('#collection-scroll-tools').hidden,
          hint: document.querySelector('.scroll-hint-text').textContent,
        })""")
        check("mobile users receive the horizontal-scroll indication",
              mobile_overflow["overflow"] > 0 and not mobile_overflow["toolsHidden"]
              and "right" in mobile_overflow["hint"], str(mobile_overflow))

        mobile_table_start = page.eval_on_selector(
            "#collection-table-frame", "element => element.getBoundingClientRect().top + scrollY"
        )
        page.evaluate("position => scrollTo(0, position + 180)", mobile_table_start)
        page.wait_for_timeout(120)
        mobile_sticky = page.evaluate("""() => {
          const overlay = document.querySelector('#collection-sticky-header').getBoundingClientRect();
          const toolbar = document.querySelector('#collection-scroll-tools').getBoundingClientRect();
          return {
            visible: getComputedStyle(document.querySelector('#collection-sticky-header')).display
              !== 'none',
            top: overlay.top,
            toolbarBottom: toolbar.bottom,
            release: document.querySelector('#collection-sticky-header th:nth-child(2)')
              .innerText.trim(),
          };
        }""")
        check("sticky collection headings remain visible on mobile",
              mobile_sticky["visible"]
              and abs(mobile_sticky["top"] - mobile_sticky["toolbarBottom"]) <= 1
              and mobile_sticky["release"] == "Release",
              str(mobile_sticky))

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

        browser.close()
        shutil.rmtree(scratch, ignore_errors=True)

    failures = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"[{'ok ' if ok else 'FAIL'}] {name}" + (f"\n       {detail}" if not ok and detail else ""))
    print(f"\n{len(results) - len(failures)}/{len(results)} browser checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

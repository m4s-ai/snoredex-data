#!/usr/bin/env python3
"""Browser tests for the public site (#7, #9, #10).

These drive the real page in Chromium rather than asserting on the generator's output, because
the behaviours the epic asks for — filtering, sorting, URL round-trip, year headings, checklist
download — only exist at runtime.

Run against the local file, exactly as a reader with a checkout would:

    python verification/test_site.py

Requires `playwright` and the Chromium already present in this image. Skips with a clear message
if the browser is unavailable, so the suite never fails for the wrong reason.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed; skipping browser tests")
        print("  pip install playwright")
        return 0

    url = INDEX.as_uri()
    with sync_playwright() as p:
        # The image ships a pinned Chromium that may not match the pip playwright build's
        # expected revision, so prefer whatever is actually on disk over the bundled default.
        candidates = sorted(Path("/opt/pw-browsers").glob("chromium*/chrome-linux/chrome"))
        browser = None
        for candidate in candidates:
            try:
                browser = p.chromium.launch(executable_path=str(candidate))
                break
            except Exception:
                continue
        if browser is None:
            try:
                browser = p.chromium.launch()
            except Exception as error:  # pragma: no cover - environment dependent
                print(f"chromium unavailable, skipping browser tests: {error}")
                return 0

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
        check("all rows render", total == 203, f"data has {total} rows")

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

        count_text = page.text_content("#count")
        check("shown/total count is displayed", "203" in (count_text or ""), count_text or "")

        # --- filtering ---
        page.fill("#f-q", "jungle")
        page.wait_for_timeout(120)
        filtered = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        check("global search filters rows", 0 < filtered < 203, f"{filtered} rows for 'jungle'")

        page.fill("#f-q", "")
        page.wait_for_timeout(120)

        # Language tri-state: absent must be the complement of present.
        page.select_option("#f-lang-JA", "present")
        page.wait_for_timeout(120)
        present = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        page.select_option("#f-lang-JA", "absent")
        page.wait_for_timeout(120)
        absent = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        check("language tri-state present/absent partitions the rows",
              present + absent == 203 and present > 0 and absent > 0,
              f"present={present} absent={absent} total=203")

        page.select_option("#f-lang-JA", "")
        page.wait_for_timeout(120)

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
        check("reset restores the unfiltered chronological view", reset_rows == 203,
              f"{reset_rows} rows after reset")

        # --- correction links are stable, one per row ---
        links = page.eval_on_selector_all(
            "#rows td.corr a", "els => els.map(e => e.getAttribute('href'))")
        check("exactly one correction link per row", len(links) == 203, f"{len(links)} links")
        # Links now deep-link into the generated issue form (#20) with the row identity in
        # query parameters, rather than pasting a prose body. Identity must still be the stable
        # rowId, never the rendered position.
        check("every correction link targets the correction issue form",
              all("template=printing-correction.yml" in href for href in links),
              "correction links must open the generated form")
        check("every correction link prefills the stable row id",
              all("row-id=" in href for href in links),
              "correction links must carry rowId, not the generated row number")

        # --- checklist builder ---
        preview = page.text_content("#cl-preview")
        check("checklist preview reports an item count", "checklist items" in (preview or ""),
              preview or "")

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
        target = Path("/tmp/claude-0/checklist-test.html")
        target.parent.mkdir(parents=True, exist_ok=True)
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
              "CC BY-NC-SA" in content and "never that a printing does not exist" in content,
              "notice block missing")
        checkbox_count = content.count('class="cb"')
        check("checklist has an ownership checkbox per item",
              checkbox_count > 100, f"{checkbox_count} checkboxes")
        check("checklist sets A4 page size with print styles",
              "@page" in content and "A4" in content, "print CSS missing")

        # --- print smoke tests on both paper sizes ---
        # A4 is 794 CSS px at 96dpi, US Letter 816. Emulating print media and clamping the
        # viewport to the paper width is what catches a table that silently truncates on paper.
        PAPER = {"A4": 794, "Letter": 816}
        for paper, width in PAPER.items():
            page.emulate_media(media="print")
            page.set_viewport_size({"width": width, "height": 1000})
            page.wait_for_timeout(120)
            overflow = page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"collection page prints without horizontal overflow ({paper})",
                  overflow <= 1, f"overflow {overflow}px at {width}px")

        checklist_page = browser.new_page()
        checklist_page.goto(target.as_uri())
        for paper, width in PAPER.items():
            checklist_page.emulate_media(media="print")
            checklist_page.set_viewport_size({"width": width, "height": 1000})
            checklist_page.wait_for_timeout(120)
            overflow = checklist_page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"downloaded checklist prints without horizontal overflow ({paper})",
                  overflow <= 1, f"overflow {overflow}px at {width}px")
        checklist_page.close()

        page.emulate_media(media="screen")
        page.set_viewport_size({"width": 1280, "height": 900})

        # --- mobile layout ---
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(120)
        body_overflow = page.evaluate(
            "() => document.body.scrollWidth - document.body.clientWidth")
        check("mobile layout does not scroll the page body horizontally", body_overflow <= 1,
              f"body overflow {body_overflow}px at 390px wide")

        browser.close()

    failures = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"[{'ok ' if ok else 'FAIL'}] {name}" + (f"\n       {detail}" if not ok and detail else ""))
    print(f"\n{len(results) - len(failures)}/{len(results)} browser checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

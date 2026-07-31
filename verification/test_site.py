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

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


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
        check("exact/approximate release status is filterable", 0 < approximate < 203,
              f"{approximate} approximate rows")
        page.select_option("#f-dateStatus", [])
        page.wait_for_timeout(120)

        first_name = page.evaluate(
            "JSON.parse(document.getElementById('data-rows').textContent)[0].name"
        )
        page.select_option("#f-name", [first_name])
        page.wait_for_timeout(120)
        named = page.eval_on_selector_all("#rows tr:not(.yearsep)", "els => els.length")
        check("card name has an exact field filter", 0 < named < 203,
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
            page.emulate_media(media="print")
            page.set_viewport_size({"width": width, "height": 1000})
            page.wait_for_timeout(120)
            overflow = page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"collection page prints without horizontal overflow ({paper})",
                  overflow <= 1, f"overflow {overflow}px at {width}px")

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
        page.set_viewport_size({"width": 1280, "height": 900})

        # --- mobile layout ---
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

        browser.close()
        shutil.rmtree(scratch, ignore_errors=True)

    failures = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"[{'ok ' if ok else 'FAIL'}] {name}" + (f"\n       {detail}" if not ok and detail else ""))
    print(f"\n{len(results) - len(failures)}/{len(results)} browser checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

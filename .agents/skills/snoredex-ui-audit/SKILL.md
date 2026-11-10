---
name: snoredex-ui-audit
description: Audit the generated static Snoredex UI for responsive layout, accessibility, interaction, dark mode, print and image behavior, or inspect the artwork records in data/images.json for issue-based corrections. The embedded browser proposal interface is retired.
---

<!-- doc: role=static-UI audit and artwork correction handoff workflow skill; stage=task -->

# Snoredex UI audit

Review artwork proposals or produce a reproducible review of the static site's behavior, according to the requested task. Keep generated output and data truth boundaries intact.

## UI-audit context

Read [AGENTS.md](../../../AGENTS.md). `index.html` and `gallery.html` are written by `scripts/build.py` from `templates/index.html`, `site/gallery.html` and `data/`; the styles and scripts are `site/app.css`, `site/app.js`, `site/gallery.css` and `site/gallery.js`. Trace defects to those sources instead of editing a built page.

The embedded artwork/proposal interface was retired by owner instruction on 2026-10-10.
For artwork findings, inspect `data/images.json` (assets, gallery images, artwork groups) and cite
exact item ids, source observations and images in the site's linked correction issue form. Do not offer the retired
browser editor or proposal export. Existing browser draft storage must not be deleted.
Corrections still require positive evidence and reviewed canonical integration; the browser never
writes catalogue truth. For ordinary site behavior, use the UI-audit procedure below.

## UI-audit workflow

1. Confirm whether the user requested audit-only or implementation. In audit-only mode, do not modify files or open issues.
2. Establish current branch, working-tree state, and the existing generated page. For audit-only work, serve that tree without regenerating files. When artifact preparation is authorized, build it with `python scripts/publish.py --out _site`.
3. Run `python verification/test_site.py` when Playwright and Chromium are available. Serve the site locally and use a browser for behavior the automated suite does not cover.
4. Test representative narrow mobile, tablet, desktop, and wide viewports. Check overflow discoverability, sticky behavior, clipped content, zoom, keyboard navigation, focus visibility, semantics, accessible names, contrast, reduced motion, dark mode, print, and enlarged card images.
5. Verify findings against the owning source and existing tests. Distinguish data defects from presentation defects and avoid speculative redesign advice.
6. Report each actionable finding with severity, reproduction steps, viewport or input method, affected source path, user impact, and the smallest likely repair. Report unavailable browser coverage explicitly.
7. If implementation is separately authorized, edit only the UI sources, add a focused regression (runtime behaviour in `verification/test_site.py`; a rule about the data in `scripts/check.py`), run `python scripts/regen.py` and `python verification/test_site.py`, then build a fresh artifact with `python scripts/publish.py --out _site` before running `python scripts/publish.py --out _site --verify`. Review the built diff.

Prioritize broken access, hidden data, and misleading presentation over cosmetic preference.

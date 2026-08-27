---
name: snoredex-ui-audit
description: Audit the generated Snoredex static UI for responsive layout, accessibility, interaction, dark mode, print, and image behavior. Use for UI review and reproducible browser findings; not for data-verdict research or redesign without a request.
---

<!-- doc: role=static-UI audit workflow skill; stage=task -->

# Snoredex UI audit

Produce a prioritized, reproducible review of the static site's actual behavior while keeping generated output and data truth boundaries intact.

## UI-audit context

Read [CLAUDE.md](../../../CLAUDE.md), [HANDOVER.md](../../../HANDOVER.md), and the site/consumer paths in [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md). `index.html` is generated: trace defects to the owning generator, styles, templates, or canonical data instead of editing it directly.

## UI-audit workflow

1. Confirm whether the user requested audit-only or implementation. In audit-only mode, do not modify files or open issues.
2. Establish current branch, working-tree state, and a reproducible local build. Use `python scripts/publish.py --out _site` when an isolated publication artifact is needed.
3. Run `python verification/test_site.py` when Playwright and Chromium are available. Serve the site locally and use a browser for behavior the automated suite does not cover.
4. Test representative narrow mobile, tablet, desktop, and wide viewports. Check overflow discoverability, sticky behavior, clipped content, zoom, keyboard navigation, focus visibility, semantics, accessible names, contrast, reduced motion, dark mode, print, and enlarged card images.
5. Verify findings against the owning source and existing tests. Distinguish data defects from presentation defects and avoid speculative redesign advice.
6. Report each actionable finding with severity, reproduction steps, viewport or input method, affected source path, user impact, and the smallest likely repair. Report unavailable browser coverage explicitly.
7. If implementation is separately authorized, edit only canonical UI sources, add a focused regression, run `python scripts/regen.py`, `python verification/test_site.py`, and `python scripts/publish.py --out _site --verify`, then review the generated diff.

Prioritize broken access, hidden data, and misleading presentation over cosmetic preference.

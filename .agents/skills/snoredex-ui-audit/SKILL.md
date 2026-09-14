---
name: snoredex-ui-audit
description: Review Snoredex artwork groups and export browser proposals, or audit the generated static UI for responsive layout, accessibility, interaction, dark mode, print and image behavior. Use for artwork proposal review or reproducible UI findings; not for applying proposals to canonical data, data-verdict research or redesign without a request.
---

<!-- doc: role=browser artwork proposal review and static-UI audit workflow skill; stage=task -->

# Snoredex UI audit

Review artwork proposals or produce a reproducible review of the static site's behavior, according to the requested task. Keep generated output and data truth boundaries intact.

## UI-audit context

Read [AGENTS.md](../../../AGENTS.md), [HANDOVER.md](../../../HANDOVER.md), and the site/consumer paths in [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md). `index.html` is generated: trace defects to the owning generator, styles, templates, or canonical data instead of editing it directly.

For artwork grouping, detection or proposal export, use the artwork procedure below. For layout,
accessibility or browser behavior, use the UI-audit procedure. Selecting an artwork route does not
request a responsive-layout audit.

## Artwork proposal review procedure

1. Read [ADR-0007](../../../verification/ADR-0007-embedded-artwork-review-ui.md). Open the local generated page or an explicitly selected deployment and load its artwork-review section. Record the projection version and identify the requested release/group using stable graph IDs. If the browser or source image is unavailable, report that limit rather than inventing an observation.
2. Inspect the retained source image, its content hash and the affected localized releases and physical prints. Automatic image groups are unreviewed anchors, not accepted artwork identities. Keep language, finish and identity claims separate.
3. When the request authorizes preparing proposals, choose the supported action that matches the observation: confirm, correct, reassign, split, unclear or propose-variant. Supply reviewer details and before/proposed-after values. Reassignment uses an existing artwork-group ID from the current projection: either an `IMAGE-GROUP:*` or a `RELEASE-GROUP:*` target. Uncertainty stays unclear. Respect the image guards and do not infer invisible properties.
4. Save the proposal locally and check the saved/unsaved status. Download the versioned proposal JSON for handoff; preserve stale drafts separately and report storage failures. For inspection-only requests, report findings without saving proposals or changing browser storage.
5. Report the selected IDs, projection/schema versions, source observations/hashes, action and export location. The browser writes only local drafts/exports. No reviewed proposal importer or decision store exists yet: the export is review material, and this procedure never applies it to authoritative data or deploys changes.

## UI-audit workflow

1. Confirm whether the user requested audit-only or implementation. In audit-only mode, do not modify files or open issues.
2. Establish current branch, working-tree state, and a reproducible local build. Use `python scripts/publish.py --out _site` when an isolated publication artifact is needed.
3. Run `python verification/test_site.py` when Playwright and Chromium are available. Serve the site locally and use a browser for behavior the automated suite does not cover.
4. Test representative narrow mobile, tablet, desktop, and wide viewports. Check overflow discoverability, sticky behavior, clipped content, zoom, keyboard navigation, focus visibility, semantics, accessible names, contrast, reduced motion, dark mode, print, and enlarged card images.
5. Verify findings against the owning source and existing tests. Distinguish data defects from presentation defects and avoid speculative redesign advice.
6. Report each actionable finding with severity, reproduction steps, viewport or input method, affected source path, user impact, and the smallest likely repair. Report unavailable browser coverage explicitly.
7. If implementation is separately authorized, edit only canonical UI sources, add a focused regression, run `python scripts/regen.py`, `python verification/test_site.py`, and `python scripts/publish.py --out _site --verify`, then review the generated diff.

Prioritize broken access, hidden data, and misleading presentation over cosmetic preference.

---
name: snoredex-source-refresh
description: Refresh and reconcile Snoredex source-first set and card discovery runs. Use for catalogue discovery, source updates, set or promo announcements, and scheduled, release-triggered, provider-change or manual discovery runs. Excludes targeted web searches for prompt-specified cards, photo intake, evidence for an already-known claim, and TCGdex finish-snapshot refresh.
---

<!-- doc: role=source-refresh workflow skill; stage=task -->

# Snoredex source refresh

Create one immutable provider refresh and reconcile every result to a visible terminal state without turning source failure or silence into a verdict.

For targeted online evidence searches whose cards come from a prompt or issue, start with
[card search](../card-search/SKILL.md). Return here when a find needs source-first admission;
searching for one card does not require refreshing an entire provider or evaluating a whole setlist.

## Source-refresh context

Read [AGENTS.md](../../../AGENTS.md), [HANDOVER.md](../../../HANDOVER.md), [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md), and [RECURRENCE.md](../../../verification/RECURRENCE.md). Treat the adapter and discovery manifests as reviewed contracts and their generated staging files as review surfaces, not truth stores.

## Source-refresh workflow

1. Confirm whether the request is offline validation or an authorized live refresh. Network access and scheduling do not authorize commits, merges, publication, or canonical verdict changes.
2. Run `python scripts/discovery_cycle.py --check` for retained-run validation. For a live refresh, create a unique UTC run ID and run `python scripts/discovery_cycle.py --refresh --run-id <YYYYMMDDTHHMMSSZ>`.
3. Verify request/checkpoint manifests, raw bytes, hashes, provider errors, pagination, and source-capability boundaries before interpreting records.
4. Review every added, changed, disappeared, re-keyed, ambiguous, unmapped, `needsEvidence`, and gap record. Preserve provider-native locality and identifiers.
5. Reconcile each `new-candidate` to a canonical release with a reviewed mapping, or positively exclude it only when retained source evidence establishes another identity. The contract has no separate unresolved-disposition record: if neither outcome is supported, leave it as `new-candidate`; it stays counted and `workflow_loop.py --loop discovery` stays at `needs-reconciliation`. A balanced run is not a reconciled run. When reconciliation admits a specimen-backed print, apply the [specimen and reference acceptance contract](../../../verification/RESUME.md#specimen-and-reference-acceptance-contract) so retained evidence reaches the admitted identity. A candidate cannot directly mutate language, finish, set, or absence verdicts.
6. Run `python scripts/workflow_loop.py --loop discovery --max-cycles 3` and `python scripts/scoped_regen.py --lane source-discovery`. Stop when the source or owner input named by the runner is required.
7. Run `python scripts/regen.py`, inspect completeness and graph changes, and report run IDs, hashes, provider failures, reconciliation counts, explicit gaps, and remaining blockers.

## Source-refresh bot-gated retrieval

Choose an available retrieval method: ordinary HTTP, a supported browser, or an already
operator-approved local scraping backend. A Firecrawl-compatible backend is one option; neither
installing it nor configuring a VPN is a prerequisite. Credentials and private endpoint details
stay in the operator's environment. For Cloudflare, CAPTCHA, 403 or JS-only pages, use this bounded
acquisition path for discovery and adjudication inputs:

1. Collect links from the complete issue body and all comment pages, for example with
   `gh api --paginate .../issues/N/comments`. Preserve listing and exposed direct-image URLs.
2. Try the available methods that can change the result. For a configured Firecrawl-compatible
   backend use `POST /v1/scrape`, formats `markdown`, `onlyMainContent`. Inspect a successful
   response before trying another method. Do not bypass access controls or retry an unchanged
   blocker indefinitely. When access remains blocked, report the target, exact missing field,
   source/direct-image links and attempts; request only the needed capture or clarification while
   continuing independent targets. Never claim that inaccessible image bytes were inspected.
3. Byte length is a **heuristic, not proof.** Judge readability by inspecting the returned page
   content itself: a meaningful title plus real set/card/release rows means readable; a
   Cloudflare/`"Just a moment…"`/`"Performing security verification"` page, an HTML error, or an
   empty body means still gated or blocked regardless of length. Record the measured size and HTTP
   result only as supporting evidence alongside what the page actually contains.
4. Extract the evidence relevant to the disputed units (set code, number, language row, release date,
   rarity). For set-code pages, grep the markdown for the set code, numbers, and locale markers.
   A recovered page is **not an adapter run**: `scripts/source_adapters.py` and
   `scripts/card_discovery.py` fetch their configured endpoints or replay existing runs; neither
   imports externally scraped Markdown. Use their normal run path only for supported acquisitions.
   For manual retrieval, retain an issue-scoped JSON snapshot under
   [verification/evidence/](../../../verification/evidence/), following the existing research records:
   original/canonical source URL, actual retrieval date, capture method, returned content or exact
   relevant excerpt, its SHA-256, source-native identifiers, and field-specific limits. Distinguish
   a hash of the retained excerpt from a full-response hash; omit transport credentials and private
   backend details. This is a research input, not a generated run or an accepted claim. Do not invent
   run IDs, edit immutable run files, or treat the ignored cache as retained evidence.
   Before applying it, resolve the source's reviewed provider/surface and capability under
   [ADR-0003](../../../verification/ADR-0003-source-capability-coverage.md). If the provider or
   capability is missing, use [source onboarding](../snoredex-source-onboarding/SKILL.md) within
   the authorized scope. Until reviewed, retain it as a lead without borrowing another provider's
   authority. Automated discovery needs its own reviewed adapter path.
5. Classify what it proves — e.g. a localized existence as a **catch-up/reprint set** is distinct
   from existence under the original set number. Do not call a disputed unit `not-printed` because a
   set predates a market launch when a catch-up printing exists.
6. Apply the result per the owning lane: discovery/recovery feeds this `source-refresh` workflow;
   classifying supplied evidence for an existing claim belongs to
   [claim-evidence](../snoredex-claim-evidence/SKILL.md).

Never use the scraping backend for anything but read-only retrieval, and never treat retrieval alone
as a verdict.

Never rewrite an immutable run, the legacy Cardmarket baseline, or an archived pass. Zero rows and unreachable providers are failures or gaps, not empty catalogues.

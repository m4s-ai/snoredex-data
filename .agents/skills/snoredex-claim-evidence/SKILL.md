---
name: snoredex-claim-evidence
description: Apply positive external-source or collection-owner evidence to an existing Snoredex language claim or printing in data/. Use for confirmations, contradictions and adjudication inputs; not for photographs (specimen intake) or targeted searches (card search).
---

<!-- doc: role=claim-evidence workflow skill; stage=task -->

# Snoredex claim evidence

Bring one already-identified claim to the strongest state the supplied evidence justifies, while
preserving its provenance and uncertainty. There is no importer: this is a manual
procedure against `data/`, guarded by `scripts/check.py` and its `--selftest`.

## Claim-evidence context

Work from the repository root. Read [AGENTS.md](../../../AGENTS.md), the evidence ladder and
source techniques in [METHODOLOGY.md](../../../METHODOLOGY.md), and the field descriptions in
[DATA-GUIDE.md](../../../DATA-GUIDE.md). For finish, foil, stamp, marking or size claims, read the
finish section of METHODOLOGY.md as well.

## Claim-evidence workflow

1. Identify the exact target: a language claim (`data/claims.json` `languageClaims`, by `unitId`)
   or a printing (`data/printings.json`, by `itemId`). Separate language existence, locality,
   finish, edition and distribution claims.
2. Run `python scripts/check.py` once as the baseline and record pre-existing failures.
3. Classify what the source positively establishes. Provider silence, missing rows, zero results
   and TCGdex `false` are not negative evidence.
4. Resolve the provider in `data/evidence.json` `providers`. A source not listed there needs a new
   provider record (display name, category, `authorityTier` 1, 2, 3 or 5, coverage, attribution,
   notes, hosts) and never `supportsAbsence`. Attribute the claim to the source it would fail
   without; set `corroborated` only when a second provider supports this same claim.
5. Edit the record by hand: `providerId`, `sourceUrl` (a URL or null), `sourceRef` (a
   `specimen:SPEC-nnnn` reference or null), `sourceType`, an `evidence` text of at least 20
   characters, `evidenceGranularity`, `evidenceInference` and `checkedAt` (the real retrieval
   date). `applicationStatus` must follow the verdict, granularity and inference exactly as the
   check.py rule "application status follows verdict, granularity and inference" states. Retain a
   capture of the source under `verification/evidence/<task>-<date>/` (URL, retrieval date,
   relevant content, SHA-256). Never reuse a neighbour's evidence or invent a reference.
6. Treat an explicit collection-owner absence decision as adjudication input: the owner records it
   in `verification/owner_adjudications.json` (owner-only), and the claim then cites its
   `adjudicationId` with `applicationStatus: "not-printed"`. A scoped source may support the
   rationale but never produces `not-printed` itself; otherwise the claim stays `disputed`.
7. Run `python scripts/check.py`. A failing rule is a finding to fix, never to silence. Then
   `python scripts/build.py` and review the diff of the outputs; if an item was removed or re-keyed,
   name and justify it in the commit.
8. Report evidence, provider, status transition and remaining uncertainty. Run
   `python scripts/regen.py` once at delivery.

## Claim-evidence source recovery

For a bot-gated source link (Cloudflare, CAPTCHA, 403, JavaScript), use the access notes in
METHODOLOGY.md's source techniques: an in-app or authenticated user browser where authorized, then
an independent source. Retrieval is never evidence by itself; deciding what the recovered source
proves for this exact claim is this workflow's task. Catalogue metadata is not specimen evidence
and cannot establish a physical finish. Source silence proves neither absence nor first release;
keep catch-up and reprint identities separate from the original set.

Stop without changing the claim when identity, locality, source capability or owner intent is
unresolved.

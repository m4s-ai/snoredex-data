<!-- doc: role=operating rules and data-model traps; stage=auto -->
# CLAUDE.md — working instructions for this repository

The operating rules for an agent working here, and the traps that make them make sense. It is short
*relative to what it points at*: the detail lives in the documents linked below, and duplicating it
would create a second copy to keep in step. [`LESSONS.md`](LESSONS.md) carries the incident behind
each trap — read it when a rule looks arbitrary.

## What this project is

The current data is a **legacy Cardmarket-derived candidate universe** captured on 2026-07-21,
plus an independent **source-verification layer**: for each inherited card × language × variant,
does a source *outside Cardmarket* confirm that printing actually exists? It is not a complete
all-locality catalogue; the immutable boundary is recorded in
[`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json). The bounded source-first
rebuild completed under #132; its terminal state accounts for the reviewed inputs while retaining
explicit source and locality gaps rather than claiming discovery completeness.

The layer exists because Cardmarket's language filter reports **marketplace availability, not a
print manifest**, and it over-claims. The worked example is `KSS 26`: advertised in 17 languages,
actually printed in 7. Every language claim therefore needs an outside source.

The owner (`Scarrty` in git, `M4S.Collection` as licensor) directs scope and supplies physical
specimens. Owner statements are authoritative but are still graded explicitly as evidence.

## Read before you act

| Document | Read it before |
|---|---|
| [`HANDOVER.md`](HANDOVER.md) | anything — it is the cold-start entry point and repository map; priorities live in the issue tracker |
| [`verification/RESUME.md`](verification/RESUME.md) | adding or changing **any** confirmation or contradiction |
| [`verification/FINISH_SOURCES.md`](verification/FINISH_SOURCES.md) | touching finishes, foil patterns or stamps |
| [`README.md`](README.md) | *using* the data — the caveats there are load-bearing |

`RESUME.md` is long and worth it. It records every source technique, dead end and methodology
correction already made here, and reading it is how you avoid repeating one.

Reusable repository workflows live under [`.agents/skills/`](.agents/skills/). Select the narrow
skill whose description matches the task; each routes back to these canonical documents and the
existing Python workflow owners rather than copying their contracts.

## Non-negotiable rules

1. **A Cardmarket catalogue claim is not evidence; a retained card image can be.** A product's
   *language filter*, offers and counts are not evidence. An exact product image or seller photo is
   positive evidence only when the visible card face itself establishes the target language or
   other claimed property.

   All three classes are recordable. `cardmarket` is tier 5 — the catalogue this project exists to
   check, never localized-card verification. `cardmarket-product-image` and
   `cardmarket-listing-photo` are tier 2 for exact product images and seller photographs whose card
   text or treatment was actually inspected. File an accepted image as a `SPEC-nnnn` record with
   its image and listing/product provenance, never as a bare link: pages and listings change, and
   the observation has to outlive them. Tier 2 rather than 1 because the pictured card cannot be
   re-examined physically and catalogue or seller metadata may be wrong. There is no open API;
   collection is by hand or a browser session, and the rolling ~55-request quota returns HTTP 429.
2. **Grade every source.** `providerId` names it, `corroborated` says whether a second provider
   agreed, and `verification/source_registry.json` ranks each provider by `authorityTier` —
   the evidence ladder in [`README.md`](README.md#how-a-claim-becomes-a-fact), generated from that
   registry. Tiers 1-3 grade external evidence, strongest first; tier 5 marks what is **not**
   external evidence. There is deliberately no tier 4.

   A single non-URL source may confirm a unit: **19 units rest on owner attestation alone**; the
   current `E6` output reports how many rest on an inspected specimen alone. The owner holds
   those cards and no database records them, so refusing the evidence buys a false "open" count
   rather than better evidence.

   **`E3` enforces *checkable or strong*, not tier alone.** It fails only when an uncorroborated
   claim is both: no `sourceUrl` *and* below tier 2. A tier-3 page with a URL may carry a claim by
   itself, and 3 resolved units do — never report a lone tier-3 source as a rule violation, and
   never state the tiers more strictly than this ([LESSONS](LESSONS.md#a-rule-stated-more-strictly-than-the-check-enforces)).
   `E4` fails when the attestation count stops matching the data. Prefer corroboration where it
   exists — it covers 96 of 719 units, so it usually does not.

   **Grade a claim by what it rests on, never by the strongest thing beside it.** `providerId` is
   the source the unit would fall over without; corroboration from a neighbouring unit belongs in
   `evidence`, and `corroborated` means a second provider agreed about *this* unit. Fourteen units
   once claimed specimen authority because a specimen sat nearby
   ([LESSONS](LESSONS.md#the-neighbours-evidence-is-not-this-units-evidence)). `S13` and `S14` hold
   the line: `sourceRef` carries a reference or nothing, and only a cited specimen may claim
   specimen authority.

   **Source-backed is a field-level claim.** Preserve the exact source-native value and qualified
   identity the evidence states. A normalized id must exist in its canonical registry; when no
   reviewed mapping exists, keep the native value and leave the normalized id null. Source silence
   creates no positive field, and a legacy marketplace value is only a fallback when no
   source-backed value exists. Retrieval and assertion dates come from the supporting observation,
   never from a reused pass default.
3. **Never contradict on bare absence.** A source that fails to list a printing has a gap. It has
   not proved the printing does not exist. Official Pokémon sources confirm only the releases they
   name for the matching language and region. Missing rows, fields, pages, and results stay unknown.
   This rule exists because an
   absence argument produced a false contradiction (`XY-P 149`) that had to be reverted
   ([LESSONS](LESSONS.md#an-absence-argument-that-produced-a-false-contradiction)).
4. **Only a collection-owner adjudication settles an absence.** No external source can do so.
   Converging evidence from dependable sources is *Indizien*: it is the material the owner weighs,
   and deciding which way it points is the collector's job, not a property a page can assert.
   Adjudications are stored separately in `verification/owner_adjudications.json` and are never
   attributed to a single provider.

   External providers must set `supportsAbsence=false` and declare no `absenceScopes`. `E9` enforces
   that boundary. Provider coverage remains useful research context, but it never turns omission
   into evidence.

   **The finish layer has the same mechanism since #119.** `owner_adjudications.json` carries a
   second array, `finishDecisions`, and a decision there closes the list of finishes for one
   set-number-language unit with `completenessStatus=owner-adjudicated`. It exists because some
   products have no finish-specific product page to find. `/ex/` product pages
   are not published for magazine-bonus decks, and the official card page carries no finish
   vocabulary at all (`FINISH_SOURCES.md` records the probe, with a working control).

   A finish decision **closes a list and never asserts a finish.** `E13` enforces both halves. It
   must name exactly the finishes the evidence already found, and it may not apply to a unit with no
   printings. That would be an absence argument wearing the owner's name.

   **`not-printed` means no regular release.** A proof copy or an error card is a different
   category and does not falsify the decision.

   TCGdex `true` confirms a printing; TCGdex `false` does not refute one.
5. **`pending` means not yet established, never proven absent.** This holds in the data, the
   site copy, and anything you write.
6. **Routine physical evidence goes through the canonical manifest importer,** then the finish/
   graph projectors and release gate. Write a new Python pass under `verification/` only for a
   migration, bulk repair, or data-model change. Never hand-edit `units.json` or
   `finish_units.json`.
7. **Never hand-edit a generated file.** Each carries a header saying so, including the
   `<!-- generated:… -->` blocks in `README.md` and the whole of `index.html`. Regenerate instead.
8. **Run the checks after every write pass** — see [Commands](#commands). Silent data corruption
   has happened here and only the audit caught it.

## Data-model traps

These are the things that have actually caused mistakes. Full treatment in `HANDOVER.md` §4.

- **Unit** = `(setCode, number, variant, language)`, status
  `confirmed | contradicted | needs-manual-review | pending`. Every resolved unit must carry a
  non-trivial `evidence` string and a `sourceType`; `review_integrity.py` enforces it.
- **Finish unit** = `(setCode, number, language)` — deliberately **not** keyed by V-token, because
  TCGdex's positive `normal`/`holo`/`reverse` flags apply at that level. Language truth lives in
  `units.json`, finish truth in `finish_units.json`; the two backlogs are separate. **Never infer
  a physical finish from a confirmed language claim.**
- **V-tokens are opaque and set-specific.** `xsv2a` V1 = Poké Ball mirror / V2 = Master Ball
  mirror, but `xm2a` flips that order; `PPS8` V1 = Non-Holo / V2 = Holo; `xJTG` V1/V2/V3 are
  stamps. Never assume a V-token means the same thing across sets — read `variantName`. Inferring
  one set's order from another has already been right by luck, which is not the same as evidence
  ([LESSONS](LESSONS.md#v-tokens-are-set-specific-and-the-guess-is-sometimes-right)).
- **Run membership is decided by the printed set size — except for a distribution rarity.** Whether
  "the set was released in language L" reaches a card depends on the card sitting inside the set's
  numbered run, and the fact that says so is the denominator printed on it. Sizes live in
  `set_catalogue_sources.json` as `printed-set-size-record`, and a recorded size outranks the
  harvest rarity in both directions. It must **not** outrank a `Promo`, `Prize Pack Series`,
  `Oversized`, `World Championship Deck` or `Online Code Card` row: a promo's collector number is
  the number of the run card it reprints, so the comparison answers the wrong question and once
  moved `RR 33 V2` off the queue while its identical siblings stayed on it
  ([LESSONS](LESSONS.md#a-better-fact-overruled-a-rule-it-was-never-about)). Read the numbering that
  belongs to the set code, too — a shared article carries `{{Setlist/entry}}` (Japanese) and
  `{{Setlist/nmentry}}` (English) side by side.
- **Technical `finish` vs collector `finishFamily`.** `finish` stays the auditable
  non-holo/holo/reverse-holo/mirror-holo value. `finishFamily` is the presentation layer, where
  reverse-holo and mirror-holo both appear as "Reverse Holo". Never collapse the technical value
  or the underlying printing/checklist IDs merely to group the UI.
- **`markings.role` is a trichotomy.** `print-identity` (rarity symbols, contest credits),
  `reverse-holo-treatment` (EX-era set logos that are part of the reverse design — `DF 10` is the
  worked example), `distribution-promo` (prerelease, Staff, retailer, Pokémon Center marks —
  these do **not** imply a reverse holo).
- **`contradicted` is a disagreement; `not-printed` is a decision.** A contradicted unit means an
  outside source disagrees with Cardmarket. Only an explicit collection-owner adjudication settles
  a language or printing absence. Everything else is **disputed**. The current
  settled/disputed counts are generated figures, read them from `verification/evidence_semantics.json`
  (or the README), never from this file — and `DATABASE.md` is right that an application must not
  read disputed as "does not exist". `scripts/absence_model.py` holds that one rule for every
  generator; cards carry `languagesNotPrinted` and `languagesDisputed` beside
  `languagesContradicted`, and checks `E8`/`E9`/`E10` keep the split honest. Both are excluded from
  the checklist, because the README's whole promise is that nobody hunts a card that was never
  made — exclusion is not the same as asserting absence, and `analysis_checklist.json` counts what
  it left out.
- **`cardKey` = same card text, not same artwork.** It is Cardmarket's own grouping by name plus
  attack names.
- **"Spanish" is one language across two localities.** European Spanish and LATAM-ES are
  physically distinct editions, and **both are in scope since 2026-08-09** (owner decision D3 in
  [`ADR-0001`](verification/ADR-0001-locality-aware-print-identity.md)). Every existing "Spanish"
  confirmation means the European print and nothing else: Cardmarket collapses both editions into
  one filter and does not carry LATAM at all, so no LATAM row can come from the harvest. The #139
  matrix is reconciled, and three official `LA` releases are now retained as a complete positive
  slice; `xJTG` remains an explicit evidence gap. Never read a European confirmation as covering
  LATAM or a positive slice as historically exhaustive.
- **Code cards are excluded** — `verification/excluded_codecards.json`.
- **Physical specimens are cited, not described.** A card the owner holds has a stable id in
  `verification/specimens.json`; a unit references it as `sourceRef: "specimen:SPEC-0002"`. For
  routine issue evidence, prepare one observation manifest and run
  `python verification/fetch_attachment.py --issue NUMBER --manifest PATH`. The importer follows
  the issue HTML's signed image candidate, validates it, records its `photographSha256`, and
  records the stable issue URL as `photographSource`; it is provenance, not a place the image
  will still be. The direct
  `--specimen ... --from ...` form remains for a local or already reachable image. Never write a
  new prose description of a specimen — that is what the ids replaced.
- **Graph printing identity is semantic, not ordinal.** Finish records still carry their source
  `printingId` for traceability, but graph claims/nodes derive a `semanticPrintingId` from the
  release, finish, edition, foil pattern, markings, distribution, and card size. Existing graph
  ids are retained through that semantic lookup; a new semantic printing gets a hash-based id.
  The collector projection uses the same fingerprint when reconciling predecessor checklist rows,
  so inserting a printing cannot silently move collection state to a neighbouring card.
- **Reconciliation is order-independent.** Collect every candidate before refining an unknown
  dimension. Refine only when one compatible value remains; ambiguity stays `unknown`. Reordering
  equivalent inputs may not change semantic identity, provenance attachment, or checklist output.

## Commands

Run from the repository root. The normative dependency order and core suite live only in
[`scripts/regen.py`](scripts/regen.py): its `REGEN`, `CHECK`, and `TESTS` arrays are the executable
pipeline source of truth. The graph/data boundary and the deliberate Pages lane are described in
[`WORKFLOW-MAP.md`](WORKFLOW-MAP.md). Do not copy that list into another document or workflow.

For a data change, run `python scripts/regen.py --check` before editing to establish a clean
baseline, make the change in its canonical store, then run `python scripts/regen.py` and review the
diff. This runs the complete write/check/test sequence, including the within-store
`review_integrity.py` checks and cross-artifact `review_findings.py` checks. A scoped lane may add
cheaper L0–L2 checks, but it never replaces the L3 `regen.py --check` before merge.

The pre-PR gate, matching CI:

```console
pip install -r requirements.txt
python -m playwright install chromium

python scripts/regen.py                          # write every derived artifact, then run the core gate
python scripts/regen.py --check                  # skip the write phase; this is what CI calls
# Diagnostic only: limit determinism checks for a focused meta-test; never a merge substitute.
python scripts/regen.py --check --check-only scripts/evidence_semantics.py

# Scoped L0–L2 lane; report includes Run-ID, graph impact, and skipped checks. L3 is still required.
python scripts/scoped_regen.py --lane physical-evidence
python scripts/workflow_loop.py --loop physical --max-cycles 3
# Other bounded loops: evidence, discovery, news-promo, tcgdex, absence, cardmarket.

# These environment canaries deliberately stay outside regen.py.
python verification/test_site.py                 # browser acceptance tests
python verification/verify_finish_sources.py     # live TCGCSV assertions
python scripts/publish.py --out _site             # build the artifact, THEN verify it
python scripts/publish.py --out _site --verify    # --verify, not --check; exits 1 without --out
git diff --exit-code -- . ':(exclude)*.sqlite'   # equivalent scope enforced inside regen.py
```

Every `--check` mode is observational: it may not create or replace files, update timestamps, or
write databases, and it must be mutually exclusive with refresh, replay, acceptance, and other
write actions. An acceptance command must render from the newly accepted canonical state; an
immediate second offline check must be clean.

`scripts/regen.py` owns the dependency order and core suite. The reusable
`.github/workflows/release-gate.yml` calls that command directly: draft PRs skip it, ready PRs run
deterministic L3 only, and the manual Pages call runs L4. A push to `main` runs the separate P6/P7
history audit at `GITHUB_SHA`; Pages downloads and verifies the L4-produced artifact and gate
manifests instead of rebuilding a second projection tree. The workflow map is the single
human-readable explanation; this file intentionally does not maintain a second command list.

**The `.sqlite` files are excluded from regen.py's byte diff, and always must be.** A SQLite file records the
version number of the library that wrote it in its own header, so two environments running different
SQLite builds produce different bytes from identical data — measured here as 128,107 differing bytes
between SQLite 3.53.1 and 3.45.1 whose `iterdump()` output was identical line for line. Regeneration
is deterministic *within* one version and cannot be made deterministic *across* versions, `VACUUM`
included. `scripts/database.py` has always known this — `sqlite_dump()` exists precisely so `--check`
compares the logical dump instead of a file hash. `database.py --check` and
`tracker.py check-template` cover their content instead
([LESSONS](LESSONS.md#the-gate-asked-for-a-byte-match-sqlite-cannot-give)).
Their content is still covered, by those two checks, against what is committed.

`P6` scans full git history, so it fails on a shallow clone regardless of the tree. `git fetch
--unshallow` once, and it becomes a real check locally instead of expected noise.

**`P6` and `P7` read git history, so run `review_findings.py` once more after committing and
pushing.** Everything else in this gate reads the working tree, and a green run before the commit
says nothing about the commit itself: `P7` fails on any author or committer address without
`noreply` in it, and it cannot see yours until the commit exists — nor the old one until the pushed
ref stops reaching it, so an amend needs a force-push before it re-passes. Run it before the commit
for the tree, and again after the push for the history
([LESSONS](LESSONS.md#the-gate-ran-before-the-thing-it-was-checking)).

`python scripts/finishes.py --reproject` redoes only the card projection from the committed store
and needs no network; it is the fast path when a projection rule changes.

The normal release path is offline: `python scripts/regen.py` runs
`finishes.py --offline`, which reads the versioned
[`verification/finish_tcgdex_snapshot.json`](verification/finish_tcgdex_snapshot.json) and checks
every payload hash before use. It never calls TCGdex. The ignored directory
`verification/cache/finish-tcgdex/` is only a transport cache for an explicit refresh and is not
the reproducibility source.

There is no automatic scheduler. Review upstream drift deliberately, at least monthly and again
before a release or whenever TCGdex is known to have changed:

```console
python scripts/finishes.py --refresh                         # fetch, stage, and report drift
python scripts/finishes.py --refresh --accept-refresh         # accept that exact staged snapshot
python scripts/regen.py                                      # rebuild all projections offline
```

`--refresh` reports changed, added and removed URLs and stages the exact payloads in the ignored
`verification/cache/finish-tcgdex/refresh-candidate.json`; it leaves the committed snapshot and
generated outputs untouched. `--refresh --accept-refresh` consumes that staged candidate without
refetching, validates its hashes and source URL set, then writes the versioned snapshot. **Exit 2
means a source could not be reached or no valid staged candidate exists** — the artifacts are not
wrong, so retry the refresh rather than investigate absence. The evidence rules remain in
[`verification/FINISH_SOURCES.md`](verification/FINISH_SOURCES.md).

Serve the site locally with `python -m http.server 8000`, then open <http://localhost:8000/>.
`index.html` is the single public page; `verification/confirmed-releases.html` redirects to it.

### Check codes

Codes are cited beside the rules they enforce, above and throughout. For the full list, read the
`check(` calls in `verification/review_integrity.py` and `verification/review_findings.py` —
`verification/checks.py` holds the protocol both share. Looking a code up is an on-demand act, so
the index lives in the code rather than here.

## Conventions

- **Python 3.11, standard library only** for the generators. `requirements.txt` is
  verification-only: `playwright` (browser tests).
- **Use Python on every platform.** If Python is unavailable, install it; never
  substitute PowerShell for a repository workflow or implementation pass.
- The recurring toolchain is **entirely Python**. PowerShell is not a prerequisite for anything.
- **All scripts derive paths from their own location** — `Path(__file__)`. Keep this in new
  scripts; CI runs them from more than one working directory.
- **The archive is immutable.** `verification/archive/passes/` is the one-shot record of how the
  committed data came to be. Its files are never rerun and never edited; check `X3` hashes them
  against `verification/archive/MANIFEST.json` and fails on any change. A translated pass is not
  the script that produced the record.
- **`scripts/` holds only runnable things.** The five harvest scripts — `build`, `join`,
  `getimages`, `finalize` and `mkunits` — moved to `verification/archive/passes/` in #68, once
  #28 had captured their data flow. Their `_chunk*`/`_cards_stage*` inputs are not in the
  repository and are not reproducible (a 2026-07-21 scrape of a live marketplace), so
  `snorlax_cards.json` is the input of record rather than an output. `mkunits` is additionally
  destructive: it rebuilds `units.json` with fresh ids and discards the verification state.
  Never run it. Check `B1` keeps all five out of `scripts/`.
- **`scripts/analyze.py`** produces `analysis_artists.json`, `analysis_shared_cards.json`,
  `analysis_variants.json` and `analysis_language_drift.json` — nothing else generates them. It
  reads `snorlax_cards.json` only, which is #30's single canonical node. Its PowerShell
  predecessor is archived at `verification/archive/scripts/analyze.ps1`.
- **LF line endings** (check `X1`) and **no UTF-8 BOM** (check `X5`) in tracked text.
- `verification/checks.py` is the check protocol shared by the two suites: `review_integrity.py`
  validates invariants *within* each store, `review_findings.py` validates consistency *between*
  the stores and the artifacts consumers read.
- **Active instructions are one live truth.** When new research invalidates operational guidance,
  reconcile every contradictory active occurrence in the same change; appending a later correction
  does not repair an earlier stop instruction. Dated history remains a snapshot, but it cites
  retained photographs and renders by `SPEC-nnnn` and checks any remaining-work list against the
  canonical stores at the stated snapshot.

## Counts are reported, never asserted — but a losing move fails

Nothing fails because a count is the wrong *size*. Counts are reported as drift against a baseline,
and only a move in the **losing direction** is a finding. Since #69 that finding fails the run:
before it, a genuine loss printed a banner and exited 0. Structural facts still fail the run.

Each metric declares which way losing is:

- **`up-is-progress`** (the default) — units, artist coverage, finish rows. These measure work that
  exists, so a fall means something was lost.
- **`down-is-progress`** — `pending units`, `manual-review units`. These measure work left to do,
  and their baseline is the **low-water mark**, so a queue climbing back is caught immediately.

Do not "fix" a losing move by editing the baseline; find what changed. Re-anchoring a queue's
baseline *downward* after closing it is the opposite move and is correct — it tightens the check.
Never raise one to silence a rise: a gate that reddens when the project improves is a gate people
learn to edit rather than read, and this project has run one
([LESSONS](LESSONS.md#a-gate-that-reddens-when-the-project-improves)). When a queue grows because
the corpus grew, record the cause beside the number.

## Git and publication

- Repository is `github.com/m4s-ai/snoredex-data`. Work lands on a **feature branch via pull
  request** — do not push to `main`.
- **Sync `main` before starting any task.** Begin by `git fetch origin` and, from a clean
  `main`, `git pull --ff-only origin main` so the branch you cut is based on the
  latest commit, not a stale local copy. Never start work on a branch whose base is older than
  `origin/main` — that is how parallel agents' work silently collides and how stale artifacts
  sneak back in.
- **One isolated branch per issue.** Give each issue its own branch (e.g. `fix/<n>-<slug>`),
  cut fresh from the current `origin/main`, never shared with another in-flight task. This lets
  two or three agents work different issues in parallel against the same base; when a branch
  falls behind `origin/main`, reconcile by rebasing it onto the new `origin/main` (regenerate
  via `python scripts/regen.py` after, per the block above) rather than restarting from scratch.
  Do not stack unrelated tasks on one branch, and do not reuse an old branch from a previous
  issue.
- End commit messages with the trailer
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- The release gate runs on pull requests across Ubuntu and Windows. The Windows leg keeps the
  filesystem-touching steps (generator determinism, `git diff --exit-code`, `review_findings.py`,
  `publish.py --verify`) because path portability is what it is there to catch; the browser suite
  is Linux-only.
- **Merging never publishes.** Pages deployment is a manual `workflow_dispatch` run, gated on
  `verification/publication_gate.py` and the approvals recorded in `publication-decisions.json`,
  and it verifies the repository's real visibility against the GitHub API. Publishing is the one
  step in this project that cannot be undone.
- Licence grants are **in force** (granted by `M4S.Collection`, 2026-07-26). This is a mixed work
  and explicitly not OSI open source: PolyForm Noncommercial 1.0.0 for the code, CC BY-NC-SA 4.0
  for the data selection, arrangement and annotation. See [`LICENSE.md`](LICENSE.md).

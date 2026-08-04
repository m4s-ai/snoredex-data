<!-- doc: role=operating rules and data-model traps; stage=auto -->
# CLAUDE.md — working instructions for this repository

The operating rules for an agent working here, and the traps that make them make sense. It is short
*relative to what it points at*: the detail lives in the documents linked below, and duplicating it
would create a second copy to keep in step. [`LESSONS.md`](LESSONS.md) carries the incident behind
each trap — read it when a rule looks arbitrary.

## What this project is

A complete catalogue of every **Snorlax** Pokémon TCG product on Cardmarket, plus an independent
**source-verification layer**: for each card × language × variant, does a source *outside
Cardmarket* confirm that printing actually exists?

The layer exists because Cardmarket's language filter reports **marketplace availability, not a
print manifest**, and it over-claims. The worked example is `KSS 26`: advertised in 17 languages,
actually printed in 7. Every language claim therefore needs an outside source.

The owner (`Scarrty` in git, `M4S.Collection` as licensor) directs scope and supplies physical
specimens. Owner statements are authoritative but are still graded explicitly as evidence.

## Read before you act

| Document | Read it before |
|---|---|
| [`HANDOVER.md`](HANDOVER.md) | anything — it is the cold-start entry point and the current backlog |
| [`verification/RESUME.md`](verification/RESUME.md) | adding or changing **any** confirmation or contradiction |
| [`verification/FINISH_SOURCES.md`](verification/FINISH_SOURCES.md) | touching finishes, foil patterns or stamps |
| [`README.md`](README.md) | *using* the data — the caveats there are load-bearing |

`RESUME.md` is long and worth it. It records every source technique, dead end and methodology
correction already made here, and reading it is how you avoid repeating one.

## Non-negotiable rules

1. **Evidence outside Cardmarket only.** A product's *language filter* on Cardmarket is not
   evidence. A seller's *photo* of the physical card is.

   Both halves are now recordable. `cardmarket` is tier 5 — the catalogue this project exists to
   check, never verification — and `cardmarket-listing-photo` is tier 2, for a card whose text you
   read off a seller's photograph. Until 2026-08-03 only the first existed, so the second half of
   this rule had nowhere to be written down. File a listing photograph as a `SPEC-nnnn` record with
   `heldBy: "third-party seller"` and the listing URL, never as a bare link: listings are deleted
   and the observation has to outlive them. Tier 2 rather than 1 because you cannot re-examine it
   and the seller may have mislabelled the language. There is no open API; collection is by hand or
   a browser session, and the rolling ~55-request quota returns HTTP 429.
2. **Grade every source.** `providerId` names it, `corroborated` says whether a second provider
   agreed, and `verification/source_registry.json` ranks each provider by `authorityTier` —
   the evidence ladder in [`README.md`](README.md#how-a-claim-becomes-a-fact), generated from that
   registry. Tiers 1-3 grade external evidence, strongest first; tier 5 marks what is **not**
   external evidence. There is deliberately no tier 4.

   A single non-URL source may confirm a unit: **30 units rest on owner attestation alone** and 6
   on an inspected specimen alone. The owner holds those cards and no database records them, so
   refusing the evidence buys a false "open" count rather than better evidence.

   **`E3` enforces *checkable or strong*, not tier alone.** It fails only when an uncorroborated
   claim is both: no `sourceUrl` *and* below tier 2. A tier-3 page with a URL may carry a claim by
   itself, and 5 resolved units do — never report a lone tier-3 source as a rule violation, and
   never state the tiers more strictly than this ([LESSONS](LESSONS.md#a-rule-stated-more-strictly-than-the-check-enforces)).
   `E4` fails when the attestation count stops matching the data. Prefer corroboration where it
   exists — it covers 39 of 719 units, so it usually does not.

   **Grade a claim by what it rests on, never by the strongest thing beside it.** `providerId` is
   the source the unit would fall over without; corroboration from a neighbouring unit belongs in
   `evidence`, and `corroborated` means a second provider agreed about *this* unit. Fourteen units
   once claimed specimen authority because a specimen sat nearby
   ([LESSONS](LESSONS.md#the-neighbours-evidence-is-not-this-units-evidence)). `S13` and `S14` hold
   the line: `sourceRef` carries a reference or nothing, and only a cited specimen may claim
   specimen authority.
3. **Never contradict on bare absence.** A source that fails to list a printing has a gap; it has
   not proved the printing does not exist. First prove the source *covers the category* — pokumon
   lists Korean promos, so a missing Korean row there is meaningful; its West coverage is one
   lumped "English" row, so its silence on French means nothing. This rule exists because an
   absence argument produced a false contradiction (`XY-P 149`) that had to be reverted
   ([LESSONS](LESSONS.md#an-absence-argument-that-produced-a-false-contradiction)).
4. **Only a collection-owner adjudication settles an absence.** Not a source — any source.
   Converging evidence from dependable sources is *Indizien*: it is the material the owner weighs,
   and deciding which way it points is the collector's job, not a property a page can assert.
   Adjudications are stored separately in `verification/owner_adjudications.json` and are never
   attributed to a single provider.

   A provider may declare `absenceScopes` — specific pages that state a closed list rather than
   merely failing to mention something, like Elite Fourum's Black Star Promos language table or the
   Kalos Starter Set article. That is **recorded rationale, never a mechanism**: it strengthens the
   case, and `E9` checks each scope is declared and justified, but a scoped source alone leaves the
   claim `disputed`. Dependability decides whether a source may carry that weight, not whether it
   is a manufacturer — Bulbapedia and Elite Fourum qualify
   ([LESSONS](LESSONS.md#complete-official-manifest-was-narrower-than-intended)).

   **`not-printed` means no regular release.** A proof copy or an error card is a different
   category and does not falsify the decision.

   TCGdex `true` confirms a printing; TCGdex `false` does not refute one.
5. **`pending` means not yet established, never proven absent.** This holds in the data, the
   site copy, and anything you write.
6. **Write findings as a new Python pass under `verification/`,** then run report + audit +
   integrity. Do not hand-edit `units.json` or `finish_units.json`.
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
- **Technical `finish` vs collector `finishFamily`.** `finish` stays the auditable
  non-holo/holo/reverse-holo/mirror-holo value. `finishFamily` is the presentation layer, where
  reverse-holo and mirror-holo both appear as "Reverse Holo". Never collapse the technical value
  or the underlying printing/checklist IDs merely to group the UI.
- **`markings.role` is a trichotomy.** `print-identity` (rarity symbols, contest credits),
  `reverse-holo-treatment` (EX-era set logos that are part of the reverse design — `DF 10` is the
  worked example), `distribution-promo` (prerelease, Staff, retailer, Pokémon Center marks —
  these do **not** imply a reverse holo).
- **`contradicted` is a disagreement; `not-printed` is a decision.** A contradicted unit means an
  outside source disagrees with Cardmarket. Only two things settle it: a complete official manifest
  within its scope, or an explicit owner adjudication. Everything else is **disputed** — currently
  **57 settled and 27 disputed** — and `DATABASE.md` is right that an application must not read
  disputed as "does not exist". `scripts/absence_model.py` holds that one rule for every generator;
  cards carry `languagesNotPrinted` and `languagesDisputed` beside `languagesContradicted`, and
  checks `E8`/`E9`/`E10` keep the split honest. Both are excluded from the checklist, because the
  README's whole promise is that nobody hunts a card that was never made — exclusion is not the
  same as asserting absence, and `analysis_checklist.json` counts what it left out.
- **`cardKey` = same card text, not same artwork.** It is Cardmarket's own grouping by name plus
  attack names.
- **"Spanish" is European Spanish only.** LATAM-ES is a physically distinct edition, out of scope.
- **Code cards are excluded** — `verification/excluded_codecards.json`.
- **Physical specimens are cited, not described.** A card the owner holds has a stable id in
  `verification/specimens.json`; a unit references it as `sourceRef: "specimen:SPEC-0002"`. To add
  its photograph: `python verification/fetch_attachment.py --specimen SPEC-0002 --from <path>`,
  then `review_findings.py` and `scripts/database.py`. Never write a new prose description of a
  specimen — that is what the ids replaced. A photograph attached to a GitHub issue cannot be
  fetched from an agent session — the proxy refuses the whole `assets` namespace on `github.com`,
  repository-scoped form included — so the bytes have to arrive by commit, release asset or a
  `githubusercontent` URL. Record the attachment URL as `photographSource`; it is provenance, not
  a place the image will still be.

## Commands

Run from the repository root. **Both suites run before and after every write pass** — before to
confirm a clean starting state, after to catch what the pass broke. `review_integrity.py` validates
invariants *within* each store, `review_findings.py` *between* the stores and the artifacts
consumers read.

**Order matters** in the middle block: `finishes.py` writes the card finish summaries,
`language_status.py` the language verdicts, `confirmed_releases.py` reads both, and
`checklist.py` / `site.py` read those.

```console
python verification/review_integrity.py
python verification/review_findings.py

# ... do the work in a new Python pass under verification/ ...

python verification/audit_evidence.py            # evidence usability
python verification/test_owner_adjudications.py  # owner decision/store projection
python verification/report.py                    # regenerate exports
python scripts/editions.py                       # if edition data changed
python scripts/finishes.py                       # finish units/review + summaries
python scripts/language_status.py                # per-card language verdicts
python scripts/confirmed_releases.py             # chronological JSON + CSV
python scripts/source_registry.py                # provider/evidence registry
python scripts/checklist.py                      # canonical checklist items
python scripts/readme_stats.py                   # generated markdown blocks
python scripts/issue_templates.py                # community correction form
python scripts/open_items.py                     # verification/open-items.html
python scripts/database.py                       # application database + audit
python scripts/tracker.py --tracker snoredex-tracker-template.sqlite init --force
python scripts/site.py                           # index.html + alias redirect

python verification/review_integrity.py
python verification/review_findings.py
```

The pre-PR gate, matching CI:

```console
pip install -r requirements.txt
python -m playwright install chromium

python verification/review_integrity.py
python verification/review_findings.py           # stdlib only, no network — quickest check
for g in checklist readme_stats issue_templates site source_registry open_items analyze database
do python scripts/$g.py --check; done            # fail instead of writing
python scripts/tracker.py check-template         # SEE BELOW — prints failure but exits 0
python verification/test_site.py                 # browser acceptance tests
python verification/verify_finish_sources.py     # live TCGCSV assertions
python scripts/publish.py --verify               # --verify, not --check
git diff --exit-code                             # a generator whose output moves fails here
```

**`tracker.py check-template` prints its failure and exits 0.** Wrapping it in `|| echo FAIL`
stays silent; CI catches it only by running it as its own step under `-e`. Check its output, not its
status ([LESSONS](LESSONS.md#the-eight-generator-loop-is-not-the-gate)).

`P6` scans full git history, so it fails on a shallow clone regardless of the tree. `git fetch
--unshallow` once, and it becomes a real check locally instead of expected noise.

`python scripts/finishes.py --reproject` redoes only the card projection from the committed store
and needs no network; it is the fast path when a projection rule changes.

A full `finishes.py` run reads TCGdex through a cache under `verification/cache/finish-tcgdex/`;
`--refresh-cache` forces a refetch. **Exit 2 means a source could not be reached** — the artifacts
are not wrong, the upstream evidence is missing, so retry rather than investigate. The cache's
validity rules are in [`verification/FINISH_SOURCES.md`](verification/FINISH_SOURCES.md), which you
read before touching finishes anyway.

Serve the site locally with `python -m http.server 8000`, then open <http://localhost:8000/>.
`index.html` is the single public page; `verification/confirmed-releases.html` redirects to it.

### Check codes

Codes are cited beside the rules they enforce, above and throughout. For the full list, read the
`check(` calls in `verification/review_integrity.py` and `verification/review_findings.py` —
`verification/checks.py` holds the protocol both share. Looking a code up is an on-demand act, so
the index lives in the code rather than here.

## Conventions

- **Python 3.11, standard library only** for the generators. `requirements.txt` is
  verification-only: `playwright` (browser tests) and `PyYAML` (issue-form schema check).
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

# CLAUDE.md — working instructions for this repository

The operating rules for an agent working here. It is deliberately short: the detail lives in the
documents linked below, and duplicating it would create a second copy to keep in step.

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
2. **Grade every source.** `providerId` names it, `corroborated` says whether a second provider
   agreed, and `verification/source_registry.json` ranks each provider by `authorityTier`:
   *photographed specimen* (1) / *official DB* (1) > *owner attestation* (2) /
   *high-authority Elite Fourum reference* (2) > *open database* (2) /
   *fan wiki* (3) / *marketplace listing* (3) > other *collector community* (4).

   A single non-URL source may confirm a unit: **30 units rest on owner attestation alone** and 5
   on a photographed specimen alone. The owner holds those cards and no database records them, so
   refusing the evidence buys a false "open" count rather than better evidence.

   **`E3` enforces *checkable or strong*, not tier alone.** It fails when an uncorroborated claim
   is both: no `sourceUrl` *and* below tier 2. A tier-3 page with a URL may carry a claim by
   itself, and 252 resolved units do — do not read a lone tier-3 source as a rule violation, and
   do not tell a reader the tiers are stricter than that. This paragraph used to say a weaker
   source "may not" stand alone and that a check enforced it; neither was true (#65). `E4` fails
   when the attestation count stops matching the data. Prefer corroboration where it exists — it
   covers 39 of 719 units, so it usually does not.

   **Grade a claim by what it rests on, never by the strongest thing beside it.** `providerId` is
   the source the unit would fall over without; corroboration from a neighbouring unit belongs in
   `evidence`, and `corroborated` means a second provider agreed about *this* unit. Fourteen Prize
   Pack units were once filed as tier-1 photographed specimens on the owner's word because one
   German specimen and one Portuguese listing sat nearby (#64). Checks `S13` and `S14` now hold the
   line: `sourceRef` carries a reference or nothing, and only a cited specimen may claim specimen
   authority.
3. **Never contradict on bare absence.** A source that fails to list a printing has a gap; it has
   not proved the printing does not exist. First prove the source *covers the category* — pokumon
   lists Korean promos, so a missing Korean row there is meaningful; its West coverage is one
   lumped "English" row, so its silence on French means nothing. This rule exists because an
   absence argument produced a false contradiction (`XY-P 149`) that had to be reverted.
4. **A complete official manifest may establish absence,** and only within its stated scope.
   Other final absence decisions must be explicit collection-owner adjudications after reviewing
   all cited claims; they are stored separately and are not attributed to a single provider.
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
  stamps. Never assume a V-token means the same thing across sets — read `variantName`.
- **Technical `finish` vs collector `finishFamily`.** `finish` stays the auditable
  non-holo/holo/reverse-holo/mirror-holo value. `finishFamily` is the presentation layer, where
  reverse-holo and mirror-holo both appear as "Reverse Holo". Never collapse the technical value
  or the underlying printing/checklist IDs merely to group the UI.
- **`markings.role` is a trichotomy.** `print-identity` (rarity symbols, contest credits),
  `reverse-holo-treatment` (EX-era set logos that are part of the reverse design — `DF 10` is the
  worked example), `distribution-promo` (prerelease, Staff, retailer, Pokémon Center marks —
  these do **not** imply a reverse holo).
- **`cardKey` = same card text, not same artwork.** It is Cardmarket's own grouping by name plus
  attack names.
- **"Spanish" is European Spanish only.** LATAM-ES is a physically distinct edition, out of scope.
- **Code cards are excluded** — `verification/excluded_codecards.json`.
- **Physical specimens are cited, not described.** A card the owner holds has a stable id in
  `verification/specimens.json`; a unit references it as `sourceRef: "specimen:SPEC-0002"`. To add
  its photograph: file into `verification/specimens/`, set `photograph` to the filename, rerun
  `review_findings.py`. Never write a new prose description of a specimen — that is what the ids
  replaced.

## Commands

Run from the repository root. **Order matters** and it is this order: `finishes.py` writes the
card finish summaries, `language_status.py` writes the language verdicts, `confirmed_releases.py`
reads both, and `checklist.py` / `site.py` read those.

```console
python verification/review_integrity.py     # confirm a clean starting state
python verification/review_findings.py      # cross-artifact consistency

# ... do the work in a new Python pass under verification/ ...

python verification/audit_evidence.py       # after any write
python verification/test_owner_adjudications.py  # owner decision/store projection regression
python verification/report.py               # regenerate exports
python scripts/editions.py                  # if edition data changed
python scripts/finishes.py                  # finish units/review + main summaries
python scripts/language_status.py           # per-card language verdicts
python scripts/confirmed_releases.py        # chronological JSON + CSV
python scripts/source_registry.py           # provider/evidence registry
python scripts/checklist.py                 # canonical checklist items
python scripts/readme_stats.py              # generated README blocks
python scripts/issue_templates.py           # community correction form
python scripts/open_items.py                # verification/open-items.html
python scripts/database.py                  # current-state application database + audit
python scripts/tracker.py --tracker snoredex-tracker-template.sqlite init --force
python scripts/site.py                      # index.html + alias redirect

python verification/review_integrity.py     # after any write
python verification/review_findings.py      # after any write
```

Eight generators take `--check`, which fails instead of writing: `checklist`, `readme_stats`,
`issue_templates`, `site`, `source_registry`, `open_items`, `analyze`, `database`. The gate runs
those with `--check`, validates the blank tracker template, runs
`finishes.py --reproject`, `language_status.py` and `confirmed_releases.py` for real, and then
asserts `git diff --exit-code` — so a generator whose output would move fails the build either
way. `publish.py` takes `--verify` rather than `--check`.

`python scripts/finishes.py --reproject` redoes only the card projection from the committed store
and needs no network; it is the fast path when a projection rule changes.

A full `finishes.py` run reads TCGdex through a cache under `verification/cache/finish-tcgdex/`.
Entries carry their URL, fetch time, HTTP status, content hash and item count, expire after 30
days, and are never written for a failed or implausible response — an empty body, a non-object, or
anything without an `id` is an error, not an answer. Transient failures (timeouts, 429, 5xx) are
retried with backoff; a 404 is an answer and is not. `--refresh-cache` forces a refetch. Exit 2
means a source could not be reached, matching `verify_finish_sources.py`: the artifacts are not
wrong, the upstream evidence is missing, so retry rather than investigate.

The pre-PR gate, matching CI:

```console
pip install -r requirements.txt
python -m playwright install chromium

python verification/review_findings.py      # stdlib only, no network — quickest invariant check
python scripts/site.py --check
python verification/test_site.py            # browser acceptance tests
python verification/verify_finish_sources.py  # live TCGCSV assertions
```

Serve the site locally with `python -m http.server 8000`, then open <http://localhost:8000/>.
`index.html` is the single public page; `verification/confirmed-releases.html` redirects to it.

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
- The five remaining `scripts/*.ps1` are **dormant history** — `build`, `join`, `getimages`,
  `finalize` and `mkunits`. Their `_chunk*`/`_cards_stage*` inputs are not in the repository and
  are not reproducible (a 2026-07-21 scrape of a live marketplace), so `snorlax_cards.json` is the
  input of record rather than an output. #28 captured that data flow, so they can join the archive.
  `mkunits` is additionally destructive: it rebuilds `units.json` with fresh ids and discards the
  verification state. Never run it.
- **`scripts/analyze.py`** produces `analysis_artists.json`, `analysis_shared_cards.json`,
  `analysis_variants.json` and `analysis_language_drift.json` — nothing else generates them. It
  reads `snorlax_cards.json` only, which is #30's single canonical node. Its PowerShell
  predecessor is archived at `verification/archive/scripts/analyze.ps1`.
- **LF line endings** (check `X1`) and **no UTF-8 BOM** (check `X5`) in tracked text.
- `verification/checks.py` is the check protocol shared by the two suites: `review_integrity.py`
  validates invariants *within* each store, `review_findings.py` validates consistency *between*
  the stores and the artifacts consumers read.

## Counts are reported, never asserted

The integrity suites do not fail on unit totals, coverage or queue depth. Closing an open unit is
the goal, not a regression, so counts are reported as drift against a baseline and only a count
moving **backwards** — the direction that signals data loss — is a finding. Structural facts still
fail the run.

Do not "fix" a rising number by editing the baseline. That is the exact habit this split exists to
prevent: a gate that reddens when the project makes progress is a gate people learn to edit rather
than read.

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

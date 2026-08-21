<!-- doc: role=public entry point for using the data; stage=public -->
# Snoredex Data

**A frozen 2026-07-21 Cardmarket-derived Snorlax candidate universe, with each inherited language
and finish claim re-checked against a source outside Cardmarket — not a complete all-locality
catalogue.**

<!-- generated:badges — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
[![Release gate](https://github.com/m4s-ai/snoredex-data/actions/workflows/release-gate.yml/badge.svg)](https://github.com/m4s-ai/snoredex-data/actions/workflows/release-gate.yml)
[![Legacy cards](https://img.shields.io/badge/legacy_cards-198-2563eb)](legacy-cardmarket-baseline.json)
[![Current-known checklist](https://img.shields.io/badge/current--known_checklist-826_items-2563eb)](analysis_checklist.json)
[![Publication](https://img.shields.io/badge/publication-approved-2ea44f)](publication-decisions.json)
[![Licence](https://img.shields.io/badge/licence-grants_in_force-2ea44f)](LICENSE.md)
[![AI-DECLARATION: copilot](https://img.shields.io/badge/%E4%B7%BC%20AI--DECLARATION-copilot-fee2e2?labelColor=fee2e2)](AI-DECLARATION.md)
<!-- /generated:badges -->

<!-- generated:status — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
> [!IMPORTANT]
> The licence grants are **in force**, granted by `M4S.Collection`. Publication was approved on 2026-07-31: the repository is **public** and the site may be deployed. Deployment stays a manual workflow run — merging never publishes. See
> [`publication-decisions.json`](publication-decisions.json), [`LICENSE.md`](LICENSE.md), and
> [`verification/history/LAUNCH-RUNBOOK.md`](verification/history/LAUNCH-RUNBOOK.md).
>
> **Data coverage:** `cardmarket-search-2026-07-21` is a frozen historical Cardmarket-derived candidate universe, **not a complete all-locality catalogue**. Current totals describe only known rows descended from that baseline. The source-first rebuild is tracked in [#132](https://github.com/m4s-ai/snoredex-data/issues/132).
<!-- /generated:status -->

## Why this exists

A marketplace filter answers *"can I buy this here?"*, not *"was this printed?"* — and collectors
read it as the second question. Ask Cardmarket about `KSS 26` (XY Kalos Starter Set) and it offers
**17 languages**; the expansion was printed in **7**. For some products the filter falls back to a
global language list entirely. Build a collection goal from that and you will hunt cards that were
never made.

So every language and finish claim in this repository is re-derived from evidence *outside*
Cardmarket — an official database, a photographed card, a fan wiki, a seller's photo of the actual
specimen — and each piece of evidence is named, ranked and dated. Where the outside source
disagrees with the marketplace, both survive: the raw claim, and the verdict beside it. The
over-claiming is itself a finding, so it is preserved rather than quietly corrected away.

Two rules hold everywhere in the data, the tooling and the site copy:

1. **Positive evidence only.** A source that fails to list a printing has a *gap*; it has not
   proved the printing does not exist — and no source settles an absence at any tier. Converging
   evidence from dependable sources is what the collection owner weighs; the decision is theirs,
   recorded in `verification/owner_adjudications.json` and never attributed to a single provider.
   `not-printed` means **no regular release**: a proof copy or an error card is a separate
   category and does not falsify the decision.
2. **`pending` means not yet established — never proven absent.** The same goes for `unmapped` and
   `other-product` on the finish side. Nothing here claims non-existence by silence.

## Start here

### Browse the collection

Serve the repository and open the generated single-page browser: sorting, filtering, a printable
checklist, the evidence behind each row, and a correction link on every claim.

```console
python -m http.server 8000
```

Then visit <http://localhost:8000/>. `index.html` is the whole site; nothing else needs building.

### Use the data

| You want | Read | Watch out for |
|---|---|---|
| The immutable pre-migration candidate universe | [`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json) | It records the historical Cardmarket boundary and every inherited card/unit; it is provenance, not an all-locality manifest. |
| A ready-to-use application database | [`snoredex.sqlite`](snoredex.sqlite) / [`DATABASE.md`](DATABASE.md) | Start from the `app_*` views. Historical `contradicted` rows become `disputed` unless a scoped source or explicit owner adjudication resolves them. |
| A personal have/have-not tracker | [`snoredex-tracker-template.sqlite`](snoredex-tracker-template.sqlite) | Copy the blank template or use `scripts/tracker.py`; catalogue sync preserves ownership state. |
| The Cardmarket product view — identity, rarity, art, artist, editions | [`snorlax_cards.json`](snorlax_cards.json) | Use `languagesConfirmed` for established prints and `languagesNeedsEvidence` / `languagesDisputed` for open questions. `languagesRepositoryConfirmed`, `languagesContradicted`, and raw `languages` preserve the research inputs. |
| The current-known list of physical things to collect | [`analysis_checklist.json`](analysis_checklist.json) | One record per documented printing *or* per explicitly unresolved one within current coverage — placeholders are items too. |
| The evidenced locality/era discovery frontier | [`LOCALITY-ERA-MATRIX.md`](verification/LOCALITY-ERA-MATRIX.md) / [`locality_era_matrix.json`](verification/locality_era_matrix.json) | Established, provisional and candidate tracks stay distinct; provider slices are positive frontiers, not complete print manifests. |
| Which languages a card exists in, and on whose word | [`verification/units.json`](verification/units.json) | Keyed by `(setCode, number, variant, language)`. |
| Final owner decisions on disputed claims | [`verification/owner_adjudications.json`](verification/owner_adjudications.json) | Explicit cross-source application decisions; they do not rewrite `units.json` or credit a single provider. |
| Which finishes a card exists in | [`verification/finish_units.json`](verification/finish_units.json) | Keyed by `(setCode, number, language)` — deliberately *not* by variant token. |
| Release chronology | [`analysis_confirmed_releases.json`](analysis_confirmed_releases.json) / [`.csv`](analysis_confirmed_releases.csv) | Dates follow the matching market inside a shared Bulbapedia article. |
| The coverage-versioned release migration | [`analysis_confirmed_releases_reconciled.json`](analysis_confirmed_releases_reconciled.json) / [`.csv`](analysis_confirmed_releases_reconciled.csv) | Preserves all 203 legacy rows while separating positive edition events from visible `needs-evidence` language/date links. |
| Who said what, and how strong it is | [`verification/SOURCES.md`](verification/SOURCES.md), [`verification/source_registry.json`](verification/source_registry.json) | Every claim names a provider and an authority tier. |

Then read [Scope and caveats](#scope-and-caveats--read-before-using) below. Several fields mean
something narrower than their name suggests, and that section is the difference between using this
data and misreading it.

### Report a correction

Wrong row, missing printing, a card in your hand that the data calls `pending` — that is the
contribution this project wants, and it needs no Git, Python or setup. Every row on the site
carries a **Correction?** link that pre-fills what the data currently records.
[`CONTRIBUTING.md`](CONTRIBUTING.md) explains what counts as evidence and how a report is graded.

The one thing that is not a correction: *"it isn't listed on `some-site`, so it does not exist."*
See rule 1 above.

### Work on the repository

Python 3.11, standard library only for the generators. `requirements.txt` is verification-only —
Playwright is used for the browser suite. PowerShell is not needed
for anything. Use Python on every platform; if it is missing, install it rather than
substituting PowerShell.

```console
python -m pip install -r requirements.txt
python -m playwright install chromium

python verification/review_integrity.py     # structural invariants inside each store
python verification/review_findings.py      # consistency between stores and published artifacts
python scripts/legacy_baseline.py --check   # immutable historical boundary + scope wording
python verification/test_evidence_application.py  # raw verdict/application boundary
python verification/test_site.py            # browser acceptance tests
```

Then read [`CLAUDE.md`](CLAUDE.md) for the working rules and command order,
[`HANDOVER.md`](HANDOVER.md) for the current backlog, and
[`verification/RESUME.md`](verification/RESUME.md) before touching a single confirmation or
contradiction — it records the source techniques and the dead ends already paid for here.

## What the project currently holds

<!-- generated:current-state — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
Current-known status snapshot: **2026-08-21**. Its candidate denominator is the immutable legacy baseline `cardmarket-search-2026-07-21`; these totals do not claim all-locality discovery completeness.

| Area | Current state |
|---|---|
| Legacy Cardmarket baseline | **242 products** harvested: **198 singles** retained and 44 accessories excluded. 7 retained products are code cards and are explicitly flagged. |
| Legacy language-claim review | **719 claims**: 635 externally confirmed, 84 contradicted, 0 awaiting manual review, and 0 still open within the legacy candidate universe. Raw Cardmarket languages remain preserved beside their verdicts. |
| Evidence-safe application status | **618 established**, **17 needs evidence**, **80 owner-adjudicated not printed**, and **4 disputed**. Raw verdicts and observations stay queryable; unsupported confirmation does not mint a printing. |
| Current-known physical checklist | **826 items** across 174 cards and 15 languages: 662 documented printings plus 164 explicit unresolved placeholders. |
| Current-known finish evidence | **637 card-number × language units**: 333 externally confirmed, 103 marketplace-only positives, 126 without positive finish evidence, and 75 not applicable. The remaining detail/mapping queue contains 221 units. |
| Evidence registry | **24 providers**, 896 evidence records, 889 unique URLs, and 2,796 attributed claims. Complete official manifests and the separate owner-adjudication store records final cross-source absence decisions. |
| Quality gate | Deterministic generators, structural and evidence audits, cross-artifact consistency checks, and browser regressions run on Ubuntu and Windows for pull requests. |
| Site and publication | The repository is public. The interactive site is generated and usable locally; Pages deployment is approved by the owner but still requires a manual workflow run. |
| Licensing | Verbatim PolyForm Noncommercial 1.0.0 and CC BY-NC-SA 4.0 texts are present and hash-verified. The intended mixed-work grants are active under the recorded owner approvals. |
| AI transparency | Development used AI in a human-directed copilot workflow. Scope and safeguards are declared in [`AI-DECLARATION.md`](AI-DECLARATION.md). |
<!-- /generated:current-state -->

Counts come from the committed stores and are regenerated, never typed. Open items are not debt to
be hidden: closing one is progress, so the checks report count movement as drift and only fail when
a number moves *backwards*.

## How a claim becomes a fact

**One unit, one verdict.** A language unit is `(setCode, number, variant, language)` and carries
exactly one of `confirmed`, `contradicted`, `needs-manual-review` or `pending`. Anything resolved
must cite a source; `verification/review_integrity.py` fails the build if it does not.

**Every source is ranked.** `providerId` names it, `corroborated` says whether a second provider
agreed independently, and `verification/source_registry.json` records the authority tier:

<!-- generated:authority-tiers — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
| Tier | Sources |
|---|---|
| 1 | Inspected physical specimen · Play! Pokémon rewards gallery · Pokémon Card official database (Asia) · Pokémon Card official database (Japan) · Pokémon Card official database and rules (Korea) · The Pokémon Company official cards and checklists |
| 2 | 52poke (Wiki) · Bulbapedia · CGC certification and registry · Cardmarket seller listing photograph · Collection owner attestation · Elite Fourum · PSA certification and registry · SNKRDUNK · TCGdex · pokemontcg.io |
| 3 | LigaPokemon · Limitless TCG · Retailer and specialist card listings · TCGCSV (TCGplayer product data) · koreanpokemoncards.com · pokumon.com |
| 5 | Cardmarket · Internal derivation from a sibling record |

Tiers 1, 2, 3 grade external evidence, strongest first. Tier 5 is not a weaker rung: it marks what is **not** external evidence — the marketplace catalogue this project exists to check, and attributes carried across from a sibling printing of the same card. There is deliberately no tier 4.
<!-- /generated:authority-tiers -->

**A single source may carry a claim, and usually does.** The rule check `E3` enforces is
*checkable or strong*: evidence with **no URL** — the owner's word, a card inspected in hand — must
come from tier 1 or 2, because nobody else can go and look at it. A tier-3 page anyone can open may
stand alone, and hundreds of claims do. That line is deliberate: a Bulbapedia set list is weaker
than an official database but it is not unverifiable, whereas an unlinkable claim from a weak source
is neither strong nor checkable.

So read the tier beside a claim rather than assuming corroboration. Corroboration is preferred
throughout this project and is genuinely uncommon:

<!-- generated:evidence-strength — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
| How the claim is sourced | Resolved claims |
|---|---:|
| Corroborated by a second provider | 38 |
| Single tier 1-2 source | 676 |
| Single tier 3 source | 5 |

681 of 719 resolved claims rest on one provider. Check `E3` does not forbid that: it requires an uncorroborated claim to be **checkable or strong**, so a tier-3 page anyone can open may carry one alone, and 5 do. What it forbids is a claim that is neither — all 35 claims with no URL come from tier 1 or 2, where the evidence is the owner's own cards.
<!-- /generated:evidence-strength -->

The physical cards behind the non-URL claims have stable ids in
[`verification/specimens.json`](verification/specimens.json) and are cited, never re-described in
prose — and only a *cited* specimen may claim specimen authority (check `S14`).

**Language truth and finish truth are separate layers.** `units.json` answers "was this printed in
this language?"; `finish_units.json` answers "which finishes exist for this set number and
language?" They have separate backlogs, and a confirmed language claim never implies a finish.

**Changes arrive as code, not edits.** Findings are written as a new Python pass under
`verification/`, then the generators and both check suites are re-run;
`units.json` and `finish_units.json` are never hand-edited. [`CLAUDE.md`](CLAUDE.md) has the
required command order.

## How the repository is built

The pipeline has two halves, and only one of them can be re-run.

**The harvest is historical.** `build` → `join` → `getimages` → `finalize` read the captured
Cardmarket result pages and hand `snorlax_cards.json` to everything downstream. Those inputs are
not in the repository and are **not reproducible**: they are a scrape of a live marketplace from
2026-07-21, and the same search today returns different products, prices and language filters.
Re-scraping would not rebuild this dataset, it would produce a different one. **`snorlax_cards.json`
is therefore an input to this repository, not an output of it** — the evidence layer is what is
maintained here. `mkunits` is in the same category and destructive besides: it rebuilds
`verification/units.json` with fresh ids, discarding every verification verdict. It is not part of
any rebuild.

[`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json) freezes that candidate
universe with its source commit, file hashes, counts and every inherited card/unit membership. It
never expands with the current catalogue. Cardmarket is therefore one historical provider, not the
discovery boundary; the source-first rebuild is tracked in
[#132](https://github.com/m4s-ai/snoredex-data/issues/132).

**Everything downstream regenerates from what is committed**, in this order, and the release gate
proves it by running the generators and failing if the tree moves:

```console
python scripts/analyze.py          # analysis_artists, _shared_cards, _variants, _language_drift
python scripts/finishes.py --reproject
python scripts/language_status.py
python scripts/confirmed_releases.py
python scripts/legacy_set_reconciliation.py
python scripts/source_registry.py
python scripts/checklist.py
python scripts/readme_stats.py
python scripts/issue_templates.py
python scripts/open_items.py
python scripts/database.py
python scripts/tracker.py --tracker snoredex-tracker-template.sqlite init --force
python scripts/site.py
```

Order matters: `finishes.py` writes the card finish summaries, `language_status.py` writes the
language verdicts, and everything after reads both. Every script resolves the checkout from its own
location, so any working directory works. The full CI sequence lives in
[`.github/workflows/release-gate.yml`](.github/workflows/release-gate.yml); merging never
publishes, and Pages deployment stays a manual, gated workflow run.

## Scope and caveats — read before using

- **`languages` is marketplace availability, not a print manifest — proven, not suspected.**
  Cross-checking every card × language against outside sources produced contradictions: cases where
  Cardmarket offers a language for which no printing exists, `KSS 26` being the clearest. The raw
  field is preserved because the over-claiming is the finding; the repository verdict lives beside
  it in `languagesRepositoryConfirmed` / `languagesContradicted`, while the evidence-safe
  application view uses `languagesConfirmed` / `languagesNeedsEvidence`. See
  [`verification/CONTRADICTED.json`](verification/CONTRADICTED.json).
- **A repository confirmation may still need card-level evidence.** A set/product release or a
  sibling printing is retained as an observation but cannot establish this exact card unless the
  step to the card is positively supported. Those rows are `languagesNeedsEvidence`, are also in
  `languagesUnresolved`, and do not enter chronological or checklist outputs.
- **A contradicted language is not automatically a proven absence.** `languagesContradicted`
  splits into `languagesNotPrinted` — where an explicit owner adjudication or a complete official
  manifest settled the question — and `languagesDisputed`, where a source disagrees and nothing
  has settled it. **79 are settled; 5 are disputed.** Both are excluded from the checklist, so
  that nobody is sent hunting a printing the evidence points away from, but only the first is a
  claim that the card does not exist. A photograph would overturn a disputed row.
- **Every "Spanish" claim here means European Spanish.** From Journey Together (2025), LATAM-ES is
  a physically distinct edition for regular sets — different attack translations, set name and set
  code (specimen-verified on `SVP 184`). Cardmarket does not carry it, so it is absent from this
  legacy candidate universe; that absence is not evidence that the printing does not exist.
  LATAM-ES came **into scope on 2026-08-09** as its own locality and no rows are recorded yet —
  the discovery work is [#139](https://github.com/m4s-ai/snoredex-data/issues/139).
- **`cardKey` groups the same *card*, not the same *artwork*.** It is Cardmarket's own grouping by
  card name plus attack names, so a reprint with brand-new art shares the key. Useful — it is how
  the re-illustrated reprints were found — but never read it as art identity.
- **Artist coverage is partial.** Illustrators come from pokemontcg.io/limitlesstcg
  (English-market), the official pokemon-card.com database (Japanese-market) and exact release
  histories. Mostly Korean and Chinese deck products publish no illustrator credit, so `artist`
  stays `null` there rather than being guessed; use `cardKey` to find a sibling that has one.
- **`variantAxes` and `hasReverseHolo` are marketplace hints, not the finish manifest.** The two
  finish layers answer different questions: `finishAvailability` on a card says what evidence
  attributes to *this Cardmarket product*, while `finish_units.json` says what is known for the
  *set number and language*, whichever product carries it. Product attribution is the weaker of the
  two, so each card row also carries `unitAvailableFinishes` and `unitFinishStatus` from the store.
  Read the status words exactly: `pending` = no positive evidence anywhere in the unit; `unmapped`
  = the finish is known but not yet attributed to a product; `other-product` = attributed to a
  different listing of the same card. None of the three ever means "does not exist".
- **A Cardmarket V-token is not a finish, and is set-specific.** TCGdex's `normal`/`holo`/`reverse`
  flags apply to the set number and language; a `V1`/`V2`/`V3` mapping is recorded only where it is
  unambiguous or independently identified. `xsv2a` and `xm2a` order the same two treatments
  differently — always read `variantName`.
- **Marking role is a trichotomy.** `print-identity` covers rarity symbols and contest credits;
  `reverse-holo-treatment` covers EX-era set-logo stamps that *are* part of the reverse design;
  `distribution-promo` covers prerelease, Staff, retailer and Pokémon Center stamps, which do
  **not** imply a reverse holo.
- **Release dates follow the matching market inside a shared Bulbapedia article.** A page such as
  Gym Challenge carries both `enrelease` and `jarelease`; the translated set name decides which
  applies. Reviewed records in
  [`verification/bulbapedia_release_dates.json`](verification/bulbapedia_release_dates.json) take
  precedence over the generic API fallback, and where a field lists several regional waves the
  chronological row uses the first and records that choice. The full set-by-set review is
  [`verification/history/BULBAPEDIA-RELEASE-DATE-AUDIT.md`](verification/history/BULBAPEDIA-RELEASE-DATE-AUDIT.md).
- **Code cards are excluded from the checklist** and flagged in the dataset —
  [`verification/excluded_codecards.json`](verification/excluded_codecards.json).

## Finishes, foil patterns, and stamps

Finish availability is modelled independently of Cardmarket products, keyed by set number ×
language. Because upstream catalogues are incomplete, it is deliberately a **positive-evidence
model**: an unlisted finish stays `pending` rather than being marked unavailable, and only a
complete official manifest — which a handful of English units have — may say a finish is absent.

<!-- generated:finish-coverage — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
| Known available finish | Set-number-language units |
|---|---:|
| Non-Holo | 271 |
| Holo | 144 |
| Reverse Holo family | 243 |
| Both Non-Holo and Holo | 18 |
<!-- /generated:finish-coverage -->

Units can appear in more than one row. The site and checklist present three collector-facing
families — **Non-Holo**, **Holo**, **Reverse Holo** — where Reverse Holo aggregates the technical
`reverse-holo` and `mirror-holo` values. The technical layer is never collapsed: each unit keeps
its `finishStatus`, its physical `printings`, and the exact Poké Ball, Master Ball, energy, tiled
or stamped treatment, each with its own checklist item.

Checklist items therefore carry both: `finish` (the auditable technical value), `finishFamily` (the
collector-facing projection), `foilPattern`, `markings` including the role, plus `distribution` and
`cardSize`.

That split settles two cases that are easy to confuse. `DF 10` has a normal holo printing and an
EX Dragon Frontiers reverse holo whose set-logo stamp is intrinsic to the reverse treatment. By
contrast `CL 33`, `VIV 131` and `SVP 184` carry later prerelease/Staff stamps recorded as
distribution promos — the stamp does not make a card reverse holo. The regular `JTG 117` records
holo and intricate-tile reverse-holo availability by language; the non-holo Hop's Snorlax is the
Prize Pack product (`PPS8 JTG 117` V1), a separate printing. Keeping those apart is exactly what
the product/finish split is for.

[`verification/FINISH_SOURCES.md`](verification/FINISH_SOURCES.md) has the evidence ladder and the
confirmed Prize Pack, promo, stamped, deck and jumbo cases;
[`verification/FINISH_REVIEW.csv`](verification/FINISH_REVIEW.csv) is what is still queued. Run
`python scripts/finishes.py` after
rebuilding the main dataset; it caches TCGdex responses under the gitignored
`verification/cache/finish-tcgdex/` and reattaches per-product summaries to `snorlax_cards.json`.

## Findings

[`FINDINGS.md`](FINDINGS.md) collects what the catalogue turned up: where language coverage departs
from the regional baselines, the 38 cards printed in more than one release and which of them were
re-illustrated, what each Cardmarket variant cluster turned out to be, and how the one-off harvest
was run against a Cloudflare-protected marketplace.

## Repository map

All paths are relative to the repository root.

| Path | Purpose |
|---|---|
| [`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json) | Immutable source commit, hashes, counts and membership of the historical Cardmarket candidate universe. |
| [`snorlax_cards.json`](snorlax_cards.json) | Main product dataset — one record per Cardmarket single. |
| [`snoredex.sqlite`](snoredex.sqlite) · [`DATABASE.md`](DATABASE.md) | Normalized current-state application handoff, with no evidence journal or migration history. |
| [`snoredex-tracker-template.sqlite`](snoredex-tracker-template.sqlite) | Blank, refreshable ownership tracker with `have`, `wanted`, quantity and notes. |
| [`analysis_checklist.json`](analysis_checklist.json) | Canonical physical checklist, documented printings and explicit placeholders alike. |
| [`index.html`](index.html) | The generated collection browser. The only public page; `verification/confirmed-releases.html` redirects to it. |
| [`images/`](images/) | Third-party card images used for identification; excluded from this project's licence grants. |
| [`verification/`](verification/) | The evidence layer: state stores (`units.json`, `finish_units.json`), specimens, the check suites, and the write passes that produced the data. |
| [`verification/source_adapter_staging.json`](verification/source_adapter_staging.json) | Source-first local-set staging feed: 12 locale slices, raw provenance/accounting and explicit unresolved source tracks; proposals only, never verdicts. |
| [`scripts/`](scripts/) | The generators — data, finish model, checklist, chronology, issue templates, site and publication artifact. |
| [`site/`](site/) | Source CSS and JavaScript for the generated site. |
| [`CLAUDE.md`](CLAUDE.md) · [`AGENTS.md`](AGENTS.md) | Working rules for an agent: non-negotiables, data-model traps, command order. |
| [`HANDOVER.md`](HANDOVER.md) | Cold-start guide and prioritised backlog. |
| [`verification/RESUME.md`](verification/RESUME.md) | Verification playbook — source techniques, corrections, dead ends. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to report a correction and how it is graded. |
| [`verification/history/LAUNCH-RUNBOOK.md`](verification/history/LAUNCH-RUNBOOK.md) | Ordered steps to take the site public, and what each approval attests. |

## Licence, attribution and AI transparency

A mixed work, and explicitly **not** OSI open source: **PolyForm Noncommercial 1.0.0** for the
code, **CC BY-NC-SA 4.0** for the data selection, arrangement and annotation. Card images,
artwork, names and trademarks are third-party rights this project does not hold and does not
grant. See [`LICENSE.md`](LICENSE.md) and
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Development used AI in a human-directed copilot workflow, declared under specification 0.1.2 in
[`AI-DECLARATION.md`](AI-DECLARATION.md).

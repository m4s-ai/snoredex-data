# Snoredex Data

Evidence-backed data and collection tooling for every Snorlax Pokémon TCG product found on
Cardmarket.

<!-- generated:badges — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
[![Release gate](https://github.com/m4s-ai/snoredex-data/actions/workflows/release-gate.yml/badge.svg)](https://github.com/m4s-ai/snoredex-data/actions/workflows/release-gate.yml)
[![Cards](https://img.shields.io/badge/cards-198-2563eb)](snorlax_cards.json)
[![Checklist](https://img.shields.io/badge/checklist-838_items-2563eb)](analysis_checklist.json)
[![Publication](https://img.shields.io/badge/publication-approved-2ea44f)](publication-decisions.json)
[![Licence](https://img.shields.io/badge/licence-grants_in_force-2ea44f)](LICENSE.md)
[![AI-DECLARATION: copilot](https://img.shields.io/badge/%E4%B7%BC%20AI--DECLARATION-copilot-fee2e2?labelColor=fee2e2)](AI-DECLARATION.md)
<!-- /generated:badges -->

The repository combines a preserved Cardmarket catalogue with an independent evidence layer. It
distinguishes marketplace claims from confirmed physical printings, models finishes and editions,
and produces a stable machine-readable checklist plus an interactive collection browser.

<!-- generated:status — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
> [!IMPORTANT]
> The licence grants are **in force**, granted by `M4S.Collection`. Publication was approved on 2026-07-31: the repository is **public** and the site may be deployed. Deployment stays a manual workflow run — merging never publishes. See
> [`publication-decisions.json`](publication-decisions.json), [`LICENSE.md`](LICENSE.md), and
> [`verification/LAUNCH-RUNBOOK.md`](verification/LAUNCH-RUNBOOK.md).
<!-- /generated:status -->

## Current state

<!-- generated:current-state — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
Status snapshot: **2026-08-01**, after the database review and release-readiness work merged to `main`.

| Area | Current state |
|---|---|
| Cardmarket catalogue | **242 products** harvested: **198 singles** retained and 44 accessories excluded. 7 retained products are code cards and are explicitly flagged. |
| Language verification | **719 claims**: 634 externally confirmed, 71 contradicted, 5 awaiting manual review, and 9 still open. Raw Cardmarket languages remain preserved beside their verdicts. |
| Physical checklist | **838 items** across 174 cards and 15 languages: 663 documented printings plus 175 explicit unresolved placeholders. |
| Finish evidence | **637 card-number × language units**: 332 externally confirmed, 103 marketplace-only positives, 138 without positive finish evidence, and 64 not applicable. The remaining detail/mapping queue contains 233 units. |
| Evidence registry | **18 providers**, 878 evidence records, 871 unique URLs, and 2,777 attributed claims. Only complete official manifests may establish absence. |
| Quality gate | Deterministic generators, structural and evidence audits, cross-artifact consistency checks, and browser regressions run on Ubuntu and Windows for pull requests. |
| Site and publication | The repository is public. The interactive site is generated and usable locally; Pages deployment is approved by the owner but still requires a manual workflow run. |
| Licensing | Verbatim PolyForm Noncommercial 1.0.0 and CC BY-NC-SA 4.0 texts are present and hash-verified. The intended mixed-work grants are active under the recorded owner approvals. |
| AI transparency | Development used AI in a human-directed copilot workflow. Scope and safeguards are declared in [`AI-DECLARATION.md`](AI-DECLARATION.md). |
<!-- /generated:current-state -->

The counts above come from the committed data stores. Generated dates can differ by artifact when
the underlying evidence did not change; use `snorlax_cards.json` and
`verification/finish_units.json` as the authoritative count sources.

## Use the project

- Browse the collection and build a printable checklist by serving the repository and opening
  `index.html`:

  ```console
  python -m http.server 8000
  ```

  Then visit <http://localhost:8000/>.

- Consume [`snorlax_cards.json`](snorlax_cards.json) for the Cardmarket product view. Use
  `languagesConfirmed`, `languagesContradicted`, and `languagesUnresolved` instead of treating the
  raw `languages` field as a print manifest.
- Consume [`analysis_checklist.json`](analysis_checklist.json) for stable physical-collectible
  items, or [`verification/finish_units.json`](verification/finish_units.json) for the underlying
  positive-evidence finish model.
- Before adding or changing evidence, read [`HANDOVER.md`](HANDOVER.md) and
  [`verification/RESUME.md`](verification/RESUME.md). They capture the source ladder, failed
  approaches, invariants, and remaining work.

## Validate a checkout

Python 3.11 is the supported baseline. PowerShell is no longer required for anything: the last
step that needed it, `analyze.ps1`, is now `scripts/analyze.py`. The browser suite also needs Playwright's
Chromium installation.

```console
python -m pip install -r requirements.txt
python -m playwright install chromium
python verification/review_integrity.py
python verification/audit_evidence.py
python verification/review_findings.py
python verification/test_site.py
```

The complete CI sequence, including deterministic regeneration and public-artifact hygiene, lives
in [`.github/workflows/release-gate.yml`](.github/workflows/release-gate.yml).

## Repository map

All paths and commands are relative to the repository root. Every script resolves the checkout
from its own file location and can be invoked from any working directory.

| Path | Purpose |
|---|---|
| [`snorlax_cards.json`](snorlax_cards.json) | **Main product dataset** — 198 singles with identity, language verdicts, rarity, image, variant data, artist, editions, and product-level finish summaries. |
| [`analysis_checklist.json`](analysis_checklist.json) | **Canonical physical checklist** — one stable record per documented printing, or per explicitly unresolved one. |
| [`index.html`](index.html) | Generated collection browser with sorting, filtering, checklist building, methodology, sources, and licence notices. |
| [`images/`](images/) | 198 third-party card images used for identification; excluded from this project's licence grants. |
| [`verification/units.json`](verification/units.json) | Language-verification state store: one row per card × language × variant claim. |
| [`verification/finish_units.json`](verification/finish_units.json) | Finish state store: one row per set number × language with logical printings, evidence, and product mappings. |
| [`verification/bulbapedia_release_dates.json`](verification/bulbapedia_release_dates.json) | Reviewed set-code → Bulbapedia page/field/date overrides used by the chronological export. |
| [`verification/BULBAPEDIA-RELEASE-DATE-AUDIT.md`](verification/BULBAPEDIA-RELEASE-DATE-AUDIT.md) | Full 133-set audit coverage and all 45 prior → corrected date differences. |
| [`verification/SOURCES.md`](verification/SOURCES.md) | Human-readable provider and evidence index generated from `source_registry.json`. |
| [`verification/FINISH_REVIEW.csv`](verification/FINISH_REVIEW.csv) | Remaining finish, pattern, and Cardmarket-product mapping queue. |
| [`scripts/`](scripts/) | Reproducible data, verification, checklist, issue-template, publication, and site generators. |
| [`site/`](site/) | Source CSS and JavaScript for the generated site. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to report a correction, what counts as evidence, and how reports are graded. |
| [`verification/LAUNCH-RUNBOOK.md`](verification/LAUNCH-RUNBOOK.md) | Ordered steps to take the site public, and what each approval attests. |
| [`HANDOVER.md`](HANDOVER.md) | Cold-start guide, working rules, invariants, and prioritized next actions. |
| [`verification/RESUME.md`](verification/RESUME.md) | Detailed verification playbook, source techniques, corrections, and dead ends. |
| [`LICENSE.md`](LICENSE.md) / [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | Licensing scope, licensor and contact, exclusions, attribution, and third-party rights. |
| [`AI-DECLARATION.md`](AI-DECLARATION.md) | Structured disclosure of AI involvement under the [`AI-DECLARATION.md` 0.1.2 specification](https://ai-declaration.md/en/0.1.2/). |

### How the data is produced

The pipeline has two halves, and only one of them can be re-run (#28).

**The harvest is historical.** `build` → `join` → `getimages` → `finalize` read
`_chunk1..3.json`, the captured Cardmarket result pages, and hand `snorlax_cards.json` to
everything downstream. Those chunks are not in the repository and are not reproducible: they are a
scrape of a live marketplace from 2026-07-21, and re-running the search today returns different
products, prices and language filters. Re-scraping would not rebuild this dataset, it would
produce a new one. **`snorlax_cards.json` is therefore an input to this repository, not an output
of it** — the evidence layer is what is maintained here, and every claim in it cites a source that
can be checked independently of the harvest.

`mkunits` is in the same category and is destructive besides: it rebuilds `verification/units.json`
from scratch with freshly numbered ids, discarding the verification state of all 719 units. It is
not part of any rebuild.

**Everything downstream regenerates from what is committed**, and the release gate proves it by
running the generators and failing if the output differs from the tree:

```console
python scripts/analyze.py          # analysis_artists, _shared_cards, _variants, _language_drift
python scripts/finishes.py --reproject
python scripts/language_status.py
python scripts/confirmed_releases.py
python scripts/source_registry.py
python scripts/checklist.py
python scripts/readme_stats.py
python scripts/issue_templates.py
python scripts/site.py
```

`scripts/analyze.py` reads `snorlax_cards.json` and nothing else. Its PowerShell predecessor
preferred whichever `_cards_stage*.json` happened to be present, which made the canonical input
depend on the working directory; the port is what closes #30's single-canonical-node criterion.

Scraping covered all nine result pages for Cardmarket's Pokémon product search for “snorlax.”

## Scope and caveats — read before using

- **`languages` is marketplace availability, not a print manifest — and this is now proven, not just suspected.** Cross-checking every card × language against outside sources produced **71 contradictions**: cases where Cardmarket offers a language for which no printing exists. The clearest is `KSS 26` (XY Kalos Starter Set), where Cardmarket advertises **17 languages** and the expansion was printed in **7** (EN, DE, FR, IT, ES, PT, RU). For some products the filter falls back to a global language list. See `verification/CONTRADICTED.json`.
- **"Spanish" cannot distinguish European from Latin-American Spanish.** From Journey Together (2025) LATAM-ES is a physically distinct edition for regular sets — not Prize Packs — with different attack translations, set name and set code (specimen-verified for `SVP 184`: "Presión Dinámica"/"Juntos de Aventuras" vs "Plancha Dinámica"/"Aventuras Compartidas"). Cardmarket does not support LATAM-ES; sourcing it would require the official Pokémon site. Every Spanish entry here means the European print. See `verification/RESUME.md`.
- **`cardKey` groups the same *card*, not the same *artwork*.** Cardmarket derives it from card name + attack names. Reprints with brand-new art share a `cardKey`. That's a feature here — it's exactly how the "same card, new art" cases below were found — but don't read it as art identity.
- **Artist coverage is 116/198 (59%).** Illustrators come from pokemontcg.io/limitlesstcg (English-market), the official pokemon-card.com database (Japanese-market), and exact card release histories such as Bulbapedia's EXS Snorlax record. The uncovered rows are mostly Korean/Chinese deck products with no published illustrator credit. Rather than guess, `artist` is left `null` there; use `cardKey` to find a sibling that has one.
- **`variantAxes` and `hasReverseHolo` are marketplace hints, not the finish manifest.** The two finish layers answer *different* questions, so pick deliberately rather than treating them as alternatives. `finishAvailability` on a card answers “what does evidence attribute to **this Cardmarket product**?” `verification/finish_units.json` answers “what is known for this **set number and language**, whichever product carries it?” Product attribution is necessarily the weaker of the two, so each card row also carries `unitAvailableFinishes` and `unitFinishStatus` from the store. Read the status words exactly: `pending` means no positive evidence anywhere in the unit; `unmapped` means the finish is known but no product is attributed yet; `other-product` means it is attributed to a different listing of the same card. None of the three ever means “does not exist.”
- **`languages` is the raw Cardmarket claim; the verdict lives beside it.** Each card carries `languagesConfirmed`, `languagesContradicted`, and `languagesUnresolved`. Use `languagesConfirmed` for printings backed by an outside source — 36 products still list at least one language this project has itself refuted, and `languages` deliberately preserves that claim because the over-claiming is a finding.
- **Release dates follow the matching market inside a shared Bulbapedia article.** A page such as Gym Challenge carries both the English `enrelease` and Japanese `jarelease`; the translated set name determines which field applies. Forty-five reviewed records in `verification/bulbapedia_release_dates.json` take precedence over the generic API fallback, and sourced dates in the site link to the exact page/field. Where one product field lists several regional launches or waves, the chronological row uses the first release and records that choice in the manifest note.
- **A Cardmarket V-token is not a finish.** TCGdex's `normal`/`holo`/`reverse` flags apply to the set number and language; `V1`/`V2`/`V3` mapping is recorded only when it is unambiguous or independently identified.
- **Marking role matters.** Printed identity features such as rarity symbols and contest credits use `markings.role: "print-identity"`. EX-era set-logo stamps that form part of the reverse-holo design use `markings.role: "reverse-holo-treatment"`. Later prerelease, Staff, retailer, and Pokémon Center stamps use `markings.role: "distribution-promo"` and do not imply reverse holo.

## Language drift

Baselines: Western = EN/FR/DE/ES/IT/PT · Japanese-market = JA/KO/T-Chinese.

**Narrower than baseline**

| Card | Set | Missing |
|---|---|---|
| Snorlax `SK 100` | Skyridge | FR, ES, PT |
| Snorlax `RR 33/81`, Snorlax LV.X `RR 111` | Rising Rivals | ES, PT |
| Snorlax δ `DF 10` | EX Dragon Frontiers | ES, PT |
| Snorlax `FL 15` | EX FireRed & LeafGreen | ES, PT |
| Snorlax `CL 33` | Call of Legends | ES, PT |
| Snorlax `B2 30`, `LC 64`, Rocket's Snorlax `GH 33` | Wizards era | EN only |
| Rocket's Snorlax ex `TRR 104` | EX Team Rocket Returns | EN + PT only |
| Snorlax `CLV 016` | TCG Classic | EN only |
| Snorlax Lv.40 `Pt2 070`, Snorlax δ `PCG9 001`, `PCG1 074` | JP-only sets | KO, T-Chinese |
| Snorlax GX `SM-P 1`, Eevee & Snorlax GX `SM-P 297` | Sun & Moon Promos | T-Chinese |

**Wider than baseline**

| Extra language | Cards |
|---|---|
| Dutch | Jungle `JU 11` / `JU 27`, Wizards Promo `WP 49` |
| Russian | `BKT 118`, `FCO 77`, `FLF 80`, `GEN 58` |
| Polish | Diamond & Pearl `DP 37` |
| Indonesian + Thai | modern JP sets (`sv2a`, `sv4a`, `s10a`, `s10b`, `s5a`, `s8b`, `m2a`, `svM`) |
| Thai only | `sv5a 051`, `sv4K 059` |
| S-Chinese alongside JP | `s4 84`, `sI100 341/342`, `sH 038`, `svIba 046` |

Two genuine outliers, both worth knowing about:

- **`KSS 26` (XY Kalos Starter Set) — 17 languages**, including Czech and Hungarian. Starter-set products were distributed far wider than booster sets.
- **`SVP 051` splits.** Cardmarket carries two products for the same promo number: one with the full 6 Western languages, one **English-only** (`-V2`, 20 listings). Same card, different distribution — a real drift case, not a data error.

<!-- generated:market-split — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
The market split across all 198: Western 87 · Japanese 68 · Simplified Chinese 37 · SEA promo 5 · Traditional Chinese 1.
<!-- /generated:market-split -->

`market` records which regional catalogue Cardmarket lists a product in — a marketplace claim, like
`languages` beside it. It is independent of what the product *is*: that is `isCodeCard`, derived
from the product name, and the 7 code cards are spread across markets rather than forming one.

## Shared art across releases

38 cards appear in more than one release. The interesting split is between *reprints that kept the art* and *reprints that commissioned new art*.

**Same card, genuinely new artwork** — these are the ones to know:

| Card | Printings | Artists |
|---|---|---|
| Snorlax — *Voraciousness / Thudding Press* | 17 across 11 sets | **HYOGONOSUKE** (`MEW 143`) · **GOSSAN** (`SVP 051`) · **Shigenori Negishi** (`PAF 202` Shiny) |
| Eevee & Snorlax GX | 12 across 6 sets | **Mitsuhiro Arita** (`TEU 120`) · **5ban Graphics** (`TEU 171/191`) · **Tomokazu Komiya** (`SM 169`) |
| Snorlax — *Gormandize / Body Slam* | 11 across 8 sets | **Atsuko Nishida** (`VIV 131`) · **Narumi Sato** (`SWSH 068`) · **Saki Hayashiro** (`CRE 224` Secret) |
| Hop's Snorlax | 15 across 10 sets | **GOSSAN** (`JTG 117` + prize packs) · **OKACHEKE** (`SVP 184`) |
| Snorlax — *Unfazed Fat / Thumping Snore* | 12 across 10 sets | **0313** (`LOR 143`) · **Kouki Saitou** (`LOR TG10` Illustration Rare) |
| Snorlax — *Heavy Impact* | 8 across 6 sets | **Oswaldo KATO** (`FST 206`) · **Asako Ito** (`CRZ 109`) |
| Snorlax V — *Swallow / Falling Down* | 7 across 4 sets | **Masakazu Fukuda** (`SSH 141`) · **aky CG Works** (`SSH 197` alt) |
| Snorlax — *Rolling Tackle / Heavy Impact* | 5 across 5 sets | **chibi** (`SSH 140`) · **Tika Matsuno** (`SWSH 032`) |

**Same art reused across releases** (single artist across every printing) — notably `Snorlax-Thick-Skinned-Body-Slam` (7 printings, all **Ken Sugimori**, Jungle → Base Set 2 → Legendary Collection → XY promos → JP Pokémon Jungle), `Snorlax-VMAX-G-Max-Fall` (7, all **aky CG Works**), `Snorlax-But-First-Food-Heavy-Impact` (6, all **Souichirou Gunjima**), `Snorlax-Collect-Collapse` (6, all **Eri Yamaki**).

**Most-used illustrators:** Ken Sugimori (7 English printings), 5ban Graphics (4), Mitsuhiro Arita (4), Kouki Saitou (3), aky CG Works (3).

## Finishes, foil patterns, and stamps

Finish availability is modeled independently of Cardmarket products. The authoritative file has
**637 set-number-language units**. It currently records at least one externally confirmed finish
for **332**, a marketplace-only positive claim for **103**, and no positive finish evidence yet
for **138 applicable units**. Another **64** units are `not-applicable` because every underlying
product-language claim is contradicted. Because upstream catalogues are incomplete, this is
deliberately a positive-evidence model: an unlisted finish remains `pending` rather than being
marked unavailable. The remaining review queue contains **233** units after those false-language
claims and newly sourced cases are removed. Four English units have an official
`complete-manifest`; all other sourced units remain explicitly positive-only.

Current positive coverage (units can appear in more than one row):

<!-- generated:finish-coverage — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
| Known available finish | Set-number-language units |
|---|---:|
| Non-Holo | 270 |
| Holo | 145 |
| Reverse Holo family | 242 |
| Both Non-Holo and Holo | 18 |
<!-- /generated:finish-coverage -->

The public site and checklist use three collector-facing finish families: **Non-Holo**, **Holo**,
and **Reverse Holo**. Reverse Holo aggregates the technical `reverse-holo` and `mirror-holo`
classifications, while the exact Poké Ball, Master Ball, energy, tiled, stamped, or other treatment
remains visible and keeps its own physical checklist item.

Each finish unit still contains the auditable technical `finishStatus` values `non-holo`, `holo`,
`reverse-holo`, and `mirror-holo`, plus one or more physical `printings`. The technical dimensions
remain separate, and checklist items add the collector-facing projection:

- `finish` — non-holo, holo, reverse-holo, mirror-holo, or temporarily unknown;
- `finishFamily` — the collector-facing projection used by checklist items; both reverse-holo and
  mirror-holo map to Reverse Holo;
- `foilPattern` — for example Cosmos, crosshatch, tiled type symbol, Poké Ball, or Master Ball;
- `markings` — a physical set logo, Staff, retailer, or Pokémon Center stamp, including its role;
- `distribution` and `cardSize` — how it was released and whether it is standard or jumbo.

The distinction fixes two easy-to-confuse cases. `DF 10` has a normal holo printing and an
EX Dragon Frontiers reverse holo whose set-logo stamp is intrinsic to that reverse treatment.
By contrast, `CL 33`, `VIV 131`, and `SVP 184` have later prerelease/Staff set-name stamps recorded
as distribution promos; the stamp itself does not make a card reverse holo. The regular `JTG 117`
records holo and intricate-tile reverse-holo availability by language — **not** non-holo. The
non-holo Hop's Snorlax is the Prize Pack product (`PPS8 JTG 117` V1), a separate printing; keeping
them apart is exactly what the product/finish split is for.

Source strength and completeness are explicit. Only a complete official checklist may establish
that a listed alternative is absent; API flags, TCGplayer/TCGCSV subtypes, PSA registries, and scans
are positive-only. See [`verification/FINISH_SOURCES.md`](verification/FINISH_SOURCES.md) for the
evidence ladder and the confirmed Prize Pack, promo, stamped, deck, and jumbo cases.

Two checks guard this layer: `python verification/review_findings.py` (cross-artifact
consistency, publication readiness, and the checklist regression fixtures) and
`python verification/review_integrity.py` (structural invariants). Neither asserts counts —
rising numbers are verification progress, not regressions.

Run `python scripts/finishes.py` after rebuilding the main dataset. It caches TCGdex responses in
the gitignored `verification/cache/finish-tcgdex/`, regenerates all finish outputs, and reattaches
the per-product summaries to `snorlax_cards.json`.

## Cardmarket product variants

17 set+number clusters hold more than one Cardmarket product. `variantToken` preserves Cardmarket's
opaque V1/V2/V3 split; it does not have a universal meaning. `variantAxes` preserves Cardmarket's
filter UI only as a hint.

Examples: `xsv2a 143` maps V1 to Poké Ball mirror holo and V2 to Master Ball mirror holo;
`PPS8 JTG 117` maps V1 to non-holo and V2 to Cosmos holo; `SSH 142` separates standard and jumbo
products; `xJTG 117` has three distribution stamps, all independently identified as Cosmos holo.

## Collection method

Cardmarket sits behind Cloudflare with a **rolling quota of roughly 55–60 requests per window**, independent of pacing — pausing between requests does not avoid it, and once tripped it returns HTTP 429 for several minutes. Recovery is a top-level navigation, which re-solves the challenge and restores access; scraping state was kept in `localStorage` so those recovery navigations didn't lose progress. Final settings: ~7 s/request, batches of ~50, with the runner halting and checkpointing on the first 429. All 198 product pages were retrieved with zero errors.

<!-- doc: role=evidence model, finish model and build pipeline; stage=reference -->
# Methodology

How a marketplace claim becomes a verified fact, how finishes are modelled, and how the repository
is built. The [README](README.md) says what the project is; [DATA-GUIDE.md](DATA-GUIDE.md) says
which file to use and what its fields do not mean.

## How a claim becomes a fact

**One unit, one verdict.** A language unit is `(setCode, number, variant, language)` and carries
exactly one of `confirmed`, `contradicted`, `needs-manual-review` or `pending`. Anything resolved
must cite a source; `verification/review_integrity.py` fails the build if it does not.

**Every source is ranked.** `providerId` names it, `corroborated` says whether a second provider
agreed independently, and `verification/source_registry.json` records the authority tier:

<!-- generated:authority-tiers — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
| Tier | Sources |
|---|---|
| 1 | Inspected physical specimen · Marumiya original Japanese promotional campaign · Play! Pokémon rewards gallery · Pokémon Card official database (Asia) · Pokémon Card official database (Japan) · Pokémon Card official database and rules (Korea) · Pokémon official website (Mainland China) · The Pokémon Company official cards and checklists |
| 2 | 52poke (Wiki) · Bulbapedia · CGC certification and registry · Cardmarket exact product image · Cardmarket seller listing photograph · Collection owner attestation · Elite Fourum · Malie TCGL reference · PSA certification and registry · SNKRDUNK · Seller listing photograph · TCGdex · pokemontcg.io |
| 3 | Collectory · Edaily reviewed Korean product-launch report · Kartenbasis reviewed German product date · LigaPokemon · Limitless TCG · Micromania reviewed French product date · MyComics reviewed Italian product dates · Newsworks reviewed Korean product-launch report · PKParaiso · PikaQian retained card images · PokéCardex · PokéCottage · PokéWiki reviewed localized release fields · PokéZentrum reviewed German release calendar · Pokémon Central Wiki reviewed Italian product date · Poképédia reviewed localized release fields · Retailer and specialist card listings · Sodip reviewed Italian newsstand release date · TCGCSV (TCGplayer product data) · WikiDex · World of Games reviewed Swiss German product date · koreanpokemoncards.com · pokumon.com |
| 5 | Cardmarket · Internal derivation from a sibling record |

Tiers 1, 2, 3 grade external evidence, strongest first. Tier 5 is not a weaker rung: it marks what is **not** external evidence — the marketplace catalogue this project exists to check, and attributes carried across from a sibling printing of the same card. There is deliberately no tier 4.
<!-- /generated:authority-tiers -->

**A single source may carry a claim, and usually does.** The rule check `E3` enforces is
*checkable or strong*: uncorroborated evidence with **no URL** — the owner's word, a card inspected in hand — must
come from tier 1 or 2, because nobody else can go and look at it. A tier-3 page anyone can open may
stand alone; the generated table below reports how often that happens. An unlinkable claim from
a weak source is neither strong nor checkable.

So read the tier beside a claim rather than assuming corroboration. Corroboration is preferred
throughout this project and is uncommon:

<!-- generated:evidence-strength — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
| How the claim is sourced | Resolved claims |
|---|---:|
| Corroborated by a second provider | 95 |
| Single tier 1-2 source | 618 |
| Single tier 3 source | 6 |

624 of 719 resolved claims rest on one provider. Check `E3` does not forbid that: it requires an uncorroborated claim to be **checkable or strong**, so a tier-3 page anyone can open may carry one alone, and 6 do. What it forbids is a claim that is neither — all 29 uncorroborated claims with no URL come from tier 1 or 2; their inspections, attestations or owner adjudications are retained in the repository.
<!-- /generated:evidence-strength -->

Specimen-backed claims cite stable ids in
[`verification/specimens.json`](verification/specimens.json); only a *cited* specimen may claim
specimen authority (check `S14`). Owner attestations and absence adjudications retain their own
evidence and do not imply a photographed or physically held card.

**Language truth and finish truth are separate layers.** `units.json` answers "was this printed in
this language?"; `finish_units.json` answers "which finishes exist for this set number and
language?" They have separate backlogs, and a confirmed language claim never implies a finish.

**Changes arrive through reviewed inputs and generators, not edits to state stores.** Routine
physical evidence uses the canonical observation-manifest importer. A new Python pass under
`verification/` is reserved for migration, bulk repair, or a data-model change. Then the generators
and checks are re-run; `units.json` and `finish_units.json` are never hand-edited.
[`scripts/regen.py`](scripts/regen.py) owns the command order; [`AGENTS.md`](AGENTS.md) explains when to run it.
The [specimen and reference acceptance contract](verification/RESUME.md#specimen-and-reference-acceptance-contract)
explains how retained images must remain connected to their claims and consumer views.

## Finishes, foil patterns, and stamps

Finish availability is modelled independently of Cardmarket products, keyed by set number ×
language. Because upstream catalogues are incomplete, it is deliberately a **positive-evidence
model**. An unlisted finish stays `pending` rather than being marked unavailable. Official sources
confirm only the finishes they name for the matching language and region. Only an owner-adjudicated
finish decision may close a unit after review, and that decision never introduces a finish.

<!-- generated:finish-coverage — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
| Known available finish | Set-number-language units |
|---|---:|
| Non-Holo | 316 |
| Holo | 291 |
| Reverse Holo family | 215 |
| Both Non-Holo and Holo | 71 |
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
[`verification/FINISH_REVIEW.csv`](verification/FINISH_REVIEW.csv) is what is still queued. Normal
regeneration runs through `python scripts/regen.py` and reads the committed TCGdex snapshot offline.
Refreshing that snapshot is an explicit review flow: stage with
`python scripts/finishes.py --refresh`, accept the exact staged candidate with
`python scripts/finishes.py --refresh --accept-refresh`, then regenerate.

## How the repository is built

The pipeline has two halves, and only one of them can be re-run.

**The harvest is historical.** `build` → `join` → `getimages` → `finalize` read the captured
Cardmarket result pages and hand `snorlax_cards.json` to everything downstream. Those inputs are
not in the repository and are **not reproducible**: they are a scrape of a live marketplace from
2026-07-21, and the same search today returns different products, prices and language filters.
Re-scraping would not rebuild this dataset, it would produce a different one. **`snorlax_cards.json`
is therefore a retained input with generator-owned fields, not a disposable output** —
[hybrid field ownership](WORKFLOW-MAP.md#hybrid-ownership-and-recovery) defines which parts may be
regenerated. `mkunits` is in the same category and destructive besides: it rebuilds
`verification/units.json` with fresh ids, discarding every verification verdict. It is not part of
any rebuild.

[`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json) freezes that candidate
universe with its source commit, file hashes, counts and every inherited card/unit membership. It
never expands with the current catalogue. Cardmarket is therefore one historical provider, not the
discovery boundary. The bounded source-first rebuild completed under
[#132](https://github.com/m4s-ai/snoredex-data/issues/132); its terminal result accounts for the
reviewed inputs and keeps remaining source/locality gaps explicit.

**Derived artifacts regenerate from the committed retained stores.** The executable pipeline source of
truth is [`scripts/regen.py`](scripts/regen.py), which owns the ordered `REGEN`, `CHECK`, and
`TESTS` lists. Run `python scripts/regen.py` to rebuild and verify the derived artifacts, or
`python scripts/regen.py --check` for the CI-equivalent deterministic gate. The complete input →
store → graph → projection → gate contract is in [`WORKFLOW-MAP.md`](WORKFLOW-MAP.md); it explains
why the order matters without maintaining a second command list here.

The reusable CI sequence lives in
[`.github/workflows/release-gate.yml`](.github/workflows/release-gate.yml). Draft PRs skip the
expensive job; ready PRs run deterministic L3 on Ubuntu and Windows, while the manual Pages call
runs L4 and hands a commit-/fingerprint-bound artifact to Pages. Pushes to `main` audit P6/P7 at
the exact pushed commit. Merging never publishes; Pages deployment remains a manual, gated
workflow run and deploys the already verified artifact without a second projection build.

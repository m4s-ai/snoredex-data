# HANDOVER — Snorlax Cardmarket dataset & source verification

Read this first if you are taking over cold. It is the single entry point; two deeper docs
back it up and are cited where relevant:

- **`CLAUDE.md`** — the condensed operating rules for an agent working here: the
  non-negotiables, the data-model traps, the command order and the git conventions, all pointing
  back at this file for detail. `AGENTS.md` is a pointer to it.
- **`README.md`** — the dataset spec, the findings (language drift, shared art, variants), and
  data caveats. Read before *using* the data.
- **`verification/RESUME.md`** — the verification playbook: every hard-won source technique,
  every dead end, every methodology correction. Read before *adding* any confirmation or
  contradiction. It is long (~415 lines) and worth it — it will stop you repeating mistakes
  that were already made and fixed here.

---

## 1. What this project is

A complete catalogue of every **Snorlax** Pokémon TCG product on [Cardmarket](https://www.cardmarket.com),
plus a rigorous **source-verification layer**: for each card × language × variant, does an
**external source (outside Cardmarket)** confirm that printing actually exists?

Why the verification exists: Cardmarket's language filter is *marketplace availability, not a
print manifest*. It over-claims — the worked example is `KSS 26`, advertised in 17 languages,
actually printed in 7. Every language claim therefore needs an outside source (manufacturer
site, fan wiki, marketplace listing, or a photographed physical card).

The owner (`Scarrty` in git; addressed as the domain expert throughout) directs scope and
supplies physical specimens. **Owner statements are authoritative** but graded explicitly as
evidence (see §6).

## 2. Current state (2026-07-31)

| | |
|---|---|
| Cardmarket products harvested | 242 (198 singles + 44 accessories) |
| Verification units (card × language × variant) | **719** |
| **Confirmed** with external source | **634** (88.2%) |
| **Contradicted** (Cardmarket claims it, source says no) | **71** |
| **Needs manual review** | **5** — all the same question: *does a Portuguese printing exist?* |
| **Still open** | **9** |
| Card-variants with every language resolved | 180 / 191 |
| Artist coverage in main dataset | 116 / 198 |
| Finish units (set number × language) | **637** |
| Finish units with an externally confirmed finish | **332** |
| Finish units with marketplace-only positive finish claim | **103** |
| Applicable finish units with no positive finish evidence yet | **138** |
| Finish units not applicable because every language claim is contradicted | **64** |
| Finish units in the remaining review queue | **233** |
| Finish units covered by a complete official manifest | **4** — English `DF 10`, `PPS3 LOR 143`, `PPS7 JTG 117`, `PPS8 JTG 117` |
| Finish units with unresolved Cardmarket-product mapping | **175** |

Numbers live in `verification/units.json` (the state store) and are echoed in
`snorlax_cards.json` → `meta.verification`. **After any change, run
`verification/review_integrity.py`** (27 structural checks) — it is the truth test.

The language/product claim backlog and the finish backlog are separate. Language truth lives in
`verification/units.json`; finish truth lives in `verification/finish_units.json`. Never infer a
physical finish from a confirmed language claim alone.

### The exact remaining work

**Open (9)** — genuinely undocumented, need a new source:
`BA20 MWT` ES+PT · `WCD23 LOR 143` ES+PT · `sA 10` KO+TC · `mP1 012` KO · `svG 021` TC · `svIba 046` TC.

**Manual review (5)** — all Portuguese Prize Pack / Additionals:
`xPRE 076` V1/V2 · `PPS1 VIV 131` V1/V2 · `PPS3 LOR 143`.
Next step for these: LigaPokemon (Brazilian marketplace) — see §5 for the Cloudflare workaround.

## 3. Repository layout

```
snorlax_cards.json            MAIN dataset: 198 singles, one object each. Fields: name, setCode,
                              number, setName, rarity, languages, imageUrl/imageFile, productUrl,
                              variantToken (V1/V2/V3), variantName (+source), variantAxes,
                              cardKey, artist(+source), editions{}, finishAvailability{}, market,
                              meta{}.
images/                       198 card images (SETCODE_NUMBER_NAME[_Vn]_ID.jpg).
analysis_*.json               Derived: language_drift, shared_cards, artists, variants,
                              finishes, confirmed_releases (chronological). Plus CSV exports.
artists_pokemontcgio.json     57 English cards with illustrator + exact release dates.
verification/bulbapedia_release_dates.json
                              Reviewed set-code -> Bulbapedia page/field/date overrides. Shared
                              articles often carry both enrelease and jarelease; never select by
                              article title alone. Recheck with audit_bulbapedia_release_dates.py.
scripts/                      Generators, in run order (§7 has the full command list):
                                finishes -> language_status -> confirmed_releases -> source_registry
                                -> checklist -> readme_stats -> issue_templates -> site
                              plus editions.py (edition classification) and publish.py (assembles
                              and verifies the Pages artifact). All Python, stdlib only. Five take
                              --check; see §7 for which, and how the gate covers the rest.
                              mkunits/build/join/getimages/finalize/analyze .ps1 are the original
                              harvest stages. They are DORMANT history: their _chunk*/_cards_stage*
                              inputs are not in the repository, so the committed dataset is the
                              input of record. They join the archive once #28 captures their data
                              flow.
verification/
  units.json                  THE STATE STORE. One row per card×language×variant with status,
                              sourceUrl, sourceType, evidence, checkedAt.
  evidence.jsonl              Append-only log of every confirmation (survives crashes).
  confirmed_sources.json      Export of all confirmed units.
  CONTRADICTED.json           The 71 refuted claims.
  MANUAL_REVIEW.csv / .json   The units handed to the user to decide.
  UNCONFIRMED.json            The open units, grouped by card.
  open-items.html             Browsable page of open + manual-review items (an Artifact).
  confirmed-releases.html     Browsable visual collection with images, chronology, editions,
                              confirmed languages, finish/treatment badges and filters (an Artifact).
  finish_units.json           FINISH STATE STORE. Set number×language units with physical printings,
                              finish/pattern/marking/size, sources and Cardmarket-product mappings.
  finish_overrides.json       Curated special-printing facts not expressible in group-level APIs.
  FINISH_SOURCES.md           Finish evidence hierarchy, confirmed special cases, exact source
                              endpoints and the repeatable research workflow.
  FINISH_REVIEW.json / .csv   The remaining finish, pattern and product-mapping review queue.
  RESUME.md                   The verification playbook (read before editing evidence).
  state.json                  Last completed phase.
  source_registry.json        Generated provider/evidence index. Counts live in README's
                              generated block; don't restate them here.
  report.py                   Regenerates coverage + all export files.
  audit_evidence.py           Checks every resolved unit has a non-trivial evidence string.
  classify_manual.py          (Re)tags structurally undocumentable units.
  verify_finish_sources.py    Rechecks exact TCGCSV product IDs and expected positive subtypes.
                              Replayable offline against fixtures/tcgcsv_finish_sources.json.
  review_integrity.py         27 structural checks WITHIN each store — run after every write pass.
  review_findings.py          Cross-artifact consistency BETWEEN the stores and what consumers
                              read, plus publication readiness. Stdlib only, no network.
  checks.py                   The check protocol shared by the two suites above. Counts are
                              reported, never asserted (see §7).
  publication_gate.py         Blocks deployment until publication-decisions.json records the
                              approvals; the Pages workflow feeds it the real repo visibility.
  test_site.py                Browser acceptance tests (playwright + chromium).
  parity.py                   Differential runner from the PowerShell->Python migration (#50).
                              Runs a script and its twin in throwaway trees and compares bytes.
  fixtures/                   Recorded responses so networked checks stay testable offline.
  archive/passes/             63 completed one-shot passes. Each closed a batch and is named by
                              what it did. NEVER rerun and NEVER edited: check X3 hashes every
                              file here against archive/MANIFEST.json and fails on any change.
                              Paths derive from each script's location.
  cache/                      Raw API dumps (gitignored — reproducible via the archived fetch_*
                              passes).
```

`.gitignore` excludes `verification/cache/` (13 MB reproducible API dumps) and
`verification/zoom/` (image crops). Everything else is committed.

## 4. Data model — the parts that trip people up

- **Unit** = (setCode, number, variant, language). `variant` is Cardmarket's `-V1/-V2/-V3`
  slug or `base`. Status is one of `confirmed | contradicted | needs-manual-review | pending`
  (`pending` = still open). Every resolved unit MUST have a non-trivial `evidence` string and a
  `sourceType`; `review_integrity.py` enforces this.
- **`variantName`** — Cardmarket's V1/V2/V3 tokens are opaque; the real meaning is recorded here
  (e.g. `xsv2a` V1=Poké Ball mirror / V2=Master Ball mirror; `xm2a` V1=energy-star mirror /
  V2=Poké Ball mirror — note the order flips between sets; `PPS8` V1=Non-Holo / V2=Holo;
  `xJTG` V1/V2/V3 = Journey Together / GameStop / EB Games stamps). Never assume a V-token means
  the same thing across sets.
- **Finish unit** = (setCode, number, language), deliberately not a V-token. TCGdex's positive
  `normal`/`holo`/`reverse` flags apply at this level. `printings[]` records the logical physical
  versions and maps them to Cardmarket products only when evidence supports that mapping.
  `finishStatus` is positive-evidence-only: `pending` means unknown, never proven absent.
  If every underlying product-language claim is contradicted, the finish unit remains in the state
  store as `not-applicable` and is excluded from `FINISH_REVIEW`.
- **Finish dimensions stay separate.** `finish` remains the auditable technical value
  non-holo/holo/reverse-holo/mirror-holo. Generated site/checklist `finishFamily` is the
  collector-facing layer:
  both reverse-holo and mirror-holo appear under **Reverse Holo**. `foilPattern` keeps
  Cosmos/crosshatch/type-symbol/Poké Ball/etc. distinct; `markings` is the physical stamp;
  `distribution` says how it was released; `cardSize` separates standard from jumbo. Never replace
  the technical finish or collapse the underlying printing/checklist IDs merely to group the UI.
- **Marking-role rule** — printed identity features such as rarity symbols and contest credits use
  `markings.role=print-identity`. EX-era set-logo stamps that are part of the reverse design use
  `markings.role=reverse-holo-treatment` (`DF 10` is the worked example). Later set-name
  prerelease stamps, Staff, retailer and Pokémon Center marks use
  `markings.role=distribution-promo`; they do not imply a reverse holo.
- **`editions`** — First Edition vs Unlimited, added last. `{hasFirstEdition, system,
  firstEditionLanguages, unlimitedLanguages, source}`. Ruleset (Bulbapedia + Elite Fourum
  t/16054): WOTC 1st ed = Base Set→Neo Destiny except Base Set 2; Japanese 1st ed = ADV/e-Card
  era→XY, none since Sun & Moon; Korean/Chinese/SEA never. **12 cards** have a 1st edition.
  Cardmarket's own "First Edition?" filter is unreliable (83/198, incl. modern cards) — do not
  use it.
- **`cardKey`** — Cardmarket's own grouping (name + attack names). Same cardKey = same card text,
  useful for finding the same card under a different set (e.g. a card's Traditional Chinese print
  may be a standalone promo, not a TC edition of the Japanese product).
- **Language scope**: "Spanish" = Cardmarket's European Spanish. **LATAM-ES is a separate
  edition** (specimen-proven) that Cardmarket does not list; it is out of scope. If ever added,
  source it from the official Pokémon site, sets only, from Journey Together (2025) onward.
- **Code cards** (75 units) are excluded — `verification/excluded_codecards.json`.

## 5. Source landscape — what works, what's blocked

Full detail in `RESUME.md`. The essentials:

| Source | Access | Use for |
|---|---|---|
| **TCGdex API** `api.tcgdex.net` | scriptable | en/fr/de/es/it/pt/ja/zh-tw/id/th card existence; positive normal/holo/reverse flags |
| **Official Pokemon checklists** `assets.pokemon.com` / `d1wx537rtdixyy.cloudfront.net` | scriptable PDFs | complete set and Prize Pack finish manifests; the only current finish source allowed to establish absence within its stated scope |
| **TCGCSV** `tcgcsv.com` | scriptable JSON | reproducible TCGplayer product identity plus positive Normal/Holofoil/Reverse Holofoil subtypes; positive-only marketplace evidence |
| **PSA cert/spec/registry** `psacard.com` | scriptable | exact named grading varieties; never use population counts or omissions as negative evidence |
| **Bulbapedia** | scriptable **only via in-app browser** + MediaWiki API (`/w/api.php?action=parse&prop=wikitext&redirects=1`) — plain fetch is 403 | set lists, `release=` infobox fields, `ko=`/`pt_br=` langtable lines, per-language articles (`(KTCG)`/`(TCTCG)`/`(ITCG)`/`(ATCG)`/`(SCTCG)` suffixes) |
| **Official JP** `pokemon-card.com` | scriptable (`resultAPI.php`, param `regulation_sidebar_form=all`, page param is `page` not `pg`) | Japanese cards + illustrators |
| **Official Asia** `asia.pokemon-card.com` | scriptable | tw/id/th recent cards |
| **pokumon.com** | WebFetch | per-market promo printings (one row per Asian printing; **West is one lumped "English" row — never use its absence to contradict a Western language**) |
| **Elite Fourum** `elitefourum.com` | scriptable (Discourse JSON: `/search.json`, `/t/<id>.json`) | collector-community facts (promo languages, 1st-edition timeline) |
| **LigaPokemon** `ligapokemon.com.br` | **datacenter IPs banned (Cloudflare 1008)** — use the user's real Chrome (`claude-in-chrome` tools) | Brazilian/Portuguese marketplace listings |
| **Cardmarket** | in-app browser (rolling ~55-req quota → HTTP 429; recover by navigating to re-solve the challenge) | seller photos of physical cards (a real photo of a card in language X is valid; the language *filter* is not) |

Dead ends (do not retry): `pokemonkorea.co.kr` / `pokemoncard.co.kr` (HTTP 410, gone),
`ptcg.cn` (a Magic site), `pokebeach.com` (403 to scripts), `namu.wiki` (JS-rendered),
`krystalkollectz.com` (a shop, not a database).

**Key trick**: when a source (Bulbapedia, LigaPokemon) blocks datacenter IPs, drive the user's
own Chrome via the `claude-in-chrome` MCP tools — it uses their residential IP. This is how the
Brazilian Prize Pack confirmations were obtained.

## 6. Working discipline — non-negotiable

1. **Evidence outside Cardmarket only.** The card's *language filter* on Cardmarket is not
   evidence; a seller's *photo* of the physical card is.
2. **Grade evidence.** `sourceType` distinguishes *photographed specimen* > *marketplace listing*
   / *official DB* / *fan wiki* > *owner attestation*. Currently 0 units rest on attestation alone
   without corroboration; keep it that way where possible.
3. **Never contradict on bare absence.** First prove the source *covers the category* (e.g.
   pokumon lists Korean promos, so a missing Korean row is meaningful). This rule exists because
   an absence-argument produced a false contradiction that had to be reverted (`XY-P 149`).
   The same rule applies to finishes: TCGdex `true` confirms a printing; `false` is not used to
   prove that a finish is unavailable because its variant data is still incomplete.
4. **Run `audit_evidence.py` and `review_integrity.py` after every write pass.** Silent data
   corruption has happened here (see the historical note below) and only the audit caught it.
5. **Write findings via a new Python pass under `verification/`**, then run report + audit +
   integrity. Don't hand-edit `units.json` or `finish_units.json`.
6. **Never hand-edit a generated file.** Each carries a header saying so. Regenerate it.

Historical note, kept because it explains the shape of the archived passes: the toolchain used to
be PowerShell, and **PowerShell's case-insensitivity bit four times**. `$R`/`$r` and `$EV`/`$ev`
are the same variable — declaring a log array silently wiped the evidence text — and `-match '^x'`
also matched `XY-P`/`XY2`/`XYPR`. None of it threw an error; it produced wrong data, and only the
audit caught it. The recurring toolchain is Python now (#50), so the rule no longer applies to
anything you will write; the reason rule 4 exists does.

## 7. How to resume / continue

```console
# Run from the repository root.
python verification/review_integrity.py     # confirm clean starting state
python verification/review_findings.py           # cross-artifact consistency (stdlib, no network)
python verification/report.py               # regenerate exports if needed
# ... do verification work in a new Python pass under verification/ ...
python verification/audit_evidence.py       # after any write
python scripts/editions.py                       # if edition data changed
python scripts/finishes.py                       # regenerate finish units/review + main summaries
python scripts/language_status.py                # refresh per-card language verdicts
python scripts/confirmed_releases.py             # regenerate chronological JSON + CSV
python scripts/source_registry.py                # rebuild provider/evidence registry
python scripts/checklist.py                      # rebuild canonical checklist items
python scripts/readme_stats.py                   # refresh generated README blocks
python scripts/issue_templates.py                # rebuild the community correction form
python scripts/site.py                           # rebuild index.html + the alias redirect
python verification/review_integrity.py     # after any write
python verification/review_findings.py           # after any write
python verification/test_site.py                 # browser behaviour (needs playwright+chromium)
python verification/verify_finish_sources.py # recheck machine-readable TCGCSV assertions
```

Order matters, and it is the order above: `finishes.py` writes the card finish summaries,
`language_status.py` writes the card language verdicts, `confirmed_releases.py` reads both and
writes the chronological rows, and `checklist.py` and `site.py` read those. Five generators take a
`--check` mode that fails instead of writing — `checklist`, `readme_stats`, `issue_templates`,
`site`, `source_registry` — and the release gate runs those with `--check`, runs `finishes.py
--reproject`, `language_status.py` and `confirmed_releases.py` for real, then asserts
`git diff --exit-code`. Either way a generator whose output would move fails the build.
`publish.py` takes `--verify`. `finishes.py --reproject` redoes only the card projection from the
committed finish store and needs no network, which is the fast path when a projection rule changes.

**The integrity suite no longer asserts counts.** Unit totals, coverage and queue depths are
reported as drift against a baseline, because closing an open unit is the goal, not a regression;
only a count going *backwards* is flagged. Structural facts still fail the run. Do not "fix" a
rising number by editing the baseline — that is the habit the split exists to prevent.

All scripts derive paths from their own location — `Path(__file__)`. Keep that convention in new
scripts; CI runs them from more than one working directory.

`index.html` is the single public page; `verification/confirmed-releases.html` is a redirect to
it, so there is no second page to keep in step. Commit + push:

```bash
git checkout -b <branch>
git add -A && git commit -m "..."
git push -u origin <branch>
```

Git: repo is `github.com/m4s-ai/snoredex-data`, remote `origin`, credentials already configured.
Work lands on a **feature branch via pull request** — do not push to `main`. The release gate runs
on pull requests across Ubuntu and Windows; merging never publishes, because Pages deployment is a
separate manual `workflow_dispatch` run. End commit messages with the
`Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` trailer.

## 8. Immediate next actions (in priority order)

1. **Finish review** — read `verification/FINISH_SOURCES.md`, then work the 233 rows in
   `verification/FINISH_REVIEW.csv`: first the 138 applicable units with no positive finish
   evidence, then the 175 units whose logical finish is not mapped to every Cardmarket product
   (the queues overlap). Put durable facts and source metadata in `finish_overrides.json`, rerun
   `python scripts/finishes.py`, then run integrity. Do not convert positive-only source omissions
   into negative claims. The 64 fully contradicted language groups are already `not-applicable` and
   are intentionally absent from this queue.
2. **The 5 Portuguese manual-review units** — check LigaPokemon via the user's Chrome for
   `PPS1 VIV 131` and `PPS3 LOR 143`. (`xPRE` is an Additionals product that may not appear on a
   marketplace as its own entry.)
3. **The 9 open units** — `BA20`/`WCD23` ES+PT want a photo or a localized retail listing; the
   four Asian deck products (`sA`, `mP1`, `svG`, `svIba`) want a sealed product listing from a
   seller in that market.
4. Anything the owner supplies next (they have been feeding specimens and corrections card by
   card; expect more).

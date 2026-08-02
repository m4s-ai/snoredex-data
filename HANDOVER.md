# HANDOVER — Snorlax Cardmarket dataset & source verification

Read this first if you are taking over cold. It is the single entry point; two deeper docs
back it up and are cited where relevant:

- **`CLAUDE.md`** — the condensed operating rules for an agent working here: the
  non-negotiables, the data-model traps, the command order and the git conventions, all pointing
  back at this file for detail. `AGENTS.md` is a pointer to it.
- **`README.md`** — the public entry point: why the verification exists, how to start, which file
  answers which question, and the data caveats. Read before *using* the data.
  **`FINDINGS.md`** hangs off it with the findings themselves — language drift, shared art,
  variant clusters, and how the one-off harvest was run.
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

## 2. Current state (2026-08-02)

| | |
|---|---|
| Cardmarket products harvested | 242 (198 singles + 44 accessories) |
| Verification units (card × language × variant) | **719** |
| **Confirmed** with external source | **634** (88.2%) |
| **Contradicted** (Cardmarket claims it, source says no) | **85** |
| **Needs manual review** | **0** |
| **Still open** | **0** |
| Card-variants with every language resolved | 191 / 191 |
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

### Language/product review is closed

All 719 language/product claims are now resolved: **634 confirmed, 85 contradicted, 0 manual-review,
0 pending**. The final closure moved Portuguese `xPRE 076` V1/V2 and Portuguese `PPS1`/`PPS3`
Snorlax claims to contradicted after Copag/catalog and collector evidence. It also resolved the
remaining BA20, WCD23, sA, svG, svIba and mP1 language claims. The BA20 Spanish/Portuguese finding
is recorded in `verification/passes/close_language_review.py` and in each unit's evidence: the
Elite Fourum matrix limits the stamped Battle Academy 2020 Mewtwo/Charizard Deck cards to English,
French, German and Italian; Bulbapedia and regional manufacturer/retailer checks found no Spanish
or Portuguese BA20 MWT Snorlax printing. The finish-verification queue remains a separate layer.
The clean application handoff records the collection owner's final not-printed decisions separately
in `verification/owner_adjudications.json`; the underlying contradicted verdicts and evidence stay
unchanged.

## 3. Repository layout

```
snorlax_cards.json            MAIN dataset: 198 singles, one object each. Fields: name, setCode,
                              number, setName, rarity, languages, imageUrl/imageFile, productUrl,
                              variantToken (V1/V2/V3), variantName (+source), variantAxes,
                              cardKey, artist(+source), editions{}, finishAvailability{}, market,
                              meta{}.
snoredex.sqlite               NORMALIZED HANDOFF: current products, language verdicts, editions,
                              releases, finishes, checklist and providers in one SQLite database.
                              No evidence journal or pass history. Owner adjudications are linked
                              separately for final application decisions. See DATABASE.md.
snoredex-tracker-template.sqlite
                              Blank separate collection state keyed by checklistId. Copy it or use
                              scripts/tracker.py; sync preserves have/wanted/quantity/notes.
images/                       198 card images (SETCODE_NUMBER_NAME[_Vn]_ID.jpg or .png — the
                              extension states the actual format; 55 are PNG, see #34).
analysis_*.json               Derived: language_drift, shared_cards, artists, variants,
                              finishes, confirmed_releases (chronological). Plus CSV exports.
artists_pokemontcgio.json     57 English cards with illustrator + exact release dates.
verification/bulbapedia_release_dates.json
                              Reviewed set-code -> Bulbapedia page/field/date overrides. Shared
                              articles often carry both enrelease and jarelease; never select by
                              article title alone. Recheck with audit_bulbapedia_release_dates.py.
scripts/                      Two halves; only the second can be re-run (#28).

                              LIVE generators, in run order (§7 has the full command list):
                                analyze -> finishes -> language_status -> confirmed_releases
                                -> source_registry -> checklist -> readme_stats -> issue_templates
                                -> open_items -> database -> tracker template -> site
                              plus editions.py (edition classification) and publish.py (assembles
                              and verifies the Pages artifact). Eight take --check; see §7.
                              analyze.py is the SOLE producer of analysis_artists,
                              _shared_cards, _variants and _language_drift, and reads
                              snorlax_cards.json only — the single canonical node (#30). Its
                              PowerShell predecessor is archived under archive/scripts/.
                              ALL PYTHON: PowerShell is no longer needed for anything.

                              HISTORICAL, inputs absent, do not run:
                                build -> join -> getimages -> finalize
                              They read _chunk1..3.json, a 2026-07-21 scrape of a live
                              marketplace. Not in the repo, not reproducible: the same search
                              today returns different products. snorlax_cards.json is therefore
                              the INPUT of record, not an output of this repository. These five
                              join the archive once their data flow is captured (#28 did that).

                                mkunits    Also historical, and destructive: rebuilds
                                           verification/units.json from scratch with fresh ids,
                                           discarding the state of all 719 units. Never part
                                           of a rebuild.

                              The release gate runs the live half and fails if the output differs
                              from what is committed, so "regenerates cleanly" is proven per PR.
verification/
  units.json                  THE STATE STORE. One row per card×language×variant with status,
                              sourceUrl, sourceType, evidence, checkedAt.
  owner_adjudications.json    COLLECTION-OWNER DECISIONS. Explicit final application decisions
                              after reviewing all cited claims; never rewrites units.json or
                              attributes absence to a single provider.
  evidence.jsonl              Append-only journal of what was observed, and when. NOT a
                              projection of units.json and not replayable into one: entries are
                              appended as observations happen, corrections are appended rather
                              than rewritten, and nothing guarantees the last entry for a unit
                              matches its current row. units.json is the state; this is the
                              record of how it was reached. check E5 requires every resolved
                              unit to appear here, which is the property it can actually offer.
  specimens.json              Physical cards the owner holds and inspected, each with a stable
                              SPEC-nnnn id. A unit cites one as sourceRef "specimen:SPEC-0002"
                              instead of describing it in prose. `photograph` is null until the
                              image is supplied; the claim rests on the recorded inspection either
                              way, and the file is what lets a third party re-check it.
                              TO ADD A PHOTOGRAPH: drop the file in verification/specimens/, set
                              `photograph` to its filename, run review_findings.py. Checks S7-S12
                              cover it; publish.py already allowlists the directory and LICENSE.md
                              decision 4 covers the category, so no approval is needed per image.
  confirmed_sources.json      Export of all confirmed units.
  CONTRADICTED.json           The 85 refuted claims.
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
  report.py                   Prints coverage and rewrites exactly three exports:
                              confirmed_sources.json, CONTRADICTED.json, UNCONFIRMED.json.
                              NOT "all exports" — MANUAL_REVIEW.* comes from classify_manual.py,
                              open-items.html from scripts/open_items.py, SOURCES.md from
                              scripts/source_registry.py, and the FINISH_* queue from
                              scripts/finishes.py.
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
2. **Grade evidence.** `providerId` names the source, `corroborated` says whether more than one
   provider agreed, and `verification/source_registry.json` ranks each provider by `authorityTier`:

<!-- generated:authority-tiers — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
| Tier | Sources |
|---|---|
| 1 | Photographed physical specimen · Play! Pokémon rewards gallery · Pokémon Card official database (Asia) · Pokémon Card official database (Japan) · The Pokémon Company official checklists |
| 2 | Collection owner attestation · Elite Fourum · PSA certification and registry · TCGdex · pokemontcg.io |
| 3 | Bulbapedia · LigaPokemon · Limitless TCG · Retailer and specialist card listings · TCGCSV (TCGplayer product data) · pokumon.com |
| 5 | Cardmarket · Internal derivation from a sibling record |

Tiers 1, 2, 3 grade external evidence, strongest first. Tier 5 is not a weaker rung: it marks what is **not** external evidence — the marketplace catalogue this project exists to check, and attributes carried across from a sibling printing of the same card. There is deliberately no tier 4.
<!-- /generated:authority-tiers -->

   Elite Fourum is a high-authority tier-2 reference; its authority does not by itself establish
   absence, and explicit collection-owner adjudications record final cross-source decisions.

   A single non-URL source may confirm a unit. **30 units rest on owner attestation alone** and 5
   on a photographed specimen alone, all queryable as
   `corroborated == false and providerId in {owner-attestation, photographed-specimen}`. The
   owner physically holds these cards and no database records them, so the alternative is not
   better evidence but a false "open" count.

   **What E3 actually enforces is *checkable or strong*.** It fails only when an uncorroborated
   claim is both unlinkable and weak — no `sourceUrl` and below tier 2. A tier-3 source with a URL
   may stand alone, and **252 of 719 resolved units** do (247 Bulbapedia, 3 pokumon, 2
   LigaPokemon), every one with an `https` reference across 65 distinct pages. This section used to
   say a single weaker source "is not acceptable" and that E3 enforced it; it does not, and the
   overstatement made the data look better sourced than it is (#65). The real shape: **680 of 719
   resolved claims rest on one provider** and only 39 are corroborated, which is why the README
   publishes that split as a generated block rather than a sentence anyone can leave behind.
   E4 fails if the attestation count stops matching the data.

   **A claim is graded by what it rests on, not by the strongest source near it.** The attestation
   figure read 16 until #64: fourteen `PPS7`/`PPS8 JTG 117` units carried
   `providerId: photographed-specimen` — tier 1, above an official database — while their evidence
   said "Owner (domain expert) confirms". One German holo specimen (`SPEC-0001`) and one Portuguese
   LigaPokemon listing covered *neighbouring* units of the same product, and the label had drifted
   onto all of them. `scripts/source_registry.py`, which resolves a provider from `sourceType`
   text rather than from the stored field, had been reporting `owner-attestation` for those units
   the whole time — the two computations disagreed and nothing compared them. Checks `S13` and
   `S14` close it: `sourceRef` holds a reference or nothing, and specimen authority requires a
   cited specimen.
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
python scripts/open_items.py                     # rebuild verification/open-items.html
python scripts/database.py                       # normalized current-state SQLite + handoff audit
python scripts/tracker.py --tracker snoredex-tracker-template.sqlite init --force
python scripts/site.py                           # rebuild index.html + the alias redirect
python verification/review_integrity.py     # after any write
python verification/review_findings.py           # after any write
python verification/test_site.py                 # browser behaviour (needs playwright+chromium)
python verification/verify_finish_sources.py # recheck machine-readable TCGCSV assertions
```

Order matters, and it is the order above: `finishes.py` writes the card finish summaries,
`language_status.py` writes the card language verdicts, `confirmed_releases.py` reads both and
writes the chronological rows, and `checklist.py`, `database.py` and `site.py` read those. Eight
generators take a `--check` mode that fails instead of writing — `checklist`, `readme_stats`,
`issue_templates`, `site`, `source_registry`, `open_items`, `analyze`, `database` — and the release
gate runs those with `--check`, validates the blank tracker template, runs `finishes.py --reproject`,
`language_status.py` and `confirmed_releases.py` for real, then asserts
`git diff --exit-code`. Either way a generator whose output would move fails the build.
`publish.py` takes `--verify`. `finishes.py --reproject` redoes only the card projection from the
committed finish store and needs no network, which is the fast path when a projection rule changes.

A full `finishes.py` run reads TCGdex through a cache under `verification/cache/finish-tcgdex/`.
Entries record their URL, fetch time, HTTP status, content hash and item count, expire after 30
days, and are never written for a failed or implausible response. Transient failures are retried
with backoff; a 404 is an answer and is not. `--refresh-cache` forces a refetch, and exit 2 means
a source could not be reached rather than that the data is wrong (#35).

**The integrity suite reports counts rather than asserting them, and fails on a losing move.**
Nothing fails because a count is the wrong size. Each metric declares its direction: unit totals,
artist coverage and finish rows are `up-is-progress`, so a fall means loss; `pending units` and
`manual-review units` are `down-is-progress`, and their baselines are the low-water mark so a
refilling queue is caught. Since #69 a losing move exits non-zero — it used to print
`!!! COUNTS WENT BACKWARDS` and return 0, which meant a real loss looked exactly like the permanent
false alarm that closing the language queue produced, and CI went green through both. Structural
facts still fail the run.

Do not "fix" a losing move by editing the baseline; find what changed. Re-anchoring a queue
*downward* after closing it is the opposite move and tightens the check. Raising a baseline to
silence a rise is the habit this rule exists to prevent.
`verification/test_metric_polarity.py` pins the behaviour.

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
2. **Language/product claims are closed** — no pending or manual-review units remain. Keep the
   source-specific evidence in `verification/units.json` and `verification/evidence.jsonl`; do not
   infer a new contradiction from a bare catalogue absence.
3. Anything the owner supplies next (they have been feeding specimens and corrections card by
   card; expect more).

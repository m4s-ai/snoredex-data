<!-- doc: role=cold-start orientation and repository layout; stage=task -->
# HANDOVER — Snorlax Cardmarket dataset & source verification

Read this first if you are taking over cold. This file does one job: it says **where things are**.
What to do, what is true right now, and how the verification works each live somewhere else, and
are not restated here — a second copy is a copy that goes stale.

| Question | Where it is answered |
|---|---|
| What are the rules, and what will trip me up? | [`CLAUDE.md`](CLAUDE.md) — loaded automatically; `AGENTS.md` points to it |
| What is true right now? | [`verification/DATA-HANDOFF-AUDIT.md`](verification/DATA-HANDOFF-AUDIT.md) — generated from the data, so it cannot drift |
| What should I work on? | The [issue tracker](https://github.com/m4s-ai/snoredex-data/issues) |
| How do I add or change evidence? | [`verification/RESUME.md`](verification/RESUME.md) — read it before touching a confirmation or contradiction |
| How do I *use* the data? | [`README.md`](README.md), with [`FINDINGS.md`](FINDINGS.md) for what fell out of building it |
| Why does this rule exist? | [`LESSONS.md`](LESSONS.md) — the incident behind each trap |
| What is the data's scope, and what is it *not*? | [`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json) — the frozen boundary, below |

The data here descends from a **legacy Cardmarket-derived candidate universe**: one marketplace
search captured on 2026-07-21. Verification can check what that search returned; it cannot discover
a printing Cardmarket never listed, which is why a resolved queue is not a finished catalogue. The
source-first rebuild is [#132](https://github.com/m4s-ai/snoredex-data/issues/132).

---

## 1. Repository layout

```
snorlax_cards.json            MAIN dataset: 198 singles, one object each. Fields: name, setCode,
                              number, setName, rarity, languages, imageUrl/imageFile, productUrl,
                              variantToken (V1/V2/V3), variantName (+source), variantAxes,
                              cardKey, artist(+source), editions{}, finishAvailability{}, market,
                              meta{}.
legacy-cardmarket-baseline.json
                              IMMUTABLE LEGACY BOUNDARY: source commit, file hashes and the
                              membership of the 2026-07-21 harvest. Membership is a floor — every
                              member must still exist in the live stores, and new candidates are
                              added to those stores, never to this file. It records no verification
                              state, deliberately.
verification/ADR-0001-locality-aware-print-identity.md
                              PROPOSED identity model (#134/#145): immutable candidate claims may
                              establish language-bearing card releases, which positively evidenced
                              finishes/treatments realize as physical printings. Contradicted and
                              marketplace-only claims create no existence-bearing node. Schema in
                              print_identity_schema.json; measured consequences in
                              print_identity_dryrun.json. Nothing is keyed by it yet.
verification/ADR-0002-local-set-edition-release-events.md
                              PROPOSED catalogue model (#146): locality-bearing local sets,
                              language/script editions, market/wave release events, scoped finish
                              profiles and source-native rarity claims. The independent raw registry
                              is set_catalogue_sources.json; executable constraints are in
                              set_catalogue_schema.sql; set_catalogue_dryrun.json is the measured
                               graph. Nothing is keyed by it yet.
verification/ADR-0003-source-capability-coverage.md
                              ACCEPTED evidence-routing boundary (#135): provider surfaces point
                              through explicit locality/category/time coverage edges. Every claimed
                              edge has a positive fixture and a boundary; only exact exhaustive
                              edges may carry absence. PSA/CGC and specimens are positive-only.
verification/ADR-0004-source-first-adapter-runs.md
                              ACCEPTED source-first enumeration loop (#147): retained provider runs
                              start outside the Snorlax/legacy candidate universe, preserve raw
                              locale records and park every unmapped identity as a visible candidate.
verification/ADR-0005-legacy-set-reconciliation.md
                              ACCEPTED bounded backfill (#148): all 135 aliases, 203 release rows
                              and 637 finish units project into the identity graph or an explicit
                              needs-evidence/blocked-by-source state. Coverage is versioned and lossless.
verification/ADR-0006-source-first-card-discovery.md
                              ACCEPTED card-level discovery loop (#136): localized provider queries
                              retain list/detail responses before matching and route every card into
                              a visible, non-verdict staging bucket.
verification/ADR-0007-embedded-artwork-review-ui.md
                              ACCEPTED UI boundary (#120): embed the future artwork/detection review
                              view in this static data repo, emit reviewed structured proposals rather
                              than direct writes, and wait for #140's authoritative graph outputs.
verification/ADR-0008-reviewed-catalogue-basis-lists.md
                              ACCEPTED canonical-data boundary (#187): languages, local sets,
                              editions/events, typed set relations, artwork identities/appearances
                              and physical printings are manually reviewed registries. Generators
                              emit disposable hashed views and never write truth back into them.
snoredex.sqlite               NORMALIZED HANDOFF: current products, language verdicts, editions,
                              releases, finishes, checklist and providers in one SQLite database.
                              No evidence journal or pass history. Owner adjudications are linked
                              separately for final application decisions. See DATABASE.md.
snoredex-tracker-template.sqlite
                              Blank separate collection state keyed by checklistId. Copy it or use
                              scripts/tracker.py; sync preserves have/wanted/quantity/notes.
images/                       198 card images (SETCODE_NUMBER_NAME[_Vn]_ID.jpg or .png — the
                              extension states the actual format; 55 are PNG, see #34).
README.md / CONTRIBUTING.md   The public pair: how to use the data, and how to report a
                              correction. Written for people, not agents.
DATABASE.md                   The contract snoredex.sqlite offers an application.
LICENSE.md / LICENSES/        The mixed-work licence structure plus verbatim publisher texts;
THIRD_PARTY_NOTICES.md        upstream attribution. AI-DECLARATION.md states the AI transparency
AI-DECLARATION.md             level, and check A1 holds it to the 0.1.2 specification.
LESSONS.md                    The incident behind each trap CLAUDE.md states: what went wrong,
                              what it cost, which check holds the line now. Read it when a rule
                              looks arbitrary. Deliberately not auto-loaded.
analysis_*.json               Derived: language_drift, shared_cards, artists, variants,
                              finishes, confirmed_releases (chronological). Plus CSV exports.
analysis_confirmed_releases_reconciled.json / .csv
                              GENERATED #148 compatibility pair: preserves every legacy release
                              row/CSV column and appends edition-event migration state and loss
                              diagnostics under coverage version legacy-set-reconciliation-v1.
artists_pokemontcgio.json     57 English cards with illustrator + exact release dates.
verification/bulbapedia_release_dates.json
                              Reviewed set-code -> Bulbapedia page/field/date overrides. Shared
                              articles often carry both enrelease and jarelease; never select by
                              article title alone. Recheck with audit_bulbapedia_release_dates.py.
scripts/                      Two halves; only the second can be re-run (#28).

                              LIVE generators, in run order (§7 has the full command list):
                                analyze -> finishes -> language_status -> confirmed_releases
                                -> source_registry -> source_capabilities -> source_adapters
                                -> card_discovery
                                -> legacy_set_reconciliation
                                -> checklist -> readme_stats
                                -> issue_templates
                                -> open_items -> database -> tracker template -> site
                              plus editions.py (edition classification) and publish.py (assembles
                              and verifies the Pages artifact). print_identity_dryrun.py and
                              set_catalogue_dryrun.py rebuilds the ADR-0002 graph;
                              source_adapters.py checks/reprojects retained ADR-0004 set runs;
                              card_discovery.py checks/reprojects retained ADR-0006 card runs; and
                              legacy_set_reconciliation.py rebuilds the bounded ADR-0005 ledger and
                              compatibility pair. See §7.
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
  rarity_catalogue.json       CENTRAL RARITY REFERENCE: one entry per rarity with its locale
                              codes (Illustration Rare = AR), whether it names a finish, and the
                              Bulbapedia sentence that says so, plus per-set rarity availability.
                              Reference data — it claims nothing about any card here. Rarity
                              belongs to a card release, not a work: the same card can be Common
                              in Japanese and Uncommon in English.
  set_catalogue_sources.json  INDEPENDENT SET DISCOVERY REGISTRY: immutable provider records for
                              local sets/products, dates and edition availability. A record does not
                              need a matching Snorlax. Extend it through reviewed passes; mapping and
                              unresolved states belong to the dry-run, not this raw store.
  set_catalogue_schema.sql    Executable SQLite constraint contract for ADR-0002. The dry-run loads
                              it into an empty in-memory database; #140 owns any real DB migration.
  set_catalogue_dryrun.json   GENERATED ADR-0002 graph and reports. Rebuilt from the independent
                              source registry plus ADR-0001 existence-bearing references; it never
                              creates a card release from set availability.
  legacy_set_reconciliation.json
                              GENERATED ADR-0005 migration ledger. It embeds every legacy finish
                              unit exactly, keeps scalar release dates as raw history, links only
                              positive edition events, and balances all bounded accounting buckets.
  specimens.json              Physical cards the owner holds and inspected, each with a stable
                              SPEC-nnnn id. A unit cites one as sourceRef "specimen:SPEC-0002"
                              instead of describing it in prose. `photograph` is null until the
                              image is supplied; the claim rests on the recorded inspection either
                              way, and the file is what lets a third party re-check it.
                              An optional `physicalObservation` records what the scan shows —
                              finish, foil pattern, marking, size — and quotes its `basis` from
                              the record. Optional and never back-filled: a specimen without one
                              says nothing about finish. See FINISH_SOURCES.md (#150).
                              TO ADD A PHOTOGRAPH: run fetch_attachment.py, which writes the file
                              as SPEC-nnnn.png/.jpg and sets `photograph` plus the optional
                              `photographSource` (where the bytes came from — keep the original
                              GitHub attachment URL here, since that URL outlives nothing). Then
                              run review_findings.py and scripts/database.py. Checks S7-S12 cover
                              it; publish.py already allowlists the directory and LICENSE.md
                              decision 4 covers the category, so no approval is needed per image.
                              PNG and JPEG only: publish.py also allowlists .webp, but
                              `image_format` in review_findings.py knows PNG and JPEG magic
                              alone, so a committed .webp would fail S9.
                              A photograph the owner attached to a GitHub issue CANNOT be fetched
                              here — the agent proxy refuses github.com/user-attachments/assets/
                              and the older github.com/{owner}/{repo}/assets/ form alike, so
                              adding the repo to the path is not a workaround. It is not a
                              permission problem; the repository is public and the image opens in
                              a browser. Commit the bytes to a branch and point `--from` at the
                              path. Release downloads and every githubusercontent host are
                              reachable if a URL is easier.
  confirmed_sources.json      Export of all confirmed units.
  CONTRADICTED.json           The 84 refuted claims.
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
  source_capability_schema.json
                              Versioned JSON Schema for the reviewed source capability manifest.
  source_capabilities.json    REVIEWED MANIFEST: provider operators, access/failure/freshness state,
                              query and pagination contracts, independent finish capability and
                              bounded locality/language/category/time coverage edges.
  source_capability_graph.json
                              GENERATED GRAPH: flattened coverage edges, hashed positive/boundary
                              observations and one capability-surface resolution for every source
                              currently used by a verdict. Rebuild with source_capabilities.py.
  source_adapter_schema.json   Versioned contract for source-first adapter slices, raw fields,
                               accounting buckets, explicit mappings and terminal gap states.
  source_adapters.json         REVIEWED ADAPTER/GAP INVENTORY: provider-native empty-start
                               catalogue slices plus the official and specialist tracks that are
                               still needs-evidence or blocked-by-source.
  runs/source-adapters/        IMMUTABLE RAW RUNS: exact provider response bytes, hashes,
                               request/checkpoint manifest and inputs for reproducible run diffs.
  source_adapter_staging.json  GENERATED #147 GRAPH SUMMARY: exact accounting, run errors, explicit
                               gaps, record hash and added/changed/disappeared/re-key diffs.
  source_adapter_records.jsonl GENERATED #147 RECORD FEED: one locality-aware set proposal per line.
                               Neither file can mutate set, card, finish or verification verdicts.
  card_discovery_schema.json   Versioned contract for source-first card queries, buckets, additive
                               set-code assertions, explicit mappings and terminal gap states.
  card_discovery_adapters.json REVIEWED #136 ADAPTER/GAP INVENTORY: native-name slices plus the
                               locality tracks that remain needs-evidence or blocked-by-source.
  runs/card-discovery/         IMMUTABLE RAW RUNS: exact list pages, detail pages, symbol assets,
                               hashes and resumable checkpoints.
  card_discovery_staging.json  GENERATED #136 GRAPH SUMMARY: exact detail/bucket accounting, run
                               errors, gaps and added/changed/disappeared/re-key diffs.
  card_discovery_records.jsonl GENERATED #136 RECORD FEED: one locality-aware card proposal per line.
                               Raw identifiers survive and no row may mutate a verdict.
  asia_locality_matrix.json    REVIEWED #238 MATRIX: the eight #138 Asian locality tracks, bounded
                               positive-slice references, terminal gaps and minimum regressions.
  ASIA-LOCALITY-MATRIX.md      GENERATED readable projection of the #238 Asia terminal matrix.
                               Rebuild with scripts/asia_locality_matrix.py.
  locality_era_matrix.json     REVIEWED #139 MATRIX: established, provisional, candidate and
                               #138-coordinated non-Asian locality tracks, each with explicit era
                               evidence, positive-only policy, source/gap references and child state.
  LOCALITY-ERA-MATRIX.md       GENERATED readable projection of the #139 matrix plus current legacy
                               audit counts. Rebuild with scripts/locality_matrix.py.
  report.py                   Prints coverage and rewrites exactly three exports:
                              confirmed_sources.json, CONTRADICTED.json, UNCONFIRMED.json.
                              NOT "all exports" — MANUAL_REVIEW.* comes from classify_manual.py,
                              open-items.html from scripts/open_items.py, SOURCES.md from
                              scripts/source_registry.py, and the FINISH_* queue from
                              scripts/finishes.py.
  classify_manual.py          (Re)tags structurally undocumentable units.
  fetch_attachment.py         Files a card photograph into verification/specimens/ against a
                              SPEC id, from a local path or a reachable URL. Validates format,
                              truncation and size before writing, so S9/S10 cannot be handed a
                              broken file. `--list` shows which specimens still lack one.
  verify_finish_sources.py    Rechecks exact TCGCSV product IDs and expected positive subtypes.
                              Replayable offline against fixtures/tcgcsv_finish_sources.json.
  review_integrity.py         Structural checks WITHIN each store — run after every write pass.
  review_findings.py          Cross-artifact consistency BETWEEN the stores and what consumers
                              read, plus publication readiness. Stdlib only, no network.
  checks.py                   The check protocol shared by the two suites above. Counts are
                              reported, never asserted (see §7).
  publication_gate.py         Blocks deployment until publication-decisions.json records the
                              approvals; the Pages workflow feeds it the real repo visibility.
  test_site.py                Browser acceptance tests (playwright + chromium).
  fixtures/                   Recorded responses so networked checks stay testable offline.
  specimens/                  Photographs of cited specimens, one file per SPEC-nnnn record in
                              specimens.json. Filed by fetch_attachment.py; S9/S10 hold the
                              registry and the directory to each other.
  history/                    Frozen snapshots — launch runbook, migration plan, dated reviews.
                              Each carries a "Historical record" banner and is not maintained;
                              check D3 enforces the banner (#102).
  archive/passes/             68 completed one-shot passes. Each closed a batch and is named by
                              what it did. NEVER rerun and NEVER edited: check X3 hashes every
                              file here against archive/MANIFEST.json and fails on any change.
                              Paths derive from each script's location.
  cache/                      Raw API dumps (gitignored — reproducible via the archived fetch_*
                              passes).
```

`.gitignore` excludes `verification/cache/` (13 MB reproducible API dumps) and
`verification/zoom/` (image crops). Everything else is committed.


## 2. Where to go next

This file deliberately carries no backlog. Priorities live in the issue tracker, which is the only
copy that closes when the work does.

For current figures — units confirmed, contradicted, settled, disputed — read
[`verification/DATA-HANDOFF-AUDIT.md`](verification/DATA-HANDOFF-AUDIT.md). It is regenerated by
`python scripts/database.py` from the stores themselves.

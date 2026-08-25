<!-- doc: role=workflow DAG and data contracts; stage=task -->
# Workflow DAG and data contracts

This is the normative map for issue #285. It describes how an observation becomes a
reviewed claim, a graph edge, a projection, and finally a release artifact. It does not
replace the data stores, and it does not authorize hand-editing generated projections.

`scripts/regen.py` remains the executable L3 full-build order; the scoped lanes from issue #290
are bounded L0-L2 shortcuts and never replace it. This document is the contract that gate and
impact work must use.

The active orchestration has one executable source of truth: `scripts/regen.py` owns the ordered
`REGEN`, `CHECK`, and `TESTS` lists. `.github/workflows/release-gate.yml` invokes its `--check`
mode and adds only explicit environment/publication checks. `.github/workflows/pages.yml` calls
that reusable gate first and consumes its commit-bound artifact handoff. README, CLAUDE, and
HANDOVER link here instead of maintaining another command sequence.

## 1. Terms and invariants

| Term | Meaning | Boundary |
|---|---|---|
| Input | External observation, retained run, issue manifest, snapshot candidate, or owner decision | May be incomplete; never a verdict by itself |
| Canonical store | Reviewed state or append-only evidence record | The only place a truth change is accepted |
| Graph entity | Stable identity for a claim, release, set, work, source, specimen, finish, or physical printing | Identified by semantic ID, never array position |
| Graph edge | Typed relation between entities with provenance | Must preserve positive support, scope, and conflicts |
| Projection | Generated consumer view such as finish, checklist, collector, database, or site | Never an input to another truth decision |
| Gate | A check at a defined scope and cost | A smaller gate may not claim full-gate coverage |
| Run | Immutable source-first or refresh attempt with inputs and hashes | A failed/empty run is not evidence of absence |

The following invariants apply to every path:

1. Positive evidence is required. Provider silence, a zero result, a missing image, or a
   missing TCGdex row never establishes `not-printed`.
2. Language availability, physical finish, specimen observation, locality, and collector
   presentation are separate facts and stores.
3. A generated file is a projection. It is regenerated from reviewed inputs and never
   hand-edited as a shortcut.
4. A source-first candidate remains a candidate until reviewed and reconciled to the
   canonical graph; it cannot mutate a language verdict or finish verdict directly.
5. Cardmarket is a frozen historical candidate boundary. A seller photograph is positive
   physical evidence; a Cardmarket filter or omission is not a print-manifest assertion.
6. Historical passes under `verification/archive/` are provenance, not recurring workflow.

## 2. Canonical stores

| Store | Owner / writer | What it means | Primary downstream edges |
|---|---|---|---|
| `snorlax_cards.json` | legacy input; `scripts/legacy_baseline.py` checks it | Frozen Cardmarket-derived candidate universe | candidate claim membership |
| `legacy-cardmarket-baseline.json` | reviewed immutable boundary | Historical membership floor, not verification state | candidate-claim disposition |
| `verification/units.json` | reviewed evidence passes | Card × language × variant verification state | `supports`, `contradicts`, `established-by` |
| `verification/evidence.jsonl` | append-only observation journal | What was observed and when; not replayable state | evidence provenance |
| `verification/owner_adjudications.json` | collection-owner decision | Explicit final application/absence decision | scoped adjudication edges |
| `verification/finish_units.json` | `scripts/finishes.py` from reviewed inputs | Set-number × language finish state and mappings | `asserts-finish-for`, `uses-profile`, `maps-to` |
| `verification/finish_overrides.json` | reviewed special-printing input | Finish facts not expressible by group-level sources | finish/profile edges |
| `verification/finish_tcgdex_snapshot.json` | explicit refresh/accept flow | Versioned offline TCGdex input | finish candidates; never direct verdicts |
| `verification/specimens.json` + `verification/specimens/` | `verification/fetch_attachment.py` | Stable physical cards and optional observations/photos | `observed-by`, `supported-by`, physical printing provenance |
| `verification/set_catalogue_sources.json` | reviewed catalogue input | Set/product identity, releases, dates, edition scope | `asserts-release-event`, `asserts-set-edition`, `scoped-to` |
| `scripts/source_registry.py` + `verification/source_capabilities.json` | reviewed provider and capability inputs | Provider authority plus bounded positive confirmation dimensions, including PokéCottage | provider/surface/coverage/observation edges |
| `verification/source_adapters.json` | reviewed source-first adapter inventory | Provider slices, gaps, and terminal states | source/capability and candidate edges |
| `verification/card_discovery_adapters.json` | reviewed card-discovery inventory | Locality-aware card query slices and gaps | candidate card/release edges |

The source-first raw runs and refresh candidates are immutable transport evidence:

- `verification/runs/source-adapters/`
- `verification/runs/card-discovery/`
- `verification/cache/finish-tcgdex/` (ignored transport cache only)

Their staging/record files are review surfaces. They do not write `units.json`,
`finish_units.json`, or the graph verdicts without reconciliation.

## 3. Full projection DAG

The full build is grouped here by contract boundary. The exact executable sequence is owned by
`scripts/regen.py`; this map explains the boundaries without duplicating its command arrays.

### A. Claim and evidence foundation

```text
scripts/legacy_baseline.py
  -> scripts/analyze.py
  -> scripts/evidence_semantics.py
  -> scripts/editions.py
  -> scripts/finishes.py --offline
  -> scripts/language_status.py
  -> scripts/confirmed_releases.py
  -> verification/report.py
```

- `analyze.py` is the sole producer of the analysis family and reads the legacy input.
- `evidence_semantics.py` applies conservative status/application/absence rules.
- `editions.py`, `finishes.py`, and `language_status.py` remain separate because edition,
  technical finish, and language truth are different facts.
- `confirmed_releases.py` consumes reviewed language/finish results; it does not discover
  new cards.
- `verification/report.py` exports confirmed, contradicted, and unresolved reports.

### B. Source, identity, and locality graph

```text
scripts/source_registry.py
  -> scripts/source_capabilities.py
  -> scripts/source_adapters.py
  -> scripts/authoritative_graph.py --write
  -> scripts/artwork_review.py
  -> scripts/card_discovery.py
  -> scripts/asia_locality_matrix.py
  -> scripts/locality_matrix.py
  -> scripts/completeness_gate.py
```

- Source registry resolves provider/evidence identity.
- Source capabilities records what a provider can positively establish and where its
  coverage is bounded.
- The scoped source-discovery lane checks both before adapter and graph projections, so a
  provider-policy change cannot bypass its registry or capability graph.
- Source adapters and card discovery reproject retained runs; refresh acquisition belongs
  to `discovery_cycle.py`, not to normal offline regeneration.
- `authoritative_graph.py` is the identity/provenance hub. It materializes reviewed graph
  entities and typed edges; it does not turn a candidate into a verdict merely because a
  row exists.
- Artwork, locality matrices, and completeness are graph-backed projections/gates, not
  independent truth stores.

### C. Consumer projections and publication inputs

```text
scripts/checklist.py
  -> scripts/collector_catalogue.py
  -> scripts/readme_stats.py
  -> scripts/issue_templates.py
  -> scripts/open_items.py
  -> scripts/database.py
  -> scripts/tracker.py (tracker template)
  -> scripts/site.py
```

Every consumer must retain stable semantic identity. In particular, collector and site
rows must not use array positions as identity and must not infer a physical printing from
a language claim or a marketplace candidate.

### D. Manual Pages deployment lane (after the reusable L4 gate)

```text
release-gate.yml (workflow_call, Linux + Windows)
  -> gate-manifest-{os}.json (commit/tree/catalogue fingerprints)
  -> pages-artifact (allowlisted _site + collector_deployment.json)
  -> pages.yml download-artifact
  -> verification/gate_manifest.py --check-dir
  -> scripts/publish.py --verify
  -> scripts/collector_deployment.py --check
  -> verification/publication_gate.py
  -> upload-pages-artifact
  -> deploy-pages
```

The reusable gate is mode-sensitive: draft PRs skip the job, ready PRs run deterministic L3 only,
and workflow-call/manual release paths run L4 live/browser/publication checks. A push to `main`
runs the separate P6/P7 history audit against exactly `GITHUB_SHA`. Pages does not regenerate a
second projection tree; it downloads the artifact produced after the L4 gate and rejects missing,
stale, or fingerprint-disagreeing handoffs before deployment. The explicit list is a deployment
boundary, not a second full-build order.

### E. Verification envelope

The ordered `TESTS` tuple in `scripts/regen.py` is the sole executable inventory. Do not copy that
list into documentation: adding a test would immediately make the prose stale. The ownership and
gate-matrix stores below map each current test to its contract and execution boundary.

The envelope has four distinct responsibilities:

- internal store invariants;
- domain contracts at input/projection boundaries;
- cross-artifact and publication consistency;
- determinism/readiness of the central build command.

The normative gate/impact data lives in `verification/workflow_gate_matrix.json`; its stdlib-only
regression is owned by `scripts/regen.py`.

Test responsibility is recorded in `verification/workflow_test_ownership.json`. It gives every core
test one primary contract owner, names the deterministic fixtures that may be shared, and keeps
import, projection, cross-artifact, browser, live, and publish boundaries separate.

The following operational scripts are intentionally outside the normal offline DAG:

- `scripts/discovery_cycle.py` acquires/validates a retained source-first run.
- `verification/verify_finish_sources.py` performs the explicit live finish-source check.
- `scripts/publish.py` assembles and verifies the allowlisted public artifact.
- `scripts/collector_deployment.py` binds the deployment manifest to the deployed commit.
- `scripts/absence_model.py` supplies absence/application semantics to the evidence layer.
- `scripts/measure_workflow.py` measures the selected core/CI/Pages lanes, declared store
  reads, observed file deltas, and graph fan-out. It writes the diagnostic baseline to
  `verification/workflow_runtime_baseline.json`; it is never part of the merge gate.
- `scripts/scoped_regen.py` executes one lane from `verification/scoped_pipeline_manifest.json`,
  records a Run-ID, graph impact, declared writes, and skipped checks, and leaves the L3 full gate
  as the merge boundary.
- `scripts/workflow_loop.py` evaluates the bounded physical-evidence, evidence, source-first
  discovery, News/Promo, TCGdex, absence, and Cardmarket state machines from
  `verification/workflow_loop_manifest.json`. The manifest records each loop's lane, impact
  classes, and ordering-only `dependsOn` graph; dependencies never trigger another loop. It stops
  on terminal state, unchanged progress, failed lane, or the cycle cap; it never promotes a
  missing result to an absence verdict.
- `verification/gate_manifest.py` is a runtime-only handoff contract. It binds a successful L3/L4
  gate to the full commit/tree and collector catalogue fingerprints; `pages.yml` verifies all
  OS manifests before deploying the uploaded artifact. It is intentionally not a canonical store
  and never enters `regen.py`'s generated output.

The measurement separates declared ownership from observation: the gate matrix supplies
the stores and projection roots a lane declares, while the runner records only the files
that changed during each subprocess. Live-network and browser steps are explicit opt-ins;
the default report marks them `not-run` instead of treating an unavailable environment as
a passing check.

They are invoked by a use-case or release workflow, not silently by an unrelated data
projection.

## 4. Use-case contracts

| Use case | Canonical entry | Graph impact | Required boundary |
|---|---|---|---|
| Known card confirmation | Evidence observation + reviewed unit update | Existing claim/release edge; possibly source/provenance | Evidence application and source identity; no discovery refresh |
| New card from internet/source-first | Retained adapter/discovery run, then reconciliation | New candidate/release/source edges; locality and mapping edges | Adapter/card-discovery/completeness before canonical mutation |
| New set or promo announcement (including Pokémon.com news) | Official lead, then concrete set/card source | Set/release/card edges only when positively identified | News alone is a lead; no inferred card list or finish |
| Physical card/image | Issue manifest → attachment importer → specimen | `observed-by`/`supported-by` to finish/printing | Image/hash/SPEC validation, then finish/graph/collector projection |
| Cardmarket listing | Historical candidate or positive seller photo | Candidate provenance or physical observation | Never expands the frozen baseline automatically |
| TCGdex refresh | Candidate snapshot → explicit accept | Finish candidate/profile edges | Hash/URL diff and review before accepting snapshot |
| Contradiction / absence | Scoped source or owner adjudication | `contradicts` or bounded absence/adjudication edges | No zero-result inference; unresolved stays disputed/pending |
| Artwork review | Graph-backed browser projection | Artwork/work/image observation edges | Browser proposals never write catalogue truth directly |

## 5. Graph edge contract

The current graph uses typed relations including:

`asserted-by`, `asserts-finish-for`, `asserts-finish-profile`, `asserts-local-set`,
`asserts-rarity-claim`, `asserts-rarity-for`, `asserts-release-event`, `asserts-set-edition`,
`belongs-to`, `established-by`, `identifies`, `implements`, `localized-as`, `maps-to`,
`materializes`, `observed-by`, `proposes-for`, `provenance`, `realizes`, `references`,
`relates`, `scoped-to`, `supported-by`, `supports`, and `uses-profile`.

Every new or changed edge must answer:

- Which stable `from` and `to` entity IDs does it connect?
- Is it an observation, a reviewed assertion, a contradiction, a proposal, or a
  materialized projection?
- Which source, specimen, run, or owner decision supports it?
- Which downstream projection consumes it?
- What is the correct state when the source is unavailable or incomplete?

Semantic printing identity is derived from release, finish, edition, foil pattern, markings,
distribution, and card size. It is not derived from list order.

## 6. Gate-mode boundaries (#292)

| Event | Gate | Expensive checks | Artifact behavior |
|---|---|---|---|
| Draft PR | none | none | no release artifact |
| Ready PR | L3 | offline deterministic suite on Ubuntu + Windows | gate manifest only |
| Push to `main` | P6/P7 | full-history publication audit at `GITHUB_SHA` | no second build |
| Manual Pages run | L4 | live finish sources, Linux browser, allowlist, publication approval | download the already verified `pages-artifact` |

## 7. Boundaries

- Scoped execution is an optional local optimization; it never replaces the L3 merge gate.
- Test-suite ownership lives in the versioned ownership manifest, not a copied prose list.
- Pages/CI behavior is documented in the gate-mode table above and enforced by the workflows.
- This map describes evidence, finish, source and absence flows; it does not change their data.
- Historical archives remain immutable inputs to their hash checks.

## Contract evidence

- The full input → store → graph → projection → gate path is documented.
- Every active `regen.py` generator has an owner and boundary.
- Every requested use case has an entry point and forbidden shortcut.
- Later issues can reference this file instead of inventing another workflow list.

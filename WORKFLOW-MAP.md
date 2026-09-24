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
| Gate | A read-only check at a defined scope and cost | A smaller gate may not claim full-gate coverage or mutate state |
| Run | Immutable source-first or refresh attempt with inputs and hashes | Only an eligible compatible complete run may back canonical staging; a failed/empty run is not evidence of absence |

The following invariants apply to every path:

1. Positive evidence is required. Provider silence, a zero result, a missing image, or a
   missing TCGdex row never establishes `not-printed`.
2. Language availability, physical finish, specimen observation, locality, and collector
   presentation are separate facts and stores.
3. A generated file is a projection. It is regenerated from reviewed inputs and never
   hand-edited as a shortcut.
4. A source-first candidate remains a candidate until reviewed and reconciled to the
   canonical graph; it cannot mutate a language verdict or finish verdict directly.
5. Cardmarket is a frozen historical candidate boundary. A retained exact product image or seller
   photograph is positive evidence only for visible card properties; a Cardmarket filter, offer,
   count or omission is not a print-manifest assertion.
6. Historical passes under `verification/archive/` are provenance, not recurring workflow.
7. Reconciliation consumes the complete candidate set. It refines an unknown dimension only when
   exactly one compatible value remains, so equivalent input order cannot change the result.

## 2. Canonical stores

| Store | Owner / writer | What it means | Primary downstream edges |
|---|---|---|---|
| `snorlax_cards.json` | retained candidate input with field-scoped projectors (below) | Live candidate membership and metadata, plus materialized edition/finish/language fields; only the baseline is frozen | candidate claim membership |
| `verification/authoritative_graph.json` | reviewed migration base; `scripts/authoritative_graph.py --write` refreshes its owned slice | Retained hybrid, not a disposable full projection | stable locality/identity and physical-printing edges |
| `legacy-cardmarket-baseline.json` | reviewed immutable boundary | Historical membership floor, not verification state | candidate-claim disposition |
| `verification/units.json` | reviewed evidence passes | Card × language × variant verification state | `supports`, `contradicts`, `established-by` |
| `verification/evidence.jsonl` | append-only observation journal | What was observed and when; not replayable state | evidence provenance |
| `verification/card_content_observations.json` | reviewed field observations, validated by `scripts/card_content.py` | Exact printed content and explicit source assertions for existing releases/printings; no independent membership or verdict | source registry and the bounded Malie export contract |
| `verification/owner_adjudications.json` | collection-owner decision | Explicit final application/absence decision | scoped adjudication edges |
| `verification/finish_units.json` | `scripts/finishes.py` from reviewed inputs | Set-number × language finish state and mappings | `asserts-finish-for`, `uses-profile`, `maps-to` |
| `verification/finish_overrides.json` | reviewed special-printing input | Finish facts not expressible by group-level sources | finish/profile edges |
| `verification/finish_tcgdex_snapshot.json` | explicit refresh/accept flow | Versioned offline TCGdex input | finish candidates; never direct verdicts |
| `verification/specimens.json` + `verification/specimens/` | `verification/fetch_attachment.py` | Stable photo/observation records; explicit `sameCardAs` groups validated by `scripts/specimen_groups.py` | `observed-by`, `supported-by`, physical printing provenance with per-view field sources |
| `verification/set_catalogue_sources.json` | reviewed catalogue input | Set/product identity, releases, dates, edition scope | `asserts-release-event`, `asserts-set-edition`, `scoped-to` |
| `scripts/source_registry.py` + `verification/source_capabilities.json` | reviewed provider and capability inputs | Provider authority plus bounded positive confirmation dimensions, including PokéCottage | provider/surface/coverage/observation edges |
| `verification/source_adapters.json` | reviewed source-first adapter inventory | Provider slices, gaps, and terminal states | source/capability and candidate edges |
| `verification/card_discovery_adapters.json` | reviewed card-discovery inventory | Locality-aware card query slices and gaps | candidate card/release edges |

The source registry resolves specimen citations against legacy units, admitted source-first
prints, finish printing IDs and candidate claims in the graph's retained reviewed base. It does
not consume the downstream `physical-evidence-projection` slice; citation resolution never
depends on a confirmation or corroboration verdict.
Typed standalone observations are registered under their own SPEC ID, without inventing an
upstream physical ID. Downstream, `scripts/specimen_links.py` supplies the common artwork and
collector reference resolver: release claims and source-first records plus the applicable
physical printing's explicit IDs. Artwork aggregates its release; collector provenance adds only
the current item's physical evidence. These joins expose evidence and never change admission,
corroboration, finish truth or collection identity.

The source-first raw runs are retained transport evidence; refresh candidates are staging:

- `verification/runs/source-adapters/`
- `verification/runs/card-discovery/`
- `verification/cache/finish-tcgdex/` (ignored transport cache only)

Retained runs are immutable; ignored refresh candidates are replaceable staging, not recovery
sources. The accepted finish snapshot is the versioned recovery source.

Their staging/record files are review surfaces. They do not write `units.json`,
`finish_units.json`, or the graph verdicts without reconciliation.

Canonical staging selects the newest complete retained run that is compatible with the acquisition
contract and the scoped capability pin. Failed, incomplete, empty, or acquisition-incompatible runs
remain retained but noncanonical. A replay may reuse the source run's bytes and retrieval metadata
only under that same acquisition boundary; it renders with the current reviewed projection contract
and capability state and never mutates the retained source run.

### Hybrid ownership and recovery

Do not delete either hybrid store to force regeneration. Restore a lost file from Git first.
`regen.py` updates owned fields in dependency order; it is not a replay of the original harvest
or locality migration. Never run archived migration passes to recover current state.

| Retained store / slice | Sole recurring writer | Recovery and preservation contract |
|---|---|---|
| Candidate membership, product identity and harvested metadata in `snorlax_cards.json` | Reviewed input changes; no rebuild generator | Preserve the committed file and immutable baseline. `legacy_baseline.py` validates the membership floor, not all live metadata. |
| Candidate edition fields | `scripts/editions.py` | Reproject from its reviewed edition inputs while preserving other candidate fields. |
| Candidate finish fields | `scripts/finishes.py --offline` | Reproject from accepted snapshot, overrides and specimen inputs; preserve unrelated fields. |
| Candidate language fields | `scripts/language_status.py` | Reproject from unit/evidence and owner-decision semantics; marketplace `languages` remains the input claim. |
| Graph locality, release, work and catalogue base | Reviewed graph changes; no complete rebuild generator | Preserve existing entities, mappings and stable IDs. SQLite graph tables are consumer materialization, not an independent authority. |
| Graph legacy-language candidate `sourceRecord` | `project_physical_evidence()` in `scripts/authoritative_graph.py` | Refresh from the matching `units.json` source URL only. |
| Graph finish/specimen claims and owned physical printings | The same physical projector | Replace claims with `sourceKind` `finish-printing-record` or `specimen-observation`, physical nodes with `sourceFinishUnitId` or `PHYSICAL:specimen:` IDs, incident edges and corresponding dispositions. Reuse existing semantic identity mappings and release proposals. |
| Graph summaries, ordering and generation metadata | The same physical projector | Recompute after merging the retained base and projected slice; validate before atomic replacement. |

The remaining canonical stores in the table above are retained inputs unless a writer is explicitly
named. `finish_units.json` is rebuilt by `finishes.py` from its declared reviewed sources, not
from the evidence journal. Consumer JSON/CSV reports, the artwork JSON/JS and preview derivatives,
SQLite handoff/template and static HTML are replaceable outputs of their named generators.
User collection databases and browser review proposals are user state, never disposable build
outputs. The executable rebuild sequence remains `regen.py`; restoring the reviewed inputs is
a prerequisite, not one of its steps.

ADR-0008 describes the accepted registry design. Separate reviewed artwork registries and a
complete separation of the retained graph base from its physical materialization remain design
work, not capabilities of the current rebuild. Keeping the hybrid with explicit field ownership
is the bounded F12 decision for #357; a bulk migration is outside this issue.

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
- A complete, balanced card-discovery run can still have positive `new-candidate` records.
  `workflow_loop.py --loop discovery` reports these as `needs-reconciliation` and prints their
  count plus the review file; reconcile each to a release or an explicit unresolved decision
  before calling the discovery work complete.
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

The bounded [Malie export](verification/MALIE-EXPORT.md) consumes the reviewed collector
join, the versioned profile and field observations. Its three generated files under
`exports/malie/` are an additional consumer view; they do not write evidence, graph or
collection state back. The report preserves all selected IDs, unresolved reasons and
physical dimensions, and binds the cards/profile/input bytes by digest. `regen.py`
places the exporter after its collector/source dependencies and owns its write/check/test
commands. The real-pilot test checks exact localized values, full accounting, corrupt
bundles and unchanged input/output metadata across repeated observational checks. The
same L3 path runs on Linux and Windows. The [package guide](exports/malie/README.md)
documents the standalone consumer; its isolated regression reads only the three bundle
files. Publication remains a separate gate through the existing allowlisted publisher.

The artwork review is a deliberately bounded consumer of the graph. `scripts/artwork_review.py`
writes both the canonical JSON projection and an equivalent generated JavaScript fallback. The
site embeds only a 924-byte metadata envelope; HTTP pages fetch the JSON on demand and offline
`file://` pages load the fallback script. The review section also preloads when it approaches the
viewport, keeps search/filter evaluation in memory, and emits at most 20 groups per batch with an
explicit “Load more” action. Browser proposals still carry the same projection and schema versions.

Issue #356 recorded these DOM measurements in a fresh Chromium context at 1000px height:

| Viewport | Previous initial DOM / artwork cards | Current initial DOM / artwork cards |
|---:|---:|---:|
| 320 px | 73,292 / 559 | 20,395 / 0 |
| 375 px | 73,292 / 559 | 20,395 / 0 |
| 768 px | 73,292 / 559 | 20,395 / 0 |
| 1440 px | 73,292 / 559 | 20,395 / 0 |
| 1920 px | 73,292 / 559 | 20,395 / 0 |

The static `index.html` file is 1,237,743 bytes at the #357 documentation update; serialized
browser DOM sizes are not the file transfer size.

The previous run embedded 2,965,989 artwork JSON characters and built 933 image elements. The
current initial page embeds 924 metadata characters and no artwork images. After loading, the
first batch contains 20 groups, 65 members and 97 images; the remaining groups are reachable via
the button. Local originals remain under `images/`; `images/previews/` and `images/thumbs/` hold
generated preview/thumbnail derivatives (360px and 120px maximum widths). The projection retains
each original path and SHA-256, and the UI links both the derivative preview and the original
download. During a normal `python scripts/regen.py` write, `scripts/artwork_review.py` calls the
standard-library `scripts/artwork_derivatives.py` writer before regenerating the projection.
Missing derivatives are created deterministically; `verification/artwork_derivative_manifest.json`
binds each derivative to the current source hash so a replaced source cannot reuse an old image.
Existing derivatives are reused until that hash changes.

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
also runs the explicit full retained source/card-discovery history checks; a pull request that
changes retained-run or projection-input paths runs that same history lane before merge. The
pull-request workflow does not install browser dependencies; UI-relevant paths select
`.github/workflows/ui-pr.yml`, which runs the Chromium behavior suite. Pages does not regenerate a second projection tree; it
downloads the artifact produced after the L4 gate and rejects missing, stale, or
fingerprint-disagreeing handoffs before deployment. The explicit lists are deployment and UI
boundaries, not a second full-build order.

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
- `scripts/source_adapters.py --check --full-refresh` and
  `scripts/card_discovery.py --check --full-refresh` validate every retained discovery run in the
  L4 history lane; their default `--check` projects only the selected run and direct predecessor.
- `scripts/measure_discovery.py` reports retained-run selection, raw I/O bytes, parser cost and
  projection cost for both modes without changing generated files.
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
  gate to the full commit/tree, collector catalogue fingerprints and exact Malie bundle digests;
  schema 1.1.0 rejects export bytes absent from the containing commit. `pages.yml` verifies all
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

Select the row matching the requested action, then read its skill and required domain contract.
This table is the single maintained intent-to-workflow route; a reader without automatic skill
discovery follows the same links. Selecting a route does not authorize executing its write path.

The registration column uses `workflow:<id>` from
[the gate matrix](verification/workflow_gate_matrix.json) and optional `lane:<id>` from
[the scoped manifest](verification/scoped_pipeline_manifest.json). Each registered workflow has
one row; a scoped lane may serve several compatible rows. A dash means no dedicated registered
mutation workflow: the row states whether it is observational or coordinates authorized changes
through existing owners. Commands and execution order remain owned by the existing scripts and
manifests.

| Task / intent | Registered workflow / lane | Skill | Canonical entry | Graph impact | Required boundary |
|---|---|---|---|---|---|
| Reconcile issue progress, rank dependencies or maintain the backlog | — | [issue triage](.agents/skills/snoredex-issue-triage/SKILL.md) | Current issue bodies/comments and PRs, then [evidence and reference contract](verification/RESUME.md#specimen-and-reference-acceptance-contract) | Observation only; issue maintenance cannot change evidence | Original cohort versus current catalogue; no parent/child double counting; update tracker only within authorized scope |
| Register a new source or extend its reviewed capability | — | [source onboarding](.agents/skills/snoredex-source-onboarding/SKILL.md) | [Provider declarations](scripts/source_registry.py), [capabilities](verification/source_capabilities.json), [source contract](verification/ADR-0003-source-capability-coverage.md) | Reviewed provider/capability edges; evidence application uses its existing lane | Retained positive example plus unsupported boundary; manual use needs no automatic adapter; no inferred finish or absence |
| Generate or check the bounded Malie export | `workflow:malie-export` | [issue delivery](.agents/skills/snoredex-issue-delivery/SKILL.md) | [Exporter](scripts/malie_export.py), [profile and field contract](verification/MALIE-EXPORT.md); accepted inputs only | Read release/printing/localization identity; no graph mutation | Explicit write versus observational check; complete dispositions, source binding and independent real-pilot acceptance |
| Search online for specific cards from a prompt or issue / gezielte Kartenbelege suchen | — | [card search](.agents/skills/card-search/SKILL.md) | [Evidence playbook](verification/RESUME.md); search and retention, then existing claim/specimen/admission owner | No mutation from search alone; accepted findings use the owning lane | Exact-card scope; excludes whole-setlist evaluation, set discovery and foundational research |
| Verify a known card claim / bekannten Claim belegen | `workflow:known-card-confirmation` / `lane:correction` | [claim evidence](.agents/skills/snoredex-claim-evidence/SKILL.md) | [Evidence playbook](verification/RESUME.md), observation + reviewed unit update; [application semantics](scripts/evidence_semantics.py) | Existing claim/release edge; possibly source/provenance | Evidence application and source identity; no discovery refresh |
| Refresh sources, find new cards, digging / Quellen aktualisieren, neue Karten suchen | `workflow:source-first-card-discovery` / `lane:source-discovery` | [source refresh](.agents/skills/snoredex-source-refresh/SKILL.md) | [Discovery cycle](scripts/discovery_cycle.py), [card discovery](scripts/card_discovery.py), [adapter inventory](verification/card_discovery_adapters.json); retained run, then reconciliation | New candidate/release/source edges; locality and mapping edges | Offline validation and authorized live refresh are distinct; candidate cannot mutate a verdict |
| Investigate a new set or promo announcement (including Pokémon.com news) | `workflow:set-or-promo-announcement` / `lane:source-discovery` | [source refresh](.agents/skills/snoredex-source-refresh/SKILL.md) | Official lead, then concrete set/card source via [source adapters](scripts/source_adapters.py) and [recurrence contract](verification/RECURRENCE.md) | Set/release/card edges only when positively identified | News alone is a lead; no inferred card list or finish |
| Add photos, scans or issue attachments / Fotos übernehmen | `workflow:physical-card-image` / `lane:physical-evidence` | [specimen intake](.agents/skills/snoredex-specimen-intake/SKILL.md) | Issue manifest → [attachment importer](verification/fetch_attachment.py) → specimen; [acceptance contract](verification/RESUME.md#specimen-and-reference-acceptance-contract) | `observed-by`/`supported-by` to finish/printing | Image/hash/SPEC validation, then registry, graph, artwork and collector acceptance |
| Inspect a Cardmarket page or image | `workflow:cardmarket-lead` | Metadata: [state audit](.agents/skills/snoredex-state-audit/SKILL.md); retained image: [specimen intake](.agents/skills/snoredex-specimen-intake/SKILL.md) | Historical candidate metadata, or the physical-image route above for visible-card evidence from a retained exact product image or seller photo | Candidate provenance or physical observation | Filters, offers and counts never verify a localized card or expand the frozen baseline automatically |
| Refresh TCGdex finish data / Finish-Daten aktualisieren | `workflow:tcgdex-refresh` / `lane:finish-refresh` | [finish refresh](.agents/skills/snoredex-finish-refresh/SKILL.md) | [Finish owner](scripts/finishes.py) and [finish-source contract](verification/FINISH_SOURCES.md); candidate snapshot → review → authorized accept | Finish candidate/profile edges | Hash/URL diff and review before accepting the exact staged snapshot; no card discovery |
| Assess a contradiction or owner absence decision | `workflow:absence-adjudication` / `lane:absence` | [claim evidence](.agents/skills/snoredex-claim-evidence/SKILL.md) | [Evidence playbook](verification/RESUME.md), [absence model](scripts/absence_model.py) and [application semantics](scripts/evidence_semantics.py) | `contradicts` or bounded absence/adjudication edges | Only owner adjudication settles absence; no zero-result inference; unresolved stays disputed/pending |
| Review artwork groups, detections or export browser proposals | `workflow:artwork-review` | [UI / artwork review](.agents/skills/snoredex-ui-audit/SKILL.md) — artwork proposal procedure | [Artwork projection](scripts/artwork_review.py) and [browser review contract](verification/ADR-0007-embedded-artwork-review-ui.md) | Artwork/work/image observation edges | Browser proposals never write catalogue truth directly |
| Audit state only, change nothing / Datenzustand nur prüfen | — | [state audit](.agents/skills/snoredex-state-audit/SKILL.md) | [Current handoff audit](verification/DATA-HANDOFF-AUDIT.md); relevant observational checks, or [full gate](scripts/regen.py) with `--check` | Observation only | No repair, import, refresh or snapshot acceptance; scoped lanes can write and are not automatically read-only |

The [documentation check](verification/test_pipeline_documentation.py) validates row-local
registration coverage, compatible lane impacts, owner references and existing linked targets.
It covers the registered workflows and lanes, not arbitrary unregistered scripts or prior reading.
New operator entry points must be classified during review; helpers do not require a user route.
See [ADR-0010](verification/ADR-0010-agent-discovery-surface.md) for the decision and acceptance boundary.

[Behavioral acceptance cases](verification/SKILL-WORKFLOW-ACCEPTANCE.md) exercise selection and
decisions beyond syntax/link checks. They are review fixtures, not another executable workflow.
The general [compare-implementations template](skill-templates/compare-implementations/SKILL.md)
is portable personal-skill source, outside project skill discovery. Install that directory in the
runtime's personal skills location (Codex: `$CODEX_HOME/skills`, normally `~/.codex/skills`) when
requested; keep the installed copy identical to the reviewed template and record its hash.

Bot-gated source retrieval is a helper, not another operator route. Use the
[source-refresh retrieval technique](.agents/skills/snoredex-source-refresh/SKILL.md#source-refresh-bot-gated-retrieval)
for acquisition; apply recovered evidence through the existing
[claim-evidence workflow](.agents/skills/snoredex-claim-evidence/SKILL.md).
Retrieval alone creates no graph verdict and does not bypass retained-run or adjudication contracts.

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
| Ready PR | L3 | offline deterministic suite on Ubuntu + Windows; UI paths add Chromium behavior lane | gate manifest only |
| Push to `main` | P6/P7 | full retained discovery history and publication audit at `GITHUB_SHA` | no second build |
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

<!-- doc: role=hard-coded data audit; stage=task -->
# Hard-coded data and exception audit (#400)

**Audit baseline:** `86abf2cd4091e38898851581e477322c367c057a` (`origin/main`, after #397).
**Scope:** active generators, validation code, tests, workflow definitions, and retained verification
inputs that feed generated or dynamic consumers. The audit distinguishes curated domain inputs and
minimum-coverage guards from implementation exceptions. It does not treat every literal in code
as a defect: algorithms, schemas, stable vocabularies, and security boundaries need explicit
contracts.

## Findings and disposition

| Finding | Canonical owner | Affected consumers / paths | Disposition |
|---|---|---|---|
| Three generated `card-release` asset IDs in `verification/test_collector_catalogue.py` (found during #397 review) | `collector_catalogue.json` generated from graph/source inputs | Collector catalogue generation and its regression suite | Fixed in #397. The test derives shared assets from the generated catalogue and retains the semantic SV-P 117 end-to-end regression. |
| Predecessor checklist rekeys, release rekeys, and split routes in `scripts/collector_catalogue.py` | `verification/collector_migration_routes.json` | `scripts/collector_catalogue.py`, collector catalogue migration, compatibility projection | Moved unchanged. The generator reads and validates reviewed routes; route IDs are migration inputs, not generator implementation. |
| Edition set-code/language groups and source prose in `scripts/editions.py` | `verification/edition_rules.json` | `snorlax_cards.json` editions, then checklist and release projections | Moved unchanged. Classification remains code; reviewed facts and source notes are input data. |
| Set-name aliases and curated card/set date fallbacks in `scripts/confirmed_releases.py` | `verification/confirmed_release_overrides.json` | `analysis_confirmed_releases.json`, CSV, and site | Moved unchanged. Exact-card overrides still precede Bulbapedia set dates, then set fallbacks and the English artist-date fallback. Legacy values were transferred without upgrading their provenance. |
| Czech and Hungarian excluded claim IDs duplicated in `scripts/locality_matrix.py` | `verification/locality_era_matrix.json` `excludedLegacyClaims` | Locality matrix validation/rendering and `scripts/completeness_gate.py` | Removed. Validation now checks every manifest row resolves to a contradicted unit with a reason and rejects duplicate IDs. A regression proves an additional valid manifested exclusion flows without a code change. |

## Retained literals that are contracts

- `scripts/regen.py`'s `REGEN`, `CHECK`, and `TESTS` arrays define the one executable dependency
  order and core gate. `AGENTS.md` explicitly names them the source of truth; duplicating that
  pipeline as generated configuration would create competing workflow definitions.
- `REQUIRED_TRACKS`, locality regression identities, Asian minimum regressions, completeness
  boundaries, and similar expected-minimum sets are deletion guards. They detect a missing
  reviewed coverage promise; they do not inject a data row into a projection. Their evidence and
  expected identities belong in their owning contract, while validation logic stays in code.
- Stable enums and vocabularies (statuses, languages, finishes, marking roles, evidence kinds) are
  schema/protocol contracts. Their literals define accepted values and are not per-card
  exceptions. Presentation mappings such as technical finish to `finishFamily` are code-owned
  transforms, with underlying finish truth retained in `finish_units.json`.
- `scripts/evidence_semantics.py`'s rarity-to-run-membership policy and the distribution-rarity
  guard are semantic rules. They apply to rarity classes and set-size evidence, not to a list of
  selected card IDs; the `Promo`, `Prize Pack Series`, `Oversized`, `World Championship Deck`, and
  `Online Code Card` boundary also appears in the repository's data-model contract.
- Locality track inventories, Asian minimum regressions, expected cross-locality boundaries, and
  named positive-card regression identities remain explicit validation contracts. They prevent
  deletion or accidental identity drift in bounded evidence slices; they do not create a printing
  or inject a generated asset. The exact per-claim exclusions themselves now come only from the
  locality manifest. Their owning paths are `scripts/locality_matrix.py`,
  `scripts/asia_locality_matrix.py`, and `scripts/completeness_gate.py`; source rows and expected
  evidence live in the locality manifests. The Indonesian SV-P 117 case remains a semantic
  specimen-to-collector projection regression.
- Publication allowlists and workflow permissions are security/deployment boundaries. Making them
  infer themselves from the artifacts they constrain would weaken the boundary.
- IDs and values in `verification/passes/` are immutable, one-shot historical evidence/admission
  records. They document what a specific reviewed pass accepted; they are not live generator
  overrides. `X3` protects their hashes.
- Tests may name a semantic card, release, or invariant when that identity is the regression under
  test. They must not pin generated asset IDs where the contract is shared behavior; #397 corrected
  that case.

## Audit method and limits

The active source tree was searched for generated IDs and literal exception maps, then the
identified generator paths were traced to their canonical inputs and current consumers. Generated
artifacts are validated by the repository's normal regeneration and cross-artifact checks. This is
a point-in-time audit of the repository at the baseline above; it is not a claim that every
historical pass or every future code literal is automatically classified.

The date and edition values remain curated and still need reviewed evidence when changed. Moving
them to JSON makes their ownership and review surface explicit; it does not itself prove or improve
the sources behind legacy values. Existing evidence/provenance gaps remain gaps and must not be
described as newly verified by this migration.

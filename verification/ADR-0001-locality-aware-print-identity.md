<!-- doc: role=architecture decision record for claim, card-release and physical-print identity; stage=reference -->
# ADR-0001 — Locality-aware release and physical-print identity

**Status:** accepted design, refined by
[#145](https://github.com/m4s-ai/snoredex-data/issues/145) and materialized by
[#140](https://github.com/m4s-ai/snoredex-data/issues/140) ·
**Issue:** [#134](https://github.com/m4s-ai/snoredex-data/issues/134) ·
**Parent:** [#132](https://github.com/m4s-ai/snoredex-data/issues/132) ·
**Depends on:** [#133](https://github.com/m4s-ai/snoredex-data/issues/133)

This decision defines the identity boundary for locality-aware consumers. The reviewed graph is
materialized in `snoredex.sqlite`'s `graph_*` tables and committed as
[`authoritative_graph.json`](authoritative_graph.json); compatibility projections are no longer
inputs to the application. The machine-readable contract remains
[`print_identity_schema.json`](print_identity_schema.json).

## Context

The legacy catalogue starts from Cardmarket products. A product is identified by
`(setCode, number, variantToken)` and carries a list of marketplace languages. The verification
store refines that into `(setCode, number, variant, language)` claims, but the set code and number
still belong to Cardmarket's product slot rather than necessarily to the localized card.

That creates two separate conflations:

1. **Local languages are collapsed.** A Korean claim on a Japanese product has no place to store
   the Korean set code or collector number. Several Western languages also shared one previous
   `WEST:set:number:variant` print id even though the cards are physically different language
   editions.
2. **Assertions are treated as objects.** The previous dry-run created a `print` node for every
   claim, including claims whose legacy status is contradicted and finish records supported only
   by Cardmarket catalogue hints.

The reviewed migration made the second problem measurable: 634 confirmed language units became only
303 print groups; 72 groups mixed confirmed languages, 55 groups contained contradicted claims
only, and 13 mixed statuses. Those figures describe the coarse key, not the physical world.

## Decision

Use three different grains.

### Candidate claim

A **candidate claim** is one assertion from one immutable input record. It may propose a card
release or a physical printing, but it is never itself proof that the proposed object exists.

Every input stays visible:

- all 719 legacy language units;
- all 693 recorded finish-printing claims;
- all 8 source-first specimen/card records; and
- all 75 positively excluded code-card units.

The permitted dispositions are `established-and-mapped`, `candidate-needs-evidence`,
`bounded-contradicted`, and `positively-excluded`. `bounded-contradicted` preserves the 85 existing
verdicts as non-materializing claims; this model makes no new contradiction, and #137 remains the
owner of future evidence inference.

### Card release

A **card release** is one numbered card slot in one language-bearing set edition, before finish,
stamp, distribution, size, or error distinctions. It belongs to exactly one set edition whose
locality, printed language, and script are explicit.

The identity is:

```
setEdition + localCollectorNumber + work
```

When local identifiers are unknown, `localSetCode` and `localNumber` are null. Reversible
`viaLegacy*` anchors say where the claim came from without manufacturing a local identifier.

Variant tokens do not belong in this identity. Multiple legacy variants may refer to different
physical finishes or distributions of the same language-bearing card release. Work mapping may
also stay unresolved: a positively evidenced local release does not need a guessed equivalence to
another country's card in order to exist.

### Physical printing

A **physical printing** is one positively evidenced manufactured realization of a card release.
Finish, foil pattern, markings, distribution, size, and explicit error class live here.

A confirmed language claim establishes at most a card release. A physical-printing node requires
positive evidence for the manufacturing classification. Current `finish_units.json` records with
`verificationStatus=confirmed` may establish one; `marketplace-claimed` records remain candidate
claims because Cardmarket is not external verification.

## Measured result

The 0.2.0 dry-run maps the current stores to:

| | Count |
|---|---:|
| Candidate claims | 1,495 |
| — established and mapped | 1,110 |
| — candidate, needs evidence | 225 |
| — existing bounded contradiction | 85 |
| — positively excluded | 75 |
| Language-bearing set editions | 428 |
| Established card releases | 569 |
| — with known local identifiers | 459 |
| — needing local identifiers | 110 |
| Established physical printings | 468 |
| Contradicted-only card-release proposals kept as candidates | 76 |
| Mixed-status card-release proposals | 1 |
| Cross-language release merges | **0** |
| Unexplained same-language product splits | **0** |
| Unresolved legacy language units | **0** |
| Unresolved confirmed physical claims | **0** |
| Orphan specimens | **0** |

The old 55 contradicted-only print groups become 76 language-aware release proposals because
language is no longer erased. None materializes a card release. The old 13 mixed groups reduce to
one real same-language case, French `xJTG 117`: its confirmed and contradicted variant claims point
at the same release while retaining separate claim statuses.

`BKT 118` is the representative Western fixture. English, French, German, Italian, Portuguese,
Russian, and Spanish are seven card releases in seven set editions. They may relate to one work and
share editorial set concepts later; they are not one object with a `languages[]` field.

## Invariants

1. **Language and locality are explicit and independent.** Spanish spans WEST and LATAM; English
   spans WEST and SEA.
2. **Only permitted positive evidence materializes a target.** Contradicted, unresolved,
   excluded, and marketplace-only claims remain candidates.
3. **A card release belongs to exactly one language-bearing set edition.** No release carries a
   language array.
4. **Manufacturing classifications specialize a release.** Finish, pattern, stamp, distribution,
   size, and error class cannot change set identity.
5. **Shared work never merges local releases.** Japanese `sm10 076` and Traditional-Chinese
   `AS5a 142` may share a work edge and remain different releases.
6. **Aliases and equivalence proposals preserve both raw identifiers and provenance.** Matching
   names, numbers, or art never merge automatically.
7. **An error requires positive evidence plus an explicit classification.** A generic finish pass
   cannot mint a no-symbol or other error printing.
8. **Unknown local identifiers remain null.** Legacy anchors never masquerade as local codes.

`review_findings.py` checks complete input accounting, permitted claim promotion, edition/release
language agreement, null local identifiers, positive physical-print evidence, and zero
cross-language merges through its existing N1/N2 checks rather than adding card-specific checks.

## Relationship to set/release modelling

This ADR defines only the minimum `set_edition` identity needed to keep card releases separate.
[#146](https://github.com/m4s-ai/snoredex-data/issues/146) adds the full catalogue layer:
`set_concept`, local products, release events, market/date waves, and source-backed relationships.
It must build on this language-bearing edition boundary rather than replace it with a global set id.

## Migration contract

Migration remains reversible and dry-run first.

- Every legacy/source input has exactly one candidate-claim node and disposition.
- A back-projection can recover source ids, raw identifiers, statuses, and product relationships.
- Existing evidence and verdicts migrate as recorded; nothing is re-derived here.
- An unresolved claim stays visible and creates no target.
- A newly discovered local identifier replaces a migration anchor through a provenance-bearing
  alias decision, not by overwriting history.
- Consumer migration and the graph's SQLite boundary landed in #140. The schema records the
  constraints so later projections cannot weaken the identity boundary.

## What does not change

- Authority tiers, providers, corroboration, absence scopes, and owner adjudications.
- The positive-evidence rule and the meaning of `pending`.
- The immutable legacy baseline from #133.
- Existing unit and finish verdicts.
- Collector-visible outputs; the dry-run artifact is planning data and is not published.

## Source-first records

The eight records in [`source_first_prints.json`](source_first_prints.json) positively establish
local card releases that Cardmarket never listed. Their historical `printId` values remain raw
record identifiers/aliases for migration compatibility; the dry-run maps them to card-release ids.

Their work equivalence stays explicit. `S-P 101`, for example, establishes a Korean local release
while its relationship to the work currently represented by `S-P 156` remains unresolved. The
model no longer forces a work guess merely to record the physical local card.

Reviewed migration decisions live separately in `legacy_issue_rekeys.json`. A
`same-work-decision` may attach a source-first local release to an existing work while keeping both
local release identities and both raw identifiers intact. The first accepted edge is the owner-
identified `sm10 076` / `TW:AS5a:142` relationship from #84; the other twenty #84 questions remain
explicitly `needs-positive-local-identity`, which is not an absence conclusion.

All eight cited specimens have a release claim, so the orphan count is zero. This corrects the
stale intermediate wording in the original ADR that still said two records were held after both
were resolved later on 2026-08-09.

## Owner decisions retained

- **D1:** every catch-up code backed by a physical specimen enters as its own local release.
- **D2:** releases known to exist but lacking local identifiers remain visible as
  `needs-local-identifier` after migration.
- **D3:** European Spanish and LATAM Spanish are distinct localities of one language, both in
  scope.
- **D4:** a positively evidenced and explicitly classified error is its own physical-printing
  node.
- **D5 (owner, 2026-08-10):** D1 extends to a catch-up code evidenced by a **tier-1 publisher
  record**, and the extension is **for language and identity only** — which set, which number,
  which language. Finish stays `pending`, exactly as it does for every other language claim.

  The asymmetry is the point. For identity, the publisher's own card database is at least as good
  as a specimen and better than the retailer listings four of the first eight admitted prints rest
  on: it states the collector number, the denominator, the card name and the regulation mark
  directly. For finish it is weaker and not a substitute at all — a specimen can be turned over and
  examined, a database page cannot, so nothing here may assert a foil treatment.

  D5 is what makes source-first enumeration of the Asian localities a method rather than a plan
  (#138). It does not widen what counts as tier 1, and it does not touch rule 3: a publisher
  database that fails to list a printing still has a gap, not a proof.

## Consequences

- The graph grows in the honest direction: language releases and physical treatments become
  separate collectible identities instead of overloaded product attributes.
- The local-identifier discovery queue contains established releases only; contradicted-only
  proposals no longer inflate it.
- Source-first discovery can add a local release without inventing a Cardmarket product or work
  equivalence.
- Compatibility projections remain available while consumers migrate to the graph tables.

<!-- doc: role=dated KSS correction root-cause analysis; stage=reference -->
# Spanish KSS correction: root cause and bounded audit

Snapshot: 2026-10-02. Review baseline: PR #420 at
`5299c45af4bdc5df8bad351be5e3311779be28b6`.
This is a dated investigation; current truth lives in the canonical stores.

## Evidence and intended result

`source.json` retains the inspected WikiDex statement that Spanish Bienvenidos a
Kalos was released digitally, not physically, and the owner's correction instruction.
OA-20261001-U0482 supplies the absence authority. SPEC-0132 remains a retained
digital render; its original image hash and acquisition date must not change.
The decision concerns KSS 26/39 European Spanish only.

The expected physical KSS release languages are English, French, German, Italian,
Portuguese and Russian. All other KSS language verdicts and their evidence remain
unchanged. Removing Spanish must reconcile its claim, release, edition, dependent
rarity/assertion, incident edges, product references and migration references.

## Failure chain

1. The first correction removed the Spanish card release but omitted its physical
   set edition. A digital-only language therefore still had an identified edition.
2. The replay path only removed a dependent assertion and returned early when that
   assertion was absent. It could not finish other partially applied corrections.
3. The first correction filtered product `cardReleaseIds` but updated the numerical
   `reason` only on the separate migration disposition. The product retained "7"
   beside six IDs. The later edition fix left this defect intact.
4. These are reviewed fields in a hybrid store. Regeneration refreshes its owned
   projection slice; it does not reconstruct these migration decisions or reasons.
5. The previous regression preserved the surviving product payload verbatim. That
   mistakenly treated its stale reason as data that must survive. Existing gates
   checked structure and references without checking this stored numerical rationale.

Review findings: 4165392322 (edition), 4165392330 (active narrative counts),
4165619270 (product reason). The separate 30thC replay finding 4165392336 concerns
an order-changing upsert and does not alter the KSS verdict.

## Repair and verification boundary

The KSS pass now uses one graph correction for both initial and repeated application.
It reconciles the targeted claim, dependent identities, product and migration
references and both reasons even when the retired entities are already absent.
Unrelated entities and edges are preserved; retirement is guarded against another
release depending on the edition. The evidence journal retains retired identities.

The graph validator checks numerical release-count reasons against each record's
own reference list, across all legacy products and product migrations. It does not
infer equivalence between unrelated legacy and re-keyed release lists.

Regression fixtures cover initial correction, partially retired state, and an
already-retired graph with a stale reason, followed by byte-identical replay.
They assert six releases, matching product/migration reasons, no retired identity
references, preservation of unrelated entities/edges, and guard rejection of
independently corrupted product and migration reasons.

The baseline audit found only KSS with a numerical product reason inconsistent
with its own list. U0482 was already contradicted with owner authority; F0179 had
no printings and all finishes not applicable. The Spanish release/edition IDs and
SPEC-0132 were absent from physical collector, checklist and artwork projections.
The digital image remains in the specimen registry and historical evidence.
Regenerated SQLite and consumer views must carry the corrected six-release reason.

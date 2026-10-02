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
Portuguese and Russian. All other KSS language verdicts remain unchanged. Their current evidence and owner
rationales must distinguish the historical source statement from the superseding owner physical-language conclusion. Removing Spanish must reconcile its claim, release, edition, dependent
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

## Expanded diagnosis after review 5391987130

The graph-only replay repair was incomplete. The pass still used the final U0482
provider/evidence as a completion flag for every store and returned before repairing
the specimen, owner decision and card metadata. A crash after the units write could
therefore survive every later replay. There is now one full correction path: each
store is independently reconciled, the owner decision is upserted, and the digital
observation is restored before synchronizing the replay manifest. Journal entries
retain superseded observations and decisions; a completed second replay is byte-identical.

The narrative audit also found the old physical-language list in seven KSS units
(including Dutch beyond the six review examples) and eight owner rationales. They
are reconciled to the owner's six-language physical decision while retaining the
existing verdicts, decision dates and original source grading. The earlier runnable
owner-decision pass now uses the corrected rationale too; it cannot reintroduce the
old list when restoring a missing decision. Historical text survives in the journal. U0586 also quotes the old KSS sentence
as context for a separate Korean HXY claim; the quote is retained verbatim but
explicitly labelled historical/digital-inclusive before the quoted text.

Regressions now include interruptions after units, after specimen, after adjudication,
a stale existing adjudication, and the previous graph states. They assert the owner
decision, digital-only specimen, manifest, six releases and all-store replay, rather
than assuming graph recovery proves store recovery.

The independent SPEC-0600 finding is a provenance classification error: an eBay CDN
host identifies transport, not a seller or an offer. The retained image remains
positive inspected photograph evidence under the existing unknown-origin, owner-supplied
image route. Its holder and listing remain unknown; the source-first admission, source
profile and replay manifest use that same boundary. Hash, acquisition date, printed
identity, owner rarity decision and visible Holo observation remain unchanged.

## Source-preservation correction after review 5392341219

Finding 4166150640 exposed a second narrative error at `c8be22f`: replacing the
seven-language list inside the original Bulbapedia evidence fabricated a six-language
source statement. The test incorrectly required the source list to disappear. The
physical conclusion was correct, but the evidence attribution was not.

The seven affected KSS observations now retain their complete original statement
and prior inference, explicitly qualified *before* that text as historical,
digital-inclusive and unsuitable as a physical-print manifest or absence evidence.
The later six-language owner conclusion follows separately. The pass recovers the
previously overwritten list without changing the owner suffix. U0586 already retained
its source quote correctly; owner rationales state the owner conclusion without
attributing a six-language list to Bulbapedia.

Regression expectations compare all seven complete original observations retained
in the journal, including the differently worded Dutch row. Initial, previously
misrewritten and already-qualified states must produce the same qualified result,
with byte-identical replay. Consumer exports are regenerated. Verdicts, source
grading, dates, physical identities, specimen bytes and finishes do not change.

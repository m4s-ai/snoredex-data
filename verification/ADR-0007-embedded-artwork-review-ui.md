<!-- doc: role=architecture decision record for artwork grouping and detection review; stage=reference -->
# ADR-0007: embedded artwork-grouping and detection-review interface

- **Status:** Accepted; implementation deferred until #140
- **Date:** 2026-08-11
- **Issue:** #120
- **Depends on:** ADR-0001 identity grains (#134) and the authoritative migrated outputs from #140

## Context

#120 needs an interface for reviewing artwork groups and automatic detection beside the exact
source image. The repository is currently a static, dependency-free data site that works from both
`file://` and GitHub Pages. Its authoritative state is changed by reviewed passes and rebuilt by
generators; the browser has no authenticated write API.

The interface must not bind itself to today's Cardmarket-derived row keys. One shared artwork may
connect several localized physical prints without making those prints interchangeable. A review
therefore needs distinct references for the canonical card/artwork, physical print, locality and
local collector identity, finish/error classification, evidence observation, and any proposed
equivalence edge.

## Decision

Build the review interface as an embedded client-side view in this data repository. It will ship
with the existing static site and read a generated review projection from the authoritative graph
produced by #140. It will not be a separate app/repository and will not introduce a backend.

The projection and UI use stable graph identifiers, never table positions or legacy product/unit
keys. New sets, localities and source observations enter through regenerated data, so the client
does not carry a hard-coded release catalogue.

The browser may group, split and reassign records in memory, but it never writes an authoritative
store directly. It emits a versioned structured proposal with:

- the proposal action (`confirm`, `reassign`, `split`, `unclear`, or `propose-variant`);
- affected work, artwork, physical-print and locality-bearing release identifiers;
- before and proposed-after values;
- the exact source-observation identifier and content hash;
- reviewer/evidence-class fields required by the eventual decision store; and
- the projection/schema version the proposal was made against.

A reviewed import pass validates the proposal against the then-current graph, records the human
decision, and rebuilds every consumer. Stale identifiers, source hashes or before-values fail rather
than being silently rebased. The rebuilt projection is the proof that a decision round-tripped.
Until that import succeeds, a proposal is not a catalogue fact.

The concrete proposal schema, decision-store path and import pass belong to #140's migrated graph.
Implementing them before that graph exists would freeze the legacy identity mistake into a new
surface, so #120's interactive work remains deferred until #140 supplies those outputs.

## Rejected alternatives

- **Standalone app/repository:** duplicates schema, release and deployment coordination while the
  data and its generators still change together here.
- **Backend in this repository:** adds authentication, hosting and a second state authority before
  there is evidence that reviewed proposal handoff is the bottleneck.
- **Direct browser writes:** bypass the reviewed-pass, provenance and deterministic-rebuild
  boundaries that make corrections auditable.

## Consequences

The first implementation can remain static, offline-capable and dependency-free. It has one data
projection and one review path, and future releases require regeneration rather than UI changes.
The tradeoff is deliberate: a reviewer submits or downloads a proposal instead of mutating the
catalogue live.

When #140 closes, #120 resumes with tests proving that grouping keeps localized prints distinct,
every proposal cites the displayed image observation and hash, stale proposals fail, accepted
decisions survive a clean rebuild, and no source-derived value can inject markup into the view.

A backend should be reconsidered only if measured review throughput makes proposal handoff the
constraint and the project has an explicit authentication and write-authority model.

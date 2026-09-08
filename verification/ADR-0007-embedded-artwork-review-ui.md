<!-- doc: role=architecture decision record for artwork grouping and detection review; stage=reference -->
# ADR-0007: embedded artwork-grouping and detection-review interface

- **Status:** Accepted and implemented as a static review/proposal surface
- **Date:** 2026-08-11
- **Issue:** #120
- **Implemented against:** ADR-0001 identity grains (#134) and the authoritative graph outputs from #140

## Context

#120 required an interface for reviewing artwork groups and automatic detection beside the exact
source image. The repository is a static, dependency-free data site that works from both
`file://` and GitHub Pages. Its authoritative state is changed by reviewed passes and rebuilt by
generators; the browser has no authenticated write API.

The interface must not bind itself to today's Cardmarket-derived row keys. One shared artwork may
connect several localized physical prints without making those prints interchangeable. A review
therefore needs distinct references for the canonical card/artwork, physical print, locality and
local collector identity, finish/error classification, evidence observation, and any proposed
equivalence edge.

## Decision

The review interface is an embedded client-side view in this data repository. It ships with the
existing static site and reads `verification/artwork_review_projection.json`, generated from the
authoritative graph produced by #140. The page embeds only a versioned metadata envelope; the
large projection loads on demand through HTTP and uses the generated
`verification/artwork_review_projection.js` fallback for `file://` checkouts. It is not a separate
app/repository and introduces no backend.

The projection and UI use stable graph identifiers, never table positions or legacy product/unit
keys. New sets, localities and source observations enter through regenerated data, so the client
does not carry a hard-coded release catalogue.

The browser can confirm, correct, split, or reassign a detection, mark it unclear, or propose a new
variant. Drafts remain in local storage; a reviewer can download versioned structured proposals.
The generated view may group releases by a pinned image anchor, but that is an explicitly
unreviewed image group and never a reviewed artwork identity. The current graph has no imported
appearance registry, so reviewedAppearanceId remains null until a human decision is accepted.
The browser never writes an authoritative store directly. Each proposal carries:

- the proposal action (`confirm`, `correct`, `reassign`, `split`, `unclear`, or `propose-variant`);
- affected work, artwork, physical-print and locality-bearing release identifiers;
- before and proposed-after values;
- the exact source-observation identifier and content hash;
- reviewer/evidence-class fields required by the eventual decision store; and
- the projection/schema version the proposal was made against;
- the separate automatic image-group identifier, when one exists, without treating it as an
  artworkId or reviewed appearance.

`scripts/artwork_review.py`, `verification/test_artwork_review.py`, and the browser regression pin
the projection/proposal schema, stable graph identities, source observation hashes, image guards,
local draft persistence, and the download handoff. The projection version is a digest of the
semantic projection after order-independent normalization, while the image-group anchor is stable
when later evidence is appended. No reviewed importer or decision store exists yet. A downloaded
proposal is therefore review material, not a catalogue fact; any future importer must reject stale
graph identifiers, content hashes, and before-values instead of silently rebasing them.

## Rejected alternatives

- **Standalone app/repository:** duplicates schema, release and deployment coordination while the
  data and its generators still change together here.
- **Backend in this repository:** adds authentication, hosting and a second state authority before
  there is evidence that reviewed proposal handoff is the bottleneck.
- **Direct browser writes:** bypass the reviewed-pass, provenance and deterministic-rebuild
  boundaries that make corrections auditable.

## Consequences

The implementation remains static, offline-capable and dependency-free. It has one generated data
projection and one browser review path, and new graph data enters through regeneration rather than
hard-coded UI catalogue entries. The browser loads review data only when requested or when the
review section approaches the viewport, renders bounded group batches, and uses generated preview
and thumbnail derivatives while retaining original paths and hashes for downloads and attribution.
The tradeoff is deliberate: a reviewer downloads a proposal instead of mutating the catalogue
live. The current tests prove that automatic image grouping keeps localized prints distinct, proposals
cite displayed observations and pinned hashes, unsafe image-dependent actions are blocked, and
source-derived values cannot inject markup into the view.

Import validation and accepted-decision round trips remain outside the implemented browser
boundary. They require their own reviewed decision-store contract before downloaded proposals can
affect authoritative data.

A backend should be reconsidered only if measured review throughput makes proposal handoff the
constraint and the project has an explicit authentication and write-authority model.

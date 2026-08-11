<!-- doc: role=architecture decision record for source-first card discovery; stage=reference -->
# ADR-0006: source-first card discovery and reconciliation

- **Status:** Accepted
- **Date:** 2026-08-09
- **Issue:** #136
- **Depends on:** ADR-0001 identity grains (#134), ADR-0003 capability edges (#135), and
  ADR-0004 set-frontier adapters (#147)
- **Feeds:** evidence-semantics repair in #137 and locality reconciliation in #138/#139

## Context

The legacy catalogue can verify only rows inherited from one Cardmarket search. ADR-0004 starts
outside that boundary, but enumerates sets and products rather than cards. A card-level loop still
has to ask a provider for Snorlax under its localized name, retain every returned record before
matching, and keep unmatched records visible. Otherwise the missing Traditional-Chinese
`svQP F 012/023` remains undiscoverable even though its official detail page exists.

Provider results are not a closed population. The official Asia search is recent and query-limited;
its name query also returns Munchlax because `小卡比獸` contains `卡比獸`. Expansion keys are text
query parameters such as `SVQP`, while the official symbol can carry a different printed identifier
such as `svQP F`. Pagination, individual detail pages, and symbol assets therefore all need retained
provenance.

## Decision

Adopt [`card_discovery_adapters.json`](card_discovery_adapters.json) as the reviewed adapter/gap
contract, [`card_discovery_schema.json`](card_discovery_schema.json) as its versioned schema,
immutable network runs below `verification/runs/card-discovery/`,
[`card_discovery_staging.json`](card_discovery_staging.json) as the generated graph summary, and
[`card_discovery_records.jsonl`](card_discovery_records.jsonl) as the one-record-per-line review
feed.

The first bounded slice queries the official Taiwan card search with the native full-name token
`卡比獸`. It follows all result pages declared by the source, retains each list page, then retains
and parses every referenced official detail page. It does not read a card, unit, set-code, or
collector-number list to decide what to request. ADR-0001 is read only after discovery, as the
target graph for non-destructive matching.

Each detail keeps its official id, URL, localized name, HTML expansion key, collector number, card
image URL, set-symbol URL, list-response hashes, detail-response hash, retrieval time, and complete
parsed source record. A reviewed set-code assertion may add a printed local identifier without
replacing the raw expansion key. For `SVQP`, the exact official symbol bytes are retained and the
reviewed visual reading asserts `svQP F`; both values remain queryable.

Every record reaches exactly one bucket:

- `matched` for one exact locality + language + asserted local set code + collector-number tuple,
  or an explicit exact mapping;
- `ambiguous` for multiple exact targets or an explicit equivalence proposal;
- `new-candidate` for a positive card detail with no exact local identity;
- `positively-excluded` only when the source-native record establishes another identity or an
  explicit digital-only product; or
- `needs-evidence` when a required source-native identity field cannot be parsed.

An equivalence proposal never fills `targetCardReleaseId`, never overwrites an identifier, and
always carries `destructiveMergeAllowed=false`. Discovery records also carry
`verdictMutationAllowed=false`; they cannot confirm or contradict a legacy unit.

## Loop and terminal states

One refresh follows this bounded loop:

1. resolve each active adapter slice through a registered ADR-0003 positive card-existence edge;
2. query each reviewed localized full name and retain every result page;
3. retain every referenced detail page before parsing or matching;
4. retain any reviewed symbol asset used by an additive set-code assertion;
5. normalize, reconcile to ADR-0001, and balance fetched details against all five buckets;
6. diff stable provider keys against the previous immutable run; and
7. publish the staging projection only after the checkpoint is complete and reproducible.

The manifest is checkpointed after every response. `--resume` may continue only an incomplete run
under the same contract and capability hashes; it refuses to overwrite retained bytes. A completed
run is immutable. A failed request is `source-failed` for the run and `blocked-by-source` for the
slice. Zero returned records and incomplete pagination are `needs-evidence`, never absence.

## First run result

Run `20260809T181000Z` retained three official list pages, 43 detail pages, and the exact `SVQP`
symbol asset. All 43 detail records are accounted: 41 positive Snorlax candidates and two
source-identified Munchlax exclusions. No record was silently dropped and no verdict changed.

Official detail `13148` is the mandatory counterexample: raw expansion key `SVQP`, collector number
`012/023`, localized name `卡比獸`, and a retained symbol whose reviewed reading is `svQP F`. It is
therefore a visible `new-candidate`, not an inferred match to Japanese `mP1 012/023` and not a
Traditional-Chinese contradiction.

The remaining Japanese, Indonesian, Thai, Korean, Simplified-Chinese, non-English Western/LATAM,
and specialist tracks remain explicit `needs-evidence` or `blocked-by-source` gaps. #138/#139 own
their locality slices and reconciliation decisions; adding them extends this contract and reruns
the same accounting loop.

## Western-English run result

Run `20260811T100924Z` adds one exact-name TCGdex English slice. Its list request uses the
source's strict-equality `name=eq:Snorlax` filter without pagination; [TCGdex documents](https://tcgdex.dev/rest/filtering-sorting-pagination)
that array endpoints are unpaginated unless pagination parameters are supplied. The run retains
that complete response, all 45 referenced card details, and all 38 referenced set details.

Every English row is accounted: 41 physical TCG records match one existing ADR-0001 release, and
four records (`A1-211`, `A1-250`, `A2a-063`, and `P-A-049`) are positively excluded because their
retained set details identify series `tcgp`, named Pokémon TCG Pocket. There are no English new,
ambiguous, or needs-evidence records. The adapter does not infer Pocket from an id pattern.

TCGdex's `en` records contain no source-native US/Canada, Europe, or Australia/New Zealand physical
distribution discriminator. The run therefore admits no regional split. That unresolved dimension
stays an explicit positive-evidence gap: packaging or marketplace geography alone cannot create a
new physical-card identity.

The same run refreshes the Taiwan slice, producing 88 accounted records overall: 50 matched, 32
new candidates, six positively excluded, and zero run errors. Historical runs now retain their
contract snapshots so later adapter versions can replay every checkpoint under its own immutable
contract before computing deltas.

## Italian official-archive run result

Run `20260811T105030Z` adds the publisher's Italian `cardName=Snorlax` filter as a bounded
positive-only slice. The one retained server response exposes twelve exact localized detail paths,
Italian card names and `cms2-it-it` card images. All twelve records match reviewed ADR-0001 Italian
releases; no verdict or finish state changes.

This adapter deliberately treats each result entry as the provider-native record. The complete
checkpoint means only that all twelve entries in that retained response were parsed and accounted.
It does not walk guessed detail paths or turn the filter into a historical manifest.

That boundary has a concrete positive counterexample: the independently reachable official
`pl2/111` page establishes Italian RR 111, but the same official Snorlax filter does not return its
path. The omission is therefore recorded as `official-italian-archive-filter-coverage`, a
`needs-evidence` gap. It proves the filter is incomplete; it says nothing negative about any card.

The run refreshes all active slices and accounts for 100 records overall: 62 matched, 32 new
candidates, six positively excluded, zero ambiguous or needs-evidence records, and zero run
errors. The `west-it` matrix track is terminal as `complete-positive-slice` while historical gaps
remain explicit.

## Consequences

The repository can now discover a positive official card record absent from the Cardmarket-derived
candidate universe, reproduce each versioned run without network access, resume a partial refresh,
and expose new/ambiguous records without changing evidence verdicts. The remaining 32-candidate
Taiwan queue is intentionally not auto-merged: resolving local set-symbol aliases, local
collector-number equivalence, TW/HK relationships, and shared works belongs to the locality
reconciliation loops. Likewise, the Italian filter's twelve matches cannot close eras that the
publisher response demonstrably omits.

`scripts/card_discovery.py --check`, its regression tests, independent review checks N14/N15, and
the cross-platform release gate enforce raw hashes, page/detail accounting, native identifier
preservation, the `svQP F` regression, positive Munchlax/Pocket exclusion, checkpoint semantics,
and the verdict-mutation boundary.

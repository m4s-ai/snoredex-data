<!-- doc: role=architecture decision record for source capabilities and bounded coverage; stage=reference -->
# ADR-0003: source capability and bounded coverage graph

- **Status:** Accepted
- **Date:** 2026-08-09
- **Issues:** #135; incorporates #108 and #117
- **Depends on:** ADR-0001 and ADR-0002 define the identity grains this graph may support

## Context

The source registry answers who supplied an evidence record and whether a few exact pages are
complete. It did not answer which provider surface was queried, which localities or product classes
that surface can positively describe, whether its pagination was understood, or whether a finish
field is independent from card existence. Those missing boundaries make two unsafe inferences easy:

1. a missing search result is promoted from provider silence to non-existence; and
2. a source that can identify a card is assumed to know every finish of that card.

The source-first catalogue and card discovery work in #147 and #136 must be able to enumerate
provider records without either inference. Browser-only, rate-limited, incomplete and unavailable
sources must also remain visible: access failure is operational state, not evidence.

## Decision

Adopt `verification/source_capabilities.json` as the reviewed, versioned capability manifest and
`verification/source_capability_graph.json` as its generated graph projection.

The graph has four node/edge classes:

- a **provider** declares operator, authority tier, terms and raw-record retention;
- a **surface** declares endpoint/query method, pagination, expected identifiers, access and
  failure state, freshness policy, adapter state and an independent finish capability;
- a **coverage edge** connects one surface to an explicit locality, language/script,
  product-category and time boundary; and
- an **observation** is a retained positive fixture or an out-of-scope challenge with URL,
  parameters, retrieval date, raw record and SHA-256.

The manifest is validated against `verification/source_capability_schema.json`. The generator then
applies semantic checks that JSON Schema alone cannot express:

- every provider in `source_registry.json` has a capability surface and every evidence row used by
  a verdict resolves to one surface with all of its required positive dimensions;
- every coverage edge cites a retained known-positive observation and boundary metadata;
- a zero result is `unknown` unless the exact edge is exhaustive and explicitly absence-capable;
- every absence edge cites an out-of-scope challenge and exactly matches the absence URL set in the
  provider registry;
- finish evidence requires a separate finish capability; card/set existence never supplies it;
- PSA, CGC, inspected specimens and other specimen-like surfaces are positive-only; and
- every retained observation's raw record is hashed deterministically.

`scripts/source_capabilities.py --check` is part of the documented and CI release gates. Independent
checks S5 and S6 protect source routing and the positive/absence boundary even if the generator is
changed incorrectly.

## Coverage choices

The first accepted graph is deliberately conservative.

- TCGdex has positive Western and thin Asian edges. Missing rows and false/missing variant flags
  remain unknown, especially in Korean and Simplified Chinese.
- The Japanese official card search has no finish capability. Separate official product pages may
  publish positive finish or rarity prose, but a missing page has no meaning.
- The official Asia search has positive recent Traditional-Chinese, Indonesian and Thai coverage;
  it is not treated as a historical catalogue.
- Bulbapedia requires retained wikitext/revision context. Source-native `Rare Holo` and `Rare`
  remain distinct; a rendered marker or blank field is not closure.
- 52Poké currently has a positive retained Chinese-language image record but no accepted closed
  finish surface. Korean collector sources remain present as `needs-evidence` with no claimed edge.
- LigaPokemon is a positive LATAM listing surface blocked to scripted/datacenter access. Cardmarket
  is rate-limited and product-positive only. Neither inventory can establish absence.
- An exact retained PokéCottage structured row is tier-3 positive confirmation for the card, set,
  promo, date, artist, rarity or named variant it states. A demonstrated matching Western release
  may reuse a shared fact with its equivalence basis retained; an English row alone does not create
  another localized printing, and omissions never establish absence or completeness.
- Complete official checklists positively establish the exact English card rows they name and
  their documented finish columns. Together with the reviewed Black Star Promo language table and
  the exact official Play! Pokémon Series 7 gallery, they are the only absence-capable edges. Their
  closure is URL/scope specific and cannot be inherited by another page from the same provider.
- PSA and CGC named varieties or registry rows establish concrete graded specimens. CGC personal
  registry set 102462 is retained as the #117 positive fixture, while its empty slots and the
  collector's missing cards remain unknown.

## Loop and graph consequences

An adapter introduced by #147 follows this loop:

1. resolve its provider and surface before querying;
2. retain raw URL/parameters, pagination/run state, retrieval time and response hash;
3. emit only assertions listed on a matching coverage edge;
4. keep records outside a known edge or from a failed query as `needs-evidence`;
5. test a known-positive fixture and the edge boundary;
6. challenge any proposed absence edge with an out-of-scope positive record; and
7. narrow or remove the edge when the challenge crosses its claimed boundary.

Changing an adapter from `planned` to `active` therefore requires its fixture and boundary to pass
in the same change. New locality, category, time, finish or absence claims extend the manifest first;
they never emerge implicitly from an adapter result.

## Consequences

The graph adds a maintained contract and generated artifact, but it keeps later issue work small:
#147 can add provider-native enumeration one surface at a time, #136 can discover card candidates
without inventing negatives, and #137 can evaluate evidence strength without treating provider tier
as coverage. #108 and #117 are satisfied without declaring a grading registry a global source of
truth.

No current language, finish, set or card verdict changes under this ADR. It routes and bounds the
evidence those verdicts already cite.

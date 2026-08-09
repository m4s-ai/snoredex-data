<!-- doc: role=architecture decision record for source-first catalogue adapters; stage=reference -->
# ADR-0004: source-first catalogue adapter runs

- **Status:** Accepted
- **Date:** 2026-08-09
- **Issue:** #147
- **Depends on:** ADR-0002 identity grains (#146) and ADR-0003 capability edges (#135)
- **Feeds:** card discovery in #136 and reconciliation work in #138/#139

## Context

The identity model can represent a local set, a language/script edition and market-specific release
events, and the capability graph says which provider surfaces may supply positive evidence. Neither
enumerates provider catalogues. Starting enumeration from the 135 legacy Cardmarket set profiles or
from already known Snorlax cards would preserve the old candidate-universe blind spot: a set could
only be found after the target card was already known.

Provider catalogues are also operationally messy. A request can be blocked, rate-limited, partially
paginated or empty; the same raw id can occur in several locales, and TCGdex currently even reuses
`CSV1C` for two different Simplified-Chinese set names. Release dates can differ by market. Product
and rarity prose can contain exception clauses that are lost by a convenient normalized flag.

## Decision

Adopt [`source_adapters.json`](source_adapters.json) as the reviewed adapter and gap inventory,
[`source_adapter_schema.json`](source_adapter_schema.json) as its versioned contract, immutable raw
runs below `verification/runs/source-adapters/`,
[`source_adapter_staging.json`](source_adapter_staging.json) as the latest generated graph summary,
and `source_adapter_records.jsonl` as its hashed one-record-per-line feed.

The first active adapter enumerates the provider-native TCGdex `/{locale}/sets` arrays for twelve
locale slices: English, French, German, Italian, Spanish, Portuguese, Japanese,
Traditional Chinese, Indonesian, Thai, Korean and Simplified Chinese. It starts with those locale
endpoints alone. It does not read the card store, units, legacy set profiles, ADR-0001 identities or
ADR-0002 set mappings.

A retained request records provider, surface, coverage edge, endpoint and parameters, locale,
retrieval time, HTTP/checkpoint state, exact response SHA-256 and record count. The raw response
bytes are retained. Every projected row adds the provider id, raw name/code/category,
language/script/market, native count/numbering, optional date/status and optional finish prose while
keeping the full source record and its own canonical hash.

Every row enters exactly one accounting bucket:

- `mapped` only when `explicitMappings` names a target and positive mapping evidence;
- `new-candidate` for a parseable positive source record with no explicit mapping;
- `ambiguous/needs-evidence` for identity collisions, incomplete identity fields or parked finish
  clauses; or
- `positively-excluded` only when the source record itself establishes the exclusion, such as an
  explicit digital-only flag.

There is no automatic cross-locale merge. Raw suffixes, scripts and date precision survive. The
same raw id in two locales creates two keys. Reused ids inside one locale retain every occurrence
and park them for evidence rather than overwriting either row. Diffs report added, changed,
disappeared and re-key candidates; the last is a review queue, not an alias assertion.

## Loop and terminal states

Each refresh follows one loop:

1. resolve adapter slices through an active ADR-0003 surface and coverage edge;
2. fetch the complete bounded response and retain raw bytes before normalization;
3. verify response hashes, parsing, pagination checkpoint and record count;
4. project without discarding source-native fields;
5. put every record in exactly one bucket and balance fetched against accounted;
6. diff against the preceding immutable run; and
7. publish the latest staging projection only when the committed run remains reproducible.

A slice is `complete` only when every row returned by that bounded request was retained and
accounted. It is not a claim that the provider population or Pokémon set universe is complete. An
empty response is `needs-evidence` plus a run error. A blocked or failed request is
`blocked-by-source` plus a run error. Neither state establishes absence.

## Source gaps and corrections retained

The contract keeps explicit terminal gaps for official Western catalogues, Japanese product and
card-search surfaces, Asia and CN/KR product indexes, Bulbapedia, TCGCSV, historical specialists,
Cardmarket, and non-expansion products. A surface becomes active only when it can start empty and
its indexing, retention and pagination boundary are reviewed.

Bulbapedia extraction must use MediaWiki wikitext with revision and section, because rendered
content can collapse source-native `Rare` and `Rare Holo`. Finish/product prose is retained
verbatim. Every exception clause is mapped, positively excluded or parked as needs-evidence; any
silently unparsed text is a run error. Asian symbols/codes visible only in an image require a
positive visual reading, not an inferred text value.

Cardmarket claims remain provider claims. Its rarity field may be reliable for the listing, while
listing-market locality and printing locality can still disagree. An adapter must surface that
disagreement; it may not resolve it by conflating identities.

## Consequences

The committed run contributes 1,607 positive local-set candidates across twelve request slices.
Two Simplified-Chinese records sharing raw id `CSV1C` are separately retained and parked, so the
total remains exactly accounted. No mapping into ADR-0002 is asserted in this issue; the staging
feed is ready for #136 and later explicit reconciliation.

`scripts/source_adapters.py --check`, its regression tests, independent review checks N12/N13 and
the cross-platform release gate enforce raw hashes, accounting, locale separation, gap visibility,
finish-clause handling and the ban on verdict mutation.

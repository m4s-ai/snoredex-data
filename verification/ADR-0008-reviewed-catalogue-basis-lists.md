<!-- doc: role=architecture decision record for manually reviewed catalogue basis lists; stage=reference -->
# ADR-0008 — Reviewed catalogue basis lists

**Status:** accepted design; population belongs to the authoritative migration in
[#140](https://github.com/m4s-ai/snoredex-data/issues/140)

**Issue:** [#187](https://github.com/m4s-ai/snoredex-data/issues/187)

**Builds on:** ADR-0001, ADR-0002 and ADR-0007

## Context

The repository currently proves proposed graph shapes with generated dry runs. Those projections
are useful migration audits, but they are the wrong authority for facts that a collector expects to
edit deliberately: which languages and local sets exist, how localized sets relate, which artwork
an appearance uses, and which physical variations have positive evidence. A generator must not
recreate its own source of truth from a consumer projection and then invalidate it on the next run.

The requested basis lists therefore need a one-way boundary. Sources and detector output may
propose a fact. Only a reviewed change may place it in a canonical registry. Generators read those
registries and produce replaceable views; they never write back to them.

## Decision

#140's authoritative graph will expose these manually reviewed registries. File names are the
logical contract; #140 may store them as separate JSON files or normalized database tables as long
as the same grains and foreign keys survive.

| Registry | One row means | Stable identity |
|---|---|---|
| `languages` | one printed language vocabulary used by the catalogue | opaque `languageId` |
| `localities` | one physical publication/distribution locality | opaque `localityId` |
| `localSets` | one set, deck, promo series, or product family in one locality | opaque `localSetId` |
| `setEditions` | one language/script edition of a locality-owning local set | opaque `setEditionId` |
| `releaseEvents` | one dated or explicitly undated market/wave event for a local set | opaque `releaseEventId` |
| `setRelations` | one reviewed, typed relationship between two local sets | opaque `setRelationId` |
| `artworks` | one reviewed illustration identity independent of frame, language, or finish | opaque `artworkId` |
| `artworkAppearances` | one card release displaying an artwork | opaque `appearanceId` |
| `physicalPrintings` | one positively evidenced finish/marking/size/error realization | ADR-0001 `physicalPrintingId` |

Every canonical row records `reviewedAt` and at least one evidence or decision reference. A raw
provider identifier remains an alias with provenance; it is not a canonical primary key.

### Languages and localities

A language is not a locality. Spanish may have WEST and LATAM editions; English may have WEST and
SEA distributions. Czech and Hungarian can remain observed legacy language claims without becoming
established locality-universe nodes. A language registry row therefore records its display name,
BCP-47-compatible tag or explicit unresolved tag, default script, and catalogue state. `localSet`
is the single canonical owner of physical locality. A set edition and release event reach locality
through their `localSetId`; any repeated locality/code fields in a compatibility view are derived
validation values and may not disagree with that parent. A release event's market scopes describe
distribution inside the local set's locality; they never override or mint a physical locality.

### Sets, editions, and release dates

`localSet` owns locality, local code, reviewed names, and product kind. `setEdition` links exactly
one language and script to that local set, whether or not any release event has been established.
The same visible name and code may occur in more than one locality, and one edition may have several
release events. Dates therefore live only on `releaseEvent`, with precision, approximation, status,
timezone, distribution-market scope, and source.

This prevents the two common destructive shortcuts: one scalar set date overwriting a later local
wave, and one shared code turning several physical editions into a `languages[]` field.

### Sibling and source-set relationships

Set relationships are reviewed typed edges, not equality. The initial vocabulary is:

- `localized-counterpart-of` — a locality's corresponding product;
- `uses-source-material-from` — card pool or editorial source material without identity;
- `split-from` and `combined-from` — a local product repartitions source products;
- `reissue-of` — an explicitly reviewed later issue;
- `supplemental-to` — promos/additionals that accompany a base product.

Each edge states direction, scope, evidence, and review status. It never copies card pools,
languages, collector numbers, dates, artworks, rarities, or finishes. For example, Japanese
`m2a` and Thai/Indonesian `ma3` may be reviewed as localized counterparts while remaining distinct
local sets with their own codes and release events.

### Artwork identity and chronology

An artwork is the illustration, not the artist, card text, set slot, image file, or physical
printing. Two releases sharing an artist or ADR-0001 work edge do not share artwork automatically.
Every appearance cites the exact image/source observation and the human grouping decision required
by ADR-0007.

`artworkId` is opaque and never chronological. A presentation view derives an artwork ordinal from
the earliest positively established appearance date, then uses `artworkId` as a deterministic
tie-breaker. Discovering an earlier appearance may change display ordinals but cannot rename an
artwork or break stored references.

Automatic similarity, OCR, artist matching, or shared card text creates a proposal only. Until a
reviewed decision accepts it, the records remain separate or explicitly unresolved.

### Physical card variations

The variation manifest is generated from established `physicalPrintings` joined through
`artworkAppearances`, card releases, editions, and events. It may emit entries such as Jungle First
Edition Holo, Jungle First Edition Non-Holo, Jungle Unlimited, or a No Symbol error only when each
combination is represented by a positive physical-printing row.

The generator must never take the Cartesian product of an edition list and a finish/error/stamp
list. An edition-agnostic holo observation cannot create First Edition plus Unlimited entries; a
base release cannot create a no-symbol error; a normal set card cannot inherit a promo stamp.
Unknown combinations remain absent from the view and unknown in meaning.

## Generated basis views

Consumers receive deterministic, disposable views rather than editing the registries directly:

1. `languages` — catalogue languages and their scripts/states;
2. `sets` — local sets, names, codes, editions, and release events;
3. `setEditions` — exactly one row per established edition, including editions with no event;
4. `editionReleaseEvents` — zero or more event links per edition, preserving separate dates/waves;
5. `siblingSets` — typed reviewed relationships with no inherited facts;
6. `artworkTimeline` — stable artwork ids plus derived chronological ordinals;
7. `artworkVariations` — every positively established physical variation grouped under its artwork.

Every view declares the exact canonical input hashes used to build it. Regeneration replaces a
view atomically and is byte-deterministic for unchanged registries. A generated view is never an
input to another canonical registry.

## Write and review flow

```text
source records / detector output
              ↓
        proposal staging
              ↓ reviewed pass + evidence/decision
      canonical basis registries
              ↓ deterministic generation
          consumer views
```

A reviewed pass may add, correct, split, merge, or relate canonical rows, but it must name the old
and new values and account for every affected reference. Browser proposals from ADR-0007 follow the
same path. Direct browser writes and source-to-registry auto-promotion are prohibited.

Only owner adjudication can close a reviewed list. Every external basis list is positive only.
Omission from a basis list is unknown, not proof of absence.

## Migration acceptance criteria

#140 may make these lists authoritative only when all of the following hold:

1. a clean rebuild leaves every canonical registry byte-identical;
2. every generated row back-references its canonical ids and input hashes;
3. identical codes in different localities cannot collide;
4. one edition can retain multiple market/date waves without scalar-date loss;
5. each set relation is typed and copies no neighbouring facts implicitly;
6. artwork ids survive insertion of an earlier appearance; only derived ordinals may move;
7. artwork equivalence requires a reviewed image-bearing decision;
8. every physical variation is backed by an established printing, never a generated combination;
9. every migrated dry-run row is mapped, held as a visible candidate, or positively excluded; and
10. no generator or consumer view is able to mutate a canonical registry.

## Consequences

The canonical layer changes only through intentional reviewed edits, so adding a source, rerunning
an adapter, or changing presentation order cannot rewrite catalogue truth. The cost is explicit
migration and review work in #140, particularly for artwork grouping. That cost is preferable to
giving an automatically inferred group the authority to merge localized releases or manufacture
collectible variations.

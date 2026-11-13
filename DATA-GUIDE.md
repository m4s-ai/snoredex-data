<!-- doc: role=data file guide and usage caveats; stage=public -->
# Using the data

Which file answers which question, and what each field does *not* mean. Start at the
[README](README.md) for what the project is; read [Scope and caveats](#scope-and-caveats--read-before-using)
before building anything on the data.

## Which file to use

| You want | Read |
|---|---|
| A ready-to-use application database | [`snoredex.sqlite`](snoredex.sqlite), starting from its `app_*` views ([DATABASE.md](DATABASE.md)) |
| A versioned collector-app contract | [`collector_catalogue.json`](collector_catalogue.json) (contract 1.0.0), [schema](collector_catalogue.schema.json), [fixture](collector_catalogue.fixture.json) |
| A personal have/need tracker | [`snoredex-tracker-template.sqlite`](snoredex-tracker-template.sqlite) and `scripts/collection.py` |
| The facts themselves, one record per line | the five files in `data/`, below |
| Final owner decisions | [`verification/owner_adjudications.json`](verification/owner_adjudications.json) |
| Inspected physical specimens | [`verification/specimens.json`](verification/specimens.json) |
| The historical candidate universe | [`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json): provenance, not an all-locality manifest |

## Scope and caveats — read before using

- **A Cardmarket language is marketplace availability, not a print manifest.** Every legacy
  language claim descends from a marketplace filter that over-claims (`KSS 26` is offered in 17
  languages; far fewer exist). Use `applicationStatus`, never the mere existence of a claim.
- **`pending` and `unresolved` mean not yet established, never absent.** Nothing here claims
  non-existence by silence; a source that omits a printing has a gap.
- **`disputed` is never "does not exist".** A contradicted claim without an owner adjudication is a
  disagreement. Only `not-printed`, which always cites an `adjudicationId`, is a settled absence,
  and it means no regular release.
- **`needs-evidence` is not established.** The evidence reaches the product, set or a sibling but
  not the exact card. Do not show it as confirmed.
- **"Spanish" in a legacy claim means European Spanish.** Latin-American Spanish (`LATAM`,
  `es-419`) is a physically distinct edition from Journey Together (2025) onward. Cardmarket does
  not carry it, so the LATAM printings here are a positive slice, not a complete list.
- **`cardKey` groups the same card text, not the same artwork.** A reprint with new art shares the
  key. Never read it as art identity.
- **Artist coverage is partial.** Where no reviewed credit exists, `artist` is absent or null.
- **A V-token is not a finish, and is set-specific.** Always read `variantName`.
- **The catalogue is not all-locality complete.** It grew from a frozen Cardmarket candidate
  universe plus separately evidenced admissions; source and locality gaps stay explicit.
- **Code cards are excluded** from the catalogue; their legacy claims are `out-of-scope`.

## The status vocabularies

| Field | Values and what an application may conclude |
|---|---|
| `applicationStatus` (language claims) | `exists` the printing is established; `needs-evidence` a confirmation that does not reach the exact card; `not-printed` settled absence by owner adjudication; `disputed` a source disagrees, unsettled; `unresolved` not yet researched; `out-of-scope` a code card |
| `repositoryVerdict` (language claims) | the raw verdict: `confirmed`, `contradicted`, `needs-manual-review`, `pending`, `out-of-scope`. Show `applicationStatus`, not this |
| `finishVerificationStatus` (items) | `confirmed` or `observed` established; `owner-attested` on the owner's word; `marketplace-claimed` a marketplace positive only; `pending` nothing yet |
| `completenessStatus` (items, finish units) | `owner-adjudicated` the owner closed the finish list; `positive-evidence-only` finishes found, every unlisted alternative still unknown; `pending` no positive evidence; `not-applicable` every product-language claim is contradicted |
| `itemKind` / `progressClass` | `verified-printing` / `current-known` a printing to collect; `finish-candidate` / `research` a marketplace finish claim awaiting evidence |
| `markings[].role` | `print-identity`, `reverse-holo-treatment` (part of the reverse design), `distribution-promo` (does not imply a reverse holo) |

## The catalogue contract

`collector_catalogue.json` is pinned by an external collector app that keys personal state by
`itemId`. Its collections are `localizations`, `localSets`, `setEditions`, `works`, `items` and
`assets`, plus `meta` and `qualitySummary`; the JSON schema is
[`collector_catalogue.schema.json`](collector_catalogue.schema.json). `meta.catalogueFingerprint`
hashes the whole document. An `itemId` is stored verbatim and never recomputed. No migration
routes are published, so between two catalogue versions an item can be removed or re-keyed, and a
consumer sees that as an id that is gone and one that is new.

## The five files in `data/`

Each file is UTF-8 JSON with one record per line, sorted by id. `scripts/check.py` validates
format, schema, references and the domain rules; the catalogue, pages and database are built from
these files and add only derived fields.

**`data/printings.json`** — `printings`: one record per catalogue item.
`itemId` (stable), `legacyChecklistIds` (old tracker keys, unique), `identityAnchor`, `active`,
`itemKind`, `progressClass`, `workId` and `workMappingState`, `setEditionId` (the set edition the
item belongs to), `cardReleaseId`, `physicalPrintingId`, `sourcePrintingId` and `finishUnitId` (its
finish-store printing), `sourceClaimRefs`, `cardName` and `localCardName`, `collectorNumber` and
`collectorNumberDenominator` (as printed), `edition` and `editionAssignmentStatus`,
`finishVerificationStatus`, `finish`, `finishGroupId`, `foilPattern`, `markings` (`kind`, `role`,
`text`), `distribution`, `cardSize`, `errorClass`, `rarity` (display text, normalized id, evidence
status, claim refs), `completenessStatus` and `completenessEvidence`, `imageAssetId`, and `artist`
where reviewed. `releaseDate`, `releaseDatePrecision` and `releaseApproximate` appear only where the
item's date differs from its set edition's. `meta` carries the data date (`dataAsOf`, bumped by
hand with a data change) and frozen fields of the previous pipeline.

**`data/sets.json`** — `localizations` (locality-qualified languages: `WEST/es-ES` and
`LATAM/es-419` are distinct; their `displayOrder` is the language order of the table and
gallery), `languages` (the legacy claim language codes), `localSets` (a set or
product of one locality, with its source references), `setEditions` (a local set released in one
localization, with its release date where known) and `works` (card text, by `cardKey`).

Five further collections describe sets rather than cards; `scripts/build.py` does not read them yet,
so they change no output.

- `releaseEvents` — the dated release of a set edition and its source. A `setEditions` record with
  a date names its `releaseEventId` and repeats the event's `releaseDate`, `releaseDatePrecision`
  and `releaseApproximate` (rule RE2); an edition without an event has no date established, and a
  date is never derived from the cards of a set. Each event records `providerId`, `sourceUrl`,
  `sourceRef` (a retained file under `verification/evidence/` or null), `evidence` (the page and
  field or the quoted wording) and `checkedAt` (the retrieval date, null where none was recorded).
  RE1 holds the source checkable or strong, as E3 does for claims: without a URL the provider is
  tier 1 or 2. RE3 keeps no event without an edition. The ids are opaque and never parsed; an id
  that contains a date is not the release date, and an id is not renamed after a date correction.

- `cardmarketVariantSets` — Cardmarket bookkeeping. Cardmarket files alternative versions of a card
  under an `x`-prefixed copy of the set (`xm2a` beside `m2a`). Each record names such a
  `localSetId`, the `variantOfLocalSetId` it belongs to and the `variantPrefix`. The prefix is never
  part of a set code and no id changes because of it. Rule V1 holds the variant in its base set's
  locality, its code equal to the prefix plus the base code; R5 keeps set relations off variant sets.
- `localityMarkers` — the marker a localization prints after the set code (`F` Traditional Chinese,
  `I` Indonesian, `T` Thai, `LA` Latin American Spanish, `EN`, `DE`, `FR`, `IT`, `ES`, `PT` in the
  West), one per localization. A marker enters only with its proof: `sourceRef` cites a specimen of
  that language whose observation shows the marker (rule LM1). A localization without a record has
  no marker established, which does not mean it prints none.
- `setRelationTypes` — the registry of relation types: `symmetric` (no direction; the pair is stored
  in id order), `mergesAvailability` (the two sets count as one for language availability),
  `requiresCoverage` (the relation must state `coverage`), `status` (`active` or `retired`, which
  stays valid for existing relations) and `addedAt`. A new type is a new record, not a code change;
  the rules read these properties, never a type's name, and a type is never removed while a
  relation uses it.
- `setRelations` — relations between local sets, mostly across localities, each decided by the owner
  case by case (`decidedBy`). `relationId` is `SETREL-` plus four digits, assigned by hand, never
  renumbered or reused. A relation names `fromLocalSetId`, `toLocalSetId` and its `relationType`
  (for a directed type `from` is the derived set, a catch-up or combined set, and `to` its source),
  `coverage` (`full`, `partial` or null), `cardRange` and `note` for a partial one, `differences`
  (`finish`, `card-list`, `features`) and its evidence: `basis` (`source-stated` with a tier 1-3
  `providerId` and a `sourceUrl`, or `owner-attested` with `owner-attestation`; a `sourceUrl` is
  always a URL or null), `sourceRef` (a
  retained file under `verification/evidence/` or null), `evidence` (what the source says about both
  lists) and `checkedAt`. Rules R1 to R4 hold the shape: two different sets once per type, a source
  that is never tier 5, at most one availability-merging partner per locality, and coverage where
  the type requires it. Promo series of the same name in different localities get no relation.

**`data/images.json`** — `assets` (retained images with path, hash, scope and alt text, keyed by
`asset-` plus the UUIDv5 of `https://github.com/m4s-ai/snoredex-data/asset/v1/<path>` in the URL
namespace; a specimen original, kept in the photo repository `m4s-ai/snoredex-photos` under its
`path`, records the `preview` derivative the table shows), `galleryImages` (the prepared gallery
image of an item: recipe, scope, source and the responsive sizes, content-addressed WebP at 240,
480 and a full size of 600 to 1200 px), `artworkGroups` (which gallery
group a card release belongs to) and `placeholders` (open gallery research hypotheses beside the
printing they vary).

**`data/evidence.json`** — `providers` (every source with display name, category, `authorityTier`,
coverage, usage, attribution, notes and hosts) and `printings` (per item: its `sourceLinks`, and for
a verified printing the `languageEvidence` provider, `corroborated` and `checkable`, plus the
`dateSource` of its release date).

**`data/claims.json`** — the evidence layer behind the legacy universe. `legacyProducts` (one
Cardmarket product: set, number, variant token and name, rarity, artist and its source, image,
product URL, `isCodeCard`, axes), `languageClaims` (one claim per product and language: verdict,
application status, adjudication, provider, corroboration, source URL and reference, source type,
evidence text, granularity, inference, check date, editions), `releaseRows` (legacy release dates
and their sources), `finishUnits` (one card number in one language: applicability, availability,
completeness, mapping and pattern statuses, available finishes, per-finish status, and the products
it names) and `finishPrintings` (every finish-store printing with its sources verbatim; the facts an
item already carries are not repeated). `meta` keeps the metadata of the previous database.

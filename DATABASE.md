<!-- doc: role=application database and tracker contract; stage=reference -->
# Application database and collection tracker

[`snoredex.sqlite`](snoredex.sqlite) is the current-known catalogue as a relational database, schema
`snoredex-database` 2.0.0. It is built from the canonical model in [`data/`](data/) and holds the
same facts: the catalogue items, their sets and localizations, images, providers, the legacy
language claims with their Cardmarket products, release rows and finish evidence, plus the owner
adjudications and specimens read from `verification/`. Its candidate denominator is the frozen
legacy universe in [`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json); it is not a
complete all-locality catalogue, and a Cardmarket language filter is marketplace availability, not
a print manifest.

[`templates/schema.sql`](templates/schema.sql) is the contract: every table and view, with a comment
saying what one row is. `metadata` names the schema version, the data date and the catalogue
fingerprint. The file is built, never edited:

```console
python scripts/build.py           # writes snoredex.sqlite and the other outputs
python scripts/build.py --check   # fails if a committed output is stale
```

## Where an application should start

| View | One row per |
|---|---|
| `app_checklist` | catalogue item to collect, keyed by the stable `item_id`, with names, number, edition, finish, pattern, markings, distribution, size, status and release fields resolved |
| `app_language_claims` | legacy language claim: product identity, repository verdict, application status, provider and tier, evidence, and the owner adjudication where one exists |
| `collection_tracker_seed` | item, with blank `have`, `wanted` and `quantity`; only `current-known` items start as wanted |

## What the schema enforces

- `application_status = 'not-printed'` only where an owner adjudication is cited. Only the collection
  owner settles an absence; a contradicted claim without one is `disputed`, never "does not exist".
- No column grants a source absence authority. A missing source entry is a gap, and `pending` or
  `unresolved` means not yet established, never proven absent.
- `providers.authority_tier` is 1, 2, 3 or 5: tiers 1-3 grade external evidence, strongest first;
  5 marks what is not external evidence. There is no tier 4.
- Foreign keys are declared and checked on every build (`PRAGMA foreign_key_check` must be empty).

## Example queries

```sql
-- Every Japanese printing still to collect, oldest first
SELECT item_id, card_name, set_code, collector_number, finish, release_date
FROM app_checklist WHERE language = 'Japanese' AND progress_class = 'current-known'
ORDER BY release_date;

-- Language claims by application status
SELECT application_status, COUNT(*) FROM app_language_claims GROUP BY application_status;

-- Settled absences and the owner decision behind each
SELECT unit_id, card_name, set_code, language, adjudication_decided_at
FROM app_language_claims WHERE application_status = 'not-printed';
```

## The collection tracker

[`snoredex-tracker-template.sqlite`](snoredex-tracker-template.sqlite) is a blank personal tracker keyed
by `item_id`. Personal state lives in your own copy (default `snoredex-collection.sqlite`, ignored by
git) and is managed with `scripts/collection.py`:

```console
python scripts/collection.py init                     # create your tracker from snoredex.sqlite
python scripts/collection.py set ITEM_ID have --quantity 2 --notes "binder 3"
python scripts/collection.py set ITEM_ID need         # or skip
python scripts/collection.py summary
python scripts/collection.py sync                     # after a new catalogue: refresh, add, retire
```

`sync` refreshes the catalogue copy, adds new items and marks vanished items inactive; it never
changes `have`, `wanted`, quantities or notes. A research item is tracked but never counted as need.

## Migrating an old tracker

A tracker from the previous database is keyed by the old `checklist_id`. Carry its state over with:

```console
python scripts/collection.py init
python scripts/collection.py migrate snoredex-tracker.sqlite
```

`migrate` maps every old row onto `item_id` through the items' legacy checklist ids, opens the old
file read-only, and lists every row it could not place. If a row with personal state (have,
quantity, notes, or a changed `wanted`) cannot be placed, it writes nothing and exits 1, so no
state is lost silently.

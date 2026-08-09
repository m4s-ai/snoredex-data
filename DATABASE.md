<!-- doc: role=application database and tracker contract; stage=reference -->
# Application database and collection tracker

[`snoredex.sqlite`](snoredex.sqlite) is the clean current-known handoff for applications. It joins
the repository's legacy Cardmarket-derived products, language verdicts, editions, release dates,
finish model, physical checklist and provider metadata. Its candidate denominator is recorded in
[`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json); it is not a complete
all-locality catalogue. The database deliberately excludes the append-only evidence journal and
migration/pass history.

The source JSON files remain authoritative. Regenerate and validate the database with:

```console
python scripts/database.py
python scripts/database.py --check
```

## Where an app should start

| View | Use |
|---|---|
| `app_checklist` | One flat row per physical item to collect, including explicit unresolved finish placeholders. |
| `app_products` | One row per Cardmarket product, with the dated marketplace snapshot kept separate from timeless card fields. |
| `app_language_availability` | Raw repository verdict, application status, source capability, owner decision provenance and provider strength per claimed language. |
| `collection_tracker_seed` | Stable checklist ids with blank `have`, `wanted` and quantity values. |
| `quality_summary` | Counts of warnings and intentionally incomplete fields. |

The useful status split is:

- `repository_verdict` preserves the research store exactly.
- `application_status='exists'` has positive evidence.
- `application_status='not-printed'` is reserved for an explicitly absence-capable source scope or
  an entry in `owner_adjudications`.
- `providers.supports_absence` means that a provider has at least one such scope; the row-level
  `source_absence_supported` field identifies whether this exact source URL is in one. Provider
  authority alone is never enough.
- `owner_adjudications` records the collection owner's final decision after reviewing all cited
  claims and evidence. It is not a claim that any one provider proved absence.
- `application_status='disputed'` preserves a repository contradiction with neither a scoped
  absence source nor an owner adjudication. Do not turn it into a hard “does not exist.”
- `application_status='unresolved'` means not yet established.
- `application_status='out-of-scope'` is a code card.

Absence of a `product_languages` row only means Cardmarket did not claim that language. It is not a
negative printing claim.

## Main tables

| Table | Grain |
|---|---|
| `products` | Legacy Cardmarket product id. All 198 baseline ids are explicit and unique. |
| `product_market_state` | Exactly one dated current marketplace availability snapshot per product; not timeless card identity and not a history table. |
| `product_languages` | Product × raw Cardmarket language claim, with current evidence verdict. |
| `owner_adjudications` | One explicit collection-owner application decision per adjudicated language unit, with rationale and evidence references. |
| `languages` | BCP 47 code, raw source label and normalized display label. Spanish is scoped to European Spanish (`es-ES`); Portuguese remains unqualified (`pt`). |
| `product_editions` | Product × positively established language × supported edition. Marketplace-only and explicitly absent-language projections are suppressed. |
| `release_rows` | Stable chronological row id × edition. |
| `finish_units` | Set code × collector number × language. |
| `printings` | Logical physical printing with technical finish, pattern, stamp, distribution and size kept separate. |
| `checklist_items` | Stable physical checklist id. A missing `printing_id` is an explicit unresolved placeholder. |
| `providers` / `printing_sources` | Current source metadata and finish evidence; no historical observations. |
| `checklist_evidence_refs` | Ordered evidence URLs or prose references. These are deliberately references, not falsely advertised as stable source IDs. |
| `quality_issues` | One queryable record per warning or intentional null. |

All relationships have foreign keys. JSON is retained only for naturally nested details such as a
marking list or the source's original structured payload; application identity and filter fields
are normal columns.

## Collection ownership stays separate

[`snoredex-tracker-template.sqlite`](snoredex-tracker-template.sqlite) is a blank tracker with all
838 checklist ids and `have=0`. Copy it, or create a fresh tracker:

```console
python scripts/tracker.py init
python scripts/tracker.py set pju-no-number-japanese-none-holo have
python scripts/tracker.py summary
```

The default personal file is `snoredex-tracker.sqlite` and is gitignored. Its `active_tracker` view
contains card details beside `have`, `wanted`, `quantity`, `notes` and a derived
`collection_status` (`have`, `need`, `skip`, or `research`). Unresolved catalogue placeholders
start as `research`, not as things a collector is told to buy.

After a catalogue update, refresh it with:

```console
python scripts/tracker.py sync
```

`sync` updates descriptive catalogue fields, inserts new checklist ids and marks removed ids
inactive. It does not overwrite any ownership state or notes, so applications do not need a custom
migration for ordinary catalogue refreshes.

## Example queries

```sql
-- Everything still wanted but not held
SELECT checklist_id, card_name, set_code, collector_number, language,
       edition, finish_family, finish
FROM active_tracker
WHERE collection_status = 'need'
ORDER BY release_date, set_code, collector_number;

-- Confirmed languages for a product
SELECT language, provider, authority_tier, source_url
FROM app_language_availability
WHERE product_id = 720390 AND application_status = 'exists';

-- Distinguish owner decisions from source-scoped absence
SELECT unit_id, language, repository_verdict, application_status,
       source_absence_supported, decision_authority, decision_basis,
       decision_rationale, decision_evidence_refs_json
FROM app_language_availability
WHERE application_status = 'not-printed';

-- Data warnings an importing app should surface
SELECT * FROM quality_summary ORDER BY severity DESC, category;
```

The database is UTF-8 SQLite, schema version `1.1.0`, with `PRAGMA user_version=10001`. Every build
stores SHA-256 hashes of its canonical inputs in `metadata`; `scripts/database.py --check` fails if
any source artifact changes without a database refresh.

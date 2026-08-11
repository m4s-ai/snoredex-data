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
- `application_status='exists'` has positive evidence that reaches this exact card.
- `application_status='needs-evidence'` preserves a confirmation whose set/product or sibling
  observation cannot establish this exact card.
- `application_status='not-printed'` is reserved for an entry in `owner_adjudications`.
- `providers.supports_absence` means that a provider has at least one such scope; the row-level
  `source_absence_supported` field identifies whether this exact source URL is in one. Provider
  authority alone is never enough.

`exists` is not one thing, and two columns say which kind it is (#137). `evidence_granularity`
records what the evidence was actually about, and `evidence_inference` records whether the step
from that evidence to this card holds:

| granularity | inference | rows | what it means |
|---|---|---:|---|
| `specimen-or-card` | — | 520 | a record about this card in this language |
| `product-or-set` | `carries` | 83 | the card is inside the set's numbered run, or the cited source lists it in a closed card list, so the language release reaches it |
| `product-or-set` | `does-not-carry` | **17** | a container-level statement about a promo, deck-fixed or secret-numbered card that no card list reached; application status is `needs-evidence` |
| `product-or-set` | `needs-set-size` | 0 | was: undecidable without a printed set size. The set database records those sizes now (#146), so run membership is computed rather than inferred from a rarity word |
| `sibling-derived` | — | 14 | the evidence of a neighbouring unit; application status is `needs-evidence` |

Applications may use `application_status='exists'` directly: all 31 unsupported confirmations are
now `needs-evidence`, while `repository_verdict='confirmed'` and the original observation remain
unchanged. The 17 product/set rows are not wrong — they are unproven at this granularity, and
unresolved semantics apply: not yet established, never proven absent. Fourteen cite one source, the
cross-language expansion index, which carries no card list at all, for cards no locale catalogue
here indexes; three are promo printings, whose collector number is the number of the run card they
reprint, so the set's printed size cannot reach them. The rows whose page did carry a list, and the
rows the publisher's own locale databases answer, have been recorded as card-level.

Which verdict each granularity may support on its own is now declared rather than implied, in
`verdictTransitions` in `verification/evidence_semantics.json`. In short: a card-level record
establishes a printing, and may deny one only inside a coverage edge proven exhaustive; a
product-level statement reaches the card only when the step above holds, and never denies one; an
era argument and a sibling's record establish nothing on their own. An owner adjudication settles a
contradiction whatever sits beneath it, because it is the only mechanism that can settle an absence.
`verdictsBeyondTheirGranularity` counts the raw rows outside that rule — **58** today, held by check
`N19`. The raw observations remain historical inputs: their application statuses are 31
`needs-evidence` confirmations and 27 `disputed` contradictions, so none materializes an existence
or absence claim.

`needs-set-size` is a third answer, not a softer `does-not-carry`: it is the report declining to
classify. It stands at 0 because the set database now records `printedSetSize` — the denominator
printed beside the collector number — so a card is inside the numbered run when its number is
within that size, in its own numbering. That fact outranks the rarity word in both directions,
which is what Cardmarket's era-dependent `Ultra Rare` needed: the same word covers the modern Full
Art, secret in some locales, and the EX-era `ex` and DP-era LV.X cards numbered inside the set.
The state is kept because a set whose size is not yet recorded still lands there.

The same columns explain the other statuses. Every `not-printed` row is `owner-adjudicated`, none
is source-derived, which is rule 4 visible in the data. Every `disputed` row is
`market-or-era` + `unscoped-absence`.
- `owner_adjudications` records the collection owner's final decision after reviewing all cited
  claims and evidence. It is not a claim that any one provider proved absence.
- `application_status='disputed'` preserves a repository contradiction with neither a scoped
  absence source nor an owner adjudication. Do not turn it into a hard “does not exist.”
- `application_status='needs-evidence'` is a raw confirmation whose evidence cannot reach the card.
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

-- Confirmed languages that rest on a card record rather than on the set's language list
SELECT language, provider, authority_tier, evidence_granularity, evidence_inference
FROM app_language_availability
WHERE application_status = 'exists' AND evidence_granularity = 'specimen-or-card';

-- The confirmations whose container-level statement does not reach the card (#137)
SELECT set_code, collector_number, language, evidence_granularity, source_type
FROM app_language_availability
WHERE evidence_inference = 'does-not-carry';

-- Distinguish owner decisions from source-scoped absence
SELECT unit_id, language, repository_verdict, application_status,
       source_absence_supported, decision_authority, decision_basis,
       decision_rationale, decision_evidence_refs_json
FROM app_language_availability
WHERE application_status = 'not-printed';

-- Data warnings an importing app should surface
SELECT * FROM quality_summary ORDER BY severity DESC, category;
```

The database is UTF-8 SQLite, schema version `1.2.0`, with `PRAGMA user_version=10002`. Every build
stores SHA-256 hashes of its canonical inputs in `metadata`; `scripts/database.py --check` fails if
any source artifact changes without a database refresh.

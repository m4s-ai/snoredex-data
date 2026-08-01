# Historical verification passes

The scripts in this directory are the one-shot record of completed evidence batches. Their
outputs are committed to the canonical state stores; these passes are not part of the recurring
release toolchain and are not expected to be rerun.

Recurring verification lives directly under `verification/`:

- `review_integrity.py`
- `audit_evidence.py`
- `report.py`
- `classify_manual.py`
- `verify_finish_sources.py`
- `review_findings.py`
- `test_site.py`

The active PowerShell requirement is **PowerShell 7 or newer**. Active writers use
`utf8NoBOM`; archived one-shot scripts are preserved unchanged as historical records.

The build-pipeline scripts under `scripts/` consume `_chunk1-3.json` and
`_cards_stage1-3.json`. Those inputs are not available in the repository, so that pipeline is
also historical for now. The committed dataset is the input of record. Restoring a reproducible
scrape requires a separate decision because Cardmarket access is deliberately rate-limited and
the missing stage inputs cannot be reconstructed by a code-only migration.

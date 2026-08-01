# Historical verification passes

The scripts in this directory are the one-shot record of completed evidence batches. Their
outputs are committed to the canonical state stores; these passes are not part of the recurring
release toolchain and are **not expected to be rerun**.

They live under `verification/archive/` so the path states that policy rather than a README
having to. They are never edited either: `verification/review_findings.py` check `X3` hashes
every file here against `verification/archive/MANIFEST.json` and fails if any of them changes.
The archive is the evidence of how the committed data came to be, and a record that can be
rewritten is not one.

That is also why the 61 PowerShell passes were not translated when the recurring toolchain moved
to Python (#50). A translated pass is not the script that produced the record — it is a new
script claiming to be. For a repository whose premise is that every claim is auditable back to a
source, that trade is a loss.

Recurring verification lives directly under `verification/`, and is entirely Python:

- `review_integrity.py`
- `audit_evidence.py`
- `report.py`
- `classify_manual.py`
- `verify_finish_sources.py`
- `review_findings.py`
- `test_site.py`

Running any of these needs Python only. PowerShell is no longer a prerequisite for anything in
this repository; it is needed solely to execute the archived scripts, which nobody should.

The build-pipeline scripts under `scripts/` consume `_chunk1-3.json` and `_cards_stage1-3.json`.
Those inputs are not available in the repository, so that pipeline is also historical. The
committed dataset is the input of record. Restoring a reproducible scrape requires a separate
decision because Cardmarket access is deliberately rate-limited and the missing stage inputs
cannot be reconstructed by a code-only migration — see #28, where their data flow is being
captured before those six files join this archive.

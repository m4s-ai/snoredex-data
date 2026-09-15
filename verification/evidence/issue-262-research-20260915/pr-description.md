Thai research for #262 found two missing official release dates, an existing promo finish override that did not match its legacy number, and two usable seller images. This draft applies those findings: the current Thai release audit improves from 8/28 to 13/28 without claiming a complete finish inventory.

- Add separate official Thai release events for s5a T (2021-04-30) and s10a T (2022-07-29), with retained source captures and narrowly scoped date capabilities.
- Match the existing 082/SV-P Non-Holo evidence to legacy lookup `082`, preserving the local collector number and correcting the printed stamp text to CENTRAL PATTANA.
- Import SPEC-0526 (sc3b T 126/158 Holo) and SPEC-0527 (sv4a T 145/190 Reverse Holo), preserving original images, provenance and field-specific uncertainty.
- Regenerate graph, artwork, collector and database outputs; update legacy tracker counts and add targeted assertions for the five affected releases. Include the full research report, before/after audit and remaining leads.

Validation: full `python scripts/regen.py --check` passed; complete `python scripts/regen.py` also passed for the final packaged source captures. Both new specimens reach graph, source registry, artwork and collector views. Publication captures omit irrelevant website scripts and identify their derivation explicitly; original response hashes remain recorded. Runtime logs and original responses for those derived captures remain local.

**Keep this PR as a draft.** The owner wants to collect more information before a final review-ready PR. Fifteen releases still need physical finish evidence, including MA6 with an additional rarity gap. Do not mark ready, merge, deploy, or close #262 as part of this draft.

Refs #262; parent research issue #256. No Hermes changes.

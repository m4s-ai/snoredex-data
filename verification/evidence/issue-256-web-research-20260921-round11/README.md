<!-- doc: role=retained research evidence; stage=reference -->
# Round eleven: Thai AS1b admission and Traditional Chinese AS5a holo

On 2026-09-21 manual inspection of SPEC-0543 establishes Thai Snorlax GX, AS1b A 112/150 RR, HP190, 5ban Graphics, Collapse 80, Thunderous Snore 180 and Pulverizing Pancake GX 210. The printed attacks establish the existing Work mapping. Physical finish and release date remain unknown. Admission uses the existing `build_profile`, `apply_set_graph`, `apply_release_group` and `persisted_source_row` helpers from `admit_issue262_thai_20260828.py`, plus the established graph upsert helpers. `admission.json` retains the reviewed input. The locality-set index is reconciled as examined with one positive Snorlax, not a complete set. The round-seven importer manifest now cites `TH:AS1b:112/150:base`; no nearby identity or finish is borrowed. This addresses PR review discussion_r4063826348.

New SPEC-0554 establishes Traditional Chinese AS5a C 117/184 RR, Eevee and Snorlax GX, HP270, Mitsuhiro Arita, and visible holo reflections in the silver border and illustration. No finer foil pattern is assigned. Source: https://shopee.tw/product/3768885/7017610542 . Original front and back are retained with hashes in image-inventory.json. Only the identifiable front is imported; the back has no independent localized identity. Manual inspection; local OCR unavailable. The new photo supports the existing `TW:AS5a:117/184:base` release, without declaring independent-provider corroboration.

## Other search leads

- Thai AS1b: https://ojamacard.com/product/16885/112-150-%E0%B8%84%E0%B8%B2%E0%B8%9A%E0%B8%B4%E0%B8%81%E0%B8%AD%E0%B8%99-gx-rr-as1b — exact title found; page retrieval failed, no image accepted.
- Thai AS1b: https://shopee.co.th/product/19819669/3364044609 and https://shopee.co.th/product/107078812/15746665106 — exact search-title leads only; no new inspected original, no finish inference.
- Traditional Chinese AS5a: https://shopee.tw/product/48574893/12039798516 — exact 117/184 lead; page retrieval failed, no accepted image.
- Korean 038/053 search again returned the already excluded Japanese card listing 424047523 and an explicitly Japanese shop entry. No new Korean evidence.
- Indonesian S8b 126/184 searches produced no newly inspectable matching card. This is an unresolved search gap, not evidence of absence.

All original photographs and pre-existing card facts are preserved. PR #390 remains draft and unmerged.

## Validation and impact

Baseline full check and final full regeneration/core gate passed. The physical-evidence loop reached its bounded terminal state; all five scoped steps passed. Original specimen hashes are conserved. `validation.json` records 1010 byte-for-byte unchanged catalogue items, one Traditional Chinese placeholder promoted to a physical holo on the same release, and one new Thai identity-only placeholder. Totals: 1012 items, 642 releases, 771 verified printings, 113 finish candidates, 128 research placeholders, 452 assets.

Local browser inspection loaded both affected members and every associated image. Thai AS1b has one retained seller image and zero inferred physical printings; AS5a has the new SPEC-0554 holo observation alongside its pre-existing identity images. The new Thai source row intentionally has no publisher card-image URL: the original seller URL remains in the specimen provenance. Registry identity attribution, graph reachability and artwork reachability were checked explicitly. No existing physical facts or picture hashes were removed.

Review remediation assessment: identity/provenance 9/10, conservative finish boundary 9/10, reference reachability 9/10, conservation/validation 9/10. Remaining uncertainty is Thai AS1b finish/date and other documented search gaps, not a failed gate. Remediation FINAL; external exact-head review remains pending until delivery.

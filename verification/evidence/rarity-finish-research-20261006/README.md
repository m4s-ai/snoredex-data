<!-- doc: role=retained rarity and finish research with integration boundaries; stage=reference -->
# Rarity and finish research — 2026-10-06

Research snapshot for issue #256, based on main `e452c07e7dcda1412d0e43db358a3b0a82f3f569`. This package retains 111 target records: Korean 38, Simplified Chinese 25, Indonesian/Thai/Traditional Chinese 20, and Japanese/Western 28. Scope combines actionable missing fields and releases associated with Fixed rarity; these are not 111 unresolved cards.

[Browse all targets and images](report.html). Each group has its target manifest, structured results and readable report. The source excerpts preserve retrieval limits; their hashes are not hashes of complete web responses. Ten original photograph files are retained. `retention-manifest.json` records their file hashes and the research date.

## Supported findings and proposed integration

- Korean: 26 missing release-date fields have matching official product-page support; BS2 30/40 has printed U rarity support. Product dates must retain their exact locality/product scope. Conflicting XY10 dates and weak identity bindings stay unresolved.
- Photographs: Korean sv2a 143/165 Poké Ball mirror, Korean sv4a 310/190 Holo, Japanese sv4a 310/190 Holo, and Japanese s8b 126/184 Holo were visually inspected. The two mC 568/742 views support Korean identity but do not establish physical finish.
- Five normalized Fixed assignments concern booster cards: Korean s8b 126/184, Indonesian/Thai SV4a 145/190, and Indonesian/Thai MA3 136/193. The current normalization equates no printed rarity symbol with Fixed; this does not establish fixed-product rarity. Preserve native observations rather than substituting an invented Common rarity.
- Three Chinese distribution assignments incorrectly inherit fixed-deck context: CSVH1C a001/023 and CSVH4C a003/023 are Modification Pack cards; CSVH4C p006/006 belongs to a Reward Pack. Deck finish statements must not cross these product boundaries. Official reward-pack text supports Holo, not absence of other finishes.
- Chinese local-identity aliases need reconciliation against already retained exact cards. Boxed F is a regulation mark, not rarity. Random packs inside gift boxes do not become fixed decks.

## Initial research snapshot and limits

At the initial research-only draft checkpoint, this package retained research evidence and the affected-scope diagnosis only. At that checkpoint no specimen IDs had been allocated and no canonical claims changed. This historical checkpoint is superseded by the canonical integration below. Existing SPEC links refer to previously retained evidence. Proposed photo intake must use the canonical manifest importer, with original WebP retention and pixel-identical PNG conversion. Claim acceptance and identity reconciliation must use their existing field owners.

The baseline gap lists are dated observations, not a current or exhaustive finish inventory. Previously reviewed unnumbered Japanese identities are excluded from actionable number gaps. Search failures, unavailable listings, foil-free renders and missing symbols prove no absence. Seller metadata and card-face observations remain separate.

## Follow-up — 2026-10-07

[Root image inspections](root-followup-20261007.json) retain three additional originals: [Korean CLF 016/032](KR-CLF016-032-seller.webp), [Korean sv2a mirror](KR-sv2a143-mirror-followup.webp), and [Korean XY10 057/078](KR-XY10-057-078-seller.webp). Classic supplies a positive Holo and exact-number correction; the mirror pattern subtype and XY10 Non-Holo remain qualified. Separate locality follow-up reports record fresh searches and blocked routes. No canonical integration had occurred at that follow-up capture.

After draft creation, browser retrieval recovered the [CSVH1aC 001/023 seller photograph](CN-CSVH1aC001-023-seller.webp); identity is visible, physical finish remains unresolved. The other two gallery images are packaging/shipping notices. The Indonesian MA3 Cardtell lead resolves to a digitally presented reference depiction, not new physical evidence. This supersedes the earlier web-only retrieval blocker without rewriting its historical observation. Ten original photograph files are now retained.

## Canonical integration — 2026-10-07

The accepted findings are now applied through existing field owners in draft PR #423. `intake-manifest.json` imports SPEC-0610–0619; six photos carry positive physical treatments and four carry identity only. Original WebP bytes, hashes and pixel-identical PNG conversion metadata are retained in `intake-photo-sources.json`. Unknown mirror subtypes, unavailable sources and flat renders remain qualified.

`integrate_rarity_finish_research_20261007.py` applies the reviewed bulk correction: 26 Korean date fields, the separately bound Korean Classic date/016/032 identity, three Chinese release dates, BS2 U rarity, and the exact Korean SM30A Non-Holo product statement. The sN Holo statement uses the curated finish owner. No promo-series-wide date, absent printing or finish inventory is inferred.

No-symbol rarity normalization now requires the positively reviewed release scope: eighteen deck mappings are retained, five booster mappings become unknown normalized rarity while their native observations remain. The old intake passes use the same corrected context. Chinese Modification Pack cards no longer inherit paired-deck finishes; p006/006 uses only its positive Reward Pack Holo statement through a shared correction used by initial and replay paths.

SPEC-0149 and SPEC-0153 now name the boxed F as a regulation mark. Their photographs, hashes and observation dates are preserved. `superseded-observations.json` retains the earlier prose and claims; the evidence journal records the correction separately. The graph regression checks byte-equivalent replay, all sibling booster corrections, scoped deck preservation and product boundaries. Validation results are reported in the PR after the delivery gate.

The retained-run replay `20261007T095000Z` uses the exact responses from `20260929T170052Z`: all 399 records and reconciliation buckets are unchanged. The 30thC intake replay now preserves later field-owned release dates. The current tracked-field backlog is 39 actionable releases (Korean 29, Simplified Chinese 10), from 46; removal of unsupported Chinese finishes correctly reopens evidence gaps. Five intentionally unnumbered Japanese products remain separately excluded. `collector-identity-audit.json` accounts for every retired or added item identity; all unrelated item IDs and every pre-existing photograph hash/date are preserved.

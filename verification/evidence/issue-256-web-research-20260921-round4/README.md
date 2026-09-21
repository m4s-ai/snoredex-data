<!-- doc: role=fourth research round Thai physical evidence for issue 256; stage=reference -->
# Thai seller photographs — 2026-09-21

Three original seller JPEG photographs support physical holo observations on already established Thai releases in draft PR #390. Each retained image was inspected visually at original resolution. Local Tesseract OCR remains unavailable; language, set/number and rarity text were read visually. No photo was modified, resized or enhanced for intake.

| Specimen | Existing release | Visible observation | Listing |
|---|---|---|---|
| SPEC-0530 | sc1b T 120/153 RRR | Thai VMAX HP340; multicolored foil and fine texture across the card | https://shopee.co.th/product/412643607/23229873986 |
| SPEC-0531 | sv4a 310/190 S | Thai HP150; colored foil reflections and texture in the illustration | https://shopee.co.th/product/76081799/25812272577 |
| SPEC-0532 | sc1b T 119/153 RR | Thai V HP220; multicolored reflections along lower rule bars and border | https://shopee.co.th/product/260033515/4170279559 |

The sc1b rows use existing source-first base identities. sv4a 310/190 uses canonical legacy variant V2; its source-first citation remains TH:sv4a:310/190:base. No new variant was invented to work around importer validation. Existing official renders SPEC-0255 and SPEC-0271 remain identity evidence; the new seller photographs independently carry the physical observations, without declaring a corroboration verdict.

## Rejected or unresolved leads

- Shopee https://shopee.co.th/product/412643607/25102563945 supplies a digital rendering of Thai s10b 056/071 at https://down-th.img.susercontent.com/file/th-11134207-7r98z-loun1usu8jeae5. This is not an observed physical foil; the finish gap remains open.
- Korean s2 077/096 search still returned the explicitly Japanese Bunjang listing 429728200; no Korean physical claim follows.
- Alternate Thai sv4a 310/190 listing 1416820789/27231339385 could not be retrieved through the web reader. Its title is not used as evidence.
- Thai sc1b 119/153 listings 19819669/5685794295 and 34894051/9327730685 were inaccessible to the web reader; the separate Successone photo above supplied the inspected evidence.
- Retailer catalogue claims, sold-out status and country of sale alone do not establish physical finish or absence.

## Source-count correction

PR review 4061717154 identified listing/photo duplication. Seller-listing photograph observations now prefer photographSource, falling back to listingUrl only when no photo provenance exists. The listing remains on the specimen and in collector provenance. Other evidence classes retain their existing source routing; in particular, publisher pages can carry independent statements and Cardmarket catalogue context remains product-only. A regression checks that context URLs cannot receive a second identity or finish attribution. Corrected source counts may decrease while retained observations and card coverage remain intact.

## Validation

Pre-change full regeneration check passed. The importer accepted all three photographs and verified image integrity. The physical observation loop and all five scoped physical-evidence steps passed. Final full regeneration/core gate and all 155 browser checks passed. Catalogue comparison verifies exactly three placeholder-to-printing replacements on unchanged release IDs, with the other 1007 items unchanged and all three original JPEG hashes matching. Totals are 1010 items, 762 verified printings and 449 active assets; retained exact-printing photographs replace the previous active identity images. Thai tracked-field coverage is 16/28 gap-free; 148/641 releases retain gaps overall. Two tests now compare current canonical row states instead of freezing historical counts. Post-push history audit is recorded in the PR/issue updates after commit. Main remains unchanged and PR #390 stays draft.

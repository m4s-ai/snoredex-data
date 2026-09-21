<!-- doc: role=third research round physical evidence for issue 256; stage=reference -->
# Korean seller photographs — 2026-09-21

Two formerly image-less Korean releases now have inspected physical evidence in draft PR #390. The stable records are SPEC-0528 (s5a 093/070 UR) and SPEC-0529 (s1H 070/060 HR). Each is a distinct physical card; no same-card grouping or independent corroboration is asserted.

| Specimen | Card | Visible evidence | Listing |
|---|---|---|---|
| SPEC-0528 | Korean s5a 093/070 | Hangul, set code/number, UR, Saki Hayashiro, gold reflective textured surface | https://m.bunjang.co.kr/products/430221399 |
| SPEC-0529 | Korean s1H 070/060 | Hangul, set code/number, HR, aky CG Works, rainbow reflective textured surface | https://m.bunjang.co.kr/products/430796194 |

The physical observation records `holo`; no unreviewed gold/rainbow foil-pattern identifier is invented. Printed rarity was already present in the reviewed identity records and is not independently re-adjudicated here. Local Tesseract OCR was unavailable, so card text was read visually from the original 900×1200 photographs. Both image URLs return WebP bytes despite a .jpg suffix. Their original bytes are retained here; losslessly decoded PNG copies are imported through the canonical specimen manifest. Pixel equality was checked during conversion, and both original and filed hashes are retained in sources.json.

The first image was reached from the Korean listing. The second listing's public global page https://globalbunjang.com/product/430796194 exposed its image URLs when the web reader could not retrieve the Korean page. Direct read-only HTTP requests retrieved both original photographs. Successful image retrieval and visual inspection supersede the round-two inaccessible-photo note for s5a. No seller was contacted.

## Other searches

The Bunjang s2 077/096 listing https://m.bunjang.co.kr/products/429728200 explicitly describes the Japanese edition; it is not evidence for the open Korean finish. eBay seller daviescollects-4 and Coupang offers remain uninspected leads; their metadata is not used to confirm a physical card.

## Acceptance

The pre-change full regeneration check passed. The canonical importer accepted both specimens and verified photograph integrity. The physical loop stopped after one observation cycle with no further metric change; the physical-evidence scoped lane passed all five steps. Both target releases now project as verified printings with observed holo and exact-printing image assets. Run the final full regeneration and post-push audit before declaring this batch validated. The PR remains draft; main is unchanged.

Final local validation passed: full `python scripts/regen.py`, browser 155/155, original/filed hashes and decoded-pixel equality. Exactly two research placeholders become verified printings on the same release IDs; the other 1008 items are unchanged. Verified printings rise from 757 to 759 and assets from 447 to 449. Korean gap-free releases reach 13/52 in the draft; remaining releases with tracked gaps fall to 151/641. Main is unchanged.

Review follow-up 4061561168 is addressed at the aggregate exporters: database snapshot metadata also considers the graph date, and the site uses the latest checklist, graph-backed artwork projection, confirmed releases and verification date. A targeted synthetic-date check confirmed that newer graph evidence advances the database date, site footer and embedded data-meta while older checklist/finish inputs remain unchanged.

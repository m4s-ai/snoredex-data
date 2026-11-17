<!-- doc: role=retained gallery image research and source provenance; stage=task -->
# Gallery image research, #481 round 05

Part of [#476](https://github.com/m4s-ai/snoredex-data/issues/476), inspected 2026-11-15.
`targets.json` froze four active, unprepared RR 33/111 items against main `c5263c2c` before
acquisition. This bounded round accepts one exact photograph and documents three remaining image
needs. It is not the gallery-wide acceptance in #482 and closes no language or finish question.
Before PR delivery the branch was merged with current main `5daa655c`; source records were
preserved from both sides and generated outputs were rebuilt.

## Source review and outcome

The four items initially shared a representative legacy marketplace asset; none had a matching
specimen asset. Reviewed retained sources and the round-04 report before the bounded localized
searches. The source map records acquired bytes, hashes, dimensions and URLs.

| Item | Target | Result and remaining work |
| --- | --- | --- |
| `item-053fc7df-8865-5b74-ae7e-bef9e10822b2` | German Reverse Holo | Placeholder retained. Results included English League crosshatch copies and 81/111, neither interchangeable with this card. Need a complete German 33/111 front with visible reverse foil and at least 600 effective pixels across the card. |
| `item-09429ed9-cdf8-594d-9677-19183a4798e8` | French Reverse Holo | Accepted exact photo, SPEC-0796: Ronflex niv.37, PV100, Choisir et collectionner, Se retourner 60, 33/111, RR symbol and ©2009. Rainbow foil crosses the rules area and header outside the artwork. Complete yellow border, no stand or slab hiding the face. Corrected 840 × 1176 face, 360-pixel preview and 240/480/840-pixel gallery images. |
| `item-ad9ed036-f421-5934-8a4f-61f3606bd05d` | Italian non-holo | Placeholder retained. Publisher image is only 245 × 342; its URL comes from the earlier retained publisher HTML. Italian price pages point to English sales and cannot establish an Italian face by translation. Need a larger complete Italian regular front; do not upscale the thumbnail. |
| `item-c703b5f2-de23-54f6-8897-5e9fe21d9a4d` | German non-holo | Placeholder retained. Publisher image is 245 × 342 and the acquired Last Sold face is 467 × 650, below the 600-pixel threshold before cropping. Need a larger exact German front. |

The live Italian publisher page returned an interstitial. German and Italian Last Sold listing
pages returned the same Italian-market content on this retrieval; translated labels were not
used as localized-card evidence. Seller metadata alone did not identify the French reverse:
the retained face was inspected manually. Local OCR was unavailable.

## Preparation and canonical records

`preparation.json` records the source hash, source quadrilateral, inverse homography, Pillow
version, conservative effective width, encoding parameters and derivative hashes. Classical
perspective correction preserves the complete border and printed marks; no retouching or
enlargement. The orchestrator independently reviewed the original and final crop and verified
all four homography mappings, exact reconstructed pixels, preview mode and all output hashes.
Preparation was delegated to GPT-6 Luna at medium effort.

The unchanged JPEG is reserved as `verification/specimens/SPEC-0796.jpg` in
[photo commit f6ac25a](https://github.com/m4s-ai/snoredex-photos/commit/f6ac25a5d1900e07ae807b78548eb94d421d18d6).
The remote commit and original SHA-256 were independently checked after the owner explicitly
approved the upload. Canonical changes: one specimen record, one exact image asset, one gallery
association, the existing item's image reference, and its seller-listing provenance URL.
All item ids, other items, language/finish verdicts, providers and owner decisions are unchanged.
The five consumer outputs were rebuilt from those inputs.

## Verification and remaining scope

- Full `python scripts/regen.py --check` after the main merge: passed (75 model rules and selftests).
- Full `python verification/test_site.py`: 102/102 passed.
- Built Pages artifact `_site-round05`: 2661 files, 196247 KB; allowlist verification passed.
- All four targets in the built artifact: grid/lightbox on desktop and mobile DPR2 passed.
  The accepted French image also passed 2×2, 3×3, 4×4 and 5×5 binders in both reading orders
  on both viewports (16 layout checks), with adequate loaded pixel sizes and no browser/HTTP errors.
- A scope assertion verified only the intended specimen and exact image association were added;
  all other item records, ids and verdicts were preserved. `validation.json` records the final scope.
- Full photo checkout check after the main merge: all 706 photographs match their SHA-256 and
  carry no GPS. The earlier SPEC-0042 register mismatch was already corrected on main and that
  correction is preserved; the 14 previously unregistered photo files are now registered there.
  SPEC-0796 remains the only specimen this round adds.

The three remaining image needs stay open in #481; #476 and #482 remain open.
No Pages deployment was performed.

<!-- doc: role=retained gallery image research and source provenance; stage=task -->
# Gallery image research, #481 round 05

Part of [#476](https://github.com/m4s-ai/snoredex-data/issues/476).
`targets.json` freezes four active, unprepared RR 33/111 items before source acquisition,
against main `c5263c2c`. This deliberately bounded follow-up does not repeat the old 973-item
inventory or assert a gallery-wide visual acceptance. Acquisition date: 2026-11-15.

## Source review

No existing specimen asset is assigned to these four items: their shared legacy asset is a
representative marketplace image, not an exact localized front. The round-04 report already
records the unsuccessful German/French reverse leads. Rechecked stored sources before the
bounded searches for exact German, French and Italian RR 33/111 fronts.

| Item | Target | Result and remaining work |
| --- | --- | --- |
| `item-053fc7df-8865-5b74-ae7e-bef9e10822b2` | German Reverse Holo | No qualifying exact photo acquired. Search results include English League crosshatch copies and 81/111, neither interchangeable with this card. Need a complete German 33/111 front with visible reverse foil and at least 600 effective pixels across the card. |
| `item-09429ed9-cdf8-594d-9677-19183a4798e8` | French Reverse Holo | `fr-reverse.jpg`, 1200 × 1600: Ronflex niv.37, PV100, Choisir et collectionner, Se retourner 60, 33/111, RR symbol and ©2009; rainbow foil crosses the rules area and header outside the artwork. All four yellow borders are visible, with no stand, stamp or slab hiding them. Classically perspective-corrected to 840 × 1176 without enlargement; the complete border and readable face passed independent visual review. Preview and three gallery sizes are prepared. **Photo upload and canonical gallery association remain pending.** |
| `item-ad9ed036-f421-5934-8a4f-61f3606bd05d` | Italian non-holo | The exact publisher image is only 245 × 342. The retained publisher HTML from the earlier local-name research identifies its URL. Italian-language price pages point to English sales and cannot supply an Italian card face by translation. Need a larger complete Italian regular front; do not upscale the publisher thumbnail. |
| `item-c703b5f2-de23-54f6-8897-5e9fe21d9a4d` | German non-holo | The localized publisher image is only 245 × 342; the Last Sold German face is 467 × 650. Both are below the 600-pixel minimum before any crop. Need a larger exact German front; neither image is accepted. |

The source map records the acquired bytes, hashes and URLs. Seller metadata alone was not used
to identify the French reverse; its retained card face was inspected. The Last Sold Italian
listing page and German listing page returned the same Italian-market content on this retrieval;
their translated market labels are not localized-card evidence. The live Italian publisher page
returned a 1032-byte interstitial; its retained earlier HTML remains the URL provenance.

## Handoff

- Prepared: inverse projective homography, complete perimeter, 360-pixel palette preview and
  240/480/840-pixel WebPs. `preparation.json` records geometry, encoder parameters and hashes.
  The first draft was rejected for enlarging the narrow source edge and clipping the top border;
  only the independently reviewed 840-pixel revision is retained as the prepared output.
- The photo-repository collision check found ids through `SPEC-0795`; `SPEC-0796` is tentative
  until its original is pushed. Automatic approval review rejected that push for lack of an
  explicit chat instruction. Do not retry until the owner grants it; recheck collisions before
  reserving an id. No specimen or item has been assigned this tentative id in canonical data.
- After the upload, register the seller photo and add only its exact French printing association
  to `data/images.json`. Keep existing language and finish verdicts separate from this gallery work.
- Inspect this item on desktop/mobile in grid, binder and lightbox after integration, then build
  and verify the Pages artifact. `proposed-records.json` is a reviewable proposal only; it must
  be reconciled with the photo repository before applying its tentative specimen id.
- Three targets remain documented image needs. The French candidate remains a placeholder
  until preparation and visual acceptance pass. No issue criterion is closed by this report.

The current offline baseline gate passed before gallery-data edits (none have been made).
Windows required a writable temporary directory and permission for the test-created local Git
repositories. The first restricted attempts failed at those environment boundaries; the complete
retry passed all model/selftests, build checks, link checks and 11 publication checks.

The research-stage `python scripts/regen.py` also passed. A separate assert-based check verified all four
target memberships against active `data/printings.json`, their lack of a prepared gallery image,
and all four retained file hashes and dimensions. Generated outputs remained unchanged. Browser,
photo-repository intake and Pages-artifact acceptance are pending because no canonical gallery
association has changed. Preparation was delegated to GPT-6 Luna at medium effort; the orchestrator
independently reviewed the original and revised crop and verified source SHA-256, all four
homography corner mappings, no enlargement, exact reconstructed crop pixels, palette preview mode
and all three WebP dimensions and hashes. Local OCR was unavailable; card fields were visually read.

After preparation, `python scripts/regen.py` passed again with canonical data unchanged. A local
gallery preview was built from the proposed records in memory. All four target entries passed grid
and lightbox checks on desktop and mobile DPR2; the prepared French image also passed 2×2, 3×3,
4×4 and 5×5 binder layouts in both reading orders on both viewports (16 layout checks). Loaded
resource pixel sizes cover the displayed pixel density, with no browser/page or HTTP errors.
The orchestrator visually inspected the desktop/mobile lightboxes and mobile binder crop.
`preview-check.json` records this limited scope; it does not replace post-integration browser
checks or Pages-artifact verification.

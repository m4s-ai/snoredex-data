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
| `item-09429ed9-cdf8-594d-9677-19183a4798e8` | French Reverse Holo | `fr-reverse.jpg`, 1200 × 1600, is a promising exact photo: Ronflex niv.37, PV100, Choisir et collectionner, Se retourner 60, 33/111, RR symbol and ©2009; rainbow foil crosses the rules area and header outside the artwork. All four yellow borders are visible, with no stand, stamp or slab hiding them. Top edge is about 840 pixels wide; perspective correction and final sharpness review are still required. **Candidate only: no prepared image or accepted gallery association yet.** |
| `item-ad9ed036-f421-5934-8a4f-61f3606bd05d` | Italian non-holo | The exact publisher image is only 245 × 342. The retained publisher HTML from the earlier local-name research identifies its URL. Italian-language price pages point to English sales and cannot supply an Italian card face by translation. Need a larger complete Italian regular front; do not upscale the publisher thumbnail. |
| `item-c703b5f2-de23-54f6-8897-5e9fe21d9a4d` | German non-holo | The localized publisher image is only 245 × 342; the Last Sold German face is 467 × 650. Both are below the 600-pixel minimum before any crop. Need a larger exact German front; neither image is accepted. |

The source map records the acquired bytes, hashes and URLs. Seller metadata alone was not used
to identify the French reverse; its retained card face was inspected. The Last Sold Italian
listing page and German listing page returned the same Italian-market content on this retrieval;
their translated market labels are not localized-card evidence. The live Italian publisher page
returned a 1032-byte interstitial; its retained earlier HTML remains the URL provenance.

## Handoff

- French candidate: classically rectify the card perimeter, retain every border and printed
  mark, determine effective width from its narrowest edge, and assess the corrected full view.
- If accepted, register the seller photo as a new specimen, retain its original in
  `snoredex-photos`, and add only its exact French printing association to `data/images.json`.
  Keep the existing language and finish verdicts separate from this gallery work.
- Produce 240/480/full responsive derivatives with source and output hashes; inspect this item
  on desktop/mobile in grid, binder and lightbox, then build and verify the Pages artifact.
- Three targets remain documented image needs. The French candidate remains a placeholder
  until preparation and visual acceptance pass. No issue criterion is closed by this report.

The current offline baseline gate passed before gallery-data edits (none have been made).
Windows required a writable temporary directory and permission for the test-created local Git
repositories. The first restricted attempts failed at those environment boundaries; the complete
retry passed all model/selftests, build checks, link checks and 11 publication checks.

The final `python scripts/regen.py` also passed. A separate assert-based check verified all four
target memberships against active `data/printings.json`, their lack of a prepared gallery image,
and all four retained file hashes and dimensions. Generated outputs remained unchanged. Browser,
photo-repository intake and Pages-artifact acceptance are pending because no gallery association
has been accepted or changed in this research handoff.

<!-- doc: role=retained gallery image preparation and acceptance; stage=task -->
# Gallery image round 08, #481 / PR #593

Twelve active targets are fixed in `targets.json` at `850c43de`. Eight initial targets and
four further retained photographs were selected before derivative preparation. Two complete
Traditional Chinese catalogue images are accepted as representative renders. Ten targets retain
placeholders and concrete image needs. This round changes no original, specimen record, asset
metadata, primary image reference, item identity, language/finish verdict or owner decision.

| Target | Retained source | Result / remaining image need |
| --- | --- | --- |
| English VIV 131/185 Reverse Holo | SPEC-0753 | About 490 effective face pixels in the easel scene. Need a closer full reverse front. SPEC-0752 is the different artwork-Holo finish; SPEC-0756 is the stamped promo. |
| Simplified Chinese CSVH1C a001/023 | SPEC-0619 | About 500 effective face pixels. Need a closer full front at least 600 pixels wide. |
| Japanese sI100 342 | SPEC-0592 | Stand tips cover the lower number line and rim. Need an unobstructed full front. The watermark below the card does not resolve the obstruction. |
| Traditional Chinese sv4a F 145/190 Reverse Holo | SPEC-0692 | Upper perimeter reaches the source boundary; the complete top edge cannot be verified in the retained crop. Need a full-perimeter front. |
| Korean sm9 066/095 | SPEC-0620 | Only about 580 face pixels inside the 633-pixel canvas. Need a closer full front. |
| Korean sv2a 143/165 | SPEC-0675 | About 500 face pixels and stand across the bottom rim. Need a closer unobstructed front. |
| Traditional Chinese sv2a F 181/165 | SPEC-0300 | Accepted representative render, full native 868 × 1212 source canvas. |
| Traditional Chinese sv4a F 310/190 | SPEC-0303 | Accepted representative render, full 1364 × 1905 canvas downscaled to 1200 × 1676. |
| French PGO 055/078 | SPEC-0652 | Soft native-detail text and artwork despite a large front/back scene. Need a sharper full front. |
| French VIV 131/185 Holo | SPEC-0649 | Sealed-bag seam and reflections cross the artwork. Need a front clear of packaging seams. SPEC-0755 is a worn Reverse Holo, a different target. |
| Korean s10a 077/071 | SPEC-0539 | Bright sleeve reflection crosses the top rim. Need diffuse light without rim glare. Retained render SPEC-0237 is only 512 pixels wide. |
| Korean s5a 093/070 | SPEC-0552 | About 530–560 face pixels and glare at the right edge. Need a closer full front without glare. |

`source-review.json` records ten visual quality assessments and seven alternatives excluded
from existing positive register observations and source dimensions. Scene-width estimates are
approximate; no enlargement is used to meet the 600-pixel face threshold. No live source refresh
or new original upload was needed. OCR was unavailable; accepted artwork, printed language,
number and code were read visually. A catalogue render does not independently establish the
physical finish, so both associations remain explicitly representative.

GPT-6 Luna at medium effort prepared the two derivatives. The parent inspected both original
canvases and full-size WebPs, matched the registered source hashes, and independently reconstructed
the native RGB canvases, all six WebP encodings and both palette PNG encodings exactly.
`preparation.json` records the source URLs, hashes, full-canvas pixel boxes, native/output sizes,
alpha-to-white treatment and every output hash. Final widths are 240/480/full, WebP quality 90,
method 6, Lanczos downscaling. Previews are 360 × 503 median-cut palette PNGs with Floyd-Steinberg
dither. No crop, perspective correction, enlargement, sharpening, colour adjustment or retouching.

Two existing `card-release` assets are reused; their two matching previews are regenerated.
Only two representative gallery associations are added. Existing gallery associations and
all canonical evidence and identity records remain unchanged from the batch basis. Together,
rounds 05–08 cover 34 distinct targets, twelve new gallery images (two exact, ten representative)
and 22 documented image needs. The global prepared-image count becomes 256; this is not a
whole-gallery visual acceptance. #476, #481 and whole-gallery acceptance #482 remain open.
No merge into main or Pages deployment was performed.

## Verification

Main `643ebe0d` is integrated, including its set-code guidance and page documentation.
Generated outputs were rebuilt. The full `scripts/regen.py` and pre-push
`scripts/regen.py --check` passed, including 76 data rules with negative tests. All 106 browser
checks passed. All twelve targets were checked on desktop and mobile DPR2 in grid/lightbox and
eight binder layouts each: 192 target/layout checks, correct sources/scope/placeholders,
adequate selected pixel density, no overflow and no HTTP/page errors. All 706 original photos
match their register hashes and carry no GPS.

The built and allowlist-verified `_site-round08` package has 2699 files / 203747 KB. All 2687
non-Markdown source files match byte-for-byte, and both SQLite files pass `quick_check`.
An independent comparison with current main preserves its canonical records and allows only
the PR's six new assets, twelve gallery associations, two primary references, one seller-source
link, SPEC-0796 and data dates. `validation.json` records the result. No deployment was run.

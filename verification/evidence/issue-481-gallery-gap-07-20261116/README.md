<!-- doc: role=retained gallery image preparation and acceptance; stage=task -->
# Gallery image round 07, #481 / PR #593

Twelve active targets are fixed in `targets.json` at `50f809e1`. Six retained owner-photo
targets were triaged first; six retained catalogue/retailer targets were added before derivative
preparation. Four complete catalogue images are accepted as representative renders. Eight
targets keep their placeholders and specific image needs. No original upload, specimen record,
item identity, language verdict, finish claim or owner decision changes in this round.

| Target | Original | Accepted result / remaining need |
| --- | --- | --- |
| Korean XY-P 167 | SPEC-0031 | Glare washes out printed text. Need a sharp complete front in diffuse light. |
| Thai SM-P 083 | SPEC-0026 | Stand overlaps the bottom rim. Need an unobstructed full front. |
| Korean SM-P 140 | SPEC-0028 | About 530–550 effective pixels across the card inside its slab. Need a closer complete front, at least 600 pixels wide. |
| Japanese PCG3 062/084 Unlimited | SPEC-0095 | Holder reflections and thumb at the lower-left perimeter. Owner views SPEC-0096/0097 do not resolve the obstruction. Need a clear complete perimeter; First Edition copies are a different target. |
| English SVP 184 STAFF | SPEC-0076 | Stand at the bottom rim. SPEC-0077 clips the lower edge; other retained same-card views do not supply a better complete front. |
| Simplified Chinese CS1aC 188/135 | SPEC-0098 | Thumb hides the right border. SPEC-0099/0100 also obscure text/borders. Need a front clear of fingers. |
| Indonesian SV2a I 181/165 | SPEC-0177 | Accepted representative render, full native 868 × 1212 canvas. |
| Thai sv2a 181/165 | SPEC-0266 | Accepted representative render, full native 868 × 1212 canvas. |
| Traditional Chinese SV9 F 075/100 | SPEC-0308 | Accepted representative render, full native 868 × 1212 canvas. |
| Indonesian SV4a I 310/190 | SPEC-0180 | Accepted representative render, downscaled from 1364 × 1905 to 1200 × 1676. Physical photo SPEC-0540 has insufficient effective width. |
| Simplified Chinese CS2aC 086/115 Reverse Holo | SPEC-0474 | Soft source detail despite nominal 968-pixel width. Need a sharper scan/photo. |
| Simplified Chinese CS2aC 086/115 Holo | SPEC-0473 | Soft source detail despite nominal 968-pixel width. Need a sharper scan/photo. |

`source-review.json` records 23 rejected primary/alternative sources with hashes, dimensions,
reasons and assessment method. Eight alternatives are excluded from existing registry observations
and source dimensions; the other 15 were inspected visually. Four metadata-only Instagram
alternatives have no retained image bytes. No live source refresh was run. Local OCR was
unavailable; the four accepted images' artwork, printed language, code and number were read
visually. Their catalogue display does not independently establish physical treatment.

`preparation.json` pins the four retained originals and every output. GPT-6 Luna at medium effort
prepared the images. The parent independently inspected all four full-size results and originals,
corrected an initial height-based sizing attempt, and exactly reconstructed every final WebP and
palette PNG encoding from the pinned source. Final sizes are based on width: 240/480/full WebPs,
WebP quality 90 method 6, Lanczos downscaling; previews are 360 × 503 median-cut palette PNGs.
Transparent corners are composited onto white; the entire source canvas is retained. No crop,
perspective transform, enlargement, sharpening, colour adjustment or retouching is applied.

Four existing `card-release` assets are reused. Only their matching previews are regenerated;
primary asset references and asset metadata stay unchanged. Four representative gallery
associations are added. Existing gallery records remain unchanged. With rounds 05–06 this PR
now covers 22 distinct targets, ten new gallery images (two exact, eight representative), and
twelve documented remaining image needs. The global image count becomes 254; that count is not
a whole-gallery visual acceptance.

Local verification: full regeneration gate, 106/106 general browser checks, all 706 photo hashes
and GPS checks, and all twelve targets in desktop/mobile DPR2 grid, lightbox and eight binder
layouts per viewport (192 target/layout checks). Source/scope notices, placeholders, selected
pixel density, no overflow and no HTTP/page errors were checked. The built and allowlist-verified
package `_site-round07-sync` has 2693 files / 202743 KB; its published database matches the built
source. Independent scope assertions preserve all other canonical records. `validation.json`
records the result. #476, #481 and whole-gallery acceptance #482 remain open. No merge or
Pages deployment was performed.

Before the follow-up push, main `7cfae944` was integrated. Its release events, month-date
normalization, display changes and new date rule are preserved. Generated conflicts were
resolved by rebuilding. The integrated tree passed the full pre-push gate (76 data rules with
negative tests), 106 browser checks and the 192 target/layout checks. A cumulative comparison
against that main allows only the PR's six asset additions, ten gallery additions, two primary
image references, one seller-source link, SPEC-0796 and data dates; all other canonical source
records from main are preserved.

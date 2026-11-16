<!-- doc: role=retained gallery image preparation and acceptance; stage=task -->
# Gallery image round 09, #481 / PR #593

Eight active targets are fixed in `targets.json` at `63c4d8f8`: four English/German MEW finish
items with two shared catalogue sources, and four retained physical-photo sources. Five gallery
associations are accepted: one exact photo and four representative renders. Three targets retain
placeholders and concrete image needs. Original photographs, register entries, existing assets,
primary image references, item identities, language/finish verdicts and owner decisions are unchanged.

| Target | Source | Accepted result / remaining need |
| --- | --- | --- |
| English MEW 143/165 Non-Holo | SPEC-0528 | Complete 600 × 825 catalogue render, representative. |
| English MEW 143/165 Reverse Holo | SPEC-0528 | Same catalogue render, explicitly representative; physical treatment is not inferred. |
| German MEW 143/165 Non-Holo | SPEC-0529 | Complete 600 × 825 catalogue render, representative. |
| German MEW 143/165 Reverse Holo | SPEC-0529 | Same catalogue render, explicitly representative; physical treatment is not inferred. |
| Korean sN 008/024 Mirror Holo | SPEC-0699 | Stand tips cover lower rule text and rim. Need a complete front clear of the stand. |
| Traditional Chinese SM-P 053 | SPEC-0496 | Upper perimeter meets the source boundary and detail is soft. Owner-supplied SPEC-0029 has the same framing limitation. Need a sharper full-perimeter front. |
| Japanese sv4a 310/190 | SPEC-0611 | Soft detail and holder reflections reduce readability. Need a sharper full front without holder glare. |
| Indonesian AC3b 238/204 | SPEC-0557 | Complete physical front, classically rectified to 600 × 840; exact printing. Language, number, existing full-art foil treatment and complete perimeter are visible. |

The two MEW source files are prepared once each and reused for their two finish items.
Representative notices remain visible on both item types. No finish-specific photo claim is made
from a digital image. The Indonesian photo reuses its already exact asset and source association;
no new finish claim or unpictured alternative is inferred. SPEC-0335 is metadata only, with no
retained photograph to prepare. `source-review.json` records the three rejected primaries and
one visually inspected owner-supplied alternative. No live source refresh or new original upload.

`preparation.json` pins all three source hashes, every output, and the photo geometry. GPT-6 Luna
at medium effort prepared the derivatives. The parent inspected every original and final full-size
WebP, corrected the initial photo aspect and perimeter margin, reconciled source/output metadata,
and independently reconstructed the native RGB canvases, all nine WebP encodings and all three
palette PNG encodings. Local OCR was unavailable; printed names, language, numbering and layout
were read visually. The existing specimen observation and clearly visible textured foil support
the exact Indonesian association; no claim or provider grade is edited.

SPEC-0557 source is 1024 × 1024. Its clockwise source corners are TL (166,115), TR (811,103),
BR (833,959), BL (205,967); the inverse homography maps them to output pixel centres
(0,0), (599,0), (599,839), (0,839), with bicubic resampling. The real face has over 600 effective
source pixels across it; no enlargement is used. A small amount of original background remains
around rounded corners so the complete rim is preserved. No background replacement or retouching.

Render widths remain 600, with their full source canvas and original corners. All three sources
produce WebPs at 240/480/600 widths, quality 90 method 6, using Lanczos downscaling. Preview PNGs
are median-cut 256-colour palettes with Floyd-Steinberg dither: 360 × 495 for renders and
360 × 504 for the photo. The photo preview preserves the original sRGB ICC profile. No sharpening,
colour adjustment or mark removal. Three existing previews are regenerated; no asset metadata or
primary reference changes. Existing gallery associations stay unchanged.

Together, rounds 05–09 cover 42 distinct targets, 17 new gallery images (three exact, fourteen
representative) and 25 documented remaining image needs. The global prepared-image count is 261;
this is not a whole-gallery visual acceptance. #476, #481 and whole-gallery acceptance #482 stay
open. No merge into main or Pages deployment was performed.

## Verification

Main `643ebe0d` remains integrated. The full regeneration and pre-push observational gate passed,
including 76 data rules and negative tests. All 106 browser checks passed. All eight targets were
checked in desktop/mobile DPR2 grid and lightbox, with source and exact/representative labels,
then in 2×2/3×3/4×4/5×5 binders in both reading orders: 128 target/layout checks, adequate selected
pixel sizes within the available source limit, no overflow and no HTTP/page errors. Shared MEW
sources were checked on both finish items. All 706 original hashes and GPS checks passed.

The built and allowlist-verified `_site-round09` package contains 2708 files / 204660 KB. All
2696 non-Markdown files match their built sources byte-for-byte; both SQLite files pass
`quick_check`. Scope assertions preserve every other canonical source record from the batch
basis and current main. `validation.json` records the result. No publication was run.

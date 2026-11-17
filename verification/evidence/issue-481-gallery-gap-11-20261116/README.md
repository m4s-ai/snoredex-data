<!-- doc: role=round-specific gallery source review; stage=task -->
# Gallery image research, #481 round 11

All 20 frozen IDs received targeted image-source review on 2026-11-16. Round03/04 dead ends were not retried without a new lead. Cardmarket was not requested. The three API and direct seller image retrieval paths are fully logged in `retrieval-log.json`; per-target inspection and candidate disposition are in `source-review.json` and `candidate-manifest.json`.

The initial default network path failed DNS. A separate authorized public-read route retrieved 10 image files; the search-result leads returned only four plausible new physical fronts, with one below the effective-width threshold, one with an unreadable first-edition mark, and two held for finish/quality review. TCGdex produced English and French 600×825 renders for RR81; these are representative only and do not establish exact finish. eBay URLs for English RR81 and Japanese Pt2 070 returned 80×80 placeholders. Yahoo image endpoints returned HTTP 403; Okini returned HTTP 426. Parent verification accepts two sources as representative only: the French physical front (SPEC-0800) and English catalogue image (SPEC-0801). Eighteen targets remain image needs.

| Printing | Target | Round 11 disposition |
|---|---|---|
| `F0248-P01` | Japanese 001 Holo | Seller photo is full/sharp 900×1200; 1st-edition mark unreadable. Hold. |
| `F0086-P02` | German DF 10 Reverse | New search found German regular holo, not target finish; no qualifying exact reverse image. |
| `F0087-P02` | Italian DF 10 Reverse | Found Italian regular holo, not target finish; no qualifying exact reverse image. |
| `F0101-P02` | Japanese DPBP#174 Unlimited | Tradera photo 675×900; complete face but ~550 effective px at narrow edge. Yahoo 403; Okini 426. |
| `F0091-P01` | Italian DP 37 non-holo | No exact-language photo; low-resolution English render retained. |
| `F0092-P01` | Spanish DP 37 non-holo | No exact-language photo; low-resolution English render retained. |
| `F0093-P01` | Portuguese DP 37 non-holo | SPEC-0056 shows text but stand covers bottom rim and effective width is near/below threshold. |
| `F0091-P02` | Italian DP 37 Reverse | No exact-language reverse photo; English regular render is wrong finish. |
| `F0090-P02` | German DP 37 Reverse | German regular image found, wrong finish; no exact reverse photo. |
| `F0089-P01` | French DP 37 non-holo | No exact face above the previously reviewed undersized scan. |
| `F0089-P02` | French DP 37 Reverse | No exact reverse photo; prior listing leads unchanged. |
| `—` | Korean BS2 30 non-holo | SPEC-0037 is 207×288 with face watermark; no improved physical image. |
| `F0098-P01` | Japanese DP-P 127 Holo | Physical photo 1111×1200 rejected: stand touches lower rim and text is soft. |
| `F0319-P01` | Italian RR 111 Holo | SPEC-0119 has small card face (~550 effective px); no exact Italian replacement found. |
| `F0099-P01` | Korean DP 006 Holo | SPEC-0440 is only 480×480 and card is behind holder; no better exact photo. |
| `F0301-P01` | Japanese Pt2 070 non-holo 1st Ed | eBay photo URLs are 80×80 placeholders; Yahoo URLs return 403. SPEC-0635 is Unlimited. |
| `F0312-P01` | English RR 81 non-holo | TCGdex 600×825 image accepted as representative SPEC-0801; eBay URL returned 80×80 placeholder. |
| `F0314-P01` | German RR 81 non-holo | Full face, but fine text is visibly soft at native size. Parent rejects gallery use; no finish inferred. |
| `F0315-P01` | Italian RR 81 non-holo | No exact-language photo found. |
| `F0313-P01` | French RR 81 non-holo | Physical image 698×920 has full sharp face; parent accepts as representative SPEC-0800. Finish remains unasserted; preferred over the alternative render. |

The two selected unchanged, GPS-free originals are retained in photo-repository commit
`6cd0977` (full SHA in `intake.json`). Seller listing page URLs were not established and
remain null. Neither primary image reference changes. No physical finish, language verdict,
owner decision, item identity or catalogue membership changes.

The French source corners (9,9), (689,9), (689,911), (9,911) map to 640×896 by bicubic
perspective sampling. The complete original border and corner background are retained; no
retouching, sharpening, replacement or enlargement. The English image keeps its 600×825
canvas. Both have WebPs at 240/480/full width, quality 90/method 6, Lanczos downscaling, and
360px palette PNG previews. `preparation.json` pins original and derivative hashes and geometry.
The parent inspected both native sources and every prepared full face. Luna performed source
research but reached its usage limit; preparation and filing used the documented parent fallback.
Local OCR was unavailable; text was read visually.

Round 11 is a bounded source review, not proof that the eighteen unresolved images cannot be
found. Later rounds and whole-gallery acceptance #482 remain pending. No merge or publication.

## Verification

All 75 data rules, their negative tests and the complete regeneration pass. All 711 registered
original files match their hashes and carry no GPS. All 106 general browser checks pass.
The twenty frozen targets pass desktop/mobile DPR2 grid and detail checks plus eight binder
layouts per view (320 target/layout checks): correct representative source labels, eighteen
placeholders, adequate selected image sizes within full-source limits, no overflow or HTTP/page
errors. Both final full-size WebPs were independently inspected. A transient local-server
connection reset during browser navigation did not affect any assertion; the suite exited zero.

The local allowlist-verified package contains 2728 files / 207111 KB. All 2716 non-Markdown
files match built source bytes and both SQLite files pass `quick_check`. Cumulative scope vs
main `c3a5f156` is eleven new assets, twenty-two gallery associations, three primary image
references, two source-link additions and SPEC-0796–0801. All other canonical source records
are preserved. Main 2.2.0 schema changes remain integrated. This is not whole-gallery acceptance.

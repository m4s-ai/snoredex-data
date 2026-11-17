<!-- doc: role=retained gallery source review and preparation; stage=task -->
# Gallery image round 12, #481 / PR #593

All twenty stable target IDs are fixed in `targets.json`. Fifteen gallery associations are
prepared: three exact physical photographs and twelve representative associations. Five
targets retain explicit image needs. This round changes no language/finish verdict, owner
decision, printing identity or catalogue membership.

| Sources | Result |
| --- | --- |
| SPEC-0802, German CL 33/95 | Two representative finish associations. |
| SPEC-0803, English BCR 109/149 | Two representative finish associations. |
| SPEC-0804, English CL 33/95 | Two representative associations for regular Non-Holo/Reverse only. |
| SPEC-0805, Spanish BCR 109/149 | One representative association. |
| SPEC-0806, Italian BCR 109/149 | Two representative finish associations. |
| SPEC-0807, Portuguese BCR 109/149 | One representative association. |
| SPEC-0808, Japanese LL 028/040 | Exact complete physical front; visible star foil in artwork. |
| SPEC-0809, German RR 81/111 | Exact complete physical front; visible foil bands across rules text. |
| SPEC-0810, Italian CL 33/95 | Exact reverse front, clearer artwork than glare-obscured SPEC-0106. |
| Existing SPEC-0800/0801 | Reused for French/English RR 81 reverse targets as representative only. |

The remaining five targets are English CL Prerelease and Staff, Italian CL Non-Holo and both
French CL finishes. Generic unstamped images are not substituted for the two stamp targets.
Actual stamped sources are only 205–388px wide. The Italian reverse photo is not substituted
for its non-holo sibling. The new French catalogue sources either show English text or are
below the 600px floor. Their concrete needs and attempted routes remain in `source-review.json`.
No failed retrieval or missing source establishes absence.

Retained sources were checked first. Owner-supplied Italian BCR SPEC-0068 cuts off the bottom
of the card. Italian CL SPEC-0106 has strong glare across the artwork; its new exact replacement
retains the artwork and perimeter. Japanese LL SPEC-0203 is 255×361. A new 751×1048 official
Japanese image was also inspected, but the qualifying physical photo has source priority.
Only the three exact associations replace primary image references; representative assignments
keep their previous primaries. Existing accepted gallery files are unchanged.

The nine original files are reserved in photo-repository commit
`24aea1e508dceaedca75622167ba3816d149e2c0`. Six catalogue PNGs and the Japanese JPEG are filed
unchanged. The German and Italian original WebPs are retained under `originals/`; full native
PNG decodes are filed in the photo repository. `sources.json` pins native and PNG hashes,
decoder/version and exact RGBA pixel equality. All sources and filed files have no GPS.
Seller listing URLs are retained; catalogue image addresses do not invent listing pages.

Luna medium prepared and filed the images. The parent independently inspected every source
and final full WebP and reconstructed every native/face RGB canvas, homography corner mapping,
all 27 WebP encodings and all nine palette PNG encodings (`parent-verification.json`). Local
OCR was unavailable; printed identity was read visually. The photo corner coordinates and
inverse transforms are in `preparation.json`: Japanese 600×840, German 700×980 and Italian
600×840. Catalogue faces keep their full 600×825 canvases. The WebPs are 240/480/full width,
quality 90/method 6, with Lanczos downscaling; perspective sampling is bicubic. Previews are
360px median-cut palette PNGs with Floyd–Steinberg dither and original ICC where present.
No retouching, sharpening, background replacement or enlargement.

All 75 data rules and all 720 registered original hashes/GPS checks passed after integration.
Full regeneration, 106 browser checks and targeted desktop/mobile-DPR2 acceptance passed.
All twenty targets passed grid/detail and eight binder layouts per view; five explicit placeholders remain.
The combined delivery checks all 732 registered originals. The local artifact has 2812 files,
214433 KB; 2800 non-Markdown source files match byte-for-byte and both SQLite quick checks pass.
`validation.json` records this snapshot.
Later rounds and whole-gallery acceptance #482 remain open. No merge or publication.

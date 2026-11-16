<!-- doc: role=retained gallery source review and preparation; stage=task -->
# Gallery image round 10, #481 / PR #593

The twenty target IDs are frozen in `targets.json`. Three new sources are accepted: English
Base Set 2 30/130 as a representative catalogue image (SPEC-0797), German Jungle 27/64
First Edition as an exact-printing photograph (SPEC-0798), and Japanese EC5 062/088 First
Edition as a representative photograph (SPEC-0799). The remaining seventeen targets still
need suitable images. Failed retrievals and missing catalogue images do not establish absence.

The original bytes are retained unchanged, GPS-free, in photo-repository commit
`14d386eec49e2259d2c664b6885b7916ea138081`. `intake.json` records the collision check,
provenance, dimensions and source hashes. Seller listing page addresses were not established;
their fields remain null. These photographs are third-party held, never owner attributed.

The printed German EDITION 1 mark, language, Jungle symbol and 27/64 identify the exact existing
printing independently of the grading label. Only that primary image reference is replaced.
Both representative assignments preserve their existing primary references. The Japanese edition
mark is visible, but the photograph is not used to assert its physical finish. A digital image or
a photograph without glare establishes no non-holo claim. No language, finish, owner decision,
item ID or catalogue membership changes.

`preparation.json` records the classical crop geometry, inverse homography and byte hashes.
German source corners are (316,609), (1233,615), (1235,1910), (296,1905), producing 880×1232.
Japanese corners are (198,103), (849,103), (858,1017), (198,1020), producing 600×840.
The English 600×825 source keeps its entire canvas. Rounded corners retain their original
background. There is no retouching, sharpening or enlargement. Each produces WebPs at 240,
480 and full width, quality 90/method 6, plus a 360px palette PNG preview. Perspective sampling
is bicubic; downscaling is Lanczos. Original ICC profiles are preserved in previews when present.

The parent inspected every original and full prepared face. Luna performed the source research;
its usage limit prevented further delegated preparation, so the parent completed filing and
preparation under the documented fallback. Local OCR was unavailable; printed fields were read
visually. `source-review.json` contains the parent decisions. The Portuguese XY179 Enjoei image
has only about 522–530 effective card pixels despite its 800px canvas and is rejected for gallery
use. The other rejected candidates have insufficient face resolution or mismatching treatment.

Main `c3a5f156` is integrated, including its set normalization and SQLite schema 2.2.0. Cumulative
scope checks against that main preserve all unrelated canonical records. Rounds 05–10 add twenty
gallery associations; the current prepared-image count is 264 of 940 active physical items.
This batch is not whole-gallery acceptance. Issues #476, #481 and #482 remain open; later frozen
rounds and the final gallery audit are still pending. No merge into main or publication.

## Verification

All 75 current data rules and their negative tests pass. Full regeneration rebuilt the five
outputs; its initial sandboxed sensitive-scan fixture could not clone a local test repository.
The subsequent complete observational gate passed with the required local-file access.
All 709 registered originals match their SHA-256 and carry no GPS. All 106 browser checks pass.
All twenty targets pass desktop and mobile DPR2 grid/detail checks, then eight binder layouts
each (2×2, 3×3, 4×4, 5×5 in both reading orders): 320 target/layout checks in total, with no
HTTP/page errors or horizontal overflow. All three accepted sources and their scope labels are
correct; seventeen placeholders remain explicit. Selected image sizes meet displayed demand
within the available full-source limit. Every final full-size WebP was also visually inspected.

The local, allowlist-verified package contains 2720 files / 206292 KB. All 2708 non-Markdown
files match the generated source bytes; both SQLite databases pass `quick_check`. The package
is a local acceptance artifact only. No deployment was run.

<!-- doc: role=retained gallery image preparation and acceptance; stage=task -->
# Gallery image round 06, #481 / PR #593

The six active targets were frozen in `targets.json` at PR head `0f49ae23`, starting
2026-11-15; preparation and visual acceptance continued on 2026-11-16. All sources were already
registered and retained in `m4s-ai/snoredex-photos`. No photograph, specimen record, verdict or
owner decision was created or changed in this round.

## Accepted images and remaining need

| Target | Retained source | Outcome |
| --- | --- | --- |
| English CLV 016/034 | SPEC-0786, 733 × 1024 database image | Prepared at original canvas size; render, explicitly representative. The database image does not independently establish the physical treatment. |
| Korean BW7 055/070 | SPEC-0788, 3024 × 4032 owner-supplied photo | Prepared 1200 × 1680; representative. Exact finish/edition is not established by this photo; the existing item fields stay unchanged. |
| Korean FXY 026/036 | SPEC-0789, 3024 × 4032 owner-supplied photo | Prepared 1200 × 1680; representative. No finish is inferred from its appearance. |
| Simplified Chinese CS5DC 098/153 | SPEC-0792, 1204 × 1600 seller photo | Placeholder retained: acrylic stand overlaps the lower card border and copyright. Need an unobstructed complete front at 600+ effective pixels; do not crop away or retouch the stand. |
| Simplified Chinese CS5DC 097/153 | SPEC-0793, 1600 × 2133 seller photo | Prepared 940 × 1316; representative, with the specimen's finish uncertainty preserved. |
| Simplified Chinese CSM2.1C 054/045 | SPEC-0795, 868 × 1127 seller photo | Prepared 720 × 1008; exact printing. The number, localized text and visible whole-face rainbow foil match the existing holo item. |

Older matching originals were also checked: BW7 SPEC-0442 is only 480 × 480; CSM2.1C SPEC-0147
and SPEC-0148 are 516/519 pixels wide before their slab crop. They cannot meet the 600-pixel
gallery threshold. The existing table images for the four representative cases are preserved;
only the exact CSM2.1C item receives a new primary image reference.

## Preparation and provenance

`preparation.json` records each original hash, native quadrilateral, inverse homography,
resampling, conservative full width, RGB pixel hash, preview hash and all responsive output
hashes. SPEC-0786 retains its source canvas. The other four faces are classically rectified,
with complete rims and rounded corners, no enlargement and no retouching. Slight corner
background and genuine source surface/lighting remain. All five have 360-pixel palette previews
and 240/480/full WebPs at quality 90, method 6, using Lanczos downscaling.

The five image assets and gallery associations are canonical `data/images.json` records. Four
assets have `card-release` scope and four gallery associations are `representative`; the fifth
is exact. The gallery's representative notice and retained-source label were checked in the
lightbox on desktop and mobile. New asset descriptions use readable card and set names.

Preparation ran in GPT-6 Luna at medium effort. The orchestrator independently inspected every
original and full-size output, corrected initially clipped perimeters, and verified source
hashes, all homography corners, exact RGB reconstruction, no enlargement, palette previews,
and every output's dimensions/hash. Local OCR was unavailable; printed identities were read
visually. Sources remain unchanged, including their previously removed location metadata.

## Verification and scope

- Full `scripts/regen.py` and pre-push `scripts/regen.py --check`.
- 102/102 general browser checks.
- All six targets in grid and lightbox on desktop and mobile DPR2, with correct source and scope.
- All six targets in 2×2/3×3/4×4/5×5 binders, both reading orders, both viewports:
  96 target/layout checks, adequate selected image pixel sizes, no page overflow or HTTP/page errors.
- Built `_site-round06-pr`: 2681 files, 199613 KB; allowlist verification passed.
- All 706 registered photos match their hashes and carry no GPS.
- Independent scope assertions: five image-asset/gallery additions, one primary image reference,
  and the two data-date fields. All existing images, identities, claims, registry entries,
  provider grades, finish fields and owner decisions are preserved.

`validation.json` records the batch result. The single obstructed-image need remains open in
#481. Together with round 05, this PR covers ten fixed targets, six new gallery images
(two exact, four representative), and four documented image needs. #476 and #482 remain open.
No merge or Pages deployment was performed.

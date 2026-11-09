<!-- doc: role=gallery image preparation and batch acceptance contract; stage=task -->
# Gallery images

The owner-approved plan is tracked in [#476](https://github.com/m4s-ai/snoredex-data/issues/476).
Batch 0 (#477) introduced the inventory and preparation path, the twelve-source pilot (#478)
accepted it on real sources, and later batches (#479–#481) follow this interface.

## Inputs and ownership

- `scripts/site.py` generates `verification/gallery_image_inventory.json` for every gallery item.
  It joins catalogue assets, the retained artwork projection, physical-printing specimen references
  and explicitly representative gallery images. Source-frame dimensions and hashes are recorded.
  A specimen citation to the item's existing finish-printing ID supplies exact scope for that
  item only. The citation leaves the finish projection and verification status independent.
  Remote candidates require retained local bytes before preparation.
  Local sources remain unclassified until recipe review: the SPEC directory contains both
  physical photographs and digital renders. The reviewed recipe's `mediaKind` determines priority.
- `verification/gallery_image_recipes.json` holds reviewed source choices, geometry and target
  item IDs. The same source may serve several compatible targets. An exact scope requires an exact
  candidate link. A representative image stays representative in the lightbox.
- `verification/prepare_gallery_images.py` owns the separate retained
  `verification/gallery_image_manifest.json` and content-addressed `images/gallery/*.webp` outputs.
  SPEC originals and evidence stores remain untouched.
- `scripts/gallery_image_assets.py` validates integrity and selects accepted prepared photos
  before accepted renders, then uses a placeholder. It never derives an existence verdict.

Batch membership is explicit through recipe target IDs. An item without any recipe keeps its
legacy preview until its batch begins. Once an item has a recipe, only an accepted, sufficiently
resolved prepared candidate can supply its gallery image. Pending, rejected and undersized
candidates stay visible in the inventory; a usable accepted alternative can still be selected.
The publisher includes only selected accepted gallery outputs.

Reviewed items with no candidate source use `unavailableTargets` in the recipe store:
`{itemId, note}` records a concrete image need without inventing a source or crop. IDs must be
unique and present in the inventory, and the review note must be nonempty. If a candidate later
arrives, validation requires reviewing that source and replacing the source-less entry with its
recipe. These entries display placeholders and publish no image files.

## Recipe format

Each recipe has these fields.

| Field | Meaning |
|---|---|
| `id` | Unique lowercase letters, digits and hyphens |
| `source`, `sourceSha256` | Retained candidate path and original SHA-256 from the inventory |
| `sourceDimensions` | Decoded width and height, including the browser's EXIF orientation |
| `corners` | Four pixel-coordinate pairs, upright top-left, top-right, bottom-right, bottom-left |
| `aspectRatio` | Positive width/height pair, normally `[5, 7]`; review nonstandard cards separately |
| `mediaKind` | Visually checked `photo` or `render` |
| `targets` | Array of `{itemId, scope}`, with `exact-printing` or `representative` scope |
| `review` | `{status, note}`, with `pending`, `accepted` or `rejected` status and a review explanation |

Corners describe the individual card face, preserving its edges, text and identity markings.
Choosing the upright corner order handles rotation. The renderer performs a projective transform
and bilinear sampling from the full decoded source, then high-quality responsive resizing.
Do not remove on-card marks or reconstruct obscured details. Glare, blur, watermarks over the card
and incomplete faces require a better source or a documented placeholder.

The output width is bounded by opposite source edges, perpendicular extent and the height available
at the chosen aspect ratio. Crops below 600 pixels effective width produce a `below-minimum` result without an
enlarged image. Adequate crops produce 240px and 480px variants and a full version up to 1200px.
This geometric limit complements visual sharpness review; it cannot establish that a supplied
original was never enlarged before intake.

## Prepare and accept one bounded batch

1. Regenerate the current inventory with `python scripts/site.py`. Freeze the batch's target IDs
   and source choices in an issue comment before editing recipes or retaining sources. Gap rounds
   source images with the card-search skill and retain them as SPEC files through specimen intake.
   Keep a downloaded JPEG's bytes unchanged when it carries only technical metadata. Otherwise
   retain a pixel-identical PNG (same decoded pixels, mode and dimensions) that omits the metadata,
   and record both hashes in the bundle's `source-map.json`. Every evidence bundle `README.md`
   starts with a `<!-- doc: role=...; stage=... -->` header whose stage is one of `DOC_STAGES`
   (usually `reference` or `task`); without it gate `D1` fails.
2. Record recipes with `pending` review status, hashes, decoded dimensions, corners and notes.
3. Install the pinned verification requirements and Chromium. Run
   `python verification/prepare_gallery_images.py --prepare RECIPE_ID`, passing several IDs when
   they belong to the same bounded batch. Preparation uses the pinned Chromium offline. A lock
   refuses concurrent writers; a failed write can be retried. After an interrupted process, verify
   it has exited before removing its stale `verification/gallery_image_manifest.json.lock`.
4. Inspect outputs and compare the card with its original. Review all batch outputs as a contact
   sheet and in the browser. Set the accepted/rejected status and note, then prepare those IDs
   again so the manifest binds the reviewed recipe. A retry with unchanged inputs preserves bytes
   and timestamps. Unreferenced content-addressed outputs cannot enter the published artifact.
5. Run `python scripts/site.py` and `python verification/prepare_gallery_images.py --check`.
   The check is observational and needs no browser. Source, recipe, processor or output drift fails
   the check rather than reusing stale images. Re-preparation uses `--prepare`, separate from checks.
   Never run `verification/test_site.py` in parallel with `python scripts/regen.py --check`: the
   check's read-only tree snapshot then reports the browser suite's writes as a change.
6. Check the gallery at desktop/mobile widths and high pixel density. Prepared images use srcset
   and cap their displayed width against available pixels. The lightbox links the original.
   Record batch IDs, commit, checks and unresolved image needs in its issue.

Each delivery follows the existing batch execution contract and full release gate. The browser
suite includes synthetic full-detail PNG/JPEG, perspective, rotation, responsive display, retry,
integrity and rejected-low-resolution cases. The twelve real-source pilot (#478) completed that
acceptance before series processing.

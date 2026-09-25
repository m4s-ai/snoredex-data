<!-- doc: role=issue-258 Indonesian physical evidence; stage=reference -->
# Indonesian AC3b 239/204 seller photograph — 2026-09-24

SPEC-0556 retains the exact seller photograph supplied for review: Indonesian Eevee & Snorlax GX, AC3b C 239/204 SR. The card face visibly shows Indonesian text, the number and rarity, and reflective foil across the face and border. The observation records `holo`; it does not assign a specific foil pattern or close the finish inventory.

The image endpoint returned WebP. The original 1080×1080 WebP and SHA-256 are kept in `sources.json`; the canonical specimen importer stores a PNG because it accepts PNG/JPEG only. Pillow 12.3.0 decoded the WebP to PNG with no crop, resize or enhancement. Reopening the PNG and comparing RGBA pixel bytes verified exact equality with the decoded WebP. The importer hash for the PNG and original WebP hash are both recorded.

The card is listed by a third-party eBay seller. Its item specifics are not used as proof; the card face and reflective surface were inspected visually. Tesseract is unavailable in this environment, so text identification is by visual reading. This photograph depicts one seller-held copy. It is not linked to SPEC-0334, which came from a separate Instagram carousel and has no retained photo; no same-copy relationship or independent corroboration is claimed. The record remains `allowUnprojected` because no matching canonical source-first release or finish unit is present. It is retained as an unresolved physical candidate, without a fabricated release or printing relationship.

## Acceptance

The importer accepted the losslessly decoded PNG through `manifest.json`; its offline photograph-integrity check passed. The physical workflow loop stopped after one cycle because no metric changed, and the `physical-evidence` scoped lane passed all five steps. SPEC-0556 remains a standalone, unprojected candidate until its release is represented canonically. No seller was contacted.

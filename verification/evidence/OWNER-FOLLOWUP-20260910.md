<!-- doc: role=owner follow-up evidence intake; stage=reference -->
# Owner follow-up: photographs and established finish identities

Reviewed on 2026-09-10 for PR #375 and issues #256, #258, #262 and #266.
The [reviewed manifest](issue-256-owner-followup-20260910.json) retains four new originals:

| Specimen | Identified card | Supported observation |
|---|---|---|
| SPEC-0522 | Indonesian s10a I 077/071 CHR | Readable Indonesian text and identifier; owner explicitly confirms Holo. Finish is attributed to the owner separately from the Shopee identity image. |
| SPEC-0523 | Thai s5a T 093/070 UR | Readable Thai text and identifier; fine glittering foil supports Holo. The owner supplied the photo, but its holder and original listing are unknown. |
| SPEC-0524 | Spanish Jungle 27/64, 1st Edition | Readable Spanish text, number and EDICIÓN 1 stamp. Non-Holo follows the owner's established Jungle number mapping. |
| SPEC-0525 | Spanish Jungle 27/64, Unlimited | Complete front and reverse; no first-edition stamp in the visible edition area. Non-Holo follows the same positive number mapping. |

The Indonesian WebP is losslessly decoded to PNG because the importer accepts PNG/JPEG.
Its actual 900-pixel CDN source and listing are retained. The three supplied PNG originals
are copied without cropping or recompression. No assumed seller identity, release date or
unpictured foil subtype is added. Exact language claims U0170, U0604 and U0092 now cite
the retained photographs instead of remaining set-level evidence. Indonesian and Thai
printed local identifiers are reconciled in the same change.

## All Western-language Jungle releases

The owner explicitly reaffirmed that Snorlax Jungle **11/64 is Holo and 27/64 is
Non-Holo in ALL Western languages**, for both first edition and Unlimited. This is
an established card-identity mapping. Demanding another reflection photograph for
27/64 was incorrect. The scoped owner source in finish_overrides.json applies that
positive mapping to the existing Western-language candidates; it does not create
new language or edition existence claims. FINISH_SOURCES.md documents the rule.

## Previously retained images and information

- Indonesian 117/SV-P: SPEC-0019 and SPEC-0020 already retain Poké Ball/V1 and
  Master Ball/V2 respectively. The new comparison supplied in the task places Master
  Ball left and Poké Ball right, opposite to the older retained pair. Position is
  image-specific; the ball silhouette identifies the pattern. This comparison adds
  no new printing or unresolved finish decision. The eBay original returned HTTP 403;
  no screenshot is substituted for original bytes and no duplicate specimen is invented.
- Indonesian 278/SV-P: the retained source and SPEC-0187 already establish Gym Promo
  Card Pack 11 on 2025-07-25. No new original image was supplied in that follow-up.
- Indonesian 286/SV-P: the same Taro card image is already retained as SPEC-0188.
  Existing source-first and finish evidence explicitly say **January–February 2026**.
  The structured release date 2026-01 is month-precision start, not the campaign's
  entire duration. No exact start/end day is inferred. No duplicate specimen is needed.

These already-known promos were incorrectly repeated as research requests. Issue
progress must be derived from current evidence gaps, not from recently found links.
The current photo batch resolves the previously requested images; remaining dates
and other cards' finish questions stay separate.

## Review boundary correction

A coalesced release may hold several legacy aliases. Validation now requires the
photograph identity and its cited legacy unit to match together, including variant;
an alias from one counterpart cannot be combined with another counterpart citation.
Both physical projection paths use the same check. The regression includes valid
paired aliases and the previously accepted Cartesian mismatch.

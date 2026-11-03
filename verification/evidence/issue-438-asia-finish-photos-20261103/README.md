<!-- doc: role=retained evidence for issue 438, Asian seller photographs and owner readings; stage=history -->

> Historical record — 2026-11-03; current values are determined by canonical stores.

# Issue #438: Asian finish photographs (2026-11-03)

Seller photographs found by a five-locality search (JP, KR, zh-Hans, zh-Hant, ID/TH), shown to the
collection owner on three contact sheets and read by the owner on 2026-11-03. Every image was re-fetched
from its image URL and matched byte for byte before import; `sources.json` holds the hashes and
`intake-manifest.json` replays the intake.

| Sheet | Owner reading | SPEC |
|---|---|---|
| C, plain copies | all Non-Holo | 0675 KR sv2a 143, 0676 151C 143, 0677 CS1aC 110, 0678 CSV7C 158, 0679 CSV5C 115, 0680 TW sI100 341 |
| B, line foil on R cards | all Holo | 0681 TW s8b 126, 0682 TW s4 84 |
| A, patterned foil | all reverse holos, stored as `reverse-holo` + pattern | 0683 151C 143 Master Ball, 0684 151C 143 Poké Ball, 0685 CS1aC 110 star, 0686 CS5aC 093 star, 0687 CS6bC 113 star, 0688 CSV10C 175 Poké Ball, 0689 CSV5C 115 Poké Ball, 0690 CSV7C 158 Poké Ball, 0691 CSV7C 158 Master Ball, 0692 TW sv4a 145 sparkle |

Non-Holo and Holo rest on the owner's reading (`ownerAttestedFields: ["finish"]`); lack of glare is
context only. The patterned reverse holos rest on the visible pattern. SPEC-0675 was served as WebP
and is retained under `raw/` with its lossless PNG conversion recorded.

Not imported, with reason:

- Sheet B JP/KR copies (s10a 058, s10b 056, s8b 126, sv9 075, s5a 093, XY-P 261): holo is already
  confirmed for those units. Sheet B CN R copies are covered by the terminology correction instead.
- Sheet A tile 10 (CSZC 018): reverse holo already confirmed by SPEC-0149. Tile 11 (KR sv4a 145) is
  the same seller listing as SPEC-0624, which the correction pass re-reads as `reverse-holo`.
- Sheet C JP sv2a 143, JP 20th 047 and KR mC 568: non-holo already confirmed. A plain sv2a photo
  does not speak to the separate `xsv2a` mirror product.
- ID/TH: no photograph found; YouTube openings listed in the session report remain unchecked leads.

Routes that blocked automated access (Shopee ID/TH, Tokopedia search, eBay item pages, Xianyu,
Xiaohongshu, Ruten, Mercari JP) are search gaps, never absence evidence.

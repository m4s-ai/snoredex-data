<!-- doc: role=retained research workstream report; stage=history -->

# asia-artists: summary (2026-10-22)

Targets: 101 card releases (TW Traditional Chinese, ID Indonesian, TH Thai) with no illustrator.
**Found: 101. Unresolved: 0.** Every finding's targetIds holds the cardReleaseId plus all its itemIds.

## By method
- database-credit: 82. These come from asia.pokemon-card.com/{tw,id,th}/card-search/detail/N/ pages,
  where the illustrator block ("繪師" / "Ilustrator" / "ผู้วาดภาพประกอบ") sits on the page of the exact
  expansion code + collector number. The pages are saved under raw/detail/ and raw/scan/.
- image-transcription: 17. The "Illus." line was read from repository specimens
  (verification/specimens/SPEC-*). Each one is mapped through collector_catalogue.json imageAssetId,
  with scope exact-printing or card-release.
- artwork-propagation: 2.
  - TW AS5a 222/184 HR is anchored on 203/184 SR (5ban Graphics). Medium confidence because the
    target's own credit is blurred.
  - ID s5a 093/070 UR is anchored on the TW/TH 093/070 UR specimens (Saki Hayashiro).
- Confidence: 98 high, 3 medium (AS5a 222; ID SV-P 278 and 286, which are 255px images and are
  corroborated by matching the artwork against official TW images in raw/img/).

## Best sources
1. asia.pokemon-card.com detail pages (official, one page per print). Saved files: raw/detail/*.html
   and raw/scan/*.html; fetch log is in raw/fetchlog.tsv.
2. Repository specimens SPEC-0598, 0039, 0601, 0038, 0427/0428, 0083, 0557, 0556, 0027, 0026, 0496,
   0489, 0523, 0519, 0323/0324, 0319, 0019/0020, 0187, 0188. These are referenced by path and sha256
   and were not copied.
3. Official TW card images tw00012268.png and tw00010298.png (in raw/img/), used only to compare
   artwork.

## Gaps in the official database (gaps, not absence)
- Secret rares above the printed set size are not indexed: AS5a stops at 184, S5a at 070, S10a at 071,
  AC3b at 204, and TW SC1b at 171.
- Thai AS1b and AS5a return 0 results. SM-P returns 0 for ID and TH; TW has 1 record. TW CLF returns 0.
- ID SV-P 117, 278 and 286 are not in the ID SV-P listing (all 251 records scanned).
- Searching needs local-script keywords: TW 卡比獸, TH คาบิกอน, ID Snorlax. Listing by set uses
  `list/?expansionCodes=CODE&pageNo=N`.

## Conflicts and notes
- S10a 058/071 credits differ by locale. The official TW record says "0313"; the ID and TH records say
  "313". Each is recorded verbatim. snorlax_cards.json has "0313" for the JP/EN print, so the ID/TH
  spelling is a difference in form that needs normalization review.
- None of the findings disagree with an illustrator already in snorlax_cards.json for the same set and
  number (checked S4 084, S8b 126, S10b 056, SV4a 145, SVM 094, S10a 077).
- Owner rule ARTIST-RULE.md was applied: a detail page covers every finish of its card release, and
  multiple official records for one number (M2a/MA3 136, SV2a 143, MC 568) all agree.

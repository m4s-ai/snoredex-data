<!-- doc: role=seventh research round multilingual user-supplied image intake; stage=reference -->
# Multilingual image intake - 2026-09-21

PR #390 remains draft. Seven new original images are retained in this batch. Images were manually inspected in the conversation before import; local Tesseract OCR was unavailable. WebP originals are retained and losslessly decoded to PNG for the canonical importer, with pixel equality checked. JPEG originals remain unchanged. Sources and hashes are in `sources.json`.

| Specimen | Identity | Supported observation |
|---|---|---|
| SPEC-0538 | Thai s10b 056/071 R | Physical sleeved card on wood; colored foil in illustration and borders: holo. |
| SPEC-0539 | Korean s10a 077/071 CHR | Full Bunjang photograph includes the printed number and Hangul; colored foil: holo. |
| SPEC-0540 | Indonesian SV4a I 310/190 S | Angled card in holder with visible texture and multicolored foil: holo. |
| SPEC-0541 | Indonesian S10b I 056/071 | Physical card on stand; Indonesian Portal/Tumbang and number legible, colored vertical foil: holo. Rarity area partly obscured, so no new rarity determination. |
| SPEC-0542 | Indonesian MA6 I 121/130 | Isolated depiction confirms identity, HP160, Aya Kusube, Good Sleep/Tumbang and 30th-anniversary logo. No physical finish inferred. |
| SPEC-0543 | Thai AS1b 112/150 RR | Magic Poke Shop depiction confirms identity and printed RR. Admitted in round eleven as TH:AS1b:112/150:base and linked to the retained image. No physical finish inferred. |
| SPEC-0544 | Traditional Chinese AS5D 118/169 | Isolated depiction confirms identity, HP270, Mitsuhiro Arita. Boxed C is regulation. No physical finish inferred from seller wording or absent reflections. |

## Bunjang full-image correction

The seller's media viewer loads https://media.bunjang.co.kr/product/430112687_1_1789714245.jpg (900x1200). The `_w1200.jpg` URL is a square crop, not the original, and omits the printed number. The full image was extracted from the user-supplied media viewer's actual image URL using the browser. Use the original for SPEC-0539. This resolves the cropped-number limitation in the preceding PR research comment; do not repeat that limitation for this retained image.

## Indonesian s10b replacement links

The old https://shopee.co.id/product/696838775/22468551025 could not be opened by the user. Alternative indexed offers explicitly naming Indonesia/IDN are:

- https://shopee.co.id/product/397703499/50008554082 (context supplied with the new SPEC-0541 image).
- https://shopee.co.id/product/21411737/49510515539 .
- https://shopee.co.id/product/359696179/54706131473 .

Their public product pages did not expose original photos to the web reader. The user supplied the exact CDN image used for SPEC-0541. The Japanese-labelled listing 388360157/45865703079 is not Indonesian evidence.

## Remaining evidence boundaries

The earlier conversation-only Thai AS5D 118/169 photo and blurry Thai s10a 058/071 image still lack retrievable originals; those findings remain documented in round six without fabricated specimen imports. This batch does not close those cases. The Traditional Chinese AS5D image does not establish Thai AS5D. No exact foil-pattern taxonomy, absent variant, or complete finish inventory is asserted. Store logos outside card faces are not distribution markings.

## Multilingual search follow-up

The following preceding search snapshot is retained for traceability. Its Korean cropped-image limitation and pending-image statements are superseded by the intake table above; other retrieval limits remain.

## Continued multilingual research — 2026-09-21

Draft-preserving research update; no catalogue or finish verdict changed in this sweep.

- **Korean s10a 077/071 CHR:** https://m.bunjang.co.kr/products/430112687 . Inspected seller photograph https://media.bunjang.co.kr/product/430112687_1_1788884944_w1200.jpg shows Hangul Snorlax HP150, the eating scene and colored foil at the left. However, the original image is cropped before the collector-number line, so exact number is still listing-supplied rather than photo-read. A second exact-number Korean listing is https://m.bunjang.co.kr/products/433337048 ; its page/image was not recovered. Official identity reference: https://pokemoncard.co.kr/cards/detail/BS2022011126 . No finish transfer from the official render.
- **Indonesian sv4a 310/190:** https://shopee.co.id/product/1343192572/40831397416 explicitly advertises the Indonesian Harta Berkilau card. Original physical photo still needed. Nearby listing 1189706179/44324861404 explicitly says Japanese and is excluded as Indonesian evidence.
- **Indonesian s10b 056/071:** https://shopee.co.id/product/696838775/22468551025 is an exact-number lead; language and finish still require the actual image.
- **Traditional Chinese AS5D 118/169:** https://shopee.tw/product/27756288/25871401400 explicitly advertises the Chinese starter-deck card. Seller wording 普卡 is retained as a lead, not a physical non-holo observation. Official HK identity page: https://asia.pokemon-card.com/hk/card-search/detail/3937/ . Product image could not be recovered.
- **Spanish XY179:** https://tcg.fans/pokemon/products/snorlax-holo-promo-xy179 lists Spanish among general language filters, but its actual available offer is English. https://dreephy.cl/producto/snorlax-xy179/ has general language options; neither establishes an inspected Spanish printing. No new Spanish confirmation.
- **Simplified Chinese CS2DaC 038/053:** initial search returned Traditional Chinese SH 038/053 pages; those cannot establish the Simplified Chinese release. No new confirmation.

The newly supplied Thai s10b physical-holo image, Thai AS1b identity image and Indonesian MA6 identity image remain pending canonical intake after the last reviewed commit. This comment does not claim they have already been imported. PR remains draft and unmerged.

## Catalogue impact

Four positive holo printings are added: three replace existing research placeholders; Thai s10b holo is added alongside the preserved marketplace-only non-holo candidate, without validating or deleting that candidate. Totals are 1011 items, 767 verified printings, 113 finish candidates, 131 research placeholders, 641 releases and 450 active assets. Five existing items gain evidence links only; 1002 existing items are otherwise unchanged. Links on legacy Indonesian identities do not change their historical finish verdicts or resolve their unknown-local-set mapping. Source-first localized observations retain their exact S10b I / SV4a I identities.

## Validation

Full pre-change check, seven-image importer integrity check, bounded physical loop, all five scoped steps and full regeneration/core gate passed. Original hashes and item conservation are recorded in validation.json. Post-push history audit and new exact-head review are tracked in the PR delivery.

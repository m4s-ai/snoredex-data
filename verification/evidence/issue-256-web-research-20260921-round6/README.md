<!-- doc: role=user-supplied Thai image follow-up and sixth research round for issues 256 and 262; stage=reference -->
# Thai image follow-up - 2026-09-21

All seven user-supplied image findings are accounted for below. PR #390 remains a draft. Five retrievable images are imported through `manifest.json`; two conversation-only images are documented without pretending their original bytes were recovered. Nothing establishes absence or an exhaustive finish inventory.

## Reviewed images

| Supplied target | Result | Retained evidence / next step |
|---|---|---|
| Snorlax Collect, initially unclear | **sc1a T 127/154 U**, Thai, HP150, Eri Yamaki, Collect draws two cards, Body Slam 120. The assistant's initial `scA T 123/154` reading was wrong. Reinspection and the official card page agree on 127/154. | SPEC-0533; seller photo establishes identity. Owner explicitly states "finish ist erkennbar als non holo" for this photograph; `ownerAttestedFields: ["finish"]` carries non-holo. This is not an inference from missing reflection and not a claim that the owner possesses the seller's card. |
| svM 094/175 | Thai Snorlax ex, HP260; Magic Poke Shop depiction confirms identity. | SPEC-0534, identity only. No physical finish determination. CDN URL retained; no independently verified mapping from the image to a particular product page. |
| s10a 058/071 | User-supplied low-resolution physical-card photograph on a pink Mew mat shows Thai Snorlax HP150 and colored foil. The bottom identity line remains too blurry for an exact-number assertion. | Conversation observation only. Original file/URL not available to importer; no SPEC allocated, no finish projection. Contextual lead: https://shopee.co.th/product/264581611/21684853745 . Need original or legible lower edge before exact attachment. |
| MA4 091/123 | Thai Snorlax HP160, MA4 T J 091/123 C, Toshinao Aoki; Magic Poke Shop depiction. | SPEC-0537, original supplied PNG retained, identity/printed rarity only. Contextual listing: https://shopee.co.th/product/136710401/41979577897 . No physical finish determination. |
| s10b 056/071 | Thai Snorlax HP150, s10b T F 056/071 R, Pokemon GO. OjamaCard composite depicts rainbow bands. | SPEC-0536, identity only: physical scan versus rendered foil is unresolved. Source: https://h.lnwfile.com/_/h/_raw/mu/u3/4u.jpg . |
| s8b 126/184 | The supplied PP Card Game Shop image actually reads **sc3b T 126/158 R**, HP130. | SPEC-0535, identity only. Existing sc3b confirmation remains; no transfer to s8b and no non-existence decision. CDN URL retained without inventing a verified listing association. |
| AS5D 118/169 Eevee & Snorlax-GX | Supplied conversation image clearly shows Thai text, AS5D 118/169, HP270, Mitsuhiro Arita. The boxed C is regulation, not rarity. | New positive Thai identity observation, retained here as an admission/retrieval lead. Original bytes not recoverable: contextual eBay https://www.ebay.com/itm/128015702655 returned HTTP 403; web readers on US/UK/AU failed. No SPEC, graph admission or finish assertion without retained original. This must not be attached to the existing Traditional Chinese AS5D release. |

The original Collect photograph is https://down-th.img.susercontent.com/file/7cf2fc9eebd1204f48ffb47dc15b229b.webp ; contextual seller listing is https://shopee.co.th/product/425086629/13703047839 . Independent positive identity cross-check: https://asia.pokemon-card.com/th/card-search/detail/127/ explicitly gives HP150, the two attacks, Eri Yamaki and 127/154. The existing official reference is SPEC-0253.

Additional exact listing IDs recovered from opened Shopee search results: https://shopee.co.th/product/431199770/22777598129 advertises Thai s10b 056/071 as foil; https://shopee.co.th/product/136710401/2176323915 advertises Thai AS1b 112 GX. Both product pages failed in the web reader; their titles remain leads, not card-face or finish evidence.

## Retention and attribution

`sources.json` preserves original hashes and image dimensions. WebP originals are retained; PNG copies were decoded losslessly and checked for pixel equality before intake. The original MA4 clipboard image and s10b JPEG are retained byte-for-byte. Local Tesseract OCR was unavailable; all printed identity checks use manual visual inspection. SPEC-0533 is the only new finish observation. SPEC-0534 through SPEC-0537 omit `physicalObservation`; seller artwork and contextual titles are not converted into physical observations. The owner finish statement is separated from the seller photograph's identity claim.

## Continued research

- A newly indexed Shopee two-card listing advertises Thai **SH 026/038** together with a 091/123 card: https://shopee.co.th/search?keyword=%E0%B8%84%E0%B8%B2%E0%B8%9A%E0%B8%B4%E0%B8%81%E0%B8%AD%E0%B8%99&page=1 . Its title labels the other card SV8T, so exact photos and option identities still require inspection. Search-index snippets and opened result pages differ; this is a retrieval lead only.
- https://cardtell.id/shop/WSY98QA7ZR newly advertises Snorlax MA6 121/130 in an Indonesian seller's 30th-anniversary lot. It is an Indonesian lead, not Thai proof; no language/finish transfers.
- https://mycardpal.com/article/5483a4fd-8d46-4025-a33d-f91661fb6c40 lists MA6 121 with pooled ID/TH labels, Fixed rarity and a Cardmarket link. It supplies no inspected Thai card face, so neither date nor rarity is accepted from this pooled entry.
- Searches for sc1D 132/164 and 133/164, SH 026/038, scD 111/159 and MA6 121/130 yielded no additional inspected Thai physical-finish evidence in this bounded sweep. Official sc1D identity page https://asia.pokemon-card.com/th/card-search/detail/439/ is positive identity evidence only. Empty results are not absence.

A further exact Indonesian MA6 lead is https://www.ebay.com/itm/198648492982 (seller purupuru_ex). Its indexed title says Indonesia, while item specifics inconsistently say Japan, Promo and Stamped. Holo is seller metadata, not an inspected observation. Original photo still needed; no Thai or Indonesian finish confirmation is made. `retrieval.json` records final direct-page attempts.

## Validation

Pre-change full `regen.py --check` passed. The canonical importer accepted all five observations with photograph integrity checks. The bounded physical loop stopped after one cycle with `no-metric-change`; all five scoped physical-evidence checks and full regeneration/core checks passed. Exactly one existing-release placeholder becomes a verified non-holo printing: 763 verified printings, 134 research placeholders, 1010 total items, 641 releases and 449 active assets. Four existing items gain evidence links only; the other 1005 are unchanged. Original hashes and owner/photo field attribution were checked. `validation.json` records the conservation result. No research issue is closed and no ready/merge action is authorized.

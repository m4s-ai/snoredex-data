<!-- doc: role=further Thai missing-card research and source discrepancies; stage=reference -->
# Further Thai card research — 2026-09-15

Subsequent [marketplace and sold-listing research](../issue-262-marketplaces-20260915/README.md) recovered an additional AS1b 112/150 seller image and records qualified eBay/Mavin, ThaiPick and Carousell leads. No additional identity or physical-finish claim was admitted.

Research supplement for #262 and draft PR #383. This pass followed both pages of the official Thai name search (`keyword=คาบิกอน`, `cardType=all`, `regulation=all`), retrieved all 26 linked detail pages, inspected six relevant official card images, and followed external leads for older GX releases. These are manual research captures, not a fabricated discovery run or new canonical claims. Source silence remains unknown.

## Newly located missing card

**Thai Eevee & Snorlax-GX AS5a 117/184 RR** is legible on page 13 of the [official AS5a PDF](https://asia.pokemon-card.com/th/archive/card/pdf/AS5a.pdf). The [retained crop](as5a-117.png) shows Thai attack/effect text, set code AS5a, regulation C, 117/184, RR and Mitsuhiro Arita. The Thai graph has no matching release at this pass's recorded graph hash. This is an additional admission candidate, not a new accepted printing or physical-finish confirmation.

This card was overlooked in the earlier contact-sheet triage. The earlier audit's four-candidate result was not exhaustive: there are now **five image-backed Thai admission candidates across the PDF research**: AS1b 112/150, AS5a 117/184, AS5a 203/184, AS5a 204/184 and sc1b T 165/153. The new crop uses the original PDF's actual retrieval timestamp and hash; the file was not re-downloaded or given a new retrieval date.

## Two additional leads needing exact Thai images

| Proposed identity | Located sources | Evidence boundary / next step |
|---|---|---|
| AS5D 118/169, Eevee & Snorlax-GX | [OjamaCard exact product](https://ojamacard.com/product/22143/118-169-%E0%B8%AD%E0%B8%B5%E0%B8%A7%E0%B8%B8%E0%B8%A2-%E0%B8%84%E0%B8%B2%E0%B8%9A%E0%B8%B4%E0%B8%81%E0%B8%AD%E0%B8%99-gx-as5d), [eBay item 127877826164](https://www.ebay.com/itm/127877826164), [Efour collector guide](https://www.elitefourum.com/t/collectors-guide-to-eevee-cards-in-all-languages/62616) | Seller/search text and collector-table lead. No inspected exact Thai card image; no admitted rarity or finish. Obtain the actual front. |
| AS5a 222/184, Eevee & Snorlax-GX | [Efour collector guide](https://www.elitefourum.com/t/collectors-guide-to-eevee-cards-in-all-languages/62616) | The guide lists Thai alongside Traditional Chinese. This is not enough to transfer a Chinese image or printing to Thai. Obtain an exact Thai image or localized official record. |

Neither identity has a matching Thai release in the inspected graph. The guide also repeats the already-known Thai 083/SM-P promo; it is not a new discovery. Its rarity/finish and distribution statements remain source claims, not physical observations.

The [official AS5D product page](https://asia.pokemon-card.com/th/archive/card/sun_moon_series/gx_starter_deck_5d.html) is readable. All five linked card examples were inspected: they depict other cards. They provide product context but do not establish Snorlax 118/169. This is no absence claim. Direct OjamaCard access failed certificate hostname verification on both bare and www hosts; eBay item retrieval returned 403. Certificate checks and access controls were not bypassed. Indexed offers and feedback references were not presented as inspected item photographs.

## Better retained evidence for existing entries

- **s8b source discrepancy extends to the online image:** [official detail 2468](https://asia.pokemon-card.com/th/card-search/detail/2468/) states **126/184**, while its [linked image](official-2468.png) prints **s8b T 126/158**, with Narumi Sato's standing Snorlax illustration. The earlier PDF also printed 126/158, but showed a different illustration. Keep these distinct publisher artifacts and the discrepancy; do not create an s8b 126/158 release or replace the existing identity/artwork automatically.
- **Shiny Snorlax sv4a T 310/190 S:** [official detail 8631](https://asia.pokemon-card.com/th/card-search/detail/8631/) supplies a [readable Thai image](official-8631.png) with the exact number and S rarity. The patterned depiction is an official render, not an inspected physical surface. The existing physical-finish gap remains.
- **MA6 T 121/130:** [official detail 14840](https://asia.pokemon-card.com/th/card-search/detail/14840/) supplies a [Thai render](official-14840.png) with regulation J, Aya Kusube credit and the 30th-anniversary Pikachu emblem. No rarity letter is readable beside the number; no rarity value is inferred from that omission. The previously retained product announcement schedules release for 2026-09-16, still after this pass. An available preview does not prove cards have shipped.
- **MA3 T 136/193:** the official site exposes [ordinary depiction 13046](official-13046.png), [Poké Ball depiction 13749](official-13749.png) and [Colorless Energy star depiction 13750](official-13750.png). Three distinct source images share one printed identity. These correspond to existing research/catalogue coverage and are not three newly discovered cards; no new physical-finish verdict is added.
- The 26-result official name query also contains **Snorlax Doll, SV4K 059/066**, a Trainer item. Its name match does not make it a Snorlax Pokémon release. The result count is a bounded current query, not all historical Thai cards.

## Retention and status

[page-captures.json](page-captures.json) retains actual fetch timestamps, full-response hashes, exact relevant HTML excerpts and separately labelled excerpt hashes. Full HTML responses remain ignored cache only. [image-captures.json](image-captures.json) records six original official PNGs and the derived PDF crop, including original source provenance and image hashes. [observations.json](observations.json) contains all 26 parsed official details, the comparison graph hash, the additional candidate and the two qualified leads. The existing official detail parser was reused without modifying it.

Validation: all seven retained image hashes, all JSON records, both list pages / 26 unique detail identities, and the three proposed identities' lack of matching Thai graph nodes were checked. This is a research-only write; no generated catalogue files changed. Existing #262 audit remains **13/28 gap-free**, with **15 unresolved releases**, plus the separately tracked admission candidates. **PR #383 stays a draft.** Next prioritize source-first admission of AS5a 117/184 and readable Thai fronts for AS5D 118/169 / AS5a 222/184; physical-finish evidence for the existing 15-release queue remains separate work.

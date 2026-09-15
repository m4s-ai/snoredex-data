<!-- doc: role=multilingual official set-list research and source triage; stage=reference -->

# Official set lists beyond Thai — 2026-09-15

Follow-up requested by the owner after the [Thai PDF audit](../issue-262-pdf-audit-20260915/README.md), retained in draft PR #383. This is a bounded multilingual source survey, not a completed all-language/all-set catalogue. No canonical card, rarity, finish or absence claims are changed.

## Results by language and market

| Language / market | Located source | Review status |
|---|---|---|
| Traditional Chinese — Taiwan | 24 reachable set-list PDF links from product pages | SC1b downloaded and visually triaged, page 19 inspected closely |
| Traditional Chinese — Hong Kong | 25 reachable set-list PDF links from product pages | SC1b downloaded; byte-identical to Taiwan file |
| Indonesian | 20 reachable set-list PDF links from product pages | SC1b downloaded and visually triaged, page 19 inspected closely |
| English | 4 official PDFs: XY2, SM9, SWSH1, PAR | Parsed and visually triaged |
| German | 4 official PDFs: XY2, SM9, SWSH1, PAR | Parsed and visually triaged; SWSH1 enlarged and retained |
| French | 4 official PDFs: XY2, SM9, SWSH1, PAR | Parsed and visually triaged |
| Italian | 4 official PDFs: XY2, SM9, SWSH1, PAR | Parsed and visually triaged |
| Spanish — Spain website assets | 4 official PDFs: XY2, SM9, SWSH1, PAR | Parsed and visually triaged; no Latin-American printing inference |
| Japanese | [Official card search](https://www.pokemon-card.com/card-search/) | Search interface retrieved; no set-list PDF located in this pass; result pagination not collected |
| Korean | [Official card search](https://pokemoncard.co.kr/cards) | Web reader shows search interface; direct retrieval returned HTTP 410; no PDF located |
| Simplified Chinese | [Official member card-search announcement](https://www.pokemon.cn/tcg/other/17199.html) and [collection-tool announcement](https://www.pokemon.cn/tcg/other/19154.html) | Announcements retained as source leads; mini-program content not accessed |
| Portuguese — Brazil | Official expansion pages and eight filename probes | No PDF verified: probes returned 404; expansion pages returned unusable iframe wrappers |
| Russian | [Official SM3 card-translation PDF](https://assets.pokemon.com/assets/cms2-ru-ru/pdf/trading-card-game/tcg_sun_moon_3_card_translation.pdf) | 53 pages parsed; first page inspected to classify it as a translation, not physical-print evidence |
| Dutch / Polish | Targeted web search | No official localized set-list PDF located in this pass; no absence claim |

The Asian sweep followed **303 distinct product-page URLs**, all retrieved successfully, from the Taiwan, Hong Kong and Indonesian product indexes. It found **71 PDF links**. Two Classic preorder retailer lists were excluded, leaving **69 reachable set-list links**. This is a URL count, not a count of unique PDF contents or unique expansions. Only three Asian PDFs have been downloaded and content-reviewed in this increment; the other 66 remain explicit content-review work.

The western probes establish **20 actual PDFs in five languages**, four selected sets each. File signatures, parsing and localized page titles were checked; a guessed URL alone was never accepted. These samples span XY, Sun & Moon, Sword & Shield and Scarlet & Violet, but the western search does not yet enumerate every set.

## Useful observations and traps

- **Localized rarity/finish keys:** the German SWSH1 PDF marks Relaxo **140** with Standardset and Parallelset boxes; Relaxo-V **141 / 197** and Relaxo-VMAX **142** have Holografisches Standardset boxes. The full page and its own legend are [retained](de-swsh1-page1.png). These are exact publisher checklist statements, not a universal mapping from rarity to foil pattern or distribution variant. Existing capability scope must be reviewed before admitting a claim from another checklist document.
- **Indonesian SC1b:** page 19 shows **Snorlax V 165/153 SR**, with Indonesian attack/effect text ([crop](id-sc1b-165.png)). The English species name does not make the card English.
- **Traditional Chinese SC1b:** page 19 shows **卡比獸V, sc1b F 165/153 SR** ([crop](tw-sc1b-165.png)). Taiwan and Hong Kong downloads have the identical SHA-256 `18ce453324fda3a91686aabf4711d99f96a1e751ae4a3312f50ae34951512b5b`; they are not independent corroboration and do not create a separate language.
- **Substring false positive:** PAR 175 is Snorlax Doll / Relaxo-Puppe / localized equivalent, a Trainer item. The text hit must not become a Snorlax Pokemon release.
- **Extraction false negative:** SM9 extracts no Snorlax name match in these files, but the visual lists include Eevee & Snorlax-GX / localized equivalents at **120 and 171**. Missing text matches never prove absence.
- **Partial lists:** SWSH1 ends at 202; the inspected checklist is not evidence that higher secret numbers do not exist. Keep the exact document boundary.
- **Russian translations:** the retained [example page](ru-translation-example.png) contains English and Russian card text side by side, with numbers and rarity. It supports translation content only; it does not establish physical Russian printing. The remaining 52 pages were not visually audited.
- **Simplified-Chinese variant lead:** the official announcement dated 2025-11-25 describes collection albums that track differing foil patterns and let users view styles under a card number. That makes the mini-program a promising exact-variant source, but this pass inspected the announcement only. It confirms no individual Snorlax variant.

## Verified western PDF links

| Language | XY2 | SM9 | SWSH1 | PAR |
|---|---|---|---|---|
| en | [PDF](https://assets.pokemon.com/assets/cms2/pdf/trading-card-game/checklist/xy2_web_cardlist_en.pdf) | [PDF](https://assets.pokemon.com/assets/cms2/pdf/trading-card-game/checklist/sm9_web_cardlist_en.pdf) | [PDF](https://assets.pokemon.com/assets/cms2/pdf/trading-card-game/checklist/swsh1_web_cardlist_en.pdf) | [PDF](https://assets.pokemon.com/assets/cms2/pdf/trading-card-game/checklist/par_web_cardlist_en.pdf) |
| de | [PDF](https://assets.pokemon.com/assets/cms2-de-de/pdf/trading-card-game/checklist/xy2_web_cardlist_de.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-de-de/pdf/trading-card-game/checklist/sm9_web_cardlist_de.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-de-de/pdf/trading-card-game/checklist/swsh1_web_cardlist_de.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-de-de/pdf/trading-card-game/checklist/par_web_cardlist_de.pdf) |
| fr | [PDF](https://assets.pokemon.com/assets/cms2-fr-fr/pdf/trading-card-game/checklist/xy2_web_cardlist_fr.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-fr-fr/pdf/trading-card-game/checklist/sm9_web_cardlist_fr.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-fr-fr/pdf/trading-card-game/checklist/swsh1_web_cardlist_fr.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-fr-fr/pdf/trading-card-game/checklist/par_web_cardlist_fr.pdf) |
| it | [PDF](https://assets.pokemon.com/assets/cms2-it-it/pdf/trading-card-game/checklist/xy2_web_cardlist_it.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-it-it/pdf/trading-card-game/checklist/sm9_web_cardlist_it.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-it-it/pdf/trading-card-game/checklist/swsh1_web_cardlist_it.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-it-it/pdf/trading-card-game/checklist/par_web_cardlist_it.pdf) |
| es | [PDF](https://assets.pokemon.com/assets/cms2-es-es/pdf/trading-card-game/checklist/xy2_web_cardlist_es.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-es-es/pdf/trading-card-game/checklist/sm9_web_cardlist_es.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-es-es/pdf/trading-card-game/checklist/swsh1_web_cardlist_es.pdf) | [PDF](https://assets.pokemon.com/assets/cms2-es-es/pdf/trading-card-game/checklist/par_web_cardlist_es.pdf) |

## Reachable Asian set-list queue

The source product-page URL and exact PDF-link HTML fragment are retained in `asian-product-pages.json`. Transport results and excluded retailer lists are in `asian-pdf-availability.json`. Spaces and non-ASCII characters are URL-encoded below.

| Market | PDF | Content review |
|---|---|---|
| HK | [AS5a.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/AS5a.pdf) | Pending; HEAD reachability only |
| HK | [AS5b.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/AS5b.pdf) | Pending; HEAD reachability only |
| HK | [AS6a.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/AS6a.pdf) | Pending; HEAD reachability only |
| HK | [AS6b.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/AS6b.pdf) | Pending; HEAD reachability only |
| HK | [Booster-2A.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/Booster-2A.pdf) | Pending; HEAD reachability only |
| HK | [Booster-2B.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/Booster-2B.pdf) | Pending; HEAD reachability only |
| HK | [Booster-A.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/Booster-A.pdf) | Pending; HEAD reachability only |
| HK | [Booster-B.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/Booster-B.pdf) | Pending; HEAD reachability only |
| HK | [CH-S4.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/CH-S4.pdf) | Pending; HEAD reachability only |
| HK | [S4a.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/S4a.pdf) | Pending; HEAD reachability only |
| HK | [S5I.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/S5I.pdf) | Pending; HEAD reachability only |
| HK | [S5R.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/S5R.pdf) | Pending; HEAD reachability only |
| HK | [S5a_9ups_in-number.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/S5a_9ups_in-number.pdf) | Pending; HEAD reachability only |
| HK | [S6H-Chinese-SR.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/S6H-Chinese-SR.pdf) | Pending; HEAD reachability only |
| HK | [S6K-Chinese-SR.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/S6K-Chinese-SR.pdf) | Pending; HEAD reachability only |
| HK | [S6a_9ups_in-number.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/S6a_9ups_in-number.pdf) | Pending; HEAD reachability only |
| HK | [SC1_Set_A.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/SC1_Set_A.pdf) | Pending; HEAD reachability only |
| HK | [SC1_Set_B.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/SC1_Set_B.pdf) | SC1b sample reviewed |
| HK | [SC2_Set_A.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/SC2_Set_A.pdf) | Pending; HEAD reachability only |
| HK | [SC2_Set_B.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/SC2_Set_B.pdf) | Pending; HEAD reachability only |
| HK | [s7_a.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/s7_a.pdf) | Pending; HEAD reachability only |
| HK | [s7_b.pdf](https://asia.pokemon-card.com/hk/archive/card/pdf/s7_b.pdf) | Pending; HEAD reachability only |
| HK | [cardlist1.pdf](https://asia.pokemon-card.com/hk/archive/special/card/family_game/pdf/cardlist1.pdf) | Pending; HEAD reachability only |
| HK | [cardlist2.pdf](https://asia.pokemon-card.com/hk/archive/special/card/family_game/pdf/cardlist2.pdf) | Pending; HEAD reachability only |
| HK | [cardlist3.pdf](https://asia.pokemon-card.com/hk/archive/special/card/family_game/pdf/cardlist3.pdf) | Pending; HEAD reachability only |
| ID | [1st_Cardlist_SetA.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/1st_Cardlist_SetA.pdf) | Pending; HEAD reachability only |
| ID | [1st_Cardlist_SetB.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/1st_Cardlist_SetB.pdf) | Pending; HEAD reachability only |
| ID | [AC3_setA.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/AC3_setA.pdf) | Pending; HEAD reachability only |
| ID | [AC3_setB.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/AC3_setB.pdf) | Pending; HEAD reachability only |
| ID | [ID_SC1a_9ups.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/ID_SC1a_9ups.pdf) | Pending; HEAD reachability only |
| ID | [ID_SC1b_9ups.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/ID_SC1b_9ups.pdf) | SC1b sample reviewed |
| ID | [IND_2nd_SETA.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/IND_2nd_SETA.pdf) | Pending; HEAD reachability only |
| ID | [IND_2nd_SETB.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/IND_2nd_SETB.pdf) | Pending; HEAD reachability only |
| ID | [IND_3_SETA.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/IND_3_SETA.pdf) | Pending; HEAD reachability only |
| ID | [IND_3_SETB.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/IND_3_SETB.pdf) | Pending; HEAD reachability only |
| ID | [IND_4_SETA.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/IND_4_SETA.pdf) | Pending; HEAD reachability only |
| ID | [IND_4_SETB.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/IND_4_SETB.pdf) | Pending; HEAD reachability only |
| ID | [Indonesian SC3a.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/Indonesian%20SC3a.pdf) | Pending; HEAD reachability only |
| ID | [Indonesian SC3b.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/Indonesian%20SC3b.pdf) | Pending; HEAD reachability only |
| ID | [S5I.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/S5I.pdf) | Pending; HEAD reachability only |
| ID | [S5R.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/S5R.pdf) | Pending; HEAD reachability only |
| ID | [S6H-Indonesian.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/S6H-Indonesian.pdf) | Pending; HEAD reachability only |
| ID | [S6K-Indonesian.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/S6K-Indonesian.pdf) | Pending; HEAD reachability only |
| ID | [S6a_9ups_Indonesia.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/S6a_9ups_Indonesia.pdf) | Pending; HEAD reachability only |
| ID | [S6a_9ups_in-number.pdf](https://asia.pokemon-card.com/id/archive/card/pdf/S6a_9ups_in-number.pdf) | Pending; HEAD reachability only |
| TW | [AS5a.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/AS5a.pdf) | Pending; HEAD reachability only |
| TW | [AS5b.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/AS5b.pdf) | Pending; HEAD reachability only |
| TW | [AS6a.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/AS6a.pdf) | Pending; HEAD reachability only |
| TW | [AS6b.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/AS6b.pdf) | Pending; HEAD reachability only |
| TW | [Booster-2A.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/Booster-2A.pdf) | Pending; HEAD reachability only |
| TW | [Booster-2B.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/Booster-2B.pdf) | Pending; HEAD reachability only |
| TW | [Booster-B.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/Booster-B.pdf) | Pending; HEAD reachability only |
| TW | [CH-S4.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/CH-S4.pdf) | Pending; HEAD reachability only |
| TW | [S4a.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/S4a.pdf) | Pending; HEAD reachability only |
| TW | [S5I.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/S5I.pdf) | Pending; HEAD reachability only |
| TW | [S5R.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/S5R.pdf) | Pending; HEAD reachability only |
| TW | [S5a_9ups_in-number.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/S5a_9ups_in-number.pdf) | Pending; HEAD reachability only |
| TW | [S6H-Chinese-SR.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/S6H-Chinese-SR.pdf) | Pending; HEAD reachability only |
| TW | [S6K-Chinese-SR.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/S6K-Chinese-SR.pdf) | Pending; HEAD reachability only |
| TW | [S6a_9ups_in-number.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/S6a_9ups_in-number.pdf) | Pending; HEAD reachability only |
| TW | [SC1_Set_A.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/SC1_Set_A.pdf) | Pending; HEAD reachability only |
| TW | [SC1_Set_B.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/SC1_Set_B.pdf) | SC1b sample reviewed |
| TW | [SC2_Set_A.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/SC2_Set_A.pdf) | Pending; HEAD reachability only |
| TW | [SC2_Set_B.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/SC2_Set_B.pdf) | Pending; HEAD reachability only |
| TW | [s7_a.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/s7_a.pdf) | Pending; HEAD reachability only |
| TW | [s7_b.pdf](https://asia.pokemon-card.com/tw/archive/card/pdf/s7_b.pdf) | Pending; HEAD reachability only |
| TW | [cardlist1.pdf](https://asia.pokemon-card.com/tw/archive/special/card/family_game/pdf/cardlist1.pdf) | Pending; HEAD reachability only |
| TW | [cardlist2.pdf](https://asia.pokemon-card.com/tw/archive/special/card/family_game/pdf/cardlist2.pdf) | Pending; HEAD reachability only |
| TW | [cardlist3.pdf](https://asia.pokemon-card.com/tw/archive/special/card/family_game/pdf/cardlist3.pdf) | Pending; HEAD reachability only |

## Retention and next processing steps

Original PDFs, full HTML responses and contact sheets remain in ignored `verification/cache/multilang-pdf/`; a recorded original hash does not mean the original is retained in Git. Four selected derived PNGs are committed with source hashes, source retrieval timestamps, page/crop coordinates and excerpt hashes in `retained-excerpts.json`. Product-link HTML fragments and relevant source-announcement excerpts are retained separately from full-response hashes.

Next process the 66 Asian PDF links still awaiting content review, preserving market links and comparing hashes before counting mirrors separately. Expand the five western language inventories beyond the four sample sets; use each document’s legend rather than copying a rarity/finish assumption. Portuguese, Dutch, Polish and Japanese/Korean PDF coverage remain open research gaps. Do not use blank deck-registration forms, rules PDFs, retailer lists or translated gameplay aids as localized set manifests. No new normalized card or finish claim is admitted by this survey. **Keep PR #383 as a draft.**

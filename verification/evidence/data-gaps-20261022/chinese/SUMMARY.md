<!-- doc: role=retained research workstream report; stage=history -->

> Historical record — research snapshot from 2026-10-22; current gaps are determined by canonical stores.

# Chinese workstream (TW + CN) — 2026-10-22

Counts: 74 findings, 9 unresolved (every target covered).
- localSetName (37 targets): 33 found (TW 30, CN 3); 4 unresolved (CN sets with no local identifier).
  Confidence: 28 high, 5 medium (TW SM-P and CLF, CN CS2DaC/CS4DaC/CSVSC).
- illustrator, S-Chinese (46 targets): 41 found, 5 unresolved (`via-…` releases with no local set/number).
  All 41 use method `image-transcription` (ARTIST-RULE Method A) from the exact S-Chinese print image.
  34 of them are also visually matched to a same-artwork TW print whose official TW database credit agrees (Method B used as corroboration).
  Confidence: 34 high, 7 medium (credit soft in a 255px image and no anchor compared, or partial).

Best sources
1. asia.pokemon-card.com/tw card-search detail pages (`收錄商品` product label, collector number, `繪師`, card image).
   Search with `keyword=卡比獸`, pageNo 1-4 → 44 detail pages (raw/tw/).
2. Repository images of the exact S-Chinese print: owner specimens (verification/specimens/SPEC-*) and Cardmarket CN product
   scans (images/CS*C_*.png). The CN scans visibly show simplified text plus the CN set badge, so they are exact-print images.
3. www.pokemon.cn product pages (official CN site). Find them in `/post_products-sitemap.xml`. Only the title/heading text is
   machine-readable. The body is images and the local set code is not printed.

Conflicts and caveats
- TW SC1b 165/153 Snorlax V SR: the TW database text says 繪師 "Masakazu Fukuda", but the card image on the same page prints
  "Illus.aky CG Works". The CN print of the same artwork (CS1aC 188, SPEC-0098) also prints aky CG Works. Neither is used as a
  dataset value here; flag it for whoever imports TW illustrators.
- TW SVI's official label is printed "Trianers Camp" (typo on the source, kept verbatim).
- TW names are kept with their product-type prefix (擴充包「…」, V起始牌組 …). Stripping the prefix needs a reviewed rule.
- CLF: the Classic product page doesn't print the code. The TW card DB returns 0 cards for expansionCodes=CLF (a gap, not evidence of absence).
- CN set names rest on product identity (shared run size 053/414/066), not on a printed code. They're graded medium.
- CS5aC 093 "Saboteri", CSUC 010 "Kouki Saitou", CS2aC 142 "Saki Hayashiro", CSM2cC 171 "Tomokazu Komiya", CSVL1C 109 "GOSSAN"
  are alternate artworks with no compared anchor. They're medium and need a sharper image before promotion.

Dead ends
- www.pokemon.cn resets about 1 in 4 TLS connections through the proxy. Retrying works (tools/get.sh). wp-json returns 401. /tcg redirects.
- 52poke search does not index CN set codes (CS2DaC etc.) and is organised around Japanese products.
- Bulbapedia API returns 403 to scripts (known).

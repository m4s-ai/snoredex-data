<!-- doc: role=retained research workstream report; stage=history -->

> Historical record — research snapshot from 2026-10-22; current gaps are determined by canonical stores.

# id-th-sets — localSetName for Indonesian + Thai local sets (2026-10-22)

Targets: 50 (26 ID, 24 TH). Found: 48. Unresolved: 2 (ID SM-P, TH SM-P).

## How
- asia.pokemon-card.com/{id,th} card-search: keyword `Snorlax` (ID) / `คาบิกอน` (TH), then every
  Snorlax detail page. Each detail page carries a product link ("Ada di produk" / "รวมอยู่ในชุด")
  with `expansionCodes=<code>` and the official product name -> card-level identity (40 targets, high).
- Code-level only (card itself absent from the online DB; name from the official product filter
  in the search page, code matched to the local code minus locale suffix): ID AC3b (high, plus
  archive page AC3b.html), ID s5a I, ID s10a I, ID SV-P, TH s5a T, TH s10a T (medium).
- Thai SM era is absent from the current card search; used the official Thai archive product
  pages: AS5a = booster_pack_5a.html (high), AS1b = post_3.html linking BoosterPackB.pdf (medium,
  per repo's issue-262 PDF audit mapping BoosterPackB.pdf -> AS1b).

## Best sources
1. asia.pokemon-card.com/{id,th}/card-search/detail/<n>/ — product link per exact card.
2. Product filter (`productSelectorModal`) on /card-search/list/ — code -> name for every live set.
3. /th/archive/card/sun_moon_series/*.html and /{id,th}/archive/special/card/*/index.html.

## Caveats / flags
- TH AS1b name "การ์ดชุดเสริม (ชุด B)" is verbatim but generic: the same title is used for other SM
  waves (e.g. post_6 = AS2b). Consumers may need a qualifier.
- Possible duplicate local sets: ID "S10a I" vs "s10a I", TH "s10a" vs "s10a T" — both pairs map
  to official code S10a with the same name. Not merged; flag for reconciliation.
- Secret rares (s5a 093 UR, s10a 077 CHR, AC3b 238/239 SR) and ID SV-P 117/278/286 are not in the
  online DB listings; their set names rest on code, not the card.
- TH sv4a name has a double space in source HTML; collapsed to one.
- Translations are mine, marked "translation:".

## Dead ends
- Bulbapedia API: 403 (Cloudflare) from curl, as RESUME.md predicts.
- /th/archive/card/sun_moon_series/booster_pack_1b.html: 404 (AS1b lives at post_3.html).
- No SM-P promo entry in either locale's filter or the Thai SM archive index.

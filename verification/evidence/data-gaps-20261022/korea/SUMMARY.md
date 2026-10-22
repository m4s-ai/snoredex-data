<!-- doc: role=retained research workstream report; stage=history -->

> Historical record — research snapshot from 2026-10-22; current gaps are determined by canonical stores.

# Workstream "korea": summary (2026-10-22)

## Counts
- Set names (41 targets): 40 found, 1 unresolved (`LOCALSET:KR:S-P`).
  - High: 31 (32 official Pokémon Korea catalogue product strings plus the 20th publisher teaser, minus xsv2a/xm2a, which are medium)
  - Medium: SM-P (series label taken from a combined product string), xsv2a, xm2a (Cardmarket parallel groupings),
    s5a (Bulbapedia index), CLF (Bulbapedia ko= line via repo record), SVP LA and SVP ES (pokemon.com via WebFetch, bytes not retained)
- Illustrators (26 card releases): 26 found, 0 unresolved.
  - image-transcription: 23 (18 official Pokémon Korea CDN images; 20th TCGBOX scan; s1H 070 and s5a 093 Bunjang photos; CLF 016 eBay photo; xsv2a from the official mirror image)
  - artwork-propagation: 2 (sm9 115 HR anchored on the official sm9 106 SR; xm2a anchored on the official m2a 136)
  - database-credit: 1 (DP 006 "SHizURow"; the official image is too small to read the credit)

## Best sources
1. Official image CDN `cards.image.pokemonkorea.co.kr/data/wmimages/...` is reachable by curl (HTTP 200). Full-size
   868x1212 PNGs show "Illus. NAME" plus the set mark and number clearly. It returns 415 for paths that do not exist.
2. Repo-retained official catalogue observation `verification/evidence/pokemon-korea-snorlax-catalogue-20260901.json`
   (pokemoncard.co.kr rows with product name and illustrator for 45 Korean Snorlax prints). Every credit read from an image agrees with it.
3. Official publisher graphic `20TH_teaser_B_2.jpg` (repo copy), which gives the 20th product name.

## Important observation
Most of these values already sit in the repo's official Korean catalogue evidence (product and illustrator fields)
but were never projected into `localSetName` and `artist`. This looks like a projection gap, not a research gap.
No finding conflicts with an existing dataset value, because every target field is null. One wording difference: older repo notes
call the 20th product "트레이너 세트 20th", while the official teaser prints "포켓몬 카드 게임 XY BREAK 트레이너 세트 20TH ANNIVERSARY".

## Dead ends (2026-10-22)
- pokemoncard.co.kr: HTTP 503 for curl and WebFetch.
- web.archive.org: connection reset. archive.org availability API: 429.
- collectory.cc: 403 with a Korean notice that scraping is prohibited by its terms; it offers a paid API key. Not used.
- Bulbapedia: 403 for curl and WebFetch.
- pokemon.com: 403 for curl; WebFetch works, so the page bytes could not be retained.
- marketplace-article-scans.s3.cardmarket.com: 403.
- Guessed official image paths for sm9 115, s1H 070 and s5a 093 returned 415. Those cards were covered from seller photos instead.

## Caveats
- The xsv2a and xm2a credits apply to every V-token through the same-artwork rule. No V-token meaning was assigned.
- sm9 115 HR is propagated from the 106 SR because it is the rainbow recolour of the same composition. A reviewer may want this as a separate artwork.
- S-P: the official row (SP000000101) gives only a distribution string, not a series name.
  Next lead: the product dropdown on pokemoncard.co.kr, read in a browser session.

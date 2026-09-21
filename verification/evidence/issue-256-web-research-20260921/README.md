# Research follow-up for #256 — 2026-09-21

Draft implementation for #256, #258 and the current Korean gaps documented in #260. Keep this PR as a draft until the next research round is complete; no merge or issue closure is authorized by this checkpoint. Baseline: merged main 899688c. Seven official product/date pages address ten current release-date gaps (eight KR, two ID). The seven regular-launch statements are mapped only to the ten already established card releases listed in sources.json. Physical identity, finish, rarity and special-edition dates are unchanged.

| Market | Set / cards | Regular release | Source |
|---|---|---|---|
| KR | s10a 058/071, 077/071 | 2022-07-22 | [Publisher](https://pokemoncard.co.kr/card/447) |
| KR | sv2a 143/165, 181/165 | 2023-07-28 | [Publisher](https://new.pokemonkorea.co.kr/card/551) |
| KR | sv4a 145/190, 310/190 | 2024-01-26 | [Publisher](https://new.pokemonkorea.co.kr/card/601) |
| KR | sv5a 051/066 | 2024-05-24 | [Publisher](https://pokemoncard.co.kr/card/636) |
| KR | s8b 126/184 | 2022-01-26 | [Publisher](https://new.pokemonkorea.co.kr/card/401) |
| ID | s5a I 093/070 | 2021-07-02 | [Publisher](https://asia.pokemon-card.com/id/card-search/?pageNo=4) |
| ID | s10a I 077/071 | 2022-08-26 | [Publisher](https://asia.pokemon-card.com/id/card-search/?pageNo=3) |

## Scope and conflicts

- sv2a: Do not automatically transfer to xsv2a catch-up identities.
- sv4a: Separate card-shop advance sale: 2024-01-20.
- sv5a: Separate card-shop advance sale: 2024-05-18.
- s8b: Do not use the 2022-02-03 album/accessory release.
- s5a I: Month-day-year listing; AKG product index independently displays 02 July 2021.
- s10a I: Official campaign https://asia.pokemon-card.com/id/archives/2051/ explicitly coincides with product release. Product article /id/archives/1806/ only says late August. AKG lists August 1; retain discrepancy, prioritize precise publisher date.

## Marketplace follow-up

Thai s10b 056/071 Shopee 412643607/25102563945 and OjamaCard product 28693 were already retained in earlier research: no new evidence counted. OjamaCard direct retrieval timed out; its indexed product title is not a finish observation. Thai s10a 058/071 Ojama category 725 lists rarity R, but supplies no inspected physical-finish proof in this pass. Spanish XY179 shop language/finish selectors are not a card-specific existence proof; English-only listings and Japanese cards offered by Thai sellers were excluded.

## Implementation and next research round

Apply the regular dates through set_catalogue_sources.json and the reviewed graph, with two URL-bounded date-only capability surfaces. Earlier Korean advance-sale announcements remain separate research notes and are not asserted as inspected physical distribution events. Preserve excerpt hashes; these are hashes of selected text fragments, not full HTTP responses. No newly verified physical finish resulted from this batch.

Continue with the remaining Korean date gaps, Thai physical evidence and staged Thai/Indonesian/Traditional-Chinese admission candidates already retained by #383. Prior findings stay in their existing evidence directories rather than being copied. Recompute issue counters only after validation, and distinguish this draft from merged main.

## Draft impact versus merged main

- Ten release-date gaps addressed across 14 existing catalogue items.
- Indonesian tracked-field status: 7/47 to 9/47 gap-free.
- Korean tracked-field status: 3/52 to 5/52 gap-free; six of the eight date-enriched releases still need other fields.
- Overall remaining releases: 163 to 159 (641 canonical releases unchanged).
- Item IDs, release IDs, physical printing IDs, Work mappings, finishes, rarities, editions and all 447 assets are unchanged. Only releaseDate, releaseDatePrecision and releaseSortKey change on the 14 items.
- These are draft results, not merged issue completion. Baseline full check passed; validation.json records the field-level comparison and excerpt hashes.

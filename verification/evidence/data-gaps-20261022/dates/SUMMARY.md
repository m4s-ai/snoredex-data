<!-- doc: role=retained research workstream report; stage=history -->

> Historical record — research snapshot from 2026-10-22; current gaps are determined by canonical stores.

# Dates workstream: summary (2026-10-22)

Targets: 53 items (48 card releases). **Found: 5 items with a new day-precision date. Unresolved: 48 items** (in 25 groups, plus the Italian Staff item c3adb9ce). Every target appears in `findings.json`.
The per-group sources live in `entries/*.json`. `dates_tools/build.py` turns them into `findings.json` and recomputes the sha256 of each retained file in `raw/`.

## Findings
| Target | Date | Source | Confidence |
|---|---|---|---|
| SWSH 068 FR (46088019) | 2020-10-31 | pokemon.gamespress.com/fr Vivid Voltage media alert, 28/08/2020: "Dès le 31 octobre … Boîtier Stratégies et Combats" | high |
| SWSH 068 DE (b119074a) | 2020-10-31 | gamespress /de: "Build & Battle-Box … ab dem 31. Oktober" | medium |
| SWSH 068 IT ordinary (5268bc9b) | 2020-10-31 | gamespress /it: "kit Sfida Strategica … a partire dal 31 ottobre" | medium |
| SWSH 068 ES (939a0c46) | 2020-10-31 | gamespress /es: "caja de Combina y Combate … a partire del 31 de octubre" | medium |
| S-P/CS 061 CN (bbea2621) | 2023-08-19 | pokemon.cn/tcg/event/16155.html, the second wave of 大有可玩 (2023-08-19 to 08-20) with a random promo pack; 061 is tied to this campaign by the 52poke row retained from the previous round | medium |

**Conflict with existing data:** all four SWSH 068 items currently hold `2020-11` at month precision. The official localized releases put the Build & Battle box on sale on 31 Oct 2020, so the month changes too, not only the precision. The English sibling already uses 2020-10-31.
Caveat: a logo-stamped Cosmos-holo SWSH 068 retail giveaway started on 13 Nov 2020. That is a different printing. Confirm that these targets are the plain Build & Battle promo.
CN 061 currently holds year 2023, which is consistent. The new date is earlier than the Shenyang (08-27) and Shenzhen (09-16) distributions retained earlier.

## Best sources this round
1. pokemon.gamespress.com and press.pokemon.com, the TPCi press sites. Both expose `/<lang>/Search/PressReleases?searchText=` and a per-product `Items/FetchTabContent` POST (see `dates_tools/gplist.sh` and `gpsearch.sh`). The localized releases carry dates for Build & Battle and prerelease availability.
2. pokemon.cn/tcg/?keyword= search, which was reachable this time (it returned 503 in the earlier rounds), with dated event articles and promo galleries.
3. The Poképédia, WikiDex and PokéWiki MediaWiki APIs, used for product identity (no dates were found for the remaining products).

## Dead ends and blockers (new)
- web.archive.org and wayback.archive.org were reset by the proxy on every attempt. The archive.org availability API works, but the content does not load. Several next leads depend on Wayback, for example the Devir Brazil "Selva" capture of 2000-12-13.
- Pokémon Central wiki: `api.php` parse and revisions calls get a Cloudflare 403. List search works, and WebFetch of the rendered page works.
- Bulbapedia: 403 to scripts (known).
- The wog.ch search is JS-rendered and returns no Pokémon products.
- asia.pokemon-card.com/id has no WP REST API or sitemap; the TH and TW info archives start in mid or late 2020.
- None of the gamespress or pt-BR releases names the Snorlax 3-pack blisters (SWSH 119, SVP 122) or the TAG TEAM tin (SM 169).
- The pt-BR Vivid Voltage release gives no date for the "Desafio Estratégico" (note: 8 boosters), so the European 31 Oct cannot be used for PT.

## Leads worth pursuing
- ae2013d0 (JU 27 PT): a community thread cites an archived Devir Brazil page reading "Pokémon Jungle Release (Selva in Portuguese) - 17h20 21/08/2000". Verify it in the Wayback capture before using it.
- SVP 184 Staff (5 items): a Staff-kit distribution record is needed; the 15 Mar 2025 prerelease start is only a lead.
- SWSH 119 and SVP 122 DE/ES/IT/PT, SWSH 032 ES/IT/PT, WCD23 DE/FR/IT: retailer listings that show an explicit release field, following the wog.ch precedent.

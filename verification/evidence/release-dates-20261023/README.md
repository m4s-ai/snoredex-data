<!-- doc: role=retained release-date research evidence and intake report; stage=history -->

> Historical record — research snapshot from 2026-10-23; current dates are determined by canonical stores.

# Day-precision release-date research — 2026-10-23

On 2026-10-23, 50 catalogue items had a release date with only month or year precision. Four workstreams searched for a market-specific day:
[japan](japan/), [asia-promos](asia-promos/), [west-promos](west-promos/) and [west-special](west-special/).
[findings.json](findings.json) records the outcome for every item: either a sourced value, or the attempts made and the next lead.
An unsuccessful search establishes no absence.

| Outcome | Items |
|---|---:|
| Day date applied | 9 |
| Month corrected (no day established) | 1 |
| Unresolved, current value kept | 40 |

A date is applied only for the market its source names. It must be the availability or debut date that source states. It is never borrowed from another language, channel or edition, and it is never a production date.

## Applied

[`integrate_release_date_research_20261023.py`](../../passes/integrate_release_date_research_20261023.py) appends these rows to `confirmed_release_overrides.json`. It also declares one date-only capability surface per provider.

| Item | Was | Now | Source |
|---|---|---|---|
| KR S-P 101 Snorlax | 2021 | 2021-05-01 | Official Pokémon Korea notice for the online-shop campaign. |
| KR SM-P 140 Eevee & Snorlax-GX (holo row and finish-unresolved row) | 2019 | 2019-03-20 | Official Night Unison product page: the Pokémon Store Online start. Card shops followed on 2019-03-23. |
| ES PPS3 LOR 143 | 2023-06 | 2023-08-14 | Official es-ES pokemon.com article on Prize Pack Series 3. |
| DE SVP 122 | 2024 | 2024-05-24 | Kartenbasis release field for the 3-pack blister, Relaxo variant. |
| IT SVP 122 | 2024 | 2024-05-24 | MyComics release field. lppcollecting.it gives the same day. |
| IT SWSH 032 | 2020-05 | 2020-06-05 | MyComics release field for the Snorlax pin collection. |
| FR WCD23 LOR 143 | 2023-11 | 2024-03-01 | Micromania release field. |
| DE WCD23 LOR 143 | 2023-11 | 2024-03-01 | PokéZentrum German release calendar. |
| IT WCD23 LOR 143 | 2023-11 | 2024-03 | Sodip gives the month. Its planned day conflicts with AndyCards. |

**World Championships Decks 2023.** The official German, French and Italian product pages all date the four-deck line to Q1 2024. That contradicts the Cardmarket expansion month 2023-11, which the catalogue carried until now. The retained official pages are cited only as context, because a quarter is not a day.

Five tier-3 date-only providers are new: `kartenbasis`, `mycomics`, `micromania`, `sodip` and `pokezentrum`. They follow the `wog` precedent: a retailer field dates only that retailer's named product.

## Unresolved leads worth the next session

- **KR XY-P 167:** articles from 2016-10-13 describe the Lotte Foods Kisstick campaign, so the current year 2017 is doubtful.
- **ID S-P 030:** the promo may date from the 2020-11-21 set launch.
- **FR SM 169:** every source places the King Jouet Pokébox in spring 2019, so the current 2019-02 looks too early.
- **DE SWSH 119:** 2021-06-18 is likely, but no source for it could be retained.

## Retention

`findings.json` lists every retained file in its `retention` block, with `sha256` of the committed bytes.
For 23 HTML pages, line endings were normalized to LF to satisfy check `X1`. Those entries also keep the `originalSha256` of the file as fetched.
Where a CDN blocked plain fetches, `captureForm` records that the file is the DOM serialized by headless Chromium.

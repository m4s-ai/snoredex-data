# Bulbapedia release-date audit — 2026-07-31

The read-only audit fetched all 214 pages in Bulbapedia's Pokémon TCG expansion category, then
added the product and Asian-language pages already cited by this repository. It compared 133
represented set-code/name pairs by article title, `setname`, `transsetname`, and reviewed aliases.

- 106 set/product pages now agree exactly with the generated data.
- 45 prior values differed and were corrected below.
- 6 product pages require manual interpretation because they omit a release field or give only a
  partial date. Their existing product-specific dates were not overwritten.
- 21 represented entries have no directly corresponding Bulbapedia set-release page; these are
  chiefly promo series, Cardmarket “Additionals” groupings, and card-specific campaigns.

Run `python verification/archive/passes/audit_bulbapedia_release_dates.py` to repeat the live comparison.
The reviewed source records consumed by the generator are in
`verification/bulbapedia_release_dates.json`.

| Set code | Previous | Corrected | Bulbapedia page / field |
|---|---:|---:|---|
| PJU | 1997-03 | 1997-03-05 | Jungle (TCG) / `jarelease` |
| G2 | 1999 | 1999-06-25 | Gym Challenge (TCG) / `jarelease` |
| EC5 | 2002 | 2002-10-04 | Skyridge (TCG) / `jarelease` |
| PCG1 | 2004 | 2004-04-09 | EX FireRed & LeafGreen (TCG) / `jarelease` |
| FL | 2004-09-01 | 2004-08-30 | EX FireRed & LeafGreen (TCG) / `enrelease` |
| PCG3 | 2004 | 2004-10-15 | EX Team Rocket Returns (TCG) / `jarelease` |
| TRR | 2004-11-01 | 2004-11-08 | EX Team Rocket Returns (TCG) / `enrelease` |
| PCG9 | 2006 | 2006-06-29 | EX Dragon Frontiers (TCG) / `jarelease` |
| DF | 2006-11-01 | 2006-11-08 | EX Dragon Frontiers (TCG) / `enrelease` |
| DP1 | 2006-10 | 2006-11-30 | Diamond & Pearl (TCG) / `jarelease` |
| DP | 2007-05-01 | 2007-05-23 | Diamond & Pearl (TCG) / `enrelease` |
| Pt2 | 2009-03 | 2008-12-26 | Rising Rivals (TCG) / `jarelease` |
| LL | 2010 | 2010-04-16 | Lost Link (TCG) / `date` |
| HSZ | 2012 | 2012-04-20 | National Beginning Set (TCG) / `release` |
| BW7 | 2012 | 2012-09-14 | Plasma Storm (TCG) / `jarelease` |
| HXY | 2013-12 | 2013-11-08 | Kalos Starter Set (TCG) / `jarelease` |
| XY2 | 2014-03 | 2014-03-15 | Flashfire (TCG) / `jarelease` |
| 20th | 2016-09 | 2016-02-27 | Generations (TCG) / `jarelease` |
| XY10 | 2016-03 | 2016-03-18 | Fates Collide (TCG) / `jarelease` |
| smL | 2018 | 2019-03-15 | Sun & Moon Family Pokémon Card Game (TCG) / `release` |
| BA20 | 2020-06 | 2020-06-21 | Battle Academy 2020 (TCG) / `release` |
| CSM1cC | 2025 | 2022-10-28 | Storming Emergence (ATCG) / `release` |
| CSM2bC | 2025 | 2023-01-18 | Shining Synergy (ATCG) / `release` |
| CSM2cC | 2025 | 2023-01-18 | Shining Synergy (ATCG) / `release` |
| CSM2DC | 2025 | 2023-01-18 | Shining Synergy GX Starter Deck (ATCG) / `release` |
| CSMPC | 2025 | 2023-04-15 | Battle Party Set (ATCG) / `release` |
| CS1DC | 2023 | 2023-05-19 | Dynamax Clash V Starter Deck (ATCG) / `release` |
| CSAC | 2023 | 2023-05-19 | Dynamax Clash Deck Building Gift Box (ATCG) / `release` |
| CS2aC | 2024 | 2023-08-18 | Vivid Portrayals (ATCG) / `release` |
| CSM2.1C | 2025 | 2023-09-09 | Golden Energy (ATCG) / `date` |
| CS3DC | 2024 | 2023-11-17 | Primordial Arts V Starter Deck (ATCG) / `release` |
| CS5aC | 2025 | 2024-06-18 | Gallant Galaxy (ATCG) / `release` |
| CS5DC | 2025 | 2024-06-18 | Gallant Galaxy V Starter Deck (ATCG) / `release` |
| svLN | 2024 | 2024-08-30 | Stellar Tera Type Starter Sets (TCG) / `release` |
| CS6bC | 2025 | 2024-09-20 | Marine Shadow (ATCG) / `release` |
| CSUC | 2025 | 2024-10-26 | Pokémon Card Display Set Gift Box Vol. 3 (ATCG) / `release` |
| CSZC | 2025 | 2024-11-15 | Peripheral Collection Gift Box: Variety Treasure Box (ATCG) / `release` |
| CSVH1C | 2025 | 2025-01-17 | Pikachu & Clefairy & Turtwig & Gimmighoul Happy Set (ATCG) / `release` |
| CSVL1C | 2025 | 2025-06-13 | Journey Theme Pack (ATCG) / `release` |
| CSV5C | 2024 | 2025-09-12 | Ardent Obsidian (ATCG) / `release` |
| mC | 2025-12 | 2025-12-19 | Start Deck 100 Battle Collection (TCG) / `release` |
| CSV7C | 2025 | 2026-01-16 | Blade Awakening (ATCG) / `release` |
| m3 | 2026-01 | 2026-01-23 | Nihil Zero (TCG) / `jarelease` |
| CSVH4C | 2025-26 | 2026-04-10 | Decidueye & Melmetal & Koraidon & Miraidon Happy Set (ATCG) / `release` |
| CSV10C | 2025-12 | 2026-07-16 | Together in Pursuit of Glory (ATCG) / `release` |

For multi-wave products the scalar chronological value is the first release. The manifest retains
notes for cases where that choice needs context (for example Battle Academy 2020 and HXY).

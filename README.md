# Snorlax on Cardmarket — dataset & analysis

Scraped from Cardmarket's Pokémon product search for "snorlax" (all categories, 9 pages, 242 products).

## Files

| File | Contents |
|---|---|
| `snorlax_cards.json` | **Main dataset** — 198 Snorlax *singles* with name, set code, set name, languages, rarity, image, variant info, cross-release key |
| `images/` | 198 card images, one per product (`SETCODE_NUMBER_NAME[_Vn]_ID.jpg`) |
| `artists_pokemontcgio.json` | 57 English Snorlax-family cards with illustrator credits |
| `analysis_language_drift.json` | Per-card deviation from its market's language baseline |
| `analysis_shared_cards.json` | Cards printed across multiple releases, grouped, with artists |
| `analysis_artists.json` | Artist → printings index |
| `analysis_variants.json` | Set+number clusters with more than one Cardmarket product |
| `*.ps1` | Reproducible build/join/analysis scripts |
| `verification/` | **Source verification layer** — one row per card × language × variant, each with a confirmed source outside Cardmarket. See `verification/RESUME.md` |

242 products − 44 non-card items (playmats, sleeves, binders, tins, blisters, pins, deck boxes) = **198 singles**. Six of those 198 are online/live code cards, flagged `isCodeCard: true`.

## Scope and caveats — read before using

- **`languages` is marketplace availability, not a print manifest — and this is now proven, not just suspected.** Cross-checking every card × language against outside sources produced **71 contradictions**: cases where Cardmarket offers a language for which no printing exists. The clearest is `KSS 26` (XY Kalos Starter Set), where Cardmarket advertises **17 languages** and the expansion was printed in **7** (EN, DE, FR, IT, ES, PT, RU). For some products the filter falls back to a global language list. See `verification/CONTRADICTED.json`.
- **"Spanish" cannot distinguish European from Latin-American Spanish.** From Journey Together (2025) LATAM-ES is a physically distinct edition (different attack translations, set name and set code — specimen-verified for `SVP 184`: "Presión Dinámica"/"Juntos de Aventuras" vs "Plancha Dinámica"/"Aventuras Compartidas"), but Cardmarket's filter collapses both into one "Spanish". Every Spanish entry here means the European print. See `verification/RESUME.md`.
- **`cardKey` groups the same *card*, not the same *artwork*.** Cardmarket derives it from card name + attack names. Reprints with brand-new art share a `cardKey`. That's a feature here — it's exactly how the "same card, new art" cases below were found — but don't read it as art identity.
- **Artist coverage is 79/198 (40%).** Illustrators are only published for English-market releases. The 119 uncovered rows are Japanese, Simplified-Chinese, Korean and SEA printings. Rather than guess, `artist` is left `null` there; use `cardKey` to find the English sibling.
- **Stamp variants are not labelled anywhere in Cardmarket's text.** Master Ball vs Poké Ball holo, prerelease and staff stamps are only distinguishable in the artwork and by Cardmarket splitting them into separate `-V1/-V2/-V3` products. `variantToken` captures the split; naming the stamp would require reading the images.

## Language drift

Baselines: Western = EN/FR/DE/ES/IT/PT · Japanese-market = JA/KO/T-Chinese.

**Narrower than baseline**

| Card | Set | Missing |
|---|---|---|
| Snorlax `SK 100` | Skyridge | FR, ES, PT |
| Snorlax `RR 33/81`, Snorlax LV.X `RR 111` | Rising Rivals | ES, PT |
| Snorlax δ `DF 10` | EX Dragon Frontiers | ES, PT |
| Snorlax `FL 15` | EX FireRed & LeafGreen | ES, PT |
| Snorlax `CL 33` | Call of Legends | ES, PT |
| Snorlax `B2 30`, `LC 64`, Rocket's Snorlax `GH 33` | Wizards era | EN only |
| Rocket's Snorlax ex `TRR 104` | EX Team Rocket Returns | EN + PT only |
| Snorlax `CLV 016` | TCG Classic | EN only |
| Snorlax Lv.40 `Pt2 070`, Snorlax δ `PCG9 001`, `PCG1 074` | JP-only sets | KO, T-Chinese |
| Snorlax GX `SM-P 1`, Eevee & Snorlax GX `SM-P 297` | Sun & Moon Promos | T-Chinese |

**Wider than baseline**

| Extra language | Cards |
|---|---|
| Dutch | Jungle `JU 11` / `JU 27`, Wizards Promo `WP 49` |
| Russian | `BKT 118`, `FCO 77`, `FLF 80`, `GEN 58` |
| Polish | Diamond & Pearl `DP 37` |
| Indonesian + Thai | modern JP sets (`sv2a`, `sv4a`, `s10a`, `s10b`, `s5a`, `s8b`, `m2a`, `svM`) |
| Thai only | `sv5a 051`, `sv4K 059` |
| S-Chinese alongside JP | `s4 84`, `sI100 341/342`, `sH 038`, `svIba 046` |

Two genuine outliers, both worth knowing about:

- **`KSS 26` (XY Kalos Starter Set) — 17 languages**, including Czech and Hungarian. Starter-set products were distributed far wider than booster sets.
- **`SVP 051` splits.** Cardmarket carries two products for the same promo number: one with the full 6 Western languages, one **English-only** (`-V2`, 20 listings). Same card, different distribution — a real drift case, not a data error.

The market split across all 198: Western 83 · Japanese 68 · Simplified Chinese 37 · SEA promo 5 · global code cards 4 · Traditional Chinese 1.

## Shared art across releases

38 cards appear in more than one release. The interesting split is between *reprints that kept the art* and *reprints that commissioned new art*.

**Same card, genuinely new artwork** — these are the ones to know:

| Card | Printings | Artists |
|---|---|---|
| Snorlax — *Voraciousness / Thudding Press* | 17 across 11 sets | **HYOGONOSUKE** (`MEW 143`) · **GOSSAN** (`SVP 051`) · **Shigenori Negishi** (`PAF 202` Shiny) |
| Eevee & Snorlax GX | 12 across 6 sets | **Mitsuhiro Arita** (`TEU 120`) · **5ban Graphics** (`TEU 171/191`) · **Tomokazu Komiya** (`SM 169`) |
| Snorlax — *Gormandize / Body Slam* | 11 across 8 sets | **Atsuko Nishida** (`VIV 131`) · **Narumi Sato** (`SWSH 068`) · **Saki Hayashiro** (`CRE 224` Secret) |
| Hop's Snorlax | 15 across 10 sets | **GOSSAN** (`JTG 117` + prize packs) · **OKACHEKE** (`SVP 184`) |
| Snorlax — *Unfazed Fat / Thumping Snore* | 12 across 10 sets | **0313** (`LOR 143`) · **Kouki Saitou** (`LOR TG10` Illustration Rare) |
| Snorlax — *Heavy Impact* | 8 across 6 sets | **Oswaldo KATO** (`FST 206`) · **Asako Ito** (`CRZ 109`) |
| Snorlax V — *Swallow / Falling Down* | 7 across 4 sets | **Masakazu Fukuda** (`SSH 141`) · **aky CG Works** (`SSH 197` alt) |
| Snorlax — *Rolling Tackle / Heavy Impact* | 5 across 5 sets | **chibi** (`SSH 140`) · **Tika Matsuno** (`SWSH 032`) |

**Same art reused across releases** (single artist across every printing) — notably `Snorlax-Thick-Skinned-Body-Slam` (7 printings, all **Ken Sugimori**, Jungle → Base Set 2 → Legendary Collection → XY promos → JP Pokémon Jungle), `Snorlax-VMAX-G-Max-Fall` (7, all **aky CG Works**), `Snorlax-But-First-Food-Heavy-Impact` (6, all **Souichirou Gunjima**), `Snorlax-Collect-Collapse` (6, all **Eri Yamaki**).

**Most-used illustrators:** Ken Sugimori (7 English printings), 5ban Graphics (4), Mitsuhiro Arita (4), Kouki Saitou (3), aky CG Works (3).

## Variants

17 set+number clusters hold more than one Cardmarket product. `variantAxes` records which variant dimensions Cardmarket exposes per product:

- **`Reverse Holo`** — present on regular set cards, absent on promos.
- **`First Edition?`** — present on pre-2020 sets, absent on modern ones.
- Rarity itself carries variant meaning: `Illustration Rare`, `Special Illustration Rare`, `Character Rare`, `Shiny Rare`, `Rainbow Rare`, `Secret Rare`, `Triple Rare`, `Oversized`, `Prize Pack Series`, `World Championship Deck`.

Examples: `sv2a 143` has V1/V2 (base vs Master Ball/Poké Ball holo); `SSH 142` has three products (Ultra Rare, Rainbow Rare `206`, Oversized); `xJTG 117` has V1/V2/V3 with V3 English-only.

## Collection method

Cardmarket sits behind Cloudflare with a **rolling quota of roughly 55–60 requests per window**, independent of pacing — pausing between requests does not avoid it, and once tripped it returns HTTP 429 for several minutes. Recovery is a top-level navigation, which re-solves the challenge and restores access; scraping state was kept in `localStorage` so those recovery navigations didn't lose progress. Final settings: ~7 s/request, batches of ~50, with the runner halting and checkpointing on the first 429. All 198 product pages were retrieved with zero errors.

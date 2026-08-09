# Findings

What fell out of building the dataset: where Cardmarket's language coverage departs from what the
regional print runs suggest, which cards were re-illustrated between printings, what the opaque
`V1`/`V2`/`V3` tokens turned out to mean, and how the catalogue was collected in the first place.

These are readings of the generated analyses, not a second source of truth. The files behind them
are [`analysis_language_drift.json`](analysis_language_drift.json),
[`analysis_shared_cards.json`](analysis_shared_cards.json),
[`analysis_variants.json`](analysis_variants.json) and
[`analysis_artists.json`](analysis_artists.json), all produced by `python scripts/analyze.py` from
`snorlax_cards.json`. Where a count here and a count there disagree, the JSON is right.

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

- **`KSS 26` (XY Kalos Starter Set) — 17 languages**, including Czech and Hungarian. Starter-set
  products were distributed far wider than booster sets. This is also the worked example of
  Cardmarket over-claiming: the expansion was printed in 7.
- **`SVP 051` splits.** Cardmarket carries two products for the same promo number: one with the
  full 6 Western languages, one **English-only** (`-V2`, 20 listings). Same card, different
  distribution — a real drift case, not a data error.

<!-- generated:market-split — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
The market split across all 198 legacy Cardmarket singles: Western 87 · Japanese 68 · Simplified Chinese 37 · SEA promo 5 · Traditional Chinese 1.
<!-- /generated:market-split -->

`market` records which regional catalogue Cardmarket lists a product in — a marketplace claim, like
`languages` beside it. It is independent of what the product *is*: that is `isCodeCard`, derived
from the product name, and the code cards are spread across markets rather than forming one.

## Shared art across releases

38 cards appear in more than one release. The interesting split is between *reprints that kept the
art* and *reprints that commissioned new art*.

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

**Same art reused across releases** (single artist across every printing) — notably
`Snorlax-Thick-Skinned-Body-Slam` (7 printings, all **Ken Sugimori**, Jungle → Base Set 2 →
Legendary Collection → XY promos → JP Pokémon Jungle), `Snorlax-VMAX-G-Max-Fall` (7, all
**aky CG Works**), `Snorlax-But-First-Food-Heavy-Impact` (6, all **Souichirou Gunjima**),
`Snorlax-Collect-Collapse` (6, all **Eri Yamaki**).

**Most-used illustrators:** Ken Sugimori (7 English printings), 5ban Graphics (4),
Mitsuhiro Arita (4), Kouki Saitou (3), aky CG Works (3).

Remember that `cardKey` groups by card *text* — name plus attack names — so a reprint with brand
new art shares the key. That is what makes the table above findable, and why `cardKey` must never
be read as art identity.

## Cardmarket product variants

17 set+number clusters hold more than one Cardmarket product. `variantToken` preserves Cardmarket's
opaque V1/V2/V3 split; it does not have a universal meaning, and the same token means different
things in different sets. `variantAxes` preserves Cardmarket's filter UI only as a hint.

| Cluster | What the tokens turned out to be |
|---|---|
| `xsv2a 143` | V1 Poké Ball mirror holo · V2 Master Ball mirror holo |
| `xm2a 143` | the same two treatments in the opposite order |
| `PPS8 JTG 117` | V1 non-holo · V2 Cosmos holo |
| `xJTG 117` | three distribution stamps, all independently identified as Cosmos holo |
| `SSH 142` | separates the standard and jumbo products |

Always read `variantName` rather than assuming a token carries over from another set.

## How the catalogue was collected

The harvest ran once, on 2026-07-21, against Cardmarket's Pokémon product search for “snorlax” —
all nine result pages, 242 products, of which 198 singles were retained.

Cardmarket sits behind Cloudflare with a **rolling quota of roughly 55–60 requests per window**,
independent of pacing: pausing between requests does not avoid it, and once tripped it returns
HTTP 429 for several minutes. Recovery is a top-level navigation, which re-solves the challenge and
restores access; scraping state was kept in `localStorage` so those recovery navigations did not
lose progress. Final settings were ~7 s per request in batches of ~50, with the runner halting and
checkpointing on the first 429. All 198 product pages were retrieved with zero errors.

That run is history, not a build step. The same search today returns different products, prices and
language filters, so `snorlax_cards.json` is an input of record rather than something this
repository can rebuild — see [How the repository is built](README.md#how-the-repository-is-built).

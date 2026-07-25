# Snorlax on Cardmarket — dataset & analysis

> **Taking over or continuing the project?** Read [`HANDOVER.md`](HANDOVER.md) first, then
> [`verification/RESUME.md`](verification/RESUME.md) before changing verification evidence.

## Documentation guide

All paths and commands in the documentation are relative to the repository root. PowerShell and
Python scripts resolve the checkout from their own file location, so they can be invoked from any
working directory.

| Document | Use it when |
|---|---|
| [`HANDOVER.md`](HANDOVER.md) | You need the current state, repository layout, working rules, and prioritized next actions. This is the main entry point for continuing work. |
| [`README.md`](README.md) | You are consuming the dataset and need its scope, caveats, analysis findings, and collection method. |
| [`verification/RESUME.md`](verification/RESUME.md) | You are adding or changing verification evidence. It records source techniques, failed approaches, corrections, and methodology decisions. |
| [`verification/FINISH_SOURCES.md`](verification/FINISH_SOURCES.md) | You are confirming non-holo, holo, reverse/mirror, stamped promo, Prize Pack, or jumbo versions. It defines the source ladder and repeatable finish workflow. |
| [`verification/open-items.html`](verification/open-items.html) | You want a browsable view of the pending and manual-review units. |
| [`index.html`](index.html) | You want the visual collection: card images, chronological releases, confirmed languages, finish badges, per-column filtering and sorting, and the printable checklist builder. (`verification/confirmed-releases.html` redirects here.) |
| [`verification/SOURCES.md`](verification/SOURCES.md) | You want to know which provider backs a claim, and which of them may establish an absence. |
| [`LICENSE.md`](LICENSE.md) | You want to reuse any of this, or need the third-party exclusions. |
| [`verification/MANUAL_REVIEW.csv`](verification/MANUAL_REVIEW.csv) | You are recording manual verdicts for the remaining hand-checked units. |
| [`verification/FINISH_REVIEW.csv`](verification/FINISH_REVIEW.csv) | You are resolving finish, reverse/mirror-pattern, or Cardmarket-product mapping gaps. |

For current totals, trust the opening **Current state** sections in `HANDOVER.md` and
`verification/RESUME.md`; later numbers in `RESUME.md` may describe historical checkpoints.

Scraped from Cardmarket's Pokémon product search for "snorlax" (all categories, 9 pages, 242 products).

## Files

| File | Contents |
|---|---|
| `snorlax_cards.json` | **Main dataset** — 198 Snorlax *singles* with identity, language, rarity, image, variant info, and `finishAvailability` by language |
| `images/` | 198 card images, one per product (`SETCODE_NUMBER_NAME[_Vn]_ID.jpg`) |
| `artists_pokemontcgio.json` | 57 English Snorlax-family cards with illustrator credits |
| `analysis_language_drift.json` | Per-card deviation from its market's language baseline |
| `analysis_shared_cards.json` | Cards printed across multiple releases, grouped, with artists |
| `analysis_artists.json` | Artist → printings index |
| `analysis_variants.json` | Set+number clusters with more than one Cardmarket product |
| `analysis_finishes.json` | Finish coverage, finish combinations, reverse/mirror patterns, and stamp-role counts |
| `index.html` | **The public site** — collection table with per-column sorting/filtering, checklist builder, methodology, generated sources, and licence notices. Built by `scripts/site.py`; open it directly from a checkout |
| `analysis_checklist.json` | **Canonical checklist items** — one record per documented physical printing, or per explicitly unresolved one |
| `verification/source_registry.json` / `SOURCES.md` | Provider registry and evidence index: every sourced claim mapped to exactly one provider |
| `site/` | Page styles and behaviour (`app.css`, `app.js`) |
| `scripts/` | Reproducible build pipeline (`mkunits` → `build` → `join` → `getimages` → `finalize` → `analyze` → `finishes` → `language_status` → `confirmed_releases` → `source_registry` → `checklist` → `readme_stats` → `site`) |
| `verification/finish_units.json` | **Finish state store** — one row per set number × language, with logical printings, finish/pattern/stamp/size dimensions, evidence, and Cardmarket-product mappings |
| `verification/FINISH_REVIEW.json` / `.csv` | Finish, pattern, and product-mapping gaps that still need evidence |
| `verification/finish_overrides.json` | Curated special-printing details that group-level APIs cannot express |
| `verification/FINISH_SOURCES.md` | Finish evidence hierarchy, confirmed special cases, exact API endpoints, and next source targets |
| `verification/` | **Source verification layer** — language/product claims plus the separate finish layer. Recurring tools at top level (`report`, `audit_evidence`, `classify_manual`, `verify_finish_sources`, `review_integrity`); completed one-shot passes live in `verification/passes/`. See `verification/RESUME.md` |

242 products − 44 non-card items (playmats, sleeves, binders, tins, blisters, pins, deck boxes) = **198 singles**. Six of those 198 are online/live code cards, flagged `isCodeCard: true`.

## Scope and caveats — read before using

- **`languages` is marketplace availability, not a print manifest — and this is now proven, not just suspected.** Cross-checking every card × language against outside sources produced **71 contradictions**: cases where Cardmarket offers a language for which no printing exists. The clearest is `KSS 26` (XY Kalos Starter Set), where Cardmarket advertises **17 languages** and the expansion was printed in **7** (EN, DE, FR, IT, ES, PT, RU). For some products the filter falls back to a global language list. See `verification/CONTRADICTED.json`.
- **"Spanish" cannot distinguish European from Latin-American Spanish.** From Journey Together (2025) LATAM-ES is a physically distinct edition for regular sets — not Prize Packs — with different attack translations, set name and set code (specimen-verified for `SVP 184`: "Presión Dinámica"/"Juntos de Aventuras" vs "Plancha Dinámica"/"Aventuras Compartidas"). Cardmarket does not support LATAM-ES; sourcing it would require the official Pokémon site. Every Spanish entry here means the European print. See `verification/RESUME.md`.
- **`cardKey` groups the same *card*, not the same *artwork*.** Cardmarket derives it from card name + attack names. Reprints with brand-new art share a `cardKey`. That's a feature here — it's exactly how the "same card, new art" cases below were found — but don't read it as art identity.
- **Artist coverage is 115/198 (58%).** Illustrators come from pokemontcg.io/limitlesstcg (English-market) and the official pokemon-card.com database (Japanese-market). The uncovered rows are mostly Korean/Chinese deck products with no published illustrator credit. Rather than guess, `artist` is left `null` there; use `cardKey` to find a sibling that has one.
- **`variantAxes` and `hasReverseHolo` are marketplace hints, not the finish manifest.** The two finish layers answer *different* questions, so pick deliberately rather than treating them as alternatives. `finishAvailability` on a card answers “what does evidence attribute to **this Cardmarket product**?” `verification/finish_units.json` answers “what is known for this **set number and language**, whichever product carries it?” Product attribution is necessarily the weaker of the two, so each card row also carries `unitAvailableFinishes` and `unitFinishStatus` from the store. Read the status words exactly: `pending` means no positive evidence anywhere in the unit; `unmapped` means the finish is known but no product is attributed yet; `other-product` means it is attributed to a different listing of the same card. None of the three ever means “does not exist.”
- **`languages` is the raw Cardmarket claim; the verdict lives beside it.** Each card carries `languagesConfirmed`, `languagesContradicted`, and `languagesUnresolved`. Use `languagesConfirmed` for printings backed by an outside source — 36 products still list at least one language this project has itself refuted, and `languages` deliberately preserves that claim because the over-claiming is a finding.
- **A Cardmarket V-token is not a finish.** TCGdex's `normal`/`holo`/`reverse` flags apply to the set number and language; `V1`/`V2`/`V3` mapping is recorded only when it is unambiguous or independently identified.
- **Stamp role matters.** EX-era set-logo stamps that form part of the reverse-holo design use `markings.role: "reverse-holo-treatment"`. Later prerelease, Staff, retailer, and Pokémon Center stamps use `markings.role: "distribution-promo"` and do not imply reverse holo.

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

## Finishes, foil patterns, and stamps

Finish availability is modeled independently of Cardmarket products. The authoritative file has
**637 set-number-language units**. It currently records at least one externally confirmed finish
for **331**, a marketplace-only positive claim for **104**, and no positive finish evidence yet
for **138 applicable units**. Another **64** units are `not-applicable` because every underlying
product-language claim is contradicted. Because upstream catalogues are incomplete, this is
deliberately a positive-evidence model: an unlisted finish remains `pending` rather than being
marked unavailable. The remaining review queue contains **233** units after those false-language
claims and newly sourced cases are removed. Four English units have an official
`complete-manifest`; all other sourced units remain explicitly positive-only.

Current positive coverage (units can appear in more than one row):

<!-- generated:finish-coverage — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
| Known available finish | Set-number-language units |
|---|---:|
| Non-holo | 270 |
| Holo | 145 |
| Reverse holo | 234 |
| Mirror holo | 8 |
| Both non-holo and holo | 18 |
<!-- /generated:finish-coverage -->

Each unit contains `finishStatus` for `non-holo`, `holo`, `reverse-holo`, and `mirror-holo`, plus
one or more physical `printings`. A printing keeps four separate dimensions:

- `finish` — non-holo, holo, reverse-holo, mirror-holo, or temporarily unknown;
- `foilPattern` — for example Cosmos, crosshatch, tiled type symbol, Poké Ball, or Master Ball;
- `markings` — a physical set logo, Staff, retailer, or Pokémon Center stamp, including its role;
- `distribution` and `cardSize` — how it was released and whether it is standard or jumbo.

The distinction fixes two easy-to-confuse cases. `DF 10` has a normal holo printing and an
EX Dragon Frontiers reverse holo whose set-logo stamp is intrinsic to that reverse treatment.
By contrast, `CL 33`, `VIV 131`, and `SVP 184` have later prerelease/Staff set-name stamps recorded
as distribution promos; the stamp itself does not make a card reverse holo. The regular `JTG 117`
records holo and intricate-tile reverse-holo availability by language — **not** non-holo. The
non-holo Hop's Snorlax is the Prize Pack product (`PPS8 JTG 117` V1), a separate printing; keeping
them apart is exactly what the product/finish split is for.

Source strength and completeness are explicit. Only a complete official checklist may establish
that a listed alternative is absent; API flags, TCGplayer/TCGCSV subtypes, PSA registries, and scans
are positive-only. See [`verification/FINISH_SOURCES.md`](verification/FINISH_SOURCES.md) for the
evidence ladder and the confirmed Prize Pack, promo, stamped, deck, and jumbo cases.

Two checks guard this layer: `python verification/review_findings.py` (cross-artifact
consistency, publication readiness, and the checklist regression fixtures) and
`pwsh -File verification/review_integrity.ps1` (structural invariants). Neither asserts counts —
rising numbers are verification progress, not regressions.

Run `python scripts/finishes.py` after rebuilding the main dataset. It caches TCGdex responses in
the gitignored `verification/cache/finish-tcgdex/`, regenerates all finish outputs, and reattaches
the per-product summaries to `snorlax_cards.json`.

## Cardmarket product variants

17 set+number clusters hold more than one Cardmarket product. `variantToken` preserves Cardmarket's
opaque V1/V2/V3 split; it does not have a universal meaning. `variantAxes` preserves Cardmarket's
filter UI only as a hint.

Examples: `xsv2a 143` maps V1 to Poké Ball mirror holo and V2 to Master Ball mirror holo;
`PPS8 JTG 117` maps V1 to non-holo and V2 to Cosmos holo; `SSH 142` separates standard and jumbo
products; `xJTG 117` has three distribution stamps, all independently identified as Cosmos holo.

## Collection method

Cardmarket sits behind Cloudflare with a **rolling quota of roughly 55–60 requests per window**, independent of pacing — pausing between requests does not avoid it, and once tripped it returns HTTP 429 for several minutes. Recovery is a top-level navigation, which re-solves the challenge and restores access; scraping state was kept in `localStorage` so those recovery navigations didn't lose progress. Final settings: ~7 s/request, batches of ~50, with the runner halting and checkpointing on the first 429. All 198 product pages were retrieved with zero errors.

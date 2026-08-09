<!-- doc: role=verification playbook and research log; stage=task -->
# Verification — state and how to resume

Current legacy goal: every **card × language × variant** inherited from the frozen
**legacy Cardmarket candidate universe** gets at least one confirmed source **outside Cardmarket**,
and every inherited physical **set number × language** gets a positive-evidence finish inventory
with any Cardmarket-product mappings kept explicit. This playbook does not establish all-locality
discovery completeness; #132 tracks that source-first rebuild.

This file is both the current verification playbook and a chronological research log. Use the
**Current state** section below for authoritative totals; later counts describe historical
checkpoints unless explicitly marked current. Paths and commands are relative to the repository
root.

## What this file is

The verification playbook and the research log behind it: every source technique that worked, every
dead end, every methodology correction. Read it before adding or changing a confirmation or a
contradiction.

**It does not state current figures.** Counts of units, finishes and queues are generated from the
stores into [`DATA-HANDOFF-AUDIT.md`](DATA-HANDOFF-AUDIT.md) by `python scripts/database.py`, and
open items into `verification/open-items.html`. A table typed here would be a second copy that
drifts — the one this replaced claimed 634 confirmed and 85 contradicted, against a real 635 and 84.

Run `verification/review_integrity.py` after any write pass.


### Finish verification is a separate positive-evidence layer

`units.json` answers whether a Cardmarket card-product-language claim exists. It does not answer
whether the physical printing is non-holo, holo, reverse holo, or mirror holo. That technical
question lives in `finish_units.json`, grouped by set number and language because TCGdex's finish
flags are not product-specific. The public site and checklist add a collector-facing
`finishFamily`: both technical reverse-holo and mirror-holo printings appear under **Reverse Holo**,
with their exact foil pattern and physical checklist item retained.

Only upstream `true` values are confirmations. A false or missing TCGdex flag stays `pending`; the
API's own documentation says detailed per-marketplace variant mapping is still being developed.
Cardmarket's Reverse Holo filter and rarity are retained only as `marketplace-claimed` positives.
When every underlying product-language claim is contradicted, the finish unit remains in the state
store as `not-applicable` for exact key coverage but is not finish-research work and does not appear
in `FINISH_REVIEW`.

Only a complete official checklist with explicit finish columns can establish that a covered
alternative is absent. TCGdex false values, TCGCSV subtype omissions, PSA population omissions, and
catalogue gaps cannot. The source ladder, exact endpoints, and current special-case findings are in
[`FINISH_SOURCES.md`](FINISH_SOURCES.md).

Keep technical `finish`, collector-facing `finishFamily`, `foilPattern`, `markings`, `distribution`,
and `cardSize` separate. Aggregating under Reverse Holo must never delete the underlying
reverse-holo/mirror-holo distinction, pattern, source, product mapping, or printing ID. In
particular:

- printed identity features such as rarity symbols and contest credits use `role=print-identity`;
- EX-era set-logo stamps intrinsic to a reverse treatment use `role=reverse-holo-treatment`;
- later prerelease, Staff, retailer, and Pokémon Center stamps use `role=distribution-promo`;
- a distribution stamp never changes the finish category by itself.

The worked examples are `DF 10` (Dragon Frontiers stamped reverse treatment), `CL 33` and
`SVP 184` (prerelease/Staff distribution stamps), and `JTG 117` (non-holo + holo + reverse holo).
Edit curated exceptions in `finish_overrides.json`, not generated `finish_units.json`, then run
`python scripts/finishes.py`.

### Deck products put their languages in the infobox, not in a language table

The highest-yield lookup for deck and collection products is the **`release=` field of the `DeckInfobox`**, which lists a date per market. Checking only `In other languages` misses them entirely — that is why these read as undocumented for many phases:

```
Start Deck 100        Japanese Dec 17 2021 · T-Chinese Feb 18 2022 · Korean Apr 23 2022 · S-Chinese May 17 2024
Family Card Game      Japanese · Korean · T-Chinese · S-Chinese Nov 17 2023 · Thai
Battle Academy (JP)   Japan Mar 8 2024 · South Korea Apr 20 2024 · Mainland China Jan 16 2026
CoroCoro Comic Ver.   Japanese Mar 2022 · Korean May 27 2022 · T-Chinese Oct 2 2022
```

One sweep of that field closed seven units. Note "Mainland China" means Simplified Chinese and "South Korea" means Korean — the field uses market names, not language names.

### PowerShell case-insensitivity — four incidents, one root cause

`$R`/`$r`, `$EV`/`$ev` (twice), and `-match '^x'` catching `XY-P`/`XY2`/`XY10`/`XYPR`. Variables and `-match` are both case-insensitive; use distinct names and `-cmatch`. None of these threw an error — they silently produced wrong data, and one parked 12 units where later passes skipped them.

### A domestic campaign does NOT rule out a foreign printing — corrected

An earlier version of this file argued that a Japan-only distribution channel positively proves no foreign printing exists. **That is wrong**, and it produced a false contradiction:

- Japan: `XY-P 149` via the **Marumiya** furikake/curry promotion, July 2015
- Korea: `XY-P 167` via the **Kisstick sausages** promotion, 2017 — *the same card*

Each market ran its own food-company tie-in. Bulbapedia redirects both `Snorlax (XY-P Promo 149)` and `Snorlax (XY-P Promo 167)` to one article, `Snorlax (BREAKthrough 118)`, and the illustrator (Kouki Saitou) matches on both.

**Use the redirect target as the identity test.** Two promo numbers that redirect to the same card article are the same card; that is the cheapest reliable check for cross-language promo matching, better than numbers or names.

The channel argument survives only as *supporting* evidence. The remaining contradictions built on it rest primarily on other grounds:

| Card | Channel | Independent support |
|---|---|---|
| `BW-P 207` | CoroCoro Ichiban! magazine insert | Korean BW promo list (65 cards) has no Snorlax |
| `DP-P 126` | Domino's Pizza Japan campaign | Korean list carries the sibling Lv.X as `006`, so the era is in scope — and the user confirmed it |

Korean promo articles are `{{incomplete}}`-tagged and short (22 and 65 rows), so never contradict on absence alone.

### pokumon.com — the best source found for promo printings per language

`https://pokumon.com/?s=<query>` returns one entry per market printing, each naming its language and its distribution campaign. A single search for `snorlax xy` returned:

```
Snorlax (167/XY-P Korean Promo)    Kisstick sausages promotion, 2017
Snorlax (261/XY-P Japanese Promo)  Daiichi Pan, September 2016
Snorlax (149/XY-P Japanese Promo)  Marumiya, July 2015
Snorlax (XY179 English Promo)      Snorlax-GX Box
```

**This is how to make an absence argument valid.** The source visibly carries Korean XY-P Snorlax promos, so the absence of a Korean `261` is evidence rather than a coverage gap. Establish that the source covers the category *before* treating a missing row as a finding — that check is exactly what was missing when `XY-P 149` was wrongly contradicted.

**But its Western coverage is one row per card, not one per language.** It lists a single `Snorlax (XY179 English Promo)` — yet physical copies of that promo exist in **French, German, Italian, Spanish and Portuguese**, all inspected from photographs. Searching `ronflex` returns nothing at all, so the database indexes English names only. **Never use a pokumon absence to contradict a Western language.** The asymmetry is real: per-market rows for Asian printings, a single lumped row for the West.

### `XYPR 179` — the case that proves the databases wrong

All three databases point the same way, and all three are wrong:

| Source | What it says | Reality |
|---|---|---|
| TCGdex | only `en` and `fr` exist for `xyp-XY179` | six Western languages exist |
| pokumon | one row, "XY179 **English** Promo" | ditto |
| Bulbapedia | distributed "in the **English** Snorlax-GX Box" | localized Europe-wide |

Six specimens were photographed and their card text read off — `Relaxo` / `Ronflex` / `Snorlax`, ability `Immunität` / `Vaccin` / `Immunità` / `Inmunidad` / `Imunidade`, all bearing `XY179`, Ken Sugimori and ©2016. Had the absence-argument been applied here as it was for the Asian promos, it would have produced four false contradictions.

**Grade physical evidence explicitly, and by what the claim rests on.** `sourceType` distinguishes *photographed specimen* from *owner attestation*, and `providerId` must name the source the unit would fall over without — not the strongest source standing near it. **29 units rest on owner attestation alone**; 9 rest on a photographed specimen alone, each citing its `SPEC-nnnn` record. Check `E4` holds this sentence to the data, so correct it here rather than letting it drift (it read "currently 0" for weeks while the real figure was 16, then 30). A specimen may only be claimed by a unit that cites it — `S14` — and `sourceRef` holds a reference or nothing, never prose — `S13`.

At this checkpoint, every card had at least one confirmed language. The then-25 open units were
all *additional* language claims on cards that were otherwise evidenced.

### PowerShell variable names are case-insensitive — this bit twice

`$EV` (evidence text) and `$ev` (log array) are **the same variable**. Declaring `$ev=@()` after `$EV='...'` silently wipes the text, and units get written with an empty or array-typed `evidence` while still being marked `confirmed`. It does not throw. Same class of bug as `$R`/`$r` earlier.

`audit_evidence.py` checks every resolved unit for a non-trivial string evidence field — **run it after every write pass**. It caught two corrupted units (`s5a` Indonesian/Thai) that had gone unnoticed several phases earlier.

### Traditional Chinese prints can live under a different set entirely

`svLN 010` and `mP1 012` are Japanese deck products; their Traditional Chinese printing is not a TC edition of those decks but the standalone promo **SV-P 215** (2025 Taiwan Lantern Festival). Identity was established via the shared Cardmarket `cardKey` `Snorlax-Spike-Draw-Mega-Punch`, which also covers Surging Sparks 144 — the card the TCTCG article names as the source of 215/SV-P. When a language looks impossible for a product, check whether the card exists in that language under another set.

### Two page types worth reaching for earlier next time

- **`Snorlax (TCG)`** — a master list for the species, one block per card with every release as `jpset=` / `enset=` pairs. It resolves Japanese↔English correspondence for all 40 cards in one fetch. It does **not** carry Korean or Chinese, so it only helps Japanese units.
- **Individual card articles** carry a `Release information` paragraph that often states the originating Japanese set in prose, which is the only route to Japanese secret/rainbow prints — the official `pokemon-card.com` search never returns them and the expansion article lists English numbering only. `s1H 70` was settled that way.

### Sources researched and rejected for the Korean/Chinese tail

| Source | Verdict |
|---|---|
| `pokemoncard.co.kr`, `pokemonkorea.co.kr` | **HTTP 410 Gone** — dead, in browser too, not a scraping block |
| `namu.wiki` (Korean wiki) | reachable but JS-rendered; script sees ~14 KB of chrome, no card data |
| `krystalkollectz.com` | a shop, not a database — useful only as marketplace evidence |
| `ptcg.cn` | a Magic: The Gathering site despite the name |
| `pokebeach.com` | 403 to scripts; would need WebFetch |

### Search the index under Bulbapedia's set name, never Cardmarket's

`s5a` looked absent from the cross-language index for several passes. It is not — Cardmarket's *Matchless Fighters* is filed there as *Peerless Fighters*, and the row carries all four Asian languages:

```
双璧のファイター | Peerless Fighters | 雙璧戰士 | Dua Pilar Petarung | สองยอดนักสู้ | 쌍벽의 파이터
```

Searching by the **Japanese** name is the reliable route, since that column is always present. `NOT FOUND` from a Cardmarket name means nothing.

Scope limit of that index: it covers **main expansions only**. Starter decks, family products, battle academies and gift boxes (`sI100`, `svIba`, `sA`, `sH`, `svG`, `svLN`, `20th`, `HXY`) are absent from it, and its Simplified Chinese section covers only the CS catch-up sets, never Japanese ones.

Also new suffix: **`(SCTCG)`** = Simplified Chinese promo series (`S-P Promotional cards (SCTCG)` gave an exact hit for `S-P/CS 061`, `SV-P Promotional cards (SCTCG)` for `SV-P/CS 277`).

### An empty Langtable parameter is not the same as an absent one

`Start Deck 100 Battle Collection` fills `ko=` and both `zh_` slots but lists `fr= de= it= es= pt_br= id= th=` **present and empty**. That is a deliberate "not released here", unlike an article that simply omits the parameters. Worth distinguishing before treating a blank as evidence either way — the same trap as the cross-language index columns.

### Bulbapedia keeps one article per language — the naming scheme

This is the single most useful structural fact found so far. Promo series and Asian sets each have their own article, distinguished only by a suffix:

| Suffix | Language |
|---|---|
| `(TCG)` | Japanese (and the default English articles) |
| `(KTCG)` | Korean |
| `(TCTCG)` | Traditional Chinese |
| `(ITCG)` | Indonesian |
| `(ATCG)` | Simplified Chinese |

So `SV-P Promotional cards` exists five times over. Query the suffix matching the language you need, e.g. `S-P Promotional cards (TCTCG)` for Traditional Chinese.

**Watch the numbering.** Each language's promo series numbers independently. The Korean printing of `SM-P 1` (Snorlax-GX) is `017/SM-P`, and of `SM-P 297` it is `140/SM-P`; Cardmarket files both under the *Japanese* number. Traditional Chinese `S-P 145` happens to match Cardmarket exactly, but that is luck, not a rule — match on card identity, not on the number alone.

### Elite Fourum — scriptable, and it solved what the wikis could not

`elitefourum.com` runs Discourse, so its JSON API is directly usable (PokeBeach returns 403 to scripts and needs WebFetch):

```
https://www.elitefourum.com/search.json?q=<query>
https://www.elitefourum.com/t/<topicId>.json
```

Two threads settled cases that had no wiki route at all:

- **`Black Star Promos - languages` (36573)** — a per-card table of the Wizards promos with language flags. Row *49 Snorlax* carries **only the US flag**, which contradicts Cardmarket's five European languages. Crucially the reading is verifiable: rows *8 Mew* and *20 Psyduck* both show `us/de/fr/it/es/pt`, so a lone US flag is a positive statement rather than a gap. Always sanity-check a table like this against a row you can independently confirm before trusting its blanks.
- **`Modern World Championships Decks languages` (55804)** — establishes that Worlds decks were English-only historically and gained French/Italian/German from 2022. Combined with localized 2023 retail listings this closed EN/DE/FR/IT; Spanish and Portuguese were subsequently contradicted after no localized Colorless Lugia listings were found.

Note the table is emoji-based: parse `title=":xx:"` out of the flag `<img>` tags, not the visible text.

### The `ko=` line — best remaining lever for Korean

Set and product articles carry an official Korean product name in the "In other languages" table. That is direct evidence of a Korean release and needs no Korean-language database:

```
Vivid Voltage            |ko=앙천의 볼트태클
Battle Academy (JP)      |ko=배틀 아카데미
Family Pokémon Card Game |ko=패밀리 포켓몬 카드 게임
Pokémon GO               |ko=Pokémon GO
```

Same trick works for `pt_br=`, `it=`, `fr=`, `de=`, `es=`.

Titles that cost a search to find: the Battle Academy article is a disambiguation page; the product is **`Battle Academy 2020 (TCG)`**. There is no `World Championship Deck` article at all, and `Wizards Black Star Promos (TCG)` records the Snorlax promo (Pokémon League, August 2002) but states no languages — so `WCD23` and `WP` have no documentary route and are candidates for manual review.

### Two API details that silently return nothing

**Always pass `redirects=1`.** Japanese set names are redirects to the English article, and without the flag the API returns the redirect stub (34 bytes) rather than the target — which looks exactly like "this set has no Snorlax". Resolved pairs: Tag Bolt → *Team Up*, Matchless Fighters → *Peerless Fighters*, Pokémon Jungle → *Jungle*, Challenge from the Darkness → *Gym Challenge*, Shield → *Sword & Shield*.

**The articles carry both numberings.** `{{Setlist/nmentry|...}}` rows use the English collector number, `{{Setlist/entry|...}}` rows the Japanese one. Tag Bolt 115/095 (HR) exists only in the Japanese rows — the official `pokemon-card.com` search does not return Rainbow Rares at all, so this is the only route to them.

**JP promo pages need exact-name matching**, not substring: `カビゴンGX` is contained in `イーブイ&カビゴンGX`, so a `-like` match makes both SM-P promos look ambiguous and silently skips them.

### TCGdex answers 200 for languages and eras it holds no cards for

Probed 2026-08-09 while trying to raise the Western set-level confirmations of #137 to card level.
The attempt failed, and the reason is worth more than the attempt: **TCGdex never says "I do not
cover this"**, and three of the four signals you would reach for are wrong.

| Request | Response | What it actually means |
|---|---|---|
| `ru/sets/xy2` | **HTTP 200**, `cardCount.total` **106**, `cards[]` **empty** | TCGdex serves no Russian at all |
| `it/sets/pl2` | HTTP 200, `cardCount.total` **111**, `cards[]` **empty** | the Italian set is registered; no card records exist |
| `pt/sets/ex7` | HTTP 200, `cardCount.total` **109**, `cards[]` **empty** | same |
| `pt/sets/pl2` | HTTP **404** | the same kind of gap, answered differently |
| `it/cards/pl2-33` | HTTP 404 | a data gap, **not** an absent card |

Neither the status code nor `cardCount.total` indicates coverage — `cardCount.total` is carried over
from the set record and is reported in full for a language holding zero cards. **Only a non-empty
`cards[]`, or a card endpoint answering 200, shows coverage.** Note the last two rows: two identical
gaps, one answered 200 and one 404, so even the inconsistency is not a signal.

Controls run in the same session, so the negatives are not a broken URL pattern or a dead locale:
`en/cards/svp-051` 200, `it/cards/svp-051` 200, `en/cards/pl2-33` 200 (Snorlax), `it/cards/swsh4-131`
200 — that last returning `set.name` = *Voltaggio Sfolgorante*, so it is a real Italian record and
not an English fallback.

The boundary is by **era**, not by language. Italian and Portuguese are fully populated for `xy2`
(2014, 110 cards) and `swsh4` (2020, 203) and empty for `pl2` (2009) and `col1` (2011). Before
treating any TCGdex miss as anything at all, fetch the *set* in that language and check whether
`cards[]` has entries.

This is what the rule "TCGdex `true` confirms a printing; TCGdex `false` does not refute one" is
protecting. Reading `ru/sets/xy2` → 200 → "covered, and the card is not in it" would have produced a
false contradiction of exactly the shape the `XY-P 149` incident already cost.

### Cardmarket ↔ Bulbapedia set-name mismatches (Simplified Chinese)

Cardmarket's Chinese set names are translations of the Chinese titles; Bulbapedia uses its own English renderings. None of these are guessable — find them via the ATCG category search, not by name similarity:

| Cardmarket | Bulbapedia |
|---|---|
| Azure Shadow – Pursuit | Marine Shadow |
| Brave Stars – Charm / V Starter Deck | Gallant Galaxy |
| Chasing Glory Together | Together in Pursuit of Glory |
| Adventure Special Pack | Journey Theme Pack |
| Variety Treasure Box | Peripheral Collection Gift Box: Variety Treasure Box |
| **Dark Crystal Blaze** | **Ardent Obsidian** |
| Display Set Gift Box Gengar | Pokémon Card Display Set Gift Box Vol. 3 |
| **Battle Party Dream Together** | **Battle Party: Shared Dream** |
| Battle Party Shining Dream | Battle Party: Shining Dream |

Japanese sets rename too — resolve them via `redirects=1` rather than guessing: Tag Bolt → *Team Up*, Matchless Fighters → *Peerless Fighters*, **Shocking Volt Tackle → *Amazing Volt Tackle***, Challenge from the Darkness → *Gym Challenge*, XY Beginning Set → *Kalos Starter Set*, BREAK Starter Pack → *Generations*.

### The Asian set code is in the set symbol *image*, never in the page text

Bulbapedia does not write Asian set codes anywhere in its wikitext. `Sword & Shield (ATCG)`
contains the string `sc1` exactly zero times: it calls the two halves **Set A** and **Set B**, and
the code lives in the set symbol image the setlist header points at. Fetch and read the image.

```console
curl -sG https://bulbapedia.bulbagarden.net/w/api.php \
  --data-urlencode "action=query" --data-urlencode "prop=imageinfo" \
  --data-urlencode "iiprop=url" --data-urlencode "format=json" \
  --data-urlencode "titles=File:SetSymbolSword Shield Set A.png"
```

Confirmed this way on 2026-08-09: `Set A.png` → **`sc1a F`**, `Set B.png` → **`sc1b F`**,
`SetSymbolStrength V Starter Deck Chinese.png` → **`scD F`**. The images are tiny (48×28 to
120×68) — upscale before reading, and composite onto white first because they are RGBA with a
transparent ground.

The trailing **`F`** marks the Traditional Chinese release of a code that also appears in other
languages (owner, 2026-08-09) — so `scD` and `scD F` are different things and the F is part of the
identifier, not decoration.

Two corroborations that were otherwise unreachable came from this: `sc1a F 127/154` (SPEC-0011,
whose own record said to treat the code as unconfirmed) and `scD F 111/159` (SPEC-0015, whose
record declined to assert the glyph at all). Match on **number, set size, rarity and regulation
mark** together — Bulbapedia's setlist entries carry all four, so a match on all four is a real
identification rather than a coincidence of numbering.

Related trap: a card's own glyph may look illegible at the resolution you happen to be viewing.
SPEC-0015's photograph is 3508×2480 and reads `scD F` cleanly once cropped to the corner. Check
the stored resolution before recording a glyph as unreadable.

### Market-history rule — the highest-yield technique for Asian languages

Bulbapedia's country articles carry a TCG section that dates when a language market opened. That settles whole eras at once instead of one set at a time (`verification/verification/archive/passes/verify_market_history.ps1`, an archived one-shot — never rerun it):

- **Traditional Chinese** launched **October 2019** with *All Stars Collection*. Before the Sun & Moon era only Base Set plus EX Legend Maker / EX Trainer Kit 2 were ever printed in Traditional Chinese; between 2006 and 2019 Taiwan received English-language product. Any Japanese set older than Oct 2019 therefore has **no** Traditional Chinese printing.
- **Korean**: before the DP era only Base Set and ADV Expansion Pack (plus the Treecko/Torchic/Mudkip decks) were printed in Korean. From DP through HGSS, Korean sets were *unique recombinations* — "none of the sets themselves corresponding to existing sets". Only from Black & White do Korean sets track the Japanese ones.

This contradicted 23 units in one pass. **Caveat recorded in the evidence text:** the *card* may still exist in Traditional Chinese through a later catch-up set — what is excluded is a Traditional Chinese printing *of that set*.

### What the `x…` and `PPS…` codes actually mean — this unlocked 39 units

User-supplied domain knowledge, and it overturned an earlier conclusion of mine:

- **`x<SET>`** = special editions of cards from `<SET>` — mirror-holo ball patterns or retail stamps. **Not** a Cardmarket invention, so they *are* documentable.
- **`PPS<n> <SET>`** = Play! Pokémon Prize Pack Series `<n>`, reprint of a card from `<SET>` carrying the Play! stamp.

Resolved from that:

| Card | Finding | Source |
|---|---|---|
| `xsv2a 143` V1/V2 | Master Ball / Poké Ball mirror holo. Confirmed JA/KO/TC; **contradicted ID/TH** — "Thai and Indonesian booster packs … has no Mirror Holofoil prints" | `151 (TCG)` |
| `xm2a 136` V1/V2 | Poké Ball mirror holo; Hop's Snorlax is a Trainer's Pokémon, which the set gives a regular Poké Ball mirror | `MEGA Dream ex (TCG)` |
| `xJTG 117` V1/V2/V3 | Exactly three stamped printings: "Journey Together" (MY/PH/SG), "GameStop" (US/CA), "EBGames" (AU/NZ) — all English-language retail. Confirmed EN, **contradicted FR/DE/IT/ES/PT** | `Journey Together (TCG)` set list |
| `xPRE 076` V1/V2 | Special Collection exclusive with "Prismatic Evolutions" stamp; V2 is the Jumbo printing | `Prismatic Evolutions (TCG)` set list |
| `PPS1`, `PPS3` | Series articles carry official localized product names (fr/de/it/es). Portuguese Snorlax is **contradicted** by the collector confirmation plus archived Copag announcements; Series Three packs were English and localized packs began with Series Four | Prize Pack Series articles + Copag research |

### `needs-manual-review` — cleared

At the historical checkpoint, 51 units remained genuinely undocumentable. The current manual-review
queue is empty: `MANUAL_REVIEW.csv`, `MANUAL_REVIEW.json` and `UNCONFIRMED.json` now contain no
remaining language/product claims. The Portuguese xPRE/PPS units were closed as contradicted with
the source-specific findings described above.

Deliverables for hand-checking: **`MANUAL_REVIEW.csv`** (flat, one row per unit, with empty `verdict` / `yourSource` columns) and **`MANUAL_REVIEW.json`** (grouped per card-variant, showing which languages are already confirmed for the same card). Fill `verdict` with `confirmed` or `false`.

**Thai needs its Thai-script keyword.** `asia.pokemon-card.com/th` returns nothing for `Snorlax` but 25 records for `คาบิกอน` (`verification/verification/archive/passes/asia_fetch_th.ps1`, an archived one-shot — never rerun it). Traditional Chinese likewise needs `卡比獸`; only Indonesian answers to the English name.

Yield per action is now 1–3 units. All bulk sources are exhausted; future additions will need one
lookup per card.

### Correction applied — read this before adding contradictions

The cross-language index uses **two different table shapes**:

| section | columns |
|---|---|
| Sword & Shield era and later | Japanese, English, Traditional Chinese, Indonesian, Thai, Korean |
| Sun & Moon era and earlier | Japanese, English, **Korean only** |

An earlier pass read a missing Traditional Chinese cell in an *older* section as proof of non-release. The column does not exist there at all. **7 contradictions were wrong and have been reverted to `pending`** (Tag Bolt ×3, Double Blaze, Wild Blaze, Plasma Gale, Awakening Psychic King) — see `verification/verification/archive/passes/fix_asia_setlevel.ps1`, an archived one-shot — never rerun it.

The rule now enforced: only an **explicit em-dash** (usually `colspan=3 | —`) counts as evidence of non-release. Shield (`s1H`) and Rebellion Crash (`s2`) carry that em-dash, so those contradictions stand. Verified positive rows, read from raw wikitext:

```
Dark Phantasma  | 黑暗亡靈 | Fantom Kegelapan | อันธการลวงตา | 다크판타스마
Crimson Haze    | 緋紅薄霧 | —                | หมอกสีชาด     | 크림슨헤이즈
Battle Partners | 對戰搭檔 | —                | —            | 배틀파트너즈
```

### The technique that unblocked Bulbapedia — use this from now on

Bulbapedia refuses scripted requests (403) and its long set lists get truncated by plain page fetches. Both problems disappear by driving the **MediaWiki API from inside the browser**, on the Bulbapedia origin:

```js
await fetch('/w/api.php?action=parse&page=' + encodeURIComponent(title)
            + '&prop=wikitext&format=json&formatversion=2', {credentials:'same-origin'})
// then: wikitext.match(/Snorlax[^\n]*/g)
```

This returns the complete raw wikitext. It immediately found `Dynamax Clash` 188 and 207, which the truncated page fetch had missed entirely. Batch ~10 titles per call with ~900 ms spacing.

Find the right article titles with:
`/w/api.php?action=query&list=search&srsearch=incategory:"Simplified Chinese expansions"&srlimit=60`

Cardmarket's set names do **not** match Bulbapedia's article titles for Chinese products. Confirmed mappings: `CS6bC` Azure Shadow → *Marine Shadow*, `CS5aC` Brave Stars → *Gallant Galaxy*, `CSV10C` Chasing Glory Together → *Together in Pursuit of Glory*, `CSVL1C` Adventure Special Pack → *Journey Theme Pack*, `CSZC` Variety Treasure Box → *Peripheral Collection Gift Box: Variety Treasure Box*.

Artist coverage at this checkpoint reached **113/198**, all from the official Japanese database
or pokemontcg.io — never inferred.

### `KSS 26` — the worked example of the Cardmarket artefact

Fully closed: Cardmarket advertises **17 languages**, the expansion article states the print languages exhaustively as **7** (EN, DE, FR, IT, ES, PT, RU). All seven confirmed, the other ten contradicted — Japanese, Korean, both Chinese variants, Indonesian, Thai, Dutch, Polish, Czech, Hungarian. Use this card when explaining why the language column needs a source.

### Two structural limits on what is still open

**Blank cells in the cross-language index are not evidence of non-release.** For Western-language columns a blank usually means the localized set name equals the English one. The index leaves Jungle/Portuguese blank while the Jungle *article* states Portuguese was released. Only positive cells are used as confirmation; blanks stay open. (For Dutch/Polish/Russian the index *is* reliable, because those languages have few releases and the page documents them explicitly — corroborated by the `KSS 26` article.)

**Prize Packs and "Additionals" may be structurally unprovable per language.** The Bulbapedia Prize Pack Series articles list the exact card — which evidences the printing — but state nothing about distribution languages. So `PPS1 VIV 131` and `PPS3 LOR 143` are confirmed for English only; the other five Western languages have no documentary source. The same applies to the `x…` Additionals sets, which are Cardmarket's own product grouping. Closing those ~60 units would require marketplace listings per language (eBay, CardTrader), which the user has accepted as evidence but which no card database will ever carry.

### Simplified Chinese — the route that works, and its limit

Simplified-Chinese-exclusive products have their own Bulbapedia articles with the suffix **`(ATCG)`**, e.g. `Dynamax_Clash_(ATCG)`, `Collection_151_(ATCG)`, `Shining_Synergy_(ATCG)`. These carry full set lists and are the correct source.

The blocker is **extraction truncation**: these set lists are long, and the fetch returns the head of the table only. `Collection 151` confirmed 143/151 but cut off before 169; `Shining Synergy` truncated before any Snorlax row. Add new findings to `verification/archive/passes/verify_manual.ps1`, which applies hand-verified rows.

Dead ends, do not retry: `pokemonkorea.co.kr` (410 to scripts), `pokemon.cardmon.com` (host gone), `ptcg.cn` (a Magic: The Gathering site, not Pokémon), `pokeos.com` (JS-driven). **52poke wiki** is scriptable via `wiki.52poke.com/api.php` but names card pages by *Japanese* set code (`卡比兽（S1H）`), so it evidences the card, not a Simplified Chinese printing.

Phases: `tcgdex` → `tcgdex-full` → `asia-official` → `exclude-codecards` → `rare-languages` → `jp-official` → `asia-setlevel`.

### The Traditional Chinese problem

At this checkpoint, 12 of the then-19 contradictions were Traditional Chinese on **pre-2021
Japanese sets** — Tag Bolt, Double Blaze, Wild Blaze, Plasma Gale, Rebellion Crash, Shield,
Awakening Psychic King. The Traditional Chinese TCG only launched around 2020/21, so those sets
never had a Traditional Chinese printing, yet Cardmarket offers the language filter for them.
This is the same artefact as `KSS 26`: the filter reflects Cardmarket's global language list,
not print reality. Thirty T-Chinese units on old sets were still open at that stage.

Side benefit at this stage: the official Japanese database also publishes illustrators, so artist
coverage in the **main dataset rose from 79/198 to 108/198**. See `artists_official_jp.json` and
`verification/verification/archive/passes/backfill_artists.ps1`, an archived one-shot — never rerun it.

### Official Japanese API — hard-won details

```
https://www.pokemon-card.com/card-search/resultAPI.php
  ?keyword=<UTF-8 escaped>&se_ta=&regulation_sidebar_form=all&pg=&illust=&sm_and_keyword=true&page=<N>
```

- `regulation_sidebar_form=all` is **required**; without it the API silently filters to Standard-legal cards (11 hits instead of 57).
- The page parameter is **`page`**, not `pg`. `pg=1` returns zero hits — it looks like pagination but is not.
- The search matches fuzzily and returns ゴンベ (Munchlax) alongside カビゴン; filter by name.
- Detail page `details.php/card/<id>/regu/all` yields collector number, set code (from the card image path) and illustrator.

### Language scope: Spanish — a documented blind spot, proven by specimen

"Spanish" throughout this dataset is Cardmarket's single Spanish filter. Latin-American Spanish
became a **physically distinct print edition** from **Journey Together (2025)** onward, and the
owner photographed both side by side for Hop's Snorlax SVP 184 ("Snorlax de Paul", 150 PS,
Illus. OKACHEKE, ©2025):

| | European Spanish | Latin-American Spanish |
|---|---|---|
| Attack | **Presión Dinámica** | **Plancha Dinámica** |
| Set name on card | **Juntos de Aventuras** | **Aventuras Compartidas** |
| Set code (bottom left) | differs | differs |

Same card, different translation, different set branding, different set code. **Cardmarket does not
support LATAM-ES at all** (owner) — its filter collapses both editions into one "Spanish" — so
LATAM-ES cannot be sourced from the harvest and every "Spanish" confirmation strictly means the
European print.

**LATAM-ES is in scope since 2026-08-09** — owner decision D3 in
[`ADR-0001`](ADR-0001-locality-aware-print-identity.md), which makes it a locality of its own
rather than a footnote on Spanish. No row exists yet; #139 is the discovery work, and this is the
plan it starts from (owner guidance, written before the decision):

- Source: the **official public Pokémon site**, not Cardmarket. Probed: `pokemon.com/latam`
  responds to scripts (HTTP 200); the LATAM card database would hang off that locale.
- Scope: **from Journey Together (March 2025) onward, sets only.** Prize Packs have no LATAM-ES
  edition so far.
- Cards in this dataset that fall inside that scope: `JTG 117`, `xJTG 117` (V1–V3), `SVP 184`
  (V1/V2 — LATAM specimen-proven, photo above), `POR 063`. Outside scope: `PRE`/`xPRE 076`
  (released January 2025, before JTG), `SVP 051`/`SVP 122` (older promos), and all
  `PPS…` Prize Packs.

### Scope decisions (user)

- **Code cards are out of scope** — 75 units / 7 products moved to `excluded_codecards.json`. They are code inserts, not collectible cards.
- **Prize Packs count as separate cards** and must be verified independently — they are not obtainable through the same channel as the base printing. No inheriting from the base card.
- The same strict rule is applied to the `x…` "Additionals" sets.

### The `contradicted` status

Rare-language checks turned up something more useful than a gap: for 7 units an external source **actively refutes** Cardmarket's language claim. This confirms the caveat in the main README — Cardmarket's language filter reflects seller listings and, for some products, appears to fall back to a full global language list rather than actual print availability. `KSS 26` is the clearest case: Cardmarket shows 17 languages, Bulbapedia documents 7. See `CONTRADICTED.json`.

Everything is checkpointed, and passes were designed to be idempotent: confirmed units are
skipped, caches are reused, and nothing is re-fetched. Scripts derive paths from their own
location and can be rerun from any checkout or working directory.

## Source landscape — what works, what's blocked

Moved here from `HANDOVER.md` in #103; the detail below is this file's job.

| Source | Access | Use for |
|---|---|---|
| **TCGdex API** `api.tcgdex.net` | scriptable | en/fr/de/es/it/pt/ja/zh-tw/id/th card existence; positive normal/holo/reverse flags |
| **Official Pokemon checklists** `assets.pokemon.com` / `d1wx537rtdixyy.cloudfront.net` | scriptable PDFs | complete set and Prize Pack finish manifests; the only current finish source allowed to establish absence within its stated scope |
| **TCGCSV** `tcgcsv.com` | scriptable JSON | reproducible TCGplayer product identity plus positive Normal/Holofoil/Reverse Holofoil subtypes; positive-only marketplace evidence |
| **PSA cert/spec/registry** `psacard.com` | scriptable | exact named grading varieties; never use population counts or omissions as negative evidence |
| **Bulbapedia** | scriptable **only via in-app browser** + MediaWiki API (`/w/api.php?action=parse&prop=wikitext&redirects=1`) — plain fetch is 403 | set lists, `release=` infobox fields, `ko=`/`pt_br=` langtable lines, per-language articles (`(KTCG)`/`(TCTCG)`/`(ITCG)`/`(ATCG)`/`(SCTCG)` suffixes) |
| **Official JP** `pokemon-card.com` | scriptable (`resultAPI.php`, param `regulation_sidebar_form=all`, page param is `page` not `pg`) | Japanese cards + illustrators |
| **Official Asia** `asia.pokemon-card.com` | scriptable | tw/id/th recent cards |
| **pokumon.com** | WebFetch | per-market promo printings (one row per Asian printing; **West is one lumped "English" row — never use its absence to contradict a Western language**) |
| **Elite Fourum** `elitefourum.com` | scriptable (Discourse JSON: `/search.json`, `/t/<id>.json`) | collector-community facts (promo languages, 1st-edition timeline) |
| **LigaPokemon** `ligapokemon.com.br` | **datacenter IPs banned (Cloudflare 1008)** — use the user's real Chrome (`claude-in-chrome` tools) | Brazilian/Portuguese marketplace listings |
| **Cardmarket** | in-app browser (rolling ~55-req quota → HTTP 429; recover by navigating to re-solve the challenge) | seller photos of physical cards (a real photo of a card in language X is valid; the language *filter* is not) |

Dead ends (do not retry): `pokemonkorea.co.kr` / `pokemoncard.co.kr` (HTTP 410, gone),
`ptcg.cn` (a Magic site), `pokebeach.com` (403 to scripts), `namu.wiki` (JS-rendered),
`krystalkollectz.com` (a shop, not a database).

**Key trick**: when a source (Bulbapedia, LigaPokemon) blocks datacenter IPs, drive the user's
own Chrome via the `claude-in-chrome` MCP tools — it uses their residential IP. This is how the
Brazilian Prize Pack confirmations were obtained.

## Files

| File | Role |
|---|---|
| `units.json` | **The state store.** One row per card × language × variant with `status`, `sourceUrl`, `sourceType`, `evidence`, `checkedAt`. Updated in place. |
| `evidence.jsonl` | Append-only journal of observations (never rewritten; corrections are appended). Not canonical and not replayable into `units.json` — see HANDOVER §5 |
| `confirmed_sources.json` | Export of all confirmed units with their sources |
| `UNCONFIRMED.json` | **The gap list** — grouped by card+variant, showing which languages still lack a source |
| `finish_units.json` | **Finish state store** — set number × language, logical printings, evidence, and product mappings |
| `finish_overrides.json` | Curated special finish/pattern/stamp/size and mapping facts; edit this, not generated finish units |
| `FINISH_SOURCES.md` | Finish evidence hierarchy, confirmed cases, exact source endpoints, and next research targets |
| `verify_finish_sources.py` | Live check of TCGCSV product identity and the positive subtypes declared in `finish_overrides.json` |
| `FINISH_REVIEW.json` / `.csv` | The remaining finish, reverse/mirror-pattern, and product-mapping queue |
| `state.json` | Last completed phase |
| `cache/` | Raw API responses. Deleting a file forces a refetch; keeping it makes resume instant. |

## Resume procedure

The command order lives in `CLAUDE.md` — one copy, kept beside the rules that depend on it.
This file no longer restates it.

Safe to interrupt at any point: `units.json` is rewritten only after a full pass, and
`evidence.jsonl` is appended per confirmation.

## Sources used so far

| Source | Scriptable | Covers | Yield |
|---|---|---|---|
| **TCGdex API** (`api.tcgdex.net`) | yes | en, fr, de, es, it, pt, ja, zh-tw, id, th | 352 |
| **Official Pokémon Asia** (`asia.pokemon-card.com`) | yes | tw, id, th, sg — gives expansion code + collector number + illustrator | 12 |
| pokemontcg.io | yes | English artists (main dataset) | — |
| LimitlessTCG | via WebFetch | artist backfill | — |

### Historical source-probing limits — not completeness boundaries

- **The archived TCGdex pass exhausted its then-current queries, not the locality universe.** It
  lists sets it has no cards for (e.g. `S1H` = Shield: 0 cards), and its locale coverage is uneven.
  A zero result is a source gap unless exact exhaustive scope has been established.
- **The archived official-Asia pass was query-limited.** Its `tw` query returned 43 records and the
  English Thai keyword returned none; neither result establishes database coverage. Native-name,
  product-type and locality enumeration belongs to the source-first work in #138.
- **HTTP 403 to scripts:** Bulbapedia, tcgcollector, eBay. Browser tool only.
- **Working but unintegrated:** `pokellector` (incl. `jp.` subdomain), `yuyu-tei` (JP shop listings), `pokemon-card.com` detail pages (JS-driven search, but direct `details.php/card/{id}` works), serebii, pkmncards.

## Historical checkpoint — where the then-remaining 442 sat

| Cluster | Open units | Why | Next source |
|---|---|---|---|
| Online/Live code cards (`Pokémon Products`, `Scarlet & Violet Products`) | ~57 | Not real cards; no card DB lists them | eBay/product listings, or exclude by decision |
| "Additionals" sets (`xJTG`, `xPRE`, `xsv2a`, `xm2a`) | ~45 | Cardmarket bookkeeping for the same physical card | base printing is already confirmed — needs a policy decision, see below |
| Play! Prize Pack series | ~36 | Promo reprints | Bulbapedia / Play! Pokémon pages |
| Japanese-market sets not in TCGdex | ~90 | TCGdex JP coverage is partial | official `pokemon-card.com` |
| Korean / Simplified-Chinese | ~112 | TCGdex has almost no ko/zh-cn cards | `asia.pokemon-card.com`, official CN site |
| Dutch / Polish / Russian / Czech / Hungarian | ~29 | Very small print regions | Bulbapedia set pages (via browser), eBay listings |

## Historical policy question — resolved

The "Additionals" and Prize-Pack rows are the **same physical card** as a printing that is already
confirmed — Cardmarket just files them as separate products. Inheriting the base card's evidence
was considered here, but the owner later resolved the policy: Prize Packs and `x…` Additionals
must be verified independently. See **Scope decisions (user)** above.

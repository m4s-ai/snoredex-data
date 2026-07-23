# HANDOVER — Snorlax Cardmarket dataset & source verification

Read this first if you are taking over cold. It is the single entry point; two deeper docs
back it up and are cited where relevant:

- **`README.md`** — the dataset spec, the findings (language drift, shared art, variants), and
  data caveats. Read before *using* the data.
- **`verification/RESUME.md`** — the verification playbook: every hard-won source technique,
  every dead end, every methodology correction. Read before *adding* any confirmation or
  contradiction. It is long (~415 lines) and worth it — it will stop you repeating mistakes
  that were already made and fixed here.

---

## 1. What this project is

A complete catalogue of every **Snorlax** Pokémon TCG product on [Cardmarket](https://www.cardmarket.com),
plus a rigorous **source-verification layer**: for each card × language × variant, does an
**external source (outside Cardmarket)** confirm that printing actually exists?

Why the verification exists: Cardmarket's language filter is *marketplace availability, not a
print manifest*. It over-claims — the worked example is `KSS 26`, advertised in 17 languages,
actually printed in 7. Every language claim therefore needs an outside source (manufacturer
site, fan wiki, marketplace listing, or a photographed physical card).

The owner (`Scarrty` in git; addressed as the domain expert throughout) directs scope and
supplies physical specimens. **Owner statements are authoritative** but graded explicitly as
evidence (see §6).

## 2. Current state (2026-07-23)

| | |
|---|---|
| Cardmarket products harvested | 242 (198 singles + 44 accessories) |
| Verification units (card × language × variant) | **719** |
| **Confirmed** with external source | **634** (88.2%) |
| **Contradicted** (Cardmarket claims it, source says no) | **71** |
| **Needs manual review** | **5** — all the same question: *does a Portuguese printing exist?* |
| **Still open** | **9** |
| Card-variants with every language resolved | 180 / 191 |
| Artist coverage in main dataset | 115 / 198 |

Numbers live in `verification/units.json` (the state store) and are echoed in
`snorlax_cards.json` → `meta.verification`. **After any change, run
`verification\review_integrity.ps1`** (16 structural checks) — it is the truth test.

### The exact remaining work

**Open (9)** — genuinely undocumented, need a new source:
`BA20 MWT` ES+PT · `WCD23 LOR 143` ES+PT · `sA 10` KO+TC · `mP1 012` KO · `svG 021` TC · `svIba 046` TC.

**Manual review (5)** — all Portuguese Prize Pack / Additionals:
`xPRE 076` V1/V2 · `PPS1 VIV 131` V1/V2 · `PPS3 LOR 143`.
Next step for these: LigaPokemon (Brazilian marketplace) — see §5 for the Cloudflare workaround.

## 3. Repository layout

```
snorlax_cards.json            MAIN dataset: 198 singles, one object each. Fields: name, setCode,
                              number, setName, rarity, languages, imageUrl/imageFile, productUrl,
                              variantToken (V1/V2/V3), variantName (+source), variantAxes,
                              cardKey, artist(+source), editions{}, market, meta{}.
images/                       198 card images (SETCODE_NUMBER_NAME[_Vn]_ID.jpg).
analysis_*.json               Derived: language_drift, shared_cards, artists, variants,
                              confirmed_releases (chronological). Plus analysis_confirmed_releases.csv.
artists_pokemontcgio.json     57 English cards with illustrator + exact release dates.
scripts/                      Build pipeline, in run order:
                                mkunits -> build -> join -> getimages -> finalize -> analyze
                              plus editions.py (edition classification) and
                              confirmed_releases.py (chronological table/CSV generator).
verification/
  units.json                  THE STATE STORE. One row per card×language×variant with status,
                              sourceUrl, sourceType, evidence, checkedAt.
  evidence.jsonl              Append-only log of every confirmation (survives crashes).
  confirmed_sources.json      Export of all confirmed units.
  CONTRADICTED.json           The 71 refuted claims.
  MANUAL_REVIEW.csv / .json   The units handed to the user to decide.
  UNCONFIRMED.json            The open units, grouped by card.
  open-items.html             Browsable page of open + manual-review items (an Artifact).
  confirmed-releases.html     Browsable chronological table w/ edition column (an Artifact).
  RESUME.md                   The verification playbook (read before editing evidence).
  state.json                  Last completed phase.
  report.ps1                  Regenerates coverage + all export files.
  audit_evidence.ps1          Checks every resolved unit has a non-trivial evidence string.
  classify_manual.ps1         (Re)tags structurally undocumentable units.
  review_integrity.ps1        16 structural checks — run after every write pass.
  passes/                     ~65 completed one-shot verification scripts (absolute paths,
                              still runnable). Each closed a batch; named by what it did.
  cache/                      Raw API dumps (gitignored — reproducible via fetch_* scripts).
```

`.gitignore` excludes `verification/cache/` (13 MB reproducible API dumps) and
`verification/zoom/` (image crops). Everything else is committed.

## 4. Data model — the parts that trip people up

- **Unit** = (setCode, number, variant, language). `variant` is Cardmarket's `-V1/-V2/-V3`
  slug or `base`. Status is one of `confirmed | contradicted | needs-manual-review | pending`
  (`pending` = still open). Every resolved unit MUST have a non-trivial `evidence` string and a
  `sourceType`; `review_integrity.ps1` enforces this.
- **`variantName`** — Cardmarket's V1/V2/V3 tokens are opaque; the real meaning is recorded here
  (e.g. `xsv2a` V1=Poké Ball mirror / V2=Master Ball mirror; `xm2a` V1=energy-star mirror /
  V2=Poké Ball mirror — note the order flips between sets; `PPS8` V1=Non-Holo / V2=Holo;
  `xJTG` V1/V2/V3 = Journey Together / GameStop / EB Games stamps). Never assume a V-token means
  the same thing across sets.
- **`editions`** — First Edition vs Unlimited, added last. `{hasFirstEdition, system,
  firstEditionLanguages, unlimitedLanguages, source}`. Ruleset (Bulbapedia + Elite Fourum
  t/16054): WOTC 1st ed = Base Set→Neo Destiny except Base Set 2; Japanese 1st ed = ADV/e-Card
  era→XY, none since Sun & Moon; Korean/Chinese/SEA never. **12 cards** have a 1st edition.
  Cardmarket's own "First Edition?" filter is unreliable (83/198, incl. modern cards) — do not
  use it.
- **`cardKey`** — Cardmarket's own grouping (name + attack names). Same cardKey = same card text,
  useful for finding the same card under a different set (e.g. a card's Traditional Chinese print
  may be a standalone promo, not a TC edition of the Japanese product).
- **Language scope**: "Spanish" = Cardmarket's European Spanish. **LATAM-ES is a separate
  edition** (specimen-proven) that Cardmarket does not list; it is out of scope. If ever added,
  source it from the official Pokémon site, sets only, from Journey Together (2025) onward.
- **Code cards** (75 units) are excluded — `verification/excluded_codecards.json`.

## 5. Source landscape — what works, what's blocked

Full detail in `RESUME.md`. The essentials:

| Source | Access | Use for |
|---|---|---|
| **TCGdex API** `api.tcgdex.net` | scriptable | en/fr/de/es/it/pt/ja/zh-tw/id/th card existence |
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

## 6. Working discipline — non-negotiable

1. **Evidence outside Cardmarket only.** The card's *language filter* on Cardmarket is not
   evidence; a seller's *photo* of the physical card is.
2. **Grade evidence.** `sourceType` distinguishes *photographed specimen* > *marketplace listing*
   / *official DB* / *fan wiki* > *owner attestation*. Currently 0 units rest on attestation alone
   without corroboration; keep it that way where possible.
3. **Never contradict on bare absence.** First prove the source *covers the category* (e.g.
   pokumon lists Korean promos, so a missing Korean row is meaningful). This rule exists because
   an absence-argument produced a false contradiction that had to be reverted (`XY-P 149`).
4. **Run `audit_evidence.ps1` and `review_integrity.ps1` after every write pass.** Silent data
   corruption has happened here (see next point) and only the audit caught it.
5. **PowerShell is case-insensitive** — this bit FOUR times. `$R`/`$r` and `$EV`/`$ev` are the
   same variable (declaring the log array silently wiped the evidence text); `-match '^x'` also
   matched `XY-P`/`XY2`/`XYPR`. Use **distinct variable names** and **`-cmatch`**. None of these
   threw an error; they produced wrong data.
6. **Write findings via a new `verification/passes/verify_*.ps1` script**, then run report +
   audit + integrity. Don't hand-edit `units.json`.

## 7. How to resume / continue

```powershell
cd C:\Users\marku\Claude\snorlax-cardmarket
pwsh -File verification\review_integrity.ps1     # confirm clean starting state
pwsh -File verification\report.ps1               # regenerate exports if needed
# ... do verification work in a new passes\verify_*.ps1 script ...
pwsh -File verification\audit_evidence.ps1       # after any write
pwsh -File verification\review_integrity.ps1     # after any write
python scripts\editions.py                       # if edition data changed
python scripts\confirmed_releases.py             # regenerate chronological table + CSV
```

Then update the two Artifacts (`open-items.html`, `confirmed-releases.html`) if their numbers
changed, and commit + push:

```bash
git add -A && git commit -m "..." && git push origin main
```

Git: repo is `github.com/m4s-ai/snoredex-data`, branch `main`, remote `origin`, credentials
already configured (pushes have been working). End commit messages with the
`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer. LF→CRLF warnings on commit are
normal on Windows and harmless.

## 8. Immediate next actions (in priority order)

1. **The 5 Portuguese manual-review units** — check LigaPokemon via the user's Chrome for
   `PPS1 VIV 131` and `PPS3 LOR 143`. (`xPRE` is an Additionals product that may not appear on a
   marketplace as its own entry.)
2. **The 9 open units** — `BA20`/`WCD23` ES+PT want a photo or a localized retail listing; the
   four Asian deck products (`sA`, `mP1`, `svG`, `svIba`) want a sealed product listing from a
   seller in that market.
3. Anything the owner supplies next (they have been feeding specimens and corrections card by
   card; expect more).

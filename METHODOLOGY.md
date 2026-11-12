<!-- doc: role=evidence ladder, finish model and source techniques; stage=public -->
# Methodology

How a claim in this dataset becomes a fact, how absence is handled, how finishes are evidenced,
and which source answers which question. The rules here are enforced by `scripts/check.py` where a
rule name is given.

## How a claim becomes a fact

**One claim, one verdict.** A legacy language claim (`data/claims.json` `languageClaims`) asks
whether one Cardmarket product exists in one language. It carries a raw `repositoryVerdict`
(`confirmed`, `contradicted`, `needs-manual-review`, `pending`, or `out-of-scope` for code cards)
and an `applicationStatus` that says what an application may conclude. Anything resolved must cite
a provider, an evidence text, a `sourceType` and the granularity of its evidence.

**Every source is ranked.** `providerId` names it and `corroborated` says whether a second provider
agreed independently. The providers and their tiers are in `data/evidence.json` (`providers`):

| Tier | Meaning |
|---|---|
| 1 | Primary: the publisher's own records (official databases, checklists, product pages) and an inspected physical specimen |
| 2 | Strong secondary: specialist references (Bulbapedia, TCGdex and the like), an exact Cardmarket product image or seller photograph, and a collection-owner attestation |
| 3 | Weaker secondary: retailer and community sources, single-source wikis |
| 5 | Not external evidence: the Cardmarket catalogue this project exists to check, and internal derivations |

Tiers 1-3 grade external evidence, strongest first. Tier 5 is not a weaker rung: it marks what is
not external evidence. There is no tier 4.

**A single source may carry a claim, and usually does.** The rule "E3" is *checkable or strong*:
uncorroborated evidence with **no URL** — the owner's word, a card inspected in hand — must come
from tier 1 or 2, because nobody else can go and look at it. A tier-3 page anyone can open may
stand alone. An unlinkable claim from a weak source is neither. Corroboration is preferred and
uncommon, so read the tier beside a claim rather than assuming it.

**Grade by what the claim rests on.** `providerId` is the source the claim would fall over without,
not the strongest source standing near it. A specimen-backed claim cites its stable id
(`sourceRef: "specimen:SPEC-nnnn"`, resolved in `verification/specimens.json`); only a cited
specimen may claim specimen authority. Owner attestations and absence adjudications keep their own
evidence and do not imply a photographed card.

**Granularity decides what a confirmation reaches.** `evidenceGranularity` records whether the
evidence names the exact card (`specimen-or-card`), only its product or set (`product-or-set`), its
market or era, or a sibling. A confirmed claim is `exists` only when the evidence reaches the exact
card, or a product-level observation positively carries to it (`evidenceInference: carries`, for
example a card number inside the set's printed run). Otherwise it is `needs-evidence`: retained, but
not treated as established.

**Language truth and finish truth are separate layers.** The language claims answer "was this
printed in this language?"; the finish units (`claims.finishUnits`) and each printing's `finish`
answer "which finishes exist for this set number and language?". A confirmed language claim never
implies a finish.

## How absence is handled

No source settles an absence, at any tier. A source that fails to list a printing has a gap;
official sources confirm only what they name for the matching language and region. Blank cells,
dashes, missing columns, empty parameters, zero-result searches, HTTP errors and catalogue omissions
all stay unknown.

A `contradicted` claim means an outside source disagrees with Cardmarket. Converging evidence from
dependable sources is the material the collection owner weighs; only their adjudication
(`verification/owner_adjudications.json`, cited by `adjudicationId`) turns a contradiction into
`not-printed`. Without one the application status is `disputed`, which never means "does not
exist". `not-printed` means **no regular release**: a proof copy or an error card is a separate
category and does not falsify it.

Market history (when a language market opened), campaign geography (a Japan-only food promotion)
and omitted promo rows are context, never absence rules: Japan's Marumiya `XY-P 149` and Korea's
Kisstick sausages `XY-P 167` are the same card, each market running its own tie-in.

## Finishes, foil patterns and stamps

Finish availability is modelled per set number and language, as **positive evidence only**. An
unlisted finish stays `pending`. Only an owner `finishDecisions` entry closes a unit's list, and it
names exactly the finishes the evidence already found: it never introduces one. The owner may also
reject a finish a source positively claims through `rejectedFinishes` (Japanese PCG3 062/084 is holo
only although TCGdex reports `normal`).

| Evidence | What it can establish |
|---|---|
| Official checklist with a legend and finish columns | the listed versions for that set, card, language and region |
| Official card or product database, sealed-product contents | a named printing, treatment, stamp, size or distribution |
| TCGdex `variants` flag `true` | that finish for the returned card; `false` or missing refutes nothing |
| TCGCSV / TCGplayer product with a price subtype | a marketplace claim (`marketplace-claimed`) for Normal, Holofoil or Reverse Holofoil |
| PSA cert, spec or registry entry | the exact named variety; never population counts or omissions |
| Identified physical scan | the visible finish, pattern, marking and size of that specimen |
| Owner attestation | an explicit field-specific determination (`ownerAttestedFields`); it does not close a list |

**Technical finish and collector family.** `finish` is the auditable value (`non-holo`, `holo`,
`reverse-holo`, `mirror-holo`, or `unknown`). The site presents three families, where Reverse Holo
covers both `reverse-holo` and `mirror-holo`; the technical value is never collapsed. `foilPattern`
is an optional positive description of a distinctive treatment: a null value neither asserts an
unidentified pattern nor proves a plain surface, and no pattern is invented to fill it.

**Stamps and finishes are separate fields.** An EX-era set-name stamp intrinsic to the reverse
design (`DF 10`) is `markings.role = reverse-holo-treatment` on a `reverse-holo`. Later prerelease,
Staff, Play!, retailer, Pokémon Center and championship marks are `distribution-promo` and do not
imply a reverse holo; the finish needs its own source.

**Recording what a photograph shows.** A finish claim rests on a feature a person can point at in
the retained image — a mirror band, a line texture, a Poké Ball or Master Ball outline, a set-logo
stamp — quoted in the specimen's `physicalObservation.basis`. Ordinary glare and printed pastel
gradients are not holo features, and a vision model's reading is a lead, never the finish: measured
models misread mirror holos and called non-holos reverse. A record without a `physicalObservation`
says nothing about finish; that silence is not evidence of non-holo.

**A visible mark, and its visible absence, establish a version.** If a positive source documents
exactly two versions that differ by a printed mark, a complete, legible face settles which version
a copy is. EX Dragon Frontiers 1–12 is the worked example: the official checklist gives two foil
versions and the reverse holo carries the set-logo stamp in the artwork, so a legible Italian DF 10
without the stamp is the regular holo. Other set-specific cues:

- **FireRed & LeafGreen:** the reverse holo carries its energy-symbol and Poké Ball pattern outside
  the artwork window, rules box included; the regular holo has foil only inside the artwork. Other
  EX sets use their own reverse patterns; never carry this one over.
- **Rising Rivals Rival Season print:** a diagonal crosshatch foil, distinct from both holo and
  reverse holo.
- **Western Jungle:** 11/64 is holo and 27/64 non-holo in every Western language, in both editions
  (owner, 2026-09-10).

**Editions.** For a set printed in both editions, a visible 1st Edition mark is 1st Edition and a
visibly empty mark position on a complete, legible face is Unlimited; a crop that hides the
position leaves the edition unknown. Localities without an edition system (Korean, Chinese, SEA)
never get one. A card documented in both editions is one item per edition. The mark sits:

| Era | Position |
|---|---|
| WotC | left, under the artwork |
| e-Card | beside the set symbol, lower right |
| DP, Pt | lower left, beside the copyright line |
| BW (Japanese) | lower left, left of にげる |
| PCG (Japanese) | lower left, immediately left of the code |

**"Mirror" in Chinese sources is not `mirror-holo`.** Simplified Chinese sources call the Western
holo 镜面: "R and above are mirror-processed foil" means `holo`. The technical `mirror-holo` is a
reverse holo where everything outside the artwork reflects solidly; a pattern on that foil (Poké
Ball, Master Ball, star, sparkle) is `reverse-holo` with its `foilPattern`.

**Multiple views of one card.** Each photograph keeps its own SPEC record. An additional view links
to its primary with `sameCardAs: {specimenId, basis}`; views record only their own positive
properties, combine without conflict, and never count as independent corroboration. A shared number
or artwork alone never joins two cards.

**The owner's rarity pattern is a research guide, not evidence.** Commons and Uncommons are usually
non-holo; Rares non-holo and/or holo (since Scarlet & Violet every Rare is holo); Western sets add
reverse holos in era-specific forms; Asian languages other than Simplified Chinese carry reverses
mostly in high-class and special sets. It ranks research; it confirms and refutes nothing.

## Source techniques

Which source answers which question, how to query it, and the traps. Every source below is
positive only. A failed fetch is an access caveat, not evidence; do not repeat an unchanged failed
request without a new lead or access method.

### Cardmarket

- Product pages, language filters, offers and counts are routing metadata, never localized-card
  evidence. There is no open API; a rolling quota of about 55 requests answers HTTP 429. Use the
  in-app browser. An agent never solves a bot check (HTTP 403 with a Cloudflare interstitial, which
  waiting does not clear): navigate once more, and if it still stands, ask the owner to clear it in
  the browser pane or to send the image address.
- A retained exact product image (`product-images.s3.cardmarket.com`) or seller photograph supports
  only what is visible on the pictured card face, filed as a `SPEC-nnnn` record. A selected language
  filter is never projected onto an image printed in another language.
- Seller photographs hang on the individual offers of a product page and show real cards
  (SPEC-0648 to SPEC-0652). Fetch them whenever the browser reaches the product page without a bot
  check: filter the offers by language and, where the set has both, by edition, and retain the
  article-scan URL (`marketplace-article-scans.s3.cardmarket.com/<article>/<article>.jpg`) as the
  record's `photographSource`.
- Cardmarket codes: `x<SET>` is a special treatment of a card from `<SET>` (patterned reverse,
  retail stamp) whose printed number belongs to `<SET>`; `PPS<n> <SET>` is Play! Pokémon Prize Pack
  Series `<n>`, a stamped reprint. Prize Packs and `x` printings are separate cards and need their
  own evidence; nothing is inherited from the base card.

### Bulbapedia

- Plain fetches answer 403 and long pages truncate. Drive the MediaWiki API from inside the browser
  on the Bulbapedia origin:
  `fetch('/w/api.php?action=parse&page=' + encodeURIComponent(title) + '&prop=wikitext&format=json&formatversion=2&redirects=1', {credentials: 'same-origin'})`.
  Batch about ten titles per call with about 900 ms spacing.
- **Always pass `redirects=1`**: Japanese set names redirect to the English article, and the stub
  looks exactly like "no Snorlax here". Find titles with
  `action=query&list=search&srsearch=incategory:"Simplified Chinese expansions"`.
- **One article per language**, by suffix: `(TCG)` Japanese and English, `(KTCG)` Korean,
  `(TCTCG)` Traditional Chinese, `(ITCG)` Indonesian, `(ATCG)` Simplified Chinese expansions,
  `(SCTCG)` Simplified Chinese promos. Each language's promo series numbers independently: match on
  card identity, never on the number alone.
- **Articles carry both numberings:** `{{Setlist/entry}}` rows use the Japanese number,
  `{{Setlist/nmentry}}` rows the English one.
- **Deck and collection products** list their markets in the `DeckInfobox` `release=` field, using
  market names ("Mainland China" = Simplified Chinese, "South Korea" = Korean). Set and product
  articles carry official localized names in the "In other languages" table (`ko=`, `pt_br=`,
  `it=`, `fr=`, `de=`, `es=`): positive evidence of that release. A parameter present and empty is
  not the same as an absent one, and neither proves non-release.
- **The cross-language index** covers main expansions only, and has two table shapes: Sword & Shield
  onward lists Japanese, English, Traditional Chinese, Indonesian, Thai and Korean; Sun & Moon and
  earlier list Japanese, English and Korean only. A missing column or blank cell is never evidence;
  search it by the Japanese name, which is always present.
- **When the set code is missing from the text, read the set-symbol image**
  (`action=query&prop=imageinfo&iiprop=url&titles=File:...`). The images are tiny RGBA: composite
  onto white and upscale. A trailing `F` (`sc1a F`) marks the Traditional Chinese release and is
  part of the identifier. Match on number, set size, rarity and regulation mark together.
- `Snorlax (TCG)` lists every card with `jpset=`/`enset=` pairs (Japanese↔English only). Card
  articles' "Release information" often names the originating Japanese set. A redirect target that
  joins two promo articles is a same-work lead, not an identity merge.
- Cardmarket's names do not match Bulbapedia's for Chinese products (Azure Shadow → *Marine Shadow*,
  Brave Stars → *Gallant Galaxy*, Chasing Glory Together → *Together in Pursuit of Glory*, Dark
  Crystal Blaze → *Ardent Obsidian*, Battle Party Dream Together → *Battle Party: Shared Dream*) or
  for renamed Japanese sets (Tag Bolt → *Team Up*, Matchless Fighters → *Peerless Fighters*, Shocking
  Volt Tackle → *Amazing Volt Tackle*, XY Beginning Set → *Kalos Starter Set*). Resolve them by
  category search or `redirects=1`, never by similarity.
- A shared article carries several markets' release dates (`enrelease`, `jarelease`): the market
  of the claim decides which applies.

### Official Japanese database (`pokemon-card.com`)

- `card-search/resultAPI.php?keyword=<UTF-8>&se_ta=&regulation_sidebar_form=all&pg=&illust=&sm_and_keyword=true&page=<N>`.
  Send the full parameter set and require the response to echo the keyword, `regulation=all` and the
  page; a short query silently returns the Standard listing. The page parameter is `page`, not `pg`.
- The fuzzy search also returns ゴンベ (Munchlax) and カビゴンドール (Snorlax Doll): exclude them by
  their explicit identity. Promo names need exact matching (`カビゴンGX` is inside `イーブイ&カビゴンGX`).
- `details.php/card/<id>/regu/all` gives the printed number, the set code from the image path, and
  the illustrator. Read the illustrator from its anchor (`<div class="author"><a>`), never from
  flattened page text, where it runs into stage labels.
- The card search has no finish field. Finishes come from the **product page**
  (`pokemon-card.com/ex/<set>/index.html`, which names ミラー仕様 and レアリティ); not every product
  has one.
- Specific rarity queries for Snorlax return nothing while the global queries return records; that
  is an omission, not a rule about rarity classes.

### Official Asia database (`asia.pokemon-card.com`)

- `/{tw,id,th}/card-search/detail/<n>/` gives the local set code, number, product link and
  illustrator. Search with the local name: Thai needs คาบิกอน, Traditional Chinese 卡比獸; only
  Indonesian answers to "Snorlax". It omits secret rares above the printed set size, Thai AS1b/AS5a
  and most SM-P.
- **Never take the set code from the mark asset's filename**; render the badge
  (`/<locale>/card-img/mark/<file>.png`, upscale) or read the card image. Thai codes take a `T`
  suffix and Indonesian an `I` (`sc1a T`, `sc1D I`); Sun & Moon-era codes take an `A` prefix instead
  (`AS1b`, `AC3a`). One code can name two products, and the code is not always the Japanese one
  (`136/193` is `m2a` in Traditional Chinese but `ma3` in Thai and Indonesian): identify by number,
  denominator, card name and regulation mark.
- When a structured field is missing or looks like a placeholder, check whether the image carries
  it before recording anything.
- Thai, Indonesian and Traditional Chinese have catch-up sets of already-released cards under local
  codes and numbers, and a card can live in another set entirely (`svLN 010` in Traditional Chinese
  is the standalone promo `SV-P 215`). Check for the card under another set before treating a
  language as impossible.

### The publisher's per-locale card archives

The best Western route: card pages in the locale's own language, tier 1. Paths are not guessable:
`it` `/it/gcc/archivio-carte`, `br` `/br/pokemon-estampas-ilustradas/cartas-de-pokemon`, `de`
`/de/pokemon-sammelkartenspiel/pokemon-karten`, `fr` `/fr/jcc-pokemon/cartes-pokemon`, `es`
`/es/jcc-pokemon/cartas-pokemon`, `us` `/us/pokemon-tcg/pokemon-cards`; there is no Russian archive.
Query `?cardName=snorlax&pl2=on` (expansion id as a bare flag). A filter pill is not a coverage
statement, and some locales silently ignore the set filter: the only signal is a returned card
whose own `/series/<set>/<number>/` path matches the set asked for.

### TCGdex (`api.tcgdex.net`)

- Card existence in many languages and positive `normal`/`holo`/`reverse` flags. A flag `true`
  confirms; `false` or missing refutes nothing.
- **It answers 200 for what it does not hold**: `ru/sets/xy2` returns a full `cardCount.total` and an
  empty `cards[]`; identical gaps answer 200 or 404 at random. Only a non-empty `cards[]`, or a card
  endpoint answering 200, shows coverage. Coverage ends by era, not language (Italian and Portuguese
  are full for `xy2` and empty for `pl2`). Korean and Simplified Chinese are served but sparse.

### Official checklists and marketplace exports

- Official checklist PDFs (`assets.pokemon.com`, `d1wx537rtdixyy.cloudfront.net`) confirm the rows
  and finish columns they list, for the language printed in the document only. A matching code can
  name another product (`sm1` PDFs describe the Sun & Moon expansion, not the SM promos).
- TCGCSV (`tcgcsv.com/tcgplayer/3/<group>/{products,prices}`) gives reproducible TCGplayer product
  identity and positive subtypes, recorded as `marketplace-claimed`. A product without a current
  price row is silence, not absence.
- PSA cert, spec and registry pages name exact grading varieties; never use population counts.

### Other sources

- **pokumon.com** (`?s=<query>`): one row per Asian market printing with its campaign, but one lumped
  "English" row for the West and English names only. Never use its absence against a Western
  language.
- **Elite Fourum** runs Discourse: `/search.json?q=<query>` and `/t/<id>.json`. Language tables use
  flag emoji; parse `title=":xx:"` from the `<img>` tags.
- **PokéCottage** loads its Snorlax rows from
  `pokecottagecdn.com/mastersets/data/143-snorlax-data.js`: tier-3 positive rows; inspect it and the
  matching set guide when a new set contains Snorlax.
- **Korea:** `pokemoncard.co.kr` answers HTTP 410 to scripts but works in a browser;
  `pokemonkorea.co.kr` is obsolete; full-size card images on `cards.image.pokemonkorea.co.kr` stay
  reachable and their "Illus." lines match the catalogue.
- **52poke** (`wiki.52poke.com/api.php`) names card pages by the Japanese set code, so its pages
  evidence the card, not a Simplified Chinese printing.
- **LigaPokemon** bans datacenter IPs (Cloudflare 1008): use an authenticated user browser session.
- **LATAM Spanish:** the official `pokemon.com/latam` site; the edition exists from Journey Together
  (2025) onward and differs in attack translation, set name and set code.
- **Japanese editions:** closed Yahoo! Auctions and Yahoo!フリマ listings (`auctions.c.yimg.jp`
  originals) show edition marks; eBay item pages answered 403 and aucfan 503.
- **GitHub issue attachments** are blocked at `github.com/user-attachments`, but the issue's own HTML
  page contains the resolved `private-user-images.githubusercontent.com` URLs. HTML-unescape them
  (`&amp;`), strip a trailing `\` and embedded `&`, download, and commit the bytes to the photo
  repository (specimen intake): a signed URL is perishable.
- **Dead ends** worth not repeating: `ptcg.cn` (a Magic site), `pokebeach.com` (403 to scripts),
  `namu.wiki` and `pokeos.com` (JavaScript-rendered), `krystalkollectz.com` (a shop),
  `jihuanshe.com` (an app landing page).

### Illustrators and localized names

An illustrator belongs to the artwork: every print of the same artwork, including a rainbow
recolour, shares it, and a credit may be carried to another print only after comparing the images.
The credit printed on the card beats a database field. Localized card names come from exact-print
sources; trainer-owned names are never derived (Hop is Nabil in French, Paul in Spanish, Lupo in
Portuguese). Before calling a glyph illegible, check the stored image resolution.

## How the repository is built

`data/` is the curated source, validated by `scripts/check.py`; `scripts/build.py` writes the
catalogue, both pages, the database and the tracker template from it, and
`python scripts/regen.py` runs the whole gate. The historical Cardmarket harvest and the old
pipeline that produced the first data are not reproducible and are preserved only at the tag
`refactor-reference-20261109`; the candidate universe they established is frozen in
[`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json).

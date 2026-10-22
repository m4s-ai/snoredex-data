<!-- doc: role=retained data-gap research evidence and intake report; stage=history -->

> Historical record — research snapshot from 2026-10-22; current gaps are determined by canonical stores.

# Catalogue data-gap research — 2026-10-22

A read-only inventory of `collector_catalogue.json` at `355c7f6c` (1,030 items) listed every
empty or incomplete information field. Ten research workstreams covered each gap class; every
target is accounted for in its workstream's `findings.json` as a finding or as an unresolved row
with attempts and next leads. An unsuccessful search establishes no absence.

| Workstream | Targets | Found | Unresolved |
|---|---:|---:|---:|
| [id-th-sets](id-th-sets/) — Indonesian/Thai local set names | 50 | 48 | 2 |
| [korea](korea/) — Korean/LATAM set names, Korean illustrators | 67 | 66 | 1 |
| [chinese](chinese/) — TW/CN set names, S-Chinese illustrators | 83 | 74 | 9 |
| [asia-artists](asia-artists/) — TW/ID/TH illustrators | 101 | 101 | 0 |
| [jp-west-artists](jp-west-artists/) — Japanese/Western illustrators | 80 | 79 | 1 |
| [local-names](local-names/) — localized printed card names | 1,030 items | 905 items | 125 |
| [dates](dates/) — non-day release dates | 53 | 5 | 48 |
| [edition](edition/) — unresolved editions | 160 | 50 | 110 |
| [finish](finish/) — marketplace-only and missing finishes | 146 | 48 | 118 |
| [numbers-images](numbers-images/) — collector numbers, missing images | 25 | 19 | 6 |

Every finding carries its source URL (or repository path), actual retrieval time, the verbatim
excerpt or visual transcription, and the sha256 of the retained bytes. Bytes already in the
repository (specimens, product images, retained discovery runs) are cited by path rather than
copied; everything else is retained here and listed in
[retention-manifest.json](retention-manifest.json). Two public press releases are retained with
PR contact e-mail addresses redacted; `originalSha256` records the bytes as fetched.

## Applied in this batch

[`integrate_data_gap_research_20261022.py`](../../passes/integrate_data_gap_research_20261022.py)
applies the unambiguous fields through their existing owners;
[integration-report.json](integration-report.json) accounts for every established value.

- **Local set names** — 121 local sets gain their source-native official name (Hangul, Thai,
  Chinese and Indonesian verbatim; translations are marked as such).
- **Illustrators** — 142 source-first prints and 66 legacy Cardmarket products. Methods: official
  database credit, transcription from an image of the exact print, or propagation along a visually
  confirmed identical artwork. The owner stated on 2026-10-22 that an illustrator belongs to the
  artwork: every print of the same artwork in every language and variant shares it; only a changed
  or different artwork can differ. The credit printed on the card wins over a database text field
  (TW sc1b 165/153). The credit printed "0313" is displayed in that form where two Asian databases
  render "313"; the source-native value is retained.
- **Localized card names** — the new reviewed registry
  [`verification/local_card_names.json`](../../local_card_names.json) holds 16 official species
  names, 553 exact-print release names and 122 reference name patterns. An exact-print name wins;
  otherwise a card whose English name is only the species takes the species name. Mechanic and
  trainer-owned names are never derived. Filled `localCardName`: 248 → 1,010 of 1,030.
- **Release date** — CN S-P/CS 061 gains 2023-08-19 from the official event page.

## Held for owner decision

1. Whether a rainbow/hyper-rare recolour of an SR composition counts as the same artwork
   (KR sm9 115/095 HR, TW AS5a 222/184 HR propagations).
2. Whether the four SWSH068 Build & Battle items (FR, DE, IT, ES) are that promo rather than the
   separate Cosmos-holo store giveaway; the official press releases date the box 2020-10-31.
3. Whether the Hop's Snorlax pattern names (e.g. "Hops Relaxo", "Ronflex de Nabil",
   "Snorlax de Paul", "Snorlax do Lupo") may be derived for the 18 remaining items.
4. Possible duplicate local sets (ID `S10a I`/`s10a I`, TH `s10a`/`s10a T`) and the S-Chinese
   `via-…:unknown-local-set` releases that appear to duplicate identified CN releases and carry
   Japanese release dates.
5. Seller photographs that show a different finish from a marketplace-only candidate
   (see [finish/findings.json](finish/findings.json) `unresolved`).
6. Whether a DP Battle Pokédex identifier (`DPBP#174`) may be stored as a collector number.
7. Whether items whose card is positively documented in both 1st Edition and Unlimited are split
   into one item per edition.

Edition, finish, image and collector-number findings are retained for those decisions and for the
next intake; they are not applied here.

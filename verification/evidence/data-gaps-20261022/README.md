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
  Chinese and Indonesian verbatim; translations are marked as such) as appended
  `local-set-name-record` entries, so older admission passes that rebuild their own profile records
  on replay cannot erase them. Items with a local set name: 796 → 1,021 of 1,030.
- **Illustrators** — 144 source-first prints and 66 legacy Cardmarket products (site rows with an
  artist: 878 of 883). Methods: official database credit, transcription from an image of the exact
  print, or propagation along a visually confirmed identical artwork. Owner decisions of
  2026-10-22: an illustrator belongs to the artwork, so every print of the same artwork shares it;
  a rainbow/hyper-rare recolour of the same composition is the same artwork; and a credit read
  from a retained product image needs no SPEC record because it attests the artwork, not a
  physical printing. Propagated product credits are graded `internal-derivation`. The credit
  printed on the card wins over a database text field (TW sc1b 165/153). "0313" is displayed as
  printed where two Asian databases render "313"; the source-native value is retained.
- **Localized card names** — the new reviewed registry
  [`verification/local_card_names.json`](../../local_card_names.json) holds 16 official species
  names, 553 exact-print release names and 122 reference name patterns. An exact-print name wins;
  otherwise a card whose English name is only the species takes the species name. Mechanic and
  trainer-owned names are never derived. Filled `localCardName`: 248 → 1,010 of 1,030.
- **Release dates** — CN S-P/CS 061 gains 2023-08-19 from the official event page. The four
  ordinary SWSH068 prints in French, German, Italian and Spanish gain 2020-10-31: the owner
  identified SWSH068 as the Vivid Voltage prerelease promo of the Build & Battle Box, which the
  localized TPCi press releases date to that day (declared as
  `tpci-vivid-voltage-build-battle-dates`). The Staff-stamped prerelease variant and the separate
  Cosmos-holo giveaway are not dated.

## Owner decisions (2026-10-22)

The five questions raised by this research were decided by the collection owner:

1. **Hop's Snorlax names** are derived from the reviewed patterns (`derivedPatternCardNames`).
2. **Duplicate ID/TH s10a local sets** are analysed and proposed in issue #431; no data change.
   The **S-Chinese `via-…` releases** are merged into the identified CN prints by
   [`merge_cn_via_releases_20261022.py`](../../passes/merge_cn_via_releases_20261022.py); items
   now carry the CN set, number and date instead of the Japanese harvest date.
3. **Seller finish photographs** are filed as SPEC records; every photograph in
   [finish/findings.json](finish/findings.json) was already retained under its source URL
   (for example SPEC-0444, SPEC-0453, SPEC-0454, SPEC-0456), so no new record was needed.
   Marketplace-only candidates stay unchanged.
4. **`DPBP#174`** is shown as the DP1 Snorlax Lv.35 collector number.
5. **Edition-documented cards are split** into one item per edition by
   [`split_documented_editions_20261022.py`](../../passes/split_documented_editions_20261022.py):
   Jungle 11/27 in all seven Western languages, Gym Heroes 33 (English) and the Japanese PCG1 074,
   PCG3 062, PCG9 001 and e-Card 5 062. Specimen photographs record the edition their face shows
   (owner rule: a visible 1st Edition mark, or a visibly empty mark position); see
   [edition-marks-20261022](../edition-marks-20261022/intake-manifest.json) and the owner's e-Card 5
   photographs SPEC-0632/SPEC-0633.

Image and collector-number findings without a decision are retained for the next intake.

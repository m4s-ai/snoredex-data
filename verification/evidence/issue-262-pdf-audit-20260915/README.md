<!-- doc: role=official Thai set-list discovery and PDF review record for issue 262; stage=reference -->

# Official Thai set-list PDF audit — 2026-09-15

Research for #262, retained in draft PR #383. This increment adds source observations and discovery coverage, not canonical card or finish claims.

Follow-up correction: [the subsequent Thai review](../issue-262-thai-further-20260915/README.md) found **AS5a 117/184 RR on page 13**, overlooked in this initial triage. The four candidates reported below describe this earlier pass; the cumulative Thai PDF queue now has five image-backed candidates. No claim of exhaustive card transcription is intended.

## Scope and completion

- Followed 83 distinct non-accessory product-page links from the [official product index](https://asia.pokemon-card.com/th/products/): 23 pages link PDFs, 34 link online card lists, and 26 expose neither type of link in the inspected HTML. No product-page retrieval failed.
- Downloaded and parsed all **27 distinct linked PDFs**, **464 pages**, **2,283,297,789 bytes** (about 2.28 GB). All pages received contact-sheet visual triage for Snorlax / Eevee & Snorlax; selected matches were enlarged. This is not a complete transcription of every card on all 464 pages.
- Followed every pagination link in the [official online set directory](https://asia.pokemon-card.com/th/card-search/): five numbered pages, six URL fetches because the root and `?pageNo=1` both identify page 1; **83 distinct set-list URLs**. Individual online card-result pagination is outside this PDF audit.
- The combined index below has **95 distinct set-code entries** after case-insensitive matching. It is the observed source index, not an assertion that every Thai release or product is covered. AS-era PDFs extend beyond the current online set directory.
- No Thai Snorlax text matches were extracted automatically. Image/outline-based pages and sample-watermark text make that result unsuitable as negative evidence; visual review supplied the observations.

## Card observations

| Card shown | PDF page | Printed rarity | Disposition | Retained excerpt |
|---|---:|---|---|---|
| AS1b 112/150 — Snorlax-GX | 13 | RR | candidate | [image](as1b-112.png) |
| AS5a 142/184 — Snorlax | 16 | R | corroboration | [image](as5a-142.png) |
| AS5a 203/184 — Eevee & Snorlax-GX | 23 | SR | candidate | [image](as5a-203.png) |
| AS5a 204/184 — Eevee & Snorlax-GX | 23 | SR | candidate | [image](as5a-204.png) |
| sc1a T 127/154 — Snorlax | 15 | U | corroboration | [image](sc1a-127.png) |
| sc1b T 119/153 — Snorlax V | 14 | RR | corroboration | [image](sc1b-119.png) |
| sc1b T 120/153 — Snorlax VMAX | 14 | RRR | corroboration | [image](sc1b-120.png) |
| sc1b T 165/153 — Snorlax V | 19 | SR | candidate | [image](sc1b-165.png) |
| sc3b T 126/158 — Snorlax | 14 | R | corroboration | [image](sc3b-126.png) |
| s8b T 126/158 — Snorlax | 15 | not asserted | source-discrepancy | [image](s8b-126-sample-mismatch.png) |

**Four new research candidates:** AS1b 112/150 RR, AS5a 203/184 SR, AS5a 204/184 SR, and sc1b T 165/153 SR. None has a matching Thai card-release number in the authoritative graph at `cfa5acb`. They remain explicit admission candidates: review the PDF surface capability, retain/import the reference under the existing specimen contract, map the Work, and regenerate before publishing them as accepted releases. The two AS5a cards have distinct printed numbers and artwork; they must not be collapsed into one variant.

**Publisher sample discrepancy:** the s8b PDF prints `s8b T 126/158` on Snorlax, beside Blissey V `127/184`. The existing catalogue identity is `s8b 126/184`. The retained two-card excerpt preserves that context. This is a discrepancy in a publisher sample, not evidence for a new s8b 126/158 release and not permission to overwrite the catalogue number.

Five observations corroborate identities already present: AS5a 142/184, sc1a T 127/154, sc1b T 119/153 and 120/153, sc3b T 126/158. The last card already has physical-photo Holo evidence (SPEC-0526); this sample adds no new finish claim. AS5a 142/184 also had an earlier PDF citation; rediscovery is not a new independent provider.

Visible foil-like artwork is a publisher depiction, not a measurement of a physical specimen. A flat-looking sample does not establish Non-Holo. No physical finish or exhaustive rarity-to-finish mapping is admitted. The prior 13/28 gap-free Thai audit therefore remains unchanged; the four candidates are outside that existing denominator.

## Set-list index

“Not located” means no PDF was found in this bounded product-index pass; it never means no PDF or card exists. PDF filenames containing `NoSR`/`noSR`, and lists that stop before secret numbers, must not be treated as complete rarity inventories. Each linked PDF has its hash, exact size, retrieval timestamp and page count in `pdf-processing.json`.

| Set code | Official PDF | Pages | Official online list |
|---|---|---:|---|
| AS1a | [BoosterPackA.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/BoosterPackA.pdf) | 19 | Not in inspected directory |
| AS1b | [BoosterPackB.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/BoosterPackB.pdf) | 19 | Not in inspected directory |
| AS2a | [BoosterPackA2.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/BoosterPackA2.pdf) | 22 | Not in inspected directory |
| AS2b | [BoosterPackB2.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/BoosterPackB2.pdf) | 22 | Not in inspected directory |
| AS3a | [BoosterPackA3.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/BoosterPackA3.pdf) | 23 | Not in inspected directory |
| AS3b | [BoosterPackB3.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/BoosterPackB3.pdf) | 23 | Not in inspected directory |
| AS4a | [AS4a.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/AS4a.pdf) | 23 | Not in inspected directory |
| AS4b | [AS4b.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/AS4b.pdf) | 23 | Not in inspected directory |
| AS5a | [AS5a.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/AS5a.pdf) | 24 | Not in inspected directory |
| AS5b | [AS5b.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/AS5b.pdf) | 24 | Not in inspected directory |
| AS6a | [6th_BoosterA.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/6th_BoosterA.pdf) | 26 | Not in inspected directory |
| AS6b | [6th_BoosterB.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/6th_BoosterB.pdf) | 26 | Not in inspected directory |
| M-P | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=M-P) |
| MA1 | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MA1) |
| MA2 | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MA2) |
| MA3 | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MA3) |
| MA4 | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MA4) |
| MA5 | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MA5) |
| MA6 | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MA6) |
| MAAF | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MAAF) |
| MAAL | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MAAL) |
| MATH | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MATH) |
| MATK | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MATK) |
| MATL | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MATL) |
| MATS | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=MATS) |
| S-P | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S-P) |
| S10A | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S10a) |
| S10B | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S10b) |
| S10D | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S10D) |
| S10P | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S10P) |
| S11 | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S11) |
| S11A | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S11a) |
| S12 | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S12) |
| S12A | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S12a) |
| s5a | [9upsS5a_v1.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/9upsS5a_v1.pdf) | 8 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S5a) |
| S5I | [S5I.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/S5I.pdf) | 9 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S5I) |
| S5R | [S5R.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/S5R.pdf) | 9 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S5R) |
| s6a | [S6a_9ups_in-number.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/S6a_9ups_in-number.pdf) | 8 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S6a) |
| s6H | [9upss6HSR.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/9upss6HSR.pdf) | 10 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S6H) |
| s6K | [9upsS6kSR.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/9upsS6kSR.pdf) | 10 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S6K) |
| s7D | [s7d_NoSR.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/s7d_NoSR.pdf) | 8 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S7D) |
| s7R | [s7r_NoSR.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/s7r_NoSR.pdf) | 8 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S7R) |
| s8 | [9ups_s8.pdf](https://asia.pokemon-card.com/th/archive/special/card/s8/9ups_s8.pdf) | 12 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S8) |
| S8A | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S8a) |
| s8b | [vs8b1.pdf](https://asia.pokemon-card.com/th/archive/special/card/s8b/vs8b1.pdf) | 21 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S8b) |
| s9 | [9ups_S9_noSR.pdf](https://asia.pokemon-card.com/th/archive/special/card/s9/9ups_S9_noSR.pdf) | 12 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S9) |
| S9A | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=S9a) |
| sc1a | [SC1_Set_A.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/SC1_Set_A.pdf) | 20 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SC1a) |
| sc1b | [SC1_Set_B.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/SC1_Set_B.pdf) | 19 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SC1b) |
| SC1D | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SC1D) |
| sc3a | [sc3_a.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/sc3_a.pdf) | 18 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SC3a) |
| sc3b | [sc3_b.pdf](https://asia.pokemon-card.com/th/archive/card/pdf/sc3_b.pdf) | 18 | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SC3b) |
| SCA | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SCA) |
| SCB | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SCB) |
| SCC | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SCC) |
| SCD | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SCD) |
| SCE | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SCE) |
| SCF | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SCF) |
| SH | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SH) |
| SV-P | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV-P) |
| SV10S | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV10s) |
| SV11S | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV11s) |
| SV1A | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV1a) |
| SV1S | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV1S) |
| SV1V | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV1V) |
| SV2A | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV2a) |
| SV2D | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV2D) |
| SV2P | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV2P) |
| SV3 | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV3) |
| SV3A | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV3a) |
| SV4A | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV4a) |
| SV4K | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV4K) |
| SV4M | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV4M) |
| SV5A | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV5a) |
| SV5K | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV5K) |
| SV5M | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV5M) |
| SV6 | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV6) |
| SV7S | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV7s) |
| SV8A | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=Sv8a) |
| SV8S | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV8s) |
| SV9S | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SV9s) |
| SVAL | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVAL) |
| SVAM | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVAM) |
| SVAW | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVAW) |
| SVDS | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVDs) |
| SVHK | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVHK) |
| SVHM | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVHM) |
| SVK | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVK) |
| SVM | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVM) |
| SVTG | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVTG) |
| SVTH | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVTH) |
| SVTL | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVTL) |
| SVTM | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVTM) |
| SVTR | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVTR) |
| SVTS | Not located | — | [list](https://asia.pokemon-card.com/th/card-search/list/?expansionCodes=SVTS) |

## Retention and reproducibility

- `product-page-audit.json`: 83 source URLs, product titles, response hashes, retrieval times, discovered links and retained exact PDF-link HTML fragments with separate excerpt hashes. Original HTML responses are local cache only.
- `online-set-index.json`: six fetched directory URLs and their response hashes/times, plus the complete deduplicated 83-link result. Extracted links are retained; full original HTML is local cache only.
- `pdf-queue.json` and `pdf-processing.json`: all 27 PDFs, original-byte hashes, actual retrieval times, extraction metrics and bounded visual-review status. Original PDFs and full contact sheets remain in ignored `verification/cache/thai-pdf/`; **their hashes do not mean that those 2.28 GB are retained in Git**.
- `card-observations.json` and ten PNG excerpts: repository-retained source observations with source PDF hash/URL, one-based page, crop rectangle in PDF points, render scale and excerpt hash. Crops preserve sample watermarks; they are derived excerpts, not physical photographs or original PDF files.
- Earlier URL probes remain in `../issue-262-followup-20260915/official-pdf-discovery.json`. Those transport checks are discovery history, not card-property evidence.

## Remaining source work

The bounded PDF queue is processed. For sets without a located PDF, use the linked online card lists and named product pages; do not extrapolate older checklist formats to newer sets. Product pages with neither link remain explicit discovery gaps in the audit JSON. Unlinked historical files, removed products and archives outside these indexes may still exist. The next admission work is the four exact-number candidates above; s8b needs a non-conflicting exact card source. Physical finish gaps still require evidence of the treatment itself. Keep PR #383 as a draft.

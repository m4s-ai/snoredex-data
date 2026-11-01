<!-- doc: role=bounded open-issue picture research; stage=history -->

> Historical record — research and integration snapshot of 2026-10-31/2026-11-01; canonical stores determine current values.

# Open-issue picture research — 2026-10-31

Historical research snapshot against main `2c6a8838` (full SHA in picture-inventory.json).
All nine open issues and their available comment pages were reviewed through the GitHub connector.
No open PRs were returned at the research snapshot. The sections below record that research-only stage: no claims, SPEC records, finish stores, issue bodies or
generated consumer files were changed. The downloaded files are research inputs, not imported specimens.

## Accepted integration — 2026-10-31

The research inputs were subsequently reviewed and integrated in the same issue batch.
The research-only statements below describe the earlier snapshot, not the completed intake.

- Imported seven exact-card fronts as SPEC-0663–0669 through `fetch_attachment.py` and
  [intake-manifest.json](intake-manifest.json). Six establish identity only. SPEC-0669 is an actual
  CS5aC 093/127 seller photograph with mirror-holo and vertical-line foil positively visible.
- Kept the CS2aC depiction out of intake because SPEC-0473/0474 already establish the card.
  The generic CSV5C back was excluded because its relationship to the pictured fronts is unknown.
- Retained original WebP bytes and conversion metadata in [sources.json](sources.json).
  Each accepted WebP was decoded losslessly to PNG and compared pixel-for-pixel before import.
- Reused SPEC-0323, SPEC-0553, SPEC-0622 and SPEC-0552 for the four already-photographed language
  questions. Reconciled ten exact-card language references with the guarded bulk repair
  `verification/passes/reconcile_picture_claims_20261031.py`; no status or absence decision changed.
- Added explicit local-code/number/variant finish bridges for s4 84 → CS2aC 086,
  s10a 077 → S10a F 077, s1H 70 → s1H 070 and s5a 93 → s5a 093. The CS2aC bridge follows the
  existing owner closure OAF-20260902-CS2aC-086-zh-Hans and its two actual SPECs. Other bridges
  project positively photographed holo only; no additional finish list is declared complete.
- Coalesced equivalent finish-store physical printings while retaining each source claim and
  migration disposition. Graph aliases reach collector predecessor IDs, specimen links and artwork
  evidence. Confirmed-first deterministic processing and a regression cover reverse input order,
  replay stability, alias references and rejection of invalid aliases.
- Preferred explicitly linked retained identity images over legacy product art, at `card-release`
  image scope. Existing exact-printing images keep priority; identity does not assert foil.
- Registered providers before projecting confirmed-language metadata in the core and scoped lanes;
  a regression enforces that dependency so a fresh provider retains its authority tier on the first run.
- Reference validation follows exact source-first citations through already-reviewed legacy rekeys.
  Negative cases preserve the language, printed number/denominator, native variant and exact-claim
  boundaries; a secondary photograph cannot borrow a neighbouring printing.
- Reviewed the new PAO, Excalibur and PikaQian surfaces as manual identity-only inputs. PikaQian
  requires the explicit retained-reference source type; there is no blanket host reclassification
  of historical assertions and no physical-finish capability. The exact CN seller-photo surface
  supports only the visibly inspected physical observation.

Main reconciliation: `db28300bf7b22b01569adb2da328f68b56ef3183` already contains the
owner-supplied Italian DF name, three local set names, and Italian DF 10 Holo SPEC-0662.
Those records are preserved. The unintegrated CS5aC observation was re-keyed to SPEC-0669
before replaying the canonical importer; no existing photograph was overwritten.

After projection, the collector contains **96 finish candidates and 3 research placeholders**;
only the **two Italian promo language questions** remain without card-level positive evidence.
The pending/partial pattern queue contains **57 finish units** after this integration.
Reference depictions do not resolve physical pattern questions. The other bounded searches,
blocked originals, LATAM xJTG remain open as recorded below.
No issues are closed and no publication or merge is part of this intake.
PR #454 review correction (2026-11-01): finish-bridge promotion retains the established
`PHYSICAL:specimen:SPEC-0552` and `PHYSICAL:specimen:SPEC-0553` identities, including the
owner-defined unknown-to-standard card-size default. Specimen and finish claims stay distinct.
The two real pre-bridge records and collector items are retained in
[standalone-promotion-regression.json](standalone-promotion-regression.json); replay, reversed input
order, unrelated-finish rejection and exact one-target holo migrations are tested. Before recovery,
the old projector applied to pinned main `db28300b` exactly equalled the PR graph, proving that the
reviewed hybrid base was preserved; the corrected projector regenerated only its owned slice.

Delivery validation is recorded separately in [integration-validation.json](integration-validation.json).

## What the SPEC check changed

The current catalogue has **98 finish candidates and 3 research placeholders**; the issue bodies
still describe 101 and 10. The current finish store has **58 units with pending/partial patterns**,
versus the earlier issue's 57. These are distinct denominators: one candidate item, one placeholder
item, and one finish-unit pattern question. They must not be added into a unique-card total.

[picture-inventory.json](picture-inventory.json) records all 98 candidate items, 3 placeholders,
58 pattern units and 6 language questions: **165 field rows**. It includes existing SPEC candidates,
their hashes, recorded properties, scope and consumer image scope. A same-language set/number match
is a reuse lead, not proof of the requested variant, edition, finish or size. Direct finish references
and legacy/local-code bridges were also checked. The 134 distinct existing photograph files referenced
by this inventory were present and matched their recorded SHA-256 values.

There were **21 distinct language/set/number keys with no matched retained SPEC photograph** in the
candidate/placeholder/pattern inventory before this search. Two additional Italian language questions
have regular/reverse images but lack the exact promo image. Every key below received a bounded search;
this is not an exhaustive search of every seller or a conclusion that a printing is absent.

### Reuse these records before asking for another image

| Issue / question | Already retained | What remains |
|---|---|---|
| #436 EXS vending image | SPEC-0661, distinct from SPEC-0200's Quick Starter printing | Already merged under #447. No new image search needed. |
| #439 seven older placeholders | SPEC-0440, SPEC-0625, SPEC-0028, SPEC-0030, SPEC-0462, SPEC-0463, SPEC-0609 | Already joined under #448. |
| #439 JP XY2 066/080 | SPEC-0225, SPEC-0573; SPEC-0586 explicitly establishes 1st Edition non-holo | The unresolved slot is Unlimited. Do not transfer the first-edition observation. |
| #439 TW M2a F 136/193 | SPEC-0310 / 0312 / 0313 | Retained publisher depictions cover base and two pattern identities, but have no physicalObservation. A bridge cannot invent the missing physical finish. |
| #439 TH MA3 136/193 | SPEC-0274 / 0275 / 0276 | Same distinction: images exist, physical finish remains unestablished. |
| #440 U0169, TW S10a F 077/071 | SPEC-0323 and SPEC-0324 | Exact positive images already exist; review their use in legacy claim semantics. |
| #440 U0508, KR s1H 070/060 | SPEC-0553 | Source-first citation exists; the legacy claim needs reconciliation, not another photograph. |
| #440 U0557, KR sm9 115/095 | SPEC-0622 | Direct U0557 citation already exists, despite the legacy unit retaining its older set-level source. |
| #440 U0601, KR s5a 093/070 | SPEC-0552 | Source-first citation exists; review the legacy reference. |
| #440 Italian CL 33 V2 | SPEC-0106 is Italian 33/95 **V1 reverse**, not the target promo | Exact promo still needs an image or other card-level positive source. |
| #440 Italian RR 33 V2 | SPEC-0117 is Italian 33/111 **V1 reverse**, not the target promo | Same limitation. |
| #438 / #441 CN legacy s4 84 → CS2aC 086/115 | SPEC-0473 holo; SPEC-0474 owner-confirmed reverse holo with star pattern, cited to F0057 | F0357 still shows candidates and pending pattern. Investigate the legacy/local-identity join before researching another photo. The separately downloaded PikaQian CS2aC image adds no necessary evidence. |
| #438 Western SM05 | SPEC-0653–0658 | These establish jumbo cards. They do not supply the missing **standard-size** localized finish photos. |
| #440 four disputed TW units | Owner decisions merged in #451 | No new existence picture is required to settle the absence question already decided by the owner. |

## Searches where the initial SPEC match found no retained photo

The original queries and additional seller links are retained in [search-rounds.json](search-rounds.json).
For reused SPECs above and elsewhere in the inventory, a missing finish remains open even when an identity
image exists. This round prioritized genuinely missing image records as requested.

| Language / card | Search routes and result | Next useful evidence |
|---|---|---|
| DE FL 15/112 reverse | German name/number/reverse search found [eBay 355976481073](https://www.ebay.de/itm/355976481073); original page inaccessible to web retrieval. | Retrieve the exact German front; verify reverse treatment visually. |
| IT DF 10/101 | Italian number/name search found [MyComics](https://mycomics.it/shop/snorlax-%CE%B4-specie-delta-ex-lisola-dei-draghi-10-101-italiano-holo-good) and [eBay 398168467015](https://www.ebay.it/itm/398168467015). MyComics says Italian holo; its exposed original and Next image endpoint returned 403. eBay page inaccessible. | Inspect the Italian face for localCardName and finish. Seller title alone was not applied. |
| PT BCR 109/149 reverse | Portuguese code and full-number searches, LigaPokemon domain search, MYP and seller routes. [MYP](https://mypcards.com/pokemon/produto/33239/snorlax) explicitly labels the image illustrative and exposes English attack text. No inspected Portuguese reverse photograph obtained. | Exact Portuguese seller front, including treatment. |
| PT PLS 101/135 reverse | Portuguese code/full-number and regional searches found generic prices and listings; no inspected matching front. | Exact Portuguese seller photo; do not substitute English Team Plasma listings. |
| DE KSS 26/39 reverse | Relaxo/full-number/reverse queries produced no inspected matching image. | Exact German treatment photo. |
| EN KSS 26/39 reverse | [Brickheads](https://www.brickheadscollectables.com/products/xy0-26h) advertises reverse, but its image link resolves to a coming-soon placeholder and it says images are representative. | Actual front showing reverse. This listing does not establish it. |
| FR KSS 26/39 reverse | Ronflex/full-number/reverse queries found general catalogue/price pages, no inspected reverse photo. | Exact French treatment photo. |
| IT KSS 26/39 reverse | Kalos, Italian, reverse and Easter-product aliases searched. No inspected target photo. The retained finish guide already distinguishes the Italian wave-holo research. | Exact Italian card; do not turn the unpictured Easter possibility into a printing. |
| PT KSS 26/39 reverse | Kalos/reverso/Portuguese queries and [MYP listing](https://mypcards.com/pokemon/produto/36727/snorlax). Portuguese-language websites also offered **English** cards. No inspected Portuguese reverse. | Portuguese face and visible treatment, not site language or seller location. |
| PT BKT 118/162 reverse | Portuguese code/full-number, regional and LigaPokemon searches found generic translated eBay categories and a Portuguese catalogue entry; no inspected matching reverse photo. | Exact Portuguese seller front. |
| PT FCO 77/124 reverse | Portuguese code/full-number and regional searches found catalogue/price pages and a Cardmarket filter, no inspected matching reverse photo. | Exact Portuguese seller front. |
| CN CS1aC 110/135 | [PikaQian exact reverse row](https://pikaqian.com/cards/47f5e484-2acb-4492-a941-3cc9c5a5643d) exposes an image and historical seller leads. Image retained and inspected: simplified text, CS1aC F 110/135 U, conspicuous star depiction. | Source is a small reference depiction; verify physical treatment from the linked original seller photograph before claiming a physical pattern. |
| JP xsv2a 143 | Japanese/base-set/non-holo queries found [Big Orbit](https://www.bigorbitcards.co.uk/pokemon/151-japanese/snorlax-japanese.html), which labels a base sv2a card Non-Holo. Current page returned 401. | Inspect actual localized card and map the specific legacy candidate; no transfer from a base listing to a special variant. |
| CN CS5aC 093/127 | Native code/name queries found HKTCG (image 403), then [sold eBay 127836388784](https://www.ebay.co.uk/itm/127836388784). Original 1200×1600 seller photo retained. Simplified face, CS5aC F 093/127 R, Saboteri and vertical rainbow foil visible in artwork/border. | Strong physical-photo input for identity and foil observation. It does not establish the candidate non-holo/reverse alternatives or close the finish list. Exact pattern vocabulary still needs review. |
| CN CS6bC 113/131 | Native queries found Excalibur, HKTCG and [PikaQian](https://pikaqian.com/cards/4f51c003-92e6-4ee7-ab30-e6fee8d4d80e). PikaQian reference image retained: simplified text and CS6bC H 113/131 R legible; seller leads listed. | Inspect a linked original physical-card photo for the candidate treatments/pattern. |
| CN 151C 143/151 | Native and eBay queries found [eBay 389905853131](https://www.ebay.com/itm/389905853131). Retained image shows 151C 143/151 U and a large Master Ball depiction. | The front is a stock depiction, so do not treat the graphic alone as a physically observed pattern. |
| CN CSV5C 115/129 | Corrected native alias to 卡比兽娃娃. [eBay 226993782091](https://www.ebay.com/itm/226993782091) provides a two-card front composite plus a separate generic back; both original files retained. Front depicts Master Ball and Poké Ball versions and reads CSV5C 115/129 U. | Composite/stock depiction supports identity leads; do not link the generic back as the same physical card or infer surface treatment from seller metadata. |
| JP mC 568/742 | Native full-number search found [PAO foil listing](https://pao-onlineshop.com/view/item/000000112928), specialist mirror listings and a normal listing. PAO's 524×727 front retained; Japanese text, mC H 568/742 and Po-Suzuki legible. | Image supports identity. Exact physical finish/pattern was not accepted from its printed surface or the seller's title alone. |
| CN CSV7C 158/204 | Native code/name and seller searches found [HKTCG](https://www.hktcg.com/products/csv7c-158-204-%E5%8D%A1%E6%AF%94%E5%85%BD-u), Excalibur and [PriceCharting seller links](https://www.pricecharting.com/game/pokemon-chinese-csv7c/snorlax-158). The directly followed [eBay 198383166504](https://www.ebay.com/itm/198383166504) was inaccessible. | Obtain original seller front. No new image bytes inspected for this target. |
| CN CSV10C 175/222 | Native code/name searches found HKTCG and [Excalibur foil-v1](https://excaliburtcg.co.uk/products/csv10c-175-foil-v1). Excalibur image retained: simplified name, CSV10C 175/222 R and GOSSAN visible; large ball design depicted. | Reference depiction establishes identity leads, not a physical-finish verdict or independence from another source. |
| JP m2a 136/193 pattern | Native name/number/mirror queries found specialist listings distinguishing Colorless Energy and Poké Ball mirrors, matching the existing product-page research. | Obtain an actual photographed Japanese front for the precise unresolved base/pattern unit; do not conflate m2a and xm2a without reviewed mapping. |

The two remaining exact-promo searches (#440 Italian CL 33 V2 and RR 33 V2) used Italian/English
name, full number, prerelease/promo/league variants. Results were ordinary-card listings,
English prerelease references and multilingual price sites, not an inspected Italian promo face.
Existing V1 SPECs remain useful identity neighbours only.

## All open issues, including those without a photo task

| Issue | Verified current scope | Disposition for this request |
|---|---|---|
| [#166](https://github.com/m4s-ai/snoredex-data/issues/166) | Standing photo inbox; retrieved body/comments contain the previously processed batches | No new unprocessed attachment identified. |
| [#434](https://github.com/m4s-ai/snoredex-data/issues/434) | Parent worklist includes now-merged subtask work | Used as index; did not double-count parent rows. |
| [#436](https://github.com/m4s-ai/snoredex-data/issues/436) | EXS image is now retained; Italian DF name and three local set names remain | DF photo research above; promo set names are not card-photo gaps. |
| [#438](https://github.com/m4s-ai/snoredex-data/issues/438) | 98 current finish-candidate items | Full SPEC reconciliation inventory; bounded external round for missing image keys. |
| [#439](https://github.com/m4s-ai/snoredex-data/issues/439) | 3 current placeholders; each has existing images | Reuse references above; physical finish/Unlimited edition remains separate. |
| [#440](https://github.com/m4s-ai/snoredex-data/issues/440) | Four TW disputes settled by owner; four of six remaining language questions already have exact-card photos | Existing SPEC/reference reconciliation first; two Italian promo searches unresolved. |
| [#441](https://github.com/m4s-ai/snoredex-data/issues/441) | 58 current pending/partial pattern units | Included individually in inventory. Many have identity/other-finish photos; those do not answer the requested pattern. |
| [#443](https://github.com/m4s-ai/snoredex-data/issues/443) | Manual publication task | No picture research dependency; no publication performed. |
| [#444](https://github.com/m4s-ai/snoredex-data/issues/444) | Structural provider gaps plus LATAM xJTG | Not a list of missing card photos. Bounded exact LA-117/stamped-promo search found base LA and ES listings, not a qualifying LATAM special-print photo. SPEC-0033–0036's existing official LA slice must not be reused as xJTG evidence. Provider-wide research was not started. |

## Retained inputs and acceptance limits

Nine source image files were downloaded and visually inspected. [sources.json](sources.json)
records source/listing links, dates, sizes, image formats, dimensions, hashes, observations and limits.
Seven front-image target identities lacked a matched photo in the initial SPEC check; the eighth,
CS2aC 086/115, already has SPEC-0473/0474 and needs no duplicate identity image. The ninth file is
the CSV5C generic back. No downloaded image is a byte-for-byte duplicate of an existing SPEC photograph.
That does not establish independent provenance or prove two altered images depict different cards.

Local Tesseract was unavailable. Text was read visually; no OCR result is claimed. Original WebP
bytes are retained untouched as research inputs. There was no canonical PNG conversion/import and
no SPEC ID allocation. New/unreviewed source surfaces remain leads until capability review.
The original Italian image and HKTCG retrieval failures are recorded in download-attempts.json.

The strongest next intake is the physical CS5aC 093/127 seller photograph. Accepted photographs must
go through the canonical observation manifest importer, then the appropriate projection/reference
checks and full delivery gate. The other downloaded depictions should be considered identity-only
unless an actual physical observation or a separately attributed positive source supports more.

Validation performed: inventory row counts, existing-photo presence and hashes, downloaded-image
hashes and collision comparison against all 661 SPEC records, JSON parsing and UTF-8/LF checks.
No canonical data changed, so regeneration, browser, live finish and publication gates were not run.
Research remains bounded: blocked, unpictured and uninspected alternatives remain unknown.

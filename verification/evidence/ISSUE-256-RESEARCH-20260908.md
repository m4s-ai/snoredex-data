<!-- doc: role=dated open-issue research and specimen reinspection; stage=reference -->
# Open research issues — 2026-09-08

Baseline: `fb9111761a896192f11a28b1c968039e4221c9bb`. Scope: open parent #256,
children #258, #259, #262, #263, #266, and photo inbox #166. This is a research pass,
not a claim that all evidence gaps are closed. The separate Spanish GEN 58 result
in open PR #371 is excluded from this branch and the counts below.

## Accepted observations

The [replay manifest](issue-256-reinspection-20260908.json) reuses four existing
image byte streams and imports one new seller photograph. Existing specimen IDs,
image provenance and hashes are preserved. Reinspection dates are explicit;
the images have not been enhanced or generated.

| Issue | Exact release | Specimen | Positive visible feature | Recorded scope |
|---|---|---|---|---|
| #259 | Japanese s8b 126/184 | SPEC-0212 | Vertical foil lines and spectral bands inside the illustration | Holo; no reverse-holo or exhaustive finish list |
| #262 | Thai SV9s T 109/139 | SPEC-0091 | Spectral reflections in illustration and silver border; complete Thai card face and number | Holo; no distribution inference |
| #263 | Traditional Chinese AS5a 222/184 | SPEC-0038 | Broad spectral bands crossing the photographed card | Holo; no normalized rarity inference |
| #263 | Traditional Chinese sc1b F 177/153 | SPEC-0083 | Granular foil texture and spectral bands on the foreground card | Holo for that card only; background cards excluded |
| #258 | Indonesian 052/S-P | SPEC-0488 | Foil lines in illustration and border, Indonesian text and printed Indomaret logo | Holo plus distribution-promo marking |

The new [Indomaret seller listing](https://www.ebay.com/itm/196697959025) explicitly
describes the exact card as Holo. The retained original photograph carries the
observation; the search result and marketplace language selectors do not.
The [official Thai card page](https://asia.pokemon-card.com/th/card-search/detail/11193/)
corroborates the Thai identity. It is not used as finish evidence.

SPEC-0081 and SPEC-0092 were also inspected as additional views of the same owner
cards, not counted as independent providers or additional printings. SPEC-0007
and SPEC-0010 show readable Traditional-Chinese identities, but their presentation
does not justify another physical observation in this pass. SPEC-0032 shows the
215/SV-P identity and festival mark; its slab image does not settle finish here.
SPEC-0039 and SPEC-0015 could not be displayed reliably by the image tool; no new
observation is attributed to them.

## Scope-specific remaining research

### #258 — Indonesian

The original issue text still describes many missing official images that prior
merged work has already retained. This pass targets physical evidence instead.
The 052/S-P seller image adds a physical printing without copying an English or
Japanese finish. The image search also surfaced Indonesian SV2a 181/165 and
AC3a 145/205 listings. AC3a already has physical evidence; a fresh listing is not
automatically a new release. SV2a remains a lead until its original photograph
and exact physical treatment are inspected and retained.

Legacy s10a 077 and s5a 093 need more than a same-work illustration: a shared work
does not establish a particular secret artwork, local number or print treatment.
The earlier SPEC audit's same-work classifications are not direct local-identity
confirmations for those aliases.

### #259 — Japanese

The reinspection of SPEC-0212 establishes a holo that the old reverse-holo
marketplace hint did not establish. That reverse candidate remains research.
SPEC-0195 (20th 047) and SPEC-0219 (sv4a 145) were inspected again; their flat
images do not justify promoting a physical finish from the lack of visible shine.

SPEC-0196 (207/BW-P) shows spectral reflections across the text panel, making it
a promising reverse/mirror treatment lead. The exact technical classification
remains unpromoted here. An [Elite Fourum discussion](https://www.elitefourum.com/t/why-is-every-copy-of-this-snorlax-207-bw-p-card-in-such-a-bad-condition/59320)
contains first-hand descriptions of its foil and paper insert, plus original
packaging/card photographs in posts 8 and 11. Those original photographs were
located but not yet visually inspected in this pass. The thread also corrects
the initial claim that this was the first Ichiban insert: a magazine-logo first
is different from a first-ever insert. Its condition and grading speculation
does not establish manufacturing facts.

### #262 — Thai

SPEC-0091 already described visible rainbow reflections but still said it awaited
a canonical release. The release now exists, so this pass records and projects
the visible holo. SPEC-0092 is a corroborating close-up of the same physical card.
Searches with the native name also surfaced s8b 126 and S10b 056 foil listings;
results mix Japanese and Thai cards, so a Thai storefront alone cannot establish
the pictured language. The previous AS5a 142/184 owner batch is already processed
and is not counted again.

### #263 — Traditional Chinese

Two retained owner photographs provide direct foil evidence without requiring
another marketplace search. The seller result for AS5a 117/184 RR is a further
[photo lead](https://shopee.tw/product/3768885/7017610542), not a promoted finish.
The NACG search result for 145/S-P mirror foil led to a current page with an empty
product identity; that mismatch prevents using the indexed text as a fresh exact
observation. Existing SPEC-0030 already supplies a separate 145/S-P observation.

### #266 — European Spanish

SPEC-0132 (KSS 26), SPEC-0134 (JU 27), SPEC-0135 (XY179) and SPEC-0136 (SWSH032)
were inspected again. The latter two are clean digital renders; no physical
finish follows from their appearance. SPEC-0134 has a readable first-edition
mark, but this pass does not convert that scan into an unexamined finish claim.

There is a substantive provenance question for KSS 26: the [WikiDex set article](https://www.wikidex.net/wiki/XY_%28TCG%29%3A_Bienvenidos_a_Kalos)
describes a Spanish online release and asserts that there was no Spanish physical
release. SPEC-0132 therefore cannot by itself settle physical manufacture. This
external assertion is recorded as an adjudication/research lead, not adopted as
an owner absence decision. Neither a not-printed verdict nor a finish is created.

Spanish JU 27 PSA image results need the exact listing/certification and actual
printed language checked; image-search summaries can misdescribe languages.
XY179 unboxing videos and the GAME Spain box remain product/photo leads. The
SWSH032 Spanish pin collection needs an inspected exact card photo. Generic
store option lists combining languages and Normal/Reverse/Holo are rejected.

### #166 — photo inbox

The issue and its comments report all seven opening photographs, the 24-image
Drive batch and the 29-image Korean batch processed. No newer unprocessed
attachment was found in the fetched issue. It stays open as the standing inbox;
the present reinspection does not represent a new owner-upload batch.

## Accounting and implementation finding

The [count snapshot](issue-256-reinspection-counts-20260908.json) records both
catalogue fingerprints. Counts below concern only releases without a graph-backed
physical printing, not the wider parent's date, rarity, mapping or identity gaps.

| Issue | Releases | Without physical printing before | After |
|---|---:|---:|---:|
| #258 | 47 | 38 | 37 |
| #259 | 66 | 15 | 14 |
| #262 | 27 | 20 | 19 |
| #263 | 45 | 28 | 26 |
| #266 | 50 | 5 | 5 |

The graph gains five physical printings (737 to 742), with 632 releases unchanged.
The collector catalogue goes from 995 to 996 items: four release placeholders
are replaced, and one Japanese holo is added beside the still-open reverse
candidate. Every accepted observation remains positive-evidence-only.

Projection initially exposed an order-dependent display-name bug: a source-first
release with its first physical printing was processed before the catalogue's
work-name lookup was populated. This produced a conflicting Tag Team name and
could also select the generic Snorlax fallback. The generator now seeds work
display names from the existing legacy rows before processing physicals, retaining
conflict validation and leaving source-native local names intact. Regression checks
cover all five new printings and the Japanese reverse candidate remaining research.

## Acquisition limits

Native-language web searches, image search, official pages, seller pages, local
originals and Elite Fourum were used. A direct Google Images attempt through an
isolated Chrome instance returned an unusual-traffic challenge, so no Google
results are claimed. Desktop automation was stopped; no further desktop input was
used after the user's Chrome-only instruction. Search results remain leads until
their supporting original content is inspected. No missing result establishes
absence, and no model capability claim substitutes for visible evidence.

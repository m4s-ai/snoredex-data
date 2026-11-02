<!-- doc: role=retained evidence for issue 438, Japanese seller photographs and owner readings; stage=history -->

> Historical record — 2026-11-02; current values are determined by canonical stores.

# Issue #438 — finish-photo evidence, batch 1 (2026-11-02)

Targets: the reverse-holo candidates of the Japanese cohort in issue #438. Base: `origin/main` at
`7e9021f2`.

## Why photos, and why only *these* photos

All 75 candidates already carry an `imageAssetId`; 51 point at a retained `SPEC-nnnn` record and 24 at
a legacy Cardmarket product image. Inspected samples (SPEC-0667, SPEC-0209, SPEC-0248) are described
in their own `observed` text as stock depiction, catalogue scan or official render: they establish
identity, not a finish. `physicalObservation` is unset on every candidate.

A photograph can only establish a finish positively. Missing glare never proves `non-holo`
(`FINISH_SOURCES.md`, "Recording what a scan shows"), and ordinary surface glare or printed pastel
gradients are not positive holo features. So this batch targets claims where foil is *visibly*
present: reverse-holo.

## Retrieval route used

`firecrawl` (a self-hosted instance) reaches the official sources
but not the marketplaces: eBay, Cardmarket, TCGplayer, Yahoo Auctions, Surugaya, Shopee, Bunjang and
Ruten returned `SCRAPE_ALL_ENGINES_FAILED`, HTTP 500 or a JS-empty page. The real browser does reach
them. Mercari's search and item pages were read in a browser session, and each item's original
photographs were downloaded from `static.mercdn.net`.

Retained originals (`raw/`), one per listing photograph:

| File | Listing | Target |
|---|---|---|
| `s10a-058__m79045548127__1.jpg` | https://jp.mercari.com/item/m79045548127 | s10a 058/071 ja |
| `s10a-058__m79045548127__2.jpg` | same listing, second view (card back) | — |
| `s10b-056__m16424786356__1.jpg` | https://jp.mercari.com/item/m16424786356 | s10b 056/071 ja |
| `s10b-056__m37103456060__1.jpg` | https://jp.mercari.com/item/m37103456060 | s10b 056/071 ja |
| `s4-084__m16895790520__1.jpg` | https://jp.mercari.com/item/m16895790520 | s4 084/100 ja |
| `s4-084__m60530212955__1.jpg` | https://jp.mercari.com/item/m60530212955 | s4 084/100 ja |
| `s2-077__m27952797646__1.jpg` | https://jp.mercari.com/item/m27952797646 | s2 077/096 ja |
| `sm10-076__m93852308340__1.jpg` | https://jp.mercari.com/item/m93852308340 | sm10 076/095 ja |
| `sm10-076__m96570993830__1.jpg` | https://jp.mercari.com/item/m96570993830 | sm10 076/095 ja |
| `sm10-076-mirror__m10352220396__1.jpg` | https://jp.mercari.com/item/m10352220396 | sm10 076/095 ja (listing titled `ミラー`) |
| `number-unreadable-mirror__m79219716432__1.jpg` | https://jp.mercari.com/item/m79219716432 | not attributed — printed number not legible |
| `unnumbered-mirror__m20305801647__1.jpg` | https://jp.mercari.com/item/m20305801647 | not attributed — no set or number visible |

Every file is a JPEG whose bytes were downloaded once and hashed locally; see `sources.json`.

## Status of the reading — lead, not yet evidence

A vision model (`deepseek/deepseek-v4.1-flash-1017` via OpenRouter) was asked for the printed number,
set mark and finish of each photograph. Its readings:

| Photo | Number read | Reading |
|---|---|---|
| s10a 058 m79045548127 #1 | 058/071, s10a | reverse-holo (rainbow bands outside the artwork) |
| s10a 058 m79045548127 #2 | not visible | unklar (card back) |
| s10b 056 m16424786356 #1 | 056/071, s10b | reverse-holo (vertical rainbow stripes) |
| s10b 056 m37103456060 #1 | 056/071, s10b | reverse-holo |
| s4 084 m16895790520 #1 | 084/100, S4 | reverse-holo |
| s4 084 m60530212955 #1 | 084/100, S4 | reverse-holo |
| s2 077 m27952797646 #1 | 077/096, S2 | unklar (flat) |
| sm10 076 m93852308340 #1 | 076/095, sm10 | reverse-holo (fine parallel line texture) |
| sm10 076 m96570993830 #1 | 076/095, sm10 | reverse-holo |

These stay **leads**. The repository's rule is explicit that glare and printed gradients are not
positive holo features, and a model's "rainbow" wording is exactly the failure mode that rule
describes. Calibrated on 2026-11-02 against specimens whose finish is already established:
`deepseek/deepseek-v4.1-flash-1017` scored 7/16 — all four `mirror-holo` specimens were misread, and
two known `non-holo` photographs were called `reverse-holo`; `openai/gpt-6-luna-pro` scored 7/12 with
one such false `reverse-holo`. Neither model may carry a finish claim (see `FINISH_SOURCES.md`,
"A model's reading is a lead, never the finish").

What is needed before a row becomes a `physicalObservation`: a person names the visible feature in the
retained image — mirror band, parallel line texture, Poké Ball/Master Ball outline — and that wording
goes into `basis`. The two independent listings per card (s10b 056, s4 084, sm10 076) are the
strongest leads; s10a 058 rests on one listing and s2 077 read as flat.

## Documentary route checked first, and why it is empty for these sets

The Japanese `/ex/<set>/index.html` product page is the documented finish source for Japanese sets. On
2026-11-02 `s10b`, `s8b`, `sv2a`, `sv4a`, `sv9`, `s4` and `s2` were read: `sv2a` names
`豪華ミラー仕様` (Master Ball mirror) for that set, the others carry no mirror/reverse statement for
their regular cards. `s10a`, `s5a`, `sm10`, `20th`, `sI`, `mC` and `xsv2a` return no product page at
that path. So for these reverse candidates only an inspected photograph or an owner determination
remains — the set-level document does not exist to cite.


## Owner readings, 2026-11-02

The collection owner inspected the photographs in sequence and gave these determinations (his words:
"holo meint in dem Fall Artwork und der Rand der Karte leuchtet"):

| Target | Owner determination | Repository state before the reading |
|---|---|---|
| s10a 058/071 ja | `holo` | `holo` already `confirmed`; `non-holo` and `reverse-holo` open |
| s10b 056/071 ja | `holo` | `holo` already `confirmed`; `non-holo` open |
| s4 084/100 ja | `holo` | `holo` already `confirmed`; `non-holo` and `reverse-holo` open |
| sm10 076/095 ja | `holo` | `holo` already `confirmed`; `non-holo` and `reverse-holo` open |
| s2 077/096 ja | `non-holo` | `non-holo` already `confirmed`; `reverse-holo` open |

So every reading matches a finish the data already holds, and **none of the five closes an open
candidate**: the listings show the regular printing. The same happened with every explicitly
`ミラー`-titled listing found afterwards: `m10352220396` ("カビゴン ミラー SM10 076/095") was judged
normal holo by the owner, and the two further mirror-titled listings (`m79219716432`,
`m20305801647`) could not be attributed to a unit at all — one shows no legible number, the other no
set or number. Seller vocabulary is not evidence in either direction.

This is recorded here so the next pass does not repeat the same retrieval without a new lead. The open
question for this cohort is whether the `reverse-holo` axis Cardmarket claims exists for these Japanese
set cards at all; if the owner rules it was never printed, `owner_adjudications.json` `rejectedFinishes`
is the documented route (precedents: KSS 26, PCG3 062), and it is owner-only.

## Not in this batch

- `non-holo` candidates (26): a photograph cannot establish them. They need documentary evidence, a
  documented two-version rule, or an owner decision.
- The five standard-size `SM 05` holo items: owner-attested already; the open question is the graph
  admission rule, not a photograph.
- Korean, Simplified/Traditional Chinese, Indonesian and Thai cohorts: not yet searched.

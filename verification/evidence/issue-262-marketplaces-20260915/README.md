<!-- doc: role=Thai marketplace and sold-listing research; stage=reference -->
# Thai marketplace follow-up — 2026-09-15

Manual research for #262 and draft PR #383. Searched eBay offers and purchase-feedback references, Mavin sold-item archives, Shopee Thailand, ThaiPick, Priceza, Lazada, Kaidee, public Facebook search results and Carousell Singapore. This is bounded web research, not exhaustive marketplace coverage or an adapter run. No sellers were contacted.

## Recovered image

[ThaiPick's archived Magic Poke Shop offer](https://thaipick.com/product/shopee/2182768) still links to an accessible original Shopee image, retained as [as1b112.jpg](as1b112.jpg). The pictured card visibly reads **AS1b A 112/150 RR**, with Thai text and 5ban Graphics credit. This strengthens the existing AS1b admission candidate from the official PDF; it is not a sixth missing Thai candidate. The image is a freestanding catalogue depiction with seller branding, not a demonstrated physical surface: no finish is admitted.

The archive dates its price snapshot to **2022-10-26 19:57:01**, with no timezone given. That is neither our retrieval date nor proof of a completed sale. The combined RR/SD offer describes both booster and starter-deck stock. Its pictured AS1b card cannot establish another starter-deck number or every selectable version. The original Shopee product ID is 2176323915; the shop ID was not recovered, so no product URL was invented.

## Useful leads and exclusions

| Target / source | Result | What remains to inspect |
|---|---|---|
| AS5D 118/169 — [eBay purchase-feedback reference](https://www.ebay.com/itm/127842056732) to [item 127877826164](https://www.ebay.com/itm/127877826164) | Re-found an exact item title and verified-purchase feedback. The same feedback appears on multiple listings from the seller; count it once. | Exact Thai front and finish. Feedback is a transaction reference, not an inspected card, exact sold date or sold price. Direct item page unavailable. |
| sc1b 120/153 — [Mavin archived eBay item 404493852354](https://www.mavin.io/item/Pokemon-Card-Snorlax-VMAX-RRR-120%2F153-Chinese?itemId=404493852354&q=pokemon+card) | Explicitly marked sold, $12.29 plus $0.51 shipping. Title says Chinese; language field says Thai. | Both archived photographs remained inaccessible. Preserve the conflict; do not assign Thai. Relative “a year ago” on stale indexed text is not an absolute sale date. |
| sc1b T 165/153 SR — [ThaiPick archive](https://thaipick.com/product/shopee/4941204) | Exact localized title, seller pppatpatpat / PPCARDGAMESHOP, product 9575533760. Snapshot dated 2022-12-30 02:41:00, timezone unstated. | Same Shopee product as the existing lead, not independent corroboration. Actual image and physical finish still needed. |
| sv4a 310/190 — [Shopee jupigalech](https://shopee.co.th/product/1416820789/27231339385) | Indexed title explicitly claims Thai and Shiny Foil. | Actual physical photographs were not recovered. Seller wording does not close the finish gap. |
| svM 094/175 — [TCG Bangkok store](https://www.ebay.com.au/str/tcgbangkok) | Indexed store lists an exact Thai starter-deck offer. | Exact item ID and inspected surface; store text is still only a lead. |
| Mixed Thai/Indonesian lot — [Carousell 1434675193](https://www.carousell.sg/p/read-thai-indo-language-pokemon-chr-1434675193/) | New route to a lot mentioning Snorlax and Eevee GX. | Image inaccessible; neither individual numbers nor languages established. Carousell is a Singapore marketplace, not a Thai domestic listing. |
| Snorlax 181/165 — [Carousell 1459998744](https://www.carousell.sg/p/snorlax-181-165-ar-1459998744/) | Exact Thai-labelled AR listing found. | Already-known identity, no new gap closure; image not inspected. |
| sv4a 310/190 — [eBay 386557408773](https://www.ebay.com/itm/386557408773) | Listing explicitly says Japanese despite seller location Bangkok and a generic Thai-language store description. | Excluded from Thai evidence; its sold count cannot establish a Thai printing. |

AS5a 222/184 remains a collector-text lead without a recovered Thai front. Kaidee, public Facebook, Lazada and WorthPoint searches produced no usable exact-card evidence in this pass. That says nothing about whether these cards exist or have been offered there. ThaiPick proved useful for recovering an older Shopee image; its mirror and the original seller remain one source lineage.

## Retention and next steps

`captures.json` records the original image URL, actual retrieval timestamp and SHA-256, inspected fields, selected short web excerpts and explicit retrieval limits. Web excerpts are labelled as indexed/extracted text with observation date, not full HTML captures or current inventory. Direct Carousell and ThaiPick requests returned 403; web extraction still exposed one ThaiPick page and its original image link. No Firecrawl/scraping configuration variable was present in the inspected process environment; no login or bot gate was bypassed.

Prioritize the AS5D exact front, AS5a 222/184 Thai front, and physical sv4a 310/190 / svM 094/175 photographs. Keep the Mavin language conflict unresolved until its image can be inspected. No canonical card or finish claim changes in this increment: **13/28 gap-free, 15 unresolved releases**, and the same five PDF-backed Thai admission candidates. PR #383 remains a draft.

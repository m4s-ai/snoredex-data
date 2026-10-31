<!-- doc: role=retained identity-gap research for #436; stage=history -->

> Historical record — research snapshot from 2026-10-31; current values are determined by canonical stores.

# Small catalogue identity gaps — 2026-10-31 (#436)

A value is recorded only from a positive source that states it for the exact card or set. A failed search is recorded as an attempt and establishes nothing.

## Resolved

| Gap | Value | Evidence |
|---|---|---|
| JP EXS Snorlax, Expansion Sheet 1 vending printing (1998-03-23): no image | SPEC-0661 | The pokumon.com image shows No. 143 with the diamond Uncommon symbol and no CoroCoro contest credit, which tells it apart from the Quick Starter Gift Set printing (SPEC-0200). Attached to the vending printing by [`attach_exs_vending_image_20261031.py`](../../passes/attach_exs_vending_image_20261031.py). [`register_pokumon_card_images_20261031.py`](../../passes/register_pokumon_card_images_20261031.py) registers pokumon's image CDN as an identity-only surface. |

The Cardmarket seller scan the EXS override already cited (`marketplace-article-scans …/2123921059.jpg`) returned HTTP 403 on 2026-10-31 and could not be retained.

## Still open

| Gap | Attempts on 2026-10-31 | Next lead |
|---|---|---|
| Italian DF 10 Snorlax δ: `localCardName` | TCGdex `it/cards/ex15-10` → 404. The Pokémon Central Wiki lists "Snorlax δ (EX L'Isola dei Draghi 10)", but its card image is the English print, so it is no evidence of the Italian face. eBay.it search → HTTP 403 from the cloud session. | A photograph of the Italian card, or an owner attestation. |
| ID SM-P 166 Eevee & Snorlax-GX: `localSetName` | The official asia.pokemon-card.com/id search lists promo sets only from S-P on (M-P, S-P, S10P, SV-P, SV2P), not SM-P. pokumon.com names only "SM-P Indonesian Promo". | A printed product or official source naming the Indonesian SM-era promo series, or an owner decision that it has none. |
| TH SM-P 083 Eevee & Snorlax-GX: `localSetName` | The same as Indonesian: the official TH search starts at S-P; pokumon.com names "SM-P Thai Promo". | As above. |
| KR S-P 101 Snorlax: `localSetName` | The official row SP000000101 names only the distribution product "포켓몬 카드 게임 온라인 공식 인증샵 구입특전". The detail page returned HTTP 500. The static pokemoncard.co.kr search page carries 28 of the product dropdown's options, with no Sword & Shield promo series label. | The full product dropdown in a browser session, or an owner decision. |

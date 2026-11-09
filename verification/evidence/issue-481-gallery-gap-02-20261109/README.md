<!-- doc: role=retained gallery image research and source provenance; stage=task -->
# Gallery image research, #481 round 02

The [target freeze](https://github.com/m4s-ai/snoredex-data/issues/481#issuecomment-6734420218)
covers 20 image needs in gallery order. The [source freeze](https://github.com/m4s-ai/snoredex-data/issues/481#issuecomment-6734496417)
records the choices inspected on 2026-11-09.

Twelve seller fronts show the exact existing printings. The Toretoku catalogue front is a
representative render for the confirmed Japanese 261/XY-P Holo entry. It retains the Japanese
text, printed number, Pokémon Pan logo and speckled artwork and is used as gallery media only.

`raw/` retains the original seller photograph WebPs. The Toretoku WebP is kept in the local
research workspace because it embeds contact fields. The source map retains its original URL and
hash. The gallery-only PNG carries no embedded metadata. Pillow 13.0.0 decoded each to PNG without cropping or resampling.
The reopened PNGs matched the decoded original pixels, mode and dimensions. The two hashes,
provenance, decoded dimensions and crop corners are in `source-map.json`. The SPEC importer can
replay the photographs from `manifest.json`. Text, edition and card features were inspected visually
at source resolution. Local Tesseract was unavailable.

One eBay listing advertised Legendary Collection 64/110 but its front showed the Jungle
flower and 27/64. The batch uses the separately inspected 64/110 copy showing the Legendary
Collection symbol and number.

## Round 02 image needs

| Item ID prefix | Target and search | Finding and next lead |
| --- | --- | --- |
| `item-350b3703` | Japanese 261/XY-P reverse holo, `261/XY-P カビゴン ポケモンパン キラ` | Toretoku and PokéBoon show speckling within the artwork. They do not identify a reverse finish. The reverse-holo claim is still marketplace-only. Seek a complete front with independently visible reverse treatment. |
| `item-1b4fff85` | Portuguese XY179 Holo, `Snorlax XY179 português original foto Copag` | The MYP and Shopee leads did not yield a suitable large original in this pass. Existing SPEC-0057 and SPEC-0695 were rejected in #479. Seek a sharp Portuguese front with clearly visible cosmos foil. |
| `item-1c8618e5` | Italian XY179 Holo, `Snorlax XY179 italiano promo foto` | The [Subito listing](https://www.subito.it/hobby-collezionismo/snorlax-xy179-black-star-promo-holo-ita-lucca-661738055.htm) did not yield an accessible original. Existing SPEC-0467 and SPEC-0698 failed width or focus review. Seek an Italian front with no sleeve glare. |
| `item-73a2d023` | German XY179 Holo, `Relaxo XY179 Holo Deutsch Foto` | Ricardo photos are 900 × 1200 frames but the card is roughly 480 px wide at best. Existing SPEC-0128 and SPEC-0696 are not sharp enough. Seek a closer German front. |
| `item-13fdeb56` | Japanese 062/088 first edition, `カビゴン 062/088 1ED 神秘なる山` | The [eBay original](https://www.ebay.com/itm/377577746872) has a white reflection over the rules text. Alternate detail is incomplete. The [Mercari source](https://jp.mercari.com/item/m20822162158) returned HTTP 403 for the original. Seek a diffuse-lit front. |
| `item-49f8c50e` | German Skyridge 100/144 non-holo, `Relaxo 100/144 Skyridge deutsch non holo` | The [German listing](https://www.ebay.de/itm/960027121549) did not expose an inspectable original. The accepted German reverse photo shows a different finish. Seek a full front with the regular e-Reader code. |
| `item-5c100e8b` | Italian Skyridge 100/144 reverse holo, `Snorlax 100/144 Skyridge reverse italiano` | SPEC-0113 is below the effective minimum in its slab. The [individual Italian listing](https://www.ebay.de/itm/358747551423) was unavailable. Seek a raw photo or higher-resolution grading scan. |

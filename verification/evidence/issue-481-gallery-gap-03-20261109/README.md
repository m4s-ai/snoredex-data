<!-- doc: role=retained gallery image research and source provenance; stage=task -->
# Gallery image research, #481 round 03

The [target freeze](https://github.com/m4s-ai/snoredex-data/issues/481#issuecomment-6734762852)
covers 20 image needs in gallery order. The [source freeze](https://github.com/m4s-ai/snoredex-data/issues/481#issuecomment-6734879128)
records the choices inspected on 2026-11-09.

Eleven seller photographs show complete fronts of existing printings. The FireRed & LeafGreen
reverse sources visibly show the Poké Ball treatment. For Dragon Frontiers, the existing
number-and-stamp evidence distinguishes the two treatments. One French offer titled Reverse
shows the unstamped Holo front, and a different French source shows the Reverse set logo.
The included photos are linked to the respective existing printing IDs.

`raw/` retains the received WebPs, whose metadata contains image technical fields only.
Pillow 13.0.0 decoded them to unedited PNGs. Each reopened PNG matched the original decoded
pixels, mode and dimensions. `source-map.json` records the two hashes, dimensions, sources and
crop coordinates. `manifest.json` replays the retained SPEC inputs. Text and visible marks were
inspected at source resolution. Local Tesseract was unavailable.

## FireRed, Rocket and Dragon Frontiers image decisions

| Item ID prefix | Target and search | Finding and next lead |
| --- | --- | --- |
| `item-e143b77c` | Italian Skyridge 100/144 non-holo, `Snorlax 100/144 Skyridge italiano non holo` | The [Subito listing](https://www.subito.it/hobby-collezionismo/snorlax-100-144-skyridge-e-reader-2003-carta-ita-bologna-665672062.htm) did not expose an original here. SPEC-0113 depicts Reverse. Seek a complete Italian front with the standard e-Reader code. |
| `item-a70dc0f2` | Japanese PCG1 074/082 first edition non-holo, `カビゴン PCG1 074/082 1ED` | The [Toreca Camp listing](https://torecacamp-pokemon.com/products/rc_ituqxxoljus4_c1qx) and Hareruya returned HTTP 429 for the request. The inspected eBay lead shows visible foil. Seek a complete front for the stored finish and edition. |
| `item-aef59bce` | Japanese PCG1 074/082 Unlimited non-holo, `Snorlax 074/082 Unlimited Flight of Legends` | The [retrieved face](https://www.ebay.com/itm/178543821625) visibly shows foil within the artwork. It cannot supply the stored non-holo image. Keep the finish records as they are and seek a front matching the target. |
| `item-1ccbaab1` | Italian FireRed & LeafGreen 15/112 Holo, `Snorlax 15/112 RossoFuoco VerdeFoglia holo italiano` | The [Holo lead](https://www.ebay.it/itm/398404396942) did not yield an accessible original. The reviewed Italian Reverse photo shows the Poké Ball treatment. Seek a front of the standard Holo. |
| `item-93f15213` | German FireRed & LeafGreen 15/112 Holo, `Relaxo 15/112 Feuerrot Blattgrün Holo deutsch` | The [shop lead](https://shpnpokestore.de/products/pokemon-karte-holo-relaxo-15-112-deutsch-kopie) returned HTTP 429. The reviewed German Reverse shows the Poké Ball in the rules area. Seek a full regular Holo front. |
| `item-2575f68f` | Japanese PCG3 062/084 Unlimited Holo, `R団のカビゴンex 062/084 アンリミ` | The [auction front](https://hibid.com/en/lot/319352667/pokemon-rockets-snorlax-ex-062-084-unlimited-japa) is at most 576 px wide. Other leads were inaccessible. Existing owner photographs have a thumb over a corner. Seek a complete larger front. |
| `item-669de0c0` | Japanese PCG9 001/068 first edition Holo, `Snorlax delta 001/068 1st edition Japanese` | The [graded photos](https://www.ebay.com/itm/318726829108) are too small after excluding the slab. A larger raw photo shows no stamp. Seek an unobstructed view of the marked edition. |
| `item-77994710` | Italian Dragon Frontiers 10/101 Reverse, `Snorlax 10/101 Isola dei Draghi reverse italiano` | Searches did not surface a qualifying marked Italian original. SPEC-0662 shows the unstamped Holo. Seek a complete front showing the Italian set logo. |
| `item-c64e770b` | German Dragon Frontiers 10/101 Reverse, `Relaxo 10/101 Dragon Frontiers Stempel deutsch` | The two Kleinanzeigen originals are 720 px-wide frames. Their actual card widths fall below 600 px. The regular German Holo is an alternate finish. Seek a closer, glare-free stamped front. |

<!-- doc: role=retained gallery image research and source provenance; stage=task -->
# Gallery image research, #481 round 01

The [frozen round](https://github.com/m4s-ai/snoredex-data/issues/481#issuecomment-6726889800)
covers the first 20 image needs in the Jungle artwork group. Sources were searched and inspected
on 2026-11-08. [Selected fronts](https://github.com/m4s-ai/snoredex-data/issues/481#issuecomment-6727240815)
were recorded before import.
The [English 11/64 first-edition source update](https://github.com/m4s-ai/snoredex-data/issues/481#issuecomment-6727319233)
records the replacement for an early candidate whose usable front fell below 600 pixels.

Ten seller photographs have a complete readable face and a compatible edition area. For Western
Jungle, the existing owner-reviewed number-to-finish mapping supplies the finish. The unnumbered
Japanese Jungle card displays No.143 as the Pokédex species number and shows stars and circles in
the foil. The intake links each photo to its existing finish-printing ID.

`raw/` retains the received WebP bytes. Pillow 13.0.0 decoded each original at its native size
into an unedited PNG for the canonical SPEC importer. Each reopened PNG matched the decoded
original's mode, dimensions and pixels. `source-map.json` records both hashes, dimensions,
the listing and image URLs and the inspected crop coordinates. `manifest.json` replays intake
from the retained PNGs. Text, stamp and set-symbol checks used visual inspection at source
resolution. Tesseract was unavailable.

## Remaining image needs

| Item ID prefix | Target and search | Finding and next lead |
| --- | --- | --- |
| `item-0bfa6f3f` | Italian 27/64 first edition, `Snorlax 27/64 Jungle prima edizione italiano` | The [first photo](https://www.ebay.it/itm/287121716010) obscures part of the artwork with glare, and the [second](https://www.ebay.it/itm/267591694968) obscures rules text. Seek a diffuse-lit front. |
| `item-7e440522` | Dutch 11/64 Unlimited, `Snorlax 11/64 Jungle Nederlands Unlimited` | Retained SPEC-0041 fails the earlier front review. The marketplace search exposed first-edition and English offers. Seek a Dutch front with the edition area fully visible. |
| `item-9379b3ed` | Portuguese 11/64 first edition, `Snorlax 11/64 Jungle Holo português 1ª edição` | The [seller listing](https://www.ebay.com/itm/397923018972) did not expose a retrievable front here. Other offers were ambiguous on edition. Seek a verified slab scan or a raw seller front with the stamp visible. |
| `item-a371c960` | Portuguese 27/64 first edition, `Snorlax 27/64 Selva primeira edição português` | Search exposed catalogue or price context and translated English listings. SPEC-0120 did not meet the earlier image review. Seek a Portuguese collector or grading scan showing the stamp and 27/64. |
| `item-bffdd1fe` | Spanish 11/64 first edition, `Snorlax 11/64 Jungla primera edición español holo` | Existing SPEC-0129/0130 did not meet the earlier image review. Slab listing leads did not yield a retrievable qualifying front. Seek a direct grading front with visible Spanish rules text and stamp. |
| `item-e416ec54` | Dutch 27/64 Unlimited, `Snorlax 27/64 Jungle Nederlands ongelimiteerd` | SPEC-0042/0043 did not meet the earlier image review. The [Marktplaats search](https://www.marktplaats.nl/q/snorlax%2Bjungle/) returned a first-edition Dutch lead and unverified-language offers. Seek a complete Dutch Unlimited seller photo. |
| `item-f36fcf4e` | English Base Set 2 30/130, `Snorlax 30/130 Base Set 2 front` | Both [seller views](https://www.ebay.com/itm/406284938703) are soft around the collector number and small print. Seek a sharper scan with the Base Set 2 symbol visible. |
| `item-183b9f73` | German 27/64 first edition, `Relaxo 27/64 Dschungel 1. Edition deutsch` | Seller and slab listings did not expose an inspectable original. Follow the [individual listing](https://www.ebay.de/itm/168565349539) or an exact grading scan. |
| `item-af566729` | German 27/64 Unlimited, `Relaxo 27/64 Dschungel deutsch unlimitiert` | The [individual listing](https://www.ebay.de/itm/158221627972) did not expose an inspectable original. A German price page explicitly uses an English fallback. Seek a complete German front. |
| `item-742c2d85` | French 27/64 first edition, `Ronflex 27/64 Jungle première édition français` | The [front](https://www.ebay.fr/itm/800651118387) shows the edition stamp and number but glare covers part of the rules text. Seek a diffuse-lit or flatbed front. |

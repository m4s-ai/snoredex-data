<!-- doc: role=retained Indonesian research evidence and search limitations; stage=reference -->
# Indonesian early-card research, 2026-10-02

Research only. No canonical stores changed, no SPEC IDs allocated. Public image downloads required network escalation after sandbox urllib returned WinError10061. Web-tool image fetch Cache miss did not mean the source was inaccessible: ordinary approved HTTP downloaded the originals.

| Target | Queries used (representative exact submitted queries) | Outcome |
|---|---|---|
| AS1D 108/140 | site:shopee.co.id "Snorlax" "108" "AS1D"; "Snorlax" "108/140" Indonesia; site:shopee.co.id snorlax as1d; snorlax gx as1d kartu bahasa indonesia | Positive Non-Holo assertion in First Impact GX Starter Deck article Information; exact 108/140 row and Indonesian scope inspected. Photos found via index mainly Thai; no Indonesian exact new photo. |
| AC3D 120/172 | site:shopee.co.id "Snorlax" "120" "AC3D"; "Eevee" "Snorlax" "120/172" Indonesia; site:shopee.co.id eevee snorlax ac3d; eevee snorlax ac3d starter deck indonesia | Positive Non-Holo assertion in Tag Team Collection GX Starter Deck article Information; exact 120/172 row and Indonesian-only scope inspected. Many index false matches to 166/SM-P promo or AC3b238/204. |
| sc1a I 127/154 | site:shopee.co.id "Snorlax" "127" "sc1a"; site:shopee.co.id snorlax sc1a 127; "Snorlax" "127/154" "Indonesia" "holo"; "Snorlax" "sc1a" "Indonesia" | Existing SPEC0559 source original successfully fetched at1024x1024. Identity exact; finish unresolved. Pastel/opalescent-looking text area not a reliable independent foil determination. No non-holo conclusion from absent reflections. |
| sc1b I 119/153 | site:shopee.co.id "Snorlax" "119/153"; "snorlax" "sc1b" "119"; "snorlax v" "119/153" shopee; "snorlax" "SC1b" "RR" Indonesia kartu | Exact physical Indonesian original900x900 from Shopee Malaysia rokieshop81.my. Cyan/green/rainbow reflections in upper/right illustration, border and lower rule bars establish Holo. No named pattern or complete inventory. |
| sc1D I 132/164 | site:shopee.co.id "Snorlax" "132/164"; site:shopee.co.id snorlax sc1d; "Snorlax" "132/164" "Indonesia" | Positive Non-Holo assertion in localized Sword & Shield V Starter Deck article, exact132/164 row and Indonesian scope inspected. |
| sc1D I 133/164 | site:shopee.co.id "Snorlax" "133"; "Snorlax" "133/164" "Indonesia"; snorlax v sc1d kartu indonesia | Same positive deck assertion explicitly includes Pokémon V; exact133/164 row and Indonesian scope inspected. |

## Accepted research proposals

deck-finish-proposals.json retains manually transcribed scoped excerpts, source URLs, retrieval date and individual excerpt hashes for AS1D,AC3D,sc1D I. proposed-source-records.json gives proposed existing-lane shape only. Review/capability resolution and authoritative integration remain root work. Excerpts are not raw HTML or complete-response captures; do not relabel their hashes.

sc1b-lead.image (original JPEG900x900,179754bytes):
- Listing: https://shopee.com.my/Snorlax-V-RR-sc1b-Pokemon-TCG-Indonesia-foil-holo-i.1383074464.29914412874
- Original: https://down-my.img.susercontent.com/file/id-11134207-7r98t-lzrosoy95pad0a
- Visible: Indonesian Snorlax V220, sc1b I D119/153 RR, Menelan60, Falling Down170, Masakazu Fukuda; physical card on textured maroon cloth, colored foil reflections.
- Seller title matches, but language/number/finish verdict rests on visible card itself.

sc1a-original.image (original JPEG1024x1024,470764bytes):
- Listing: https://shopee.co.id/pokemon-%28ID%29-snorlax-SC1a-127-154-U-i.164644304.29074483660
- Original variant verified by download: https://down-id.img.susercontent.com/file/id-11134201-7rasa-m5d6w400oy3h48
- Existing retained resized URL: https://down-id.img.susercontent.com/file/id-11134201-7rasa-m5d6w400oy3h48@resize_w450_nl.webp
- Visible: exact Indonesian sc1a I D127/154 U, Eri Yamaki, Mengumpulkan/Tumbang120, physical card on playmat. Finish remains unknown.
- Next useful step: root/owner review this original for an explicit field-specific finish determination; native in-Shopee query for127154,127/154,SnorlaxMengumpulkan and deck/set name may find more physical views.

## Other inspected images

lead-0.image: https://down-id.img.susercontent.com/file/id-11134207-822wg-mmmhmx4rjk7c1e from https://shopee.co.id/Pokemon-Indonesia-SNORLAX-(COMMON)-i.36208482.40379758854 ; physical Indonesian MA4I091/123, outside six-card scope.

lead-1.image,lead-2.image,lead-3.image: https://down-id.img.susercontent.com/file/sg-11134201-820nv-mnjolqxvdbsy61 , https://down-id.img.susercontent.com/file/sg-11134201-820mt-mnjolrml84y053 , https://down-id.img.susercontent.com/file/sg-11134201-820lm-mnjom6sv2f41a6 from https://shopee.co.id/Snorlax-pokemon-indonesia-english-japan-i.308769393.55009543981 . Byte-identical originals all show Indonesian MA4I091/123 despite three regional image keys. No independent corroboration.

promo-lead.image: https://down-id.img.susercontent.com/file/id-11134207-7ra0p-mcwy3dvq0c6w23 from https://shopee.co.id/Kartu-Pokemon-Indonesia-Snorlax-V-Promo-Pedang-Perisai-i.435120010.40111236289 . Physical Indonesian030/S-P Snorlax V220 with Pedang&Perisai stamp; broad white glare alone does not establish Holo. Shared with middle agent/root because target belongs to their scope.

All original byte hashes in image-hashes.json. Files retain .image suffix only in ignored cache; magic bytes are JPEG. No crops, conversions or altered originals.

## Process diagnosis

Evidence supports three concrete causes of missed sources, without claiming old rounds had exhaustively searched:
1. Requiring full number and code in every title filters out listings with broad/native deck names. Localized deck articles hold explicit physical finish statements outside exact-card product pages.
2. Restricting to Shopee Indonesia loses cross-border re-export listings of Indonesian cards. The successful sc1b result is Shopee Malaysia with an Indonesian-origin image key; printed card language still had to be inspected.
3. Treating web-tool Cache miss or sandbox network refusal as unavailable image would incorrectly stop this round. Approved ordinary HTTP retrieval returned full-resolution originals. Likewise stopping at450px derivative unnecessarily limits identity/finish review; a known CDN base variant was fetched and inspected before being called an original.

The ordinary full-size sc1a shot still does not establish Non-Holo by itself. Five of six now have positive field evidence proposals; sixth remains unknown.

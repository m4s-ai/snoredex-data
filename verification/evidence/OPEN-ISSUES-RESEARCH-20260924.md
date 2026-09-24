<!-- doc: role=live open-issue evidence research; stage=reference -->
# Open issue evidence research — 2026-09-24

This is a research-only snapshot for the seven open evidence issues checked on 2026-09-24:
[#256](https://github.com/m4s-ai/snoredex-data/issues/256), [#258](https://github.com/m4s-ai/snoredex-data/issues/258),
[#259](https://github.com/m4s-ai/snoredex-data/issues/259), [#262](https://github.com/m4s-ai/snoredex-data/issues/262),
[#263](https://github.com/m4s-ai/snoredex-data/issues/263), [#266](https://github.com/m4s-ai/snoredex-data/issues/266),
and the standing photo inbox [#166](https://github.com/m4s-ai/snoredex-data/issues/166). It continues the current issue
state after repository commit `dfa147b448021420155e27b741749f990e98b08a` (PR #390). No language, printing, finish,
or absence verdict is changed here.

## Live backlog snapshot

- **#256 parent audit:** 502/642 releases are gap-free; 140 remain. Reported fields still include 22 collector-number,
  6 image, 17 local-set identity, 35 physical-printing candidate-needs-evidence, 91 no-candidate, 1 public-source-URL,
  15 rarity and 40 release-date gaps. The child issues below are distinct work lanes; these figures are not additive.
- **#258 Indonesian:** 13/47 gap-free, 34 remain. Open rows span number/local-set identity, image, physical-printing
  candidates, no-candidate, rarity, public URL and release date.
- **#259 Japanese:** 50/67 gap-free, 17 remain. Five collector numbers are unresolved; the remaining known-card work
  includes one candidate needing evidence and no-candidate release gaps.
- **#262 Thai:** 18/29 gap-free, 11 remain. Two candidate-printing rows and nine no-candidate rows remain, with separate
  rarity and release-date fields.
- **#263 Traditional Chinese:** 23/45 gap-free, 22 remain. Seventeen no-candidate rows and five candidate rows remain,
  plus a rarity field.
- **#266 European Spanish:** 46/51 gap-free, five remain: KSS 26 candidate evidence, XYPR 179, SWSH 032, 30C ES 119
  remaining physical/rarity review (official render now visually supports holo treatment), and SVP ES 184 release date.
- **#166 photo inbox:** the current issue body says all attachments through SPEC-0527 have been processed; there were
  no unprocessed attachments to intake during this check. It remains useful for future owner photos.

These counts and issue queues are a live snapshot, not a generated canonical report. Check the issue bodies again before
using them for later work.

## New source research

### Traditional Chinese MC F 568/742 — exact listing, card face inaccessible

The [Shopee Taiwan listing](https://shopee.tw/%E3%80%90%E9%80%90%E9%9B%BB%E7%8B%97%E5%8D%A1%E8%88%96%E3%80%91%E5%AF%B6%E5%8F%AF%E5%A4%A2-PTCG-%E4%B8%AD%E6%96%87%E7%89%88-100%E5%B0%8D%E6%88%B0%E6%94%B6%E8%97%8F-%E9%8F%A1%E9%96%83-%E5%8D%A1%E6%AF%94%E7%8D%B8-%E6%87%B6%E6%95%A3%E5%A3%93%E5%88%B6-H-MC-F-568-742-i.12163161.52007816909)
is titled “Pokemon TCG Traditional Chinese 100 Battle Collection, Mirror Flash Snorlax Lazy Press H MC F 568/742”.
The visible marketplace page initially showed the exact title and listing metadata. Its product image subsequently redirected
to a CAPTCHA in the in-app browser. The title is seller/catalogue text and does not let us inspect card language, set mark,
or foil surface. Do not accept it as a physical-printing or finish observation.

**Follow-up after the owner supplied the image in chat:** the listing's 450×450 card-front image is now accessible through
the in-app browser at
[`tw-11134207-820la-mkyw9uejp81zaa@resize_w450_nl`](https://down-tw.img.susercontent.com/file/tw-11134207-820la-mkyw9uejp81zaa@resize_w450_nl).
It visibly matches Traditional Chinese 卡比獸, regulation H, MC F, 568/742, attack 懶散壓制 120, HP160 and illustrator
Po-Suzuki. That exact identity was already retained under SPEC-0503 from a separate retailer image and in the official
Taiwan source-first record. I initially misread the finish. After the owner's correction that the image clearly shows
reverse holo, the photograph was retained through the specimen importer as SPEC-0555 and the finish was recorded with
`ownerAttestedFields: ["finish"]`. The retained listing image supports the exact identity; the finish attribution is the
collection owner's, not the seller title's. This resolves the finish evidence gap for this identified printing without
asserting the list of all possible finishes or a separate physical specimen held by the owner.

### European Spanish 30C ES 119/128 — useful set context, not exact physical evidence

The [Spanish Pokémon official announcement](https://www.pokemon.com/es/noticias/productos-de-celebracion-30-o-aniversario-de-jcc-pokemon)
announces the Spanish-language 30th Celebration product and says each booster contains five holographic cards (including
one of the 30 Pikachu illustrations) plus one holographic Basic Energy.

On 2026-09-24 I rechecked the complete retained set of eleven official localized Snorlax renders,
[`SPEC-0507`–`SPEC-0517`](../research/30th-celebration-20260910/README.md). **All eleven visibly render the same
speckled holofoil treatment across the Snorlax artwork and show the 30th Pikachu stamp.** They cover English, German,
French, Italian, European Spanish, Latin-American Spanish, Portuguese, Japanese, Traditional Chinese, Thai, and
Indonesian. This includes the exact `30C ES 119/128` and `30C LA 119/128` faces. Korean and Simplified Chinese Snorlax
renders are not in this retained set. Pokédexia also labels `30C 119` “Normale (Holo)” and offers localized face images
for ES/DE/EN/FR/IT, but it is an unregistered secondary source; treat that as corroboration context, not canonical
evidence.

This visual review corrects the earlier claim below that no localized card-specific positive evidence was available.
The publisher images positively show the intended holofoil appearance for the eleven named localized cards. They remain
publisher renders rather than scans of owner-held physical cards, so the retained research still distinguishes depicted
finish from physical-specimen inspection; do not describe them as eleven physical specimens.

The owner-supplied [PokéBeach report](https://www.pokebeach.com/2026/09/30th-celebration-full-set-list-revealed-for-japan-features-176-cards)
(2026-09-09) explicitly says **every card in Japan's 30th Celebration set is foil** and lists Japanese Snorlax as card
095. The same article says the Japanese and English sets have different card lists. Its Japanese face and the official
localized renders above agree on the holo treatment; the direct localized images cover Spanish `119/128` rather than
requiring transfer from the Japanese number. Keep the remaining project finish-inventory status distinct from this
positive image-level finish observation.

The [WikiDex expansion page](https://www.wikidex.net/wiki/Celebraci%C3%B3n_30.%C2%BA_Aniversario_(TCG))
lists Snorlax 119/128, gives a 16 September 2026 Spanish/Latin American release date, and states that all expansion cards
are holographic. WikiDex is registered as tier 3 for positive localized identity from retained database scans, but this
page is not an inspected card scan and the registered capability does not establish physical finish. It is a useful lead
to review against the source-capability contract, not enough to close the physical-printing or rarity/finish issue row.
The official localized gallery render is positive card-face evidence, while still not a physical specimen.

The owner also supplied [PokéWallet's 30th Celebration reveal](https://pokewallet.io/blog/30th-celebration-set-officially-revealed),
dated 2026-06-01. My initial reading wrongly restricted the "30" Pikachu stamp to Classic Collection reprints. A visual
check of PokéBeach's [Japanese set-list gallery](https://www.pokebeach.com/2026/09/30th-celebration-full-set-list-revealed-for-japan-features-176-cards)
shows the stamp on ordinary main-set cards as well: it is visible at the lower right of #049 Zapdos, #050 Zekrom,
#051 Toxtricity, and #095 Snorlax. PokéWallet's English-facing article also visibly shows it on ordinary main-set
Greninja ex, Espeon, and Sylveon ex, while its separate [30-card list](https://pokewallet.io/blog/30th-celebration-classic-collection-all-30-cards)
shows Base Set Pikachu and Charizard carrying it. These images establish that the mark is not confined to the Classic
Collection and appears on both Japanese and English card images. The owner further attests that all cards across the
worldwide releases carry the stamp regardless of their release-specific card lists; record that universal scope as owner
attestation, with the inspected main-set images as visual corroboration. PokéWallet's prose itself only explicitly assigns
the stamp to Classic Collection cards, so do not attribute the universal claim to that prose.

For the separate all-foil claim, PokéWallet says every card in the set is foil, but does not define that claim by
localized release or provide a per-language checklist. Its June 1 post says it drew the Classic Collection cards from
Japan's official site animation. The later official [Pokémon product showcase](https://www.pokemon.com/uk/news/pokemon-tcg-30th-celebration-product-showcase),
published 2026-06-30, confirms five foil Pokémon/Trainer cards and one foil Basic Energy per booster, but does not state
that every numbered card in every localized list is foil. Pokémon's [worldwide launch notice](https://www.pokemon.com/uk/news/the-pokemon-tcg-30th-celebration-expansion-is-available-now)
confirms simultaneous release, not identical card lists or a universal stamp treatment. The official image review now
provides localized positive evidence for the eleven Snorlax faces above; PokéWallet's blanket claim remains secondary
set-level context and is not the basis for those card-specific observations.

An indexed Aukro seller page described a 30C 119/128 Snorlax as “holo”, but the listing had expired and its card photo was
not visible during inspection. The language/locality and card-face treatment could not be checked; discard as a lead.

### Other targeted leads checked

- **Thai MA4 091/123:** an indexed Thai shop listing names the card and code, but no localized card face or finish was
  inspected. Product title alone does not resolve the open physical evidence.
- **Indonesian AC3b 238/204 and 239/204:** general card-list references surfaced, but no Indonesian-language card face
  was found. Japanese/English or other localities cannot be transferred to Indonesian.
- **Japanese G2 and remaining older rows:** general Snorlax checklist pages did not supply an inspected exact localized
  card scan for the unresolved G2 identity. No claim follows from checklist omissions.

These searches produced no additional admissible physical-printing or finish evidence. Marketplace language labels,
search snippets, missing catalogue rows and inaccessible photographs remain leads only.

## Next useful evidence

1. Exact Indonesian fronts for AC3b 238/204 and 239/204, especially if a visible locality/edition mark is present.
2. Exact Thai fronts for MA4 091/123 and the remaining open #262 candidates; preserve the disagreement between official
   record, listing, and card where they do not match.
3. Exact Japanese card/number evidence for the five unresolved #259 collector numbers and a G2 Snorlax face.
4. Revisit WikiDex 30C only if a card scan or independently reviewable physical image becomes available; its expansion-level
   finish statement is not a substitute for observing the card's surface.

## Retrieval and limitations

Pages were discovered through web search and opened in the in-app browser when available. Shopee was inspected in the
in-app browser and then CAPTCHA-gated; no CAPTCHA or access control was bypassed. The Aukro item was expired. Official and
WikiDex page excerpts were read through the web page reader, but full response bodies and image files were not retained in
this report, so there are no full-response hashes. URLs above are canonical page links; the excerpts and limits are transcribed
here as research notes, not a provider refresh run or admitted claim. The baseline `python scripts/regen.py --check` was
attempted before this documentation change; all deterministic checks through the site passed except `scripts/database.py
--check` and `scripts/tracker.py check-template`, both of which could not create temporary directories under Windows
`%TEMP%` due to `WinError 5` access denied.

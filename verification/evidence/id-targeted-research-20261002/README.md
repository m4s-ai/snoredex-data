<!-- doc: role=retained Indonesian research evidence and search limitations; stage=reference -->
# Indonesian finish research — 2026-10-02

Research covers the 18 Indonesian finish gaps remaining after SPEC-0606 (AS1b 112/150 Holo).
Three authorized gpt-6.1-sol medium agents searched six targets each; the root inspected the
sc1b original and two additional localized deck articles. These seven findings are retained
research proposals, not canonical finish updates or newly allocated SPECs.

| Exact Indonesian target | Finding | Supporting source |
|---|---|---|
| AS1D 108/140 | Non-Holo | [First Impact deck](https://bulbapedia.bulbagarden.net/wiki/First_Impact_GX_Starter_Deck_(ATCG)) |
| AC3D 120/172 | Non-Holo | [Tag Team Collection deck](https://bulbapedia.bulbagarden.net/wiki/Tag_Team_Collection_GX_Starter_Deck_(ATCG)) |
| sc1D I 132/164 | Non-Holo | [Sword & Shield deck](https://bulbapedia.bulbagarden.net/wiki/Sword_%26_Shield_V_Starter_Deck_(ATCG)) |
| sc1D I 133/164 | Non-Holo | Same article explicitly includes Pokémon V |
| scA I 084/135 | Non-Holo | [Partners deck](https://bulbapedia.bulbagarden.net/wiki/Partners_V_Starter_Deck_(ATCG)) |
| scD I 111/159 | Non-Holo | [Strength deck](https://bulbapedia.bulbagarden.net/wiki/Strength_V_Starter_Deck_(ATCG)) |
| sc1b I 119/153 | Holo | [Original seller photo](https://down-my.img.susercontent.com/file/id-11134207-7r98t-lzrosoy95pad0a), [listing](https://shopee.com.my/Snorlax-V-RR-sc1b-Pokemon-TCG-Indonesia-foil-holo-i.1383074464.29914412874) |

Each deck article explicitly names its Indonesian release, includes the exact target number
in its set list and states that its cards lack Holofoil treatment. Existing localized identity
SPECs supply the printed local code. This is a positive finish statement about the named deck,
not inference from another language, source silence, rarity or a complete finish inventory.
The sc1b photograph visibly shows Indonesian text, sc1b I 119/153 and colored foil reflections.
No named foil pattern, same-card identity or inventory closure is asserted.

## Eleven unresolved targets

- sc1a I 127/154: original 1024px photograph retrieved; exact identity, finish ambiguous.
- sc3b I 126/158: no new exact physical view establishing finish.
- S-P 030: new exact physical photo; broad white glare does not establish finish. eBay Non-Holo
  titles conflict with Pokumon Mirror metadata; eBay images inaccessible in this round.
- S-P 100: INACO listing lead; no newly inspected finish-positive photo.
- S8b I 126/184: Japanese cards sold in Indonesia excluded; finish unresolved.
- S-P 356 Chatime: two new exact physical views; sleeve/binder lighting inconclusive.
- SV4s I 118/132: native Boneka Snorlax shop lead; no exact physical image recovered.
- SV4a I 145/190: new physical view, inconclusive finish. Cardtell depiction already SPEC-0562.
- SV6s I 136/167: new hand-held physical view, inconclusive finish. Mintoplus remains a render.
- SVM I 094/175: retrieved marketplace titles explicitly Japanese; no Indonesian finish evidence.
- SV9s I 109/139: exact two-image Holo offer found; original photos not inspected due access limits.

Per-target queries, original URLs, prior SPECs, access limitations and next leads are retained in
[early-research.md](early-research.md), [middle-research.md](middle-research.md) and
[modern-research.md](modern-research.md). Root browser fallback reached
the multi-language Shopee offer but its visible Indonesian variant was 136, not the middle
targets. CAPTCHA prevented further inspection; no claim rests on that inaccessible gallery.
The SV9s browser fallback likewise did not yield inspected original bytes.

## Root cause and process correction

The earlier documented PR-402 browser intake reviewed 24 supplied links. That was useful link
intake, not systematic coverage of every open Indonesian card. The earlier research record does
not prove that today's AS1b listing existed or was indexed then; its unique historical miss
cannot be established. This round demonstrates narrower, actionable coverage weaknesses:

1. Exact code/number queries miss native product names and broad multi-card offers.
2. Physical finish statements in localized deck descriptions were not consistently joined to
   their exact target rows; existing Traditional Chinese acceptance was locality-scoped.
3. Indonesia-only marketplace searches miss Indonesian cards sold through regional storefronts.
4. Web-reader failure is distinct from unavailable imagery; exposed CDN originals can work.
5. Reposted publisher renders and identical photos need hash comparison before counting new evidence.

The existing card-search skill now requires target-by-target route accounting, scoped product
finish text, native aliases, regional offers, carousel/selector inspection and explicit blockers.
No new importer, framework or universal query quota was introduced. These search requirements
preserve the existing separation between research proposals and accepted canonical evidence.

Original research images are retained unchanged, with SHA-256 hashes in [retained-image-hashes.json](retained-image-hashes.json).
Article captures are excerpts; their hashes are not complete-response hashes. No verdict, owner
decision, existing specimen or photo date was changed by this research round.

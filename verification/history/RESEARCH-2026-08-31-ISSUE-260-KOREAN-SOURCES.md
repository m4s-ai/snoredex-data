<!-- doc: role=positive Korean source research snapshot; stage=history -->
# Korean source research for issue #260 — 2026-08-31

> [!NOTE]
> Historical research snapshot based on the post-PR-333 repository state (`b1383ae`). This
> document records positive source observations and remaining uncertainty; it does not itself
> change a legacy mapping or assert that an unpictured alternative does not exist.

## Source assessment

The [Elite Fourum set-list thread](https://www.elitefourum.com/t/is-there-any-resource-for-korean-setlists/28395/4)
explicitly says that there is no single complete Korean card database. It points to Bulbapedia's
KTCG set and promo articles and to the [official Pokémon Korea card search](https://pokemoncard.co.kr/cards).
The related [Korean-card resources thread](https://www.elitefourum.com/t/resources-for-information-on-korean-cards/29444/2)
adds TCGBOX as a practical Korean-card source, while warning that Korean promo coverage is less
complete. The forum posts are a discovery map, not proof by themselves.

Evidence was graded as follows:

| Source | Positive use in this pass | Boundary |
|---|---|---|
| Pokémon Korea card detail | Korean name, local number, rarity, product and printed attacks | Catalogue render; no physical finish inference |
| Bulbapedia KTCG set/promo list | Korean release language and exact fixed-product or promo rows | Fan-maintained; omissions are not negative evidence |
| NamuWiki/NamuMoe Korean set or promo list | Korean local numbering and rarity rows | Secondary checklist; no finish inference from a row |
| Seller/Cardmarket photograph | Visible Korean card face, number and physical treatment | Only the pictured card is evidence |
| Collectory/Pokepolio | Korean edition, number and rarity when the record is explicitly KR | Catalogue identity only; displayed images may be substitutes |

## Positive results against the remaining Korean legacy queue

The following rows now have positive identity or fixed-product evidence. Existing physical
specimens remain in `verification/evidence/issue-260-bunjang-positive-evidence-20260830.json`
and the merged PR #333 specimen registry. No new mapping is asserted by this report.

| Legacy unit | Positive Korean result | Source / status |
|---|---|---|
| U0049 | `sv2a 181/165 AR`, 잠만보 | [Pokémon Korea](https://pokemoncard.co.kr/cards/detail/BS2023014181); identity positive, legacy V-label still needs a Korean face if appearance distinction is required |
| U0103 | `sv2a 143/165 U`, 잠만보 | [Pokémon Korea](https://pokemoncard.co.kr/cards/detail/BS2023014143); identity positive, exact legacy appearance still needs a Korean face |
| U0127 | `m2a 136/193`, Hop's Snorlax | [Bunjang listing](https://globalbunjang.com/product/423487583) and Korean card photo; exact physical specimen |
| U0233 | `sv5a 051/066 U` | [Pokémon Korea](https://pokemoncard.co.kr/cards/detail/BS2024007051) and retained seller photo |
| U0257 | `m3 062/080 C` | Retained Korean seller photo; [Collectory record](https://collectory.cc/cards/b6401ed6-1c9a-4703-9b55-762ac6e6d33e) corroborates identity |
| U0260 | Korean number is `sv4K 060/066 U`, not legacy `059` | [Pokepolio Korean record](https://www.pokepolio.com/cards/8ae3d25e-9838-4724-bcf3-cf5ed897d22b) and retained photo; positive correction |
| U0306 | `sv4a 145/190 N` | [Collectory KR record](https://collectory.cc/cards/cba4c986-3c69-4a8c-b065-30efbaac86ed); identity/rarity positive |
| U0379 | Korean promo is `017/SM-P`, not Japanese `001/SM-P` | [Korean promo list](https://www.namu.moe/w/%ED%8F%AC%EC%BC%93%EB%AA%AC%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84/%ED%95%9C%EA%B5%AD%20%ED%94%84%EB%A1%9C%EB%AA%A8%20%EC%B9%B4%EB%93%9C%20%EC%9D%BC%EB%9E%8C) and retained TCGBOX/photo evidence |
| U0402 | `svM 094/175` Snorlax ex | [Collectory KR record](https://collectory.cc/cards/6ff1ddb5-e091-42e4-8581-90cebe2d3b5f); sealed Korean product corroborates release identity |
| U0413 | `sm9 066/095 RR` | [Collectory KR record](https://collectory.cc/cards/46ece022-2213-48b9-bb7d-6504f5e3a4eb) and retained Bunjang photo |
| U0440 | Fixed Venusaur Deck row `016/034` | [Pokémon TCG Classic article](https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_Trading_Card_Game_Classic_(TCG)); fixed-product identity, no Korean card face found |
| U0508 | `s1H 070/060 HR` | [Shield Korean set list](https://www.namu.moe/w/%EC%8B%A4%EB%93%9C(%ED%8F%AC%EC%BC%93%EB%AA%AC%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84)); identity/rarity positive, finish not inferred |
| U0541 | `XY10 057/078 C` | [Awakening Psychic King list](https://dark.namu.moe/w/%EC%B4%88%EB%8A%A5%EB%A0%A5%EC%9D%98%20%EC%A0%9C%EC%99%95) and retained Korean seller photo |
| U0557 | `sm9 115/095 HR` | [Tag Bolt Korean list](https://dark.namu.moe/w/%ED%83%9C%EA%B7%B8%EB%B3%BC%ED%8A%B8) and [Collectory KR record](https://collectory.cc/cards/d3bcbd09-e544-468a-a596-7745da852bba); identity/rarity positive, Korean face still needed for image evidence |
| U0561 | `XY2 066/080 U` | [Pokémon Korea](https://pokemoncard.co.kr/cards/detail/BS2014002066) and retained Cardmarket seller photograph |
| U0579 | `BW7 055/070 U`, 잠만보 플라스마단 | [Pokémon Korea](https://pokemoncard.co.kr/cards/detail/BS2013001055) and retained Korean seller photo |
| U0586 | Beginning Set row is `026/039`; Collectory also has `026/036` under a Chespin's Evolution product | [Kalos Starter Set article](https://bulbapedia.bulbagarden.net/wiki/Kalos_Starter_Set_(TCG)) and [Collectory record](https://collectory.cc/cards/f0ae72d3-a5da-4535-bd33-585d2938cd6a); taxonomy conflict remains |
| U0590 | `mC 568/742` | [Collectory KR record](https://collectory.cc/cards/f7c4636f-8030-40a7-86d6-994a0bc3283c) and retained Korean photo |
| U0601 | `s5a 093/070 UR` | [Matchless Fighters Korean list](https://dark.namu.moe/w/%EC%8C%8D%EB%B2%BD%EC%9D%98%20%ED%8C%8C%EC%9D%B4%ED%84%B0); identity/rarity positive |
| U0610 | `sA 010/023` | [Collectory KR record](https://collectory.cc/cards/481d9b00-6a36-4954-bb67-c5b411d5fe39); fixed-deck identity positive |
| U0623 | Korean DP promo is `006 PROMO`, not Japanese `DP-P 127` | [Korean promo list](https://www.namu.moe/w/%ED%8F%AC%EC%BC%93%EB%AA%AC%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84/%ED%95%9C%EA%B5%AD%20%ED%94%84%EB%A1%9C%EB%AA%A8%20%EC%B9%B4%EB%93%9C%20%EC%9D%BC%EB%9E%8C) and retained Korean promo photo |
| U0641 | `sH 038/053`, not bare `038` | [Family Pokémon Card Game list](https://www.namu.moe/w/%EC%86%8C%EB%93%9C%26%EC%8B%A4%EB%93%9C%20%E3%80%8C%ED%8C%A8%EB%B0%80%EB%A6%AC%20%ED%8F%AC%EC%BC%93%EB%AA%AC%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84%E3%80%8D) and [Collectory fixed-deck list](https://collectory.cc/sets/5376cade-5bfa-4db1-8bec-bcd0e4e8fa68?rarity=N&region=kr&sort=rarity_desc) |
| U0648 | Korean product row is `svI 046/066` | [Battle Academy list](https://d.namu.moe/w/%EC%8A%A4%EC%B9%BC%EB%A0%9B%26%EB%B0%94%EC%9D%B4%EC%98%AC%EB%A0%9B%20%E3%80%8C%EB%B0%B0%ED%8B%80%20%EC%95%84%EC%B9%B4%EB%8D%B0%EB%AF%B8%E3%80%8D) and [Collectory KR record](https://collectory.cc/cards/73c55006-427b-45ae-9a58-f7facd855820); legacy `svIba` label needs normalization |
| U0677 | `svLN 010/022` | Retained Korean seller photo; identity positive |
| U0680 | Fixed Starter Pack row `047/072`; Korean release documented | [Generations article](https://bulbapedia.bulbagarden.net/wiki/Generations_(TCG)); fixed-product identity positive, no fresh Korean card face found |
| U0683 | `mC 567/742` | [Collectory KR record](https://collectory.cc/cards/a504064b-e9ee-44ee-9e6e-329a3b81974d) and retained Korean photo |
| U0763 | `mC 569/742`, Hop's Snorlax | [Collectory KR record](https://collectory.cc/cards/5c9ad620-27b1-4a36-a7fb-1d50394b1fec) and retained Korean photo |
| U0775 | Korean 151 `143/165` Master Ball mirror treatment is possible | [151 set rule](https://bulbapedia.bulbagarden.net/wiki/151_(TCG)); exact Korean Master Ball photo still needed |
| U0780 | Korean 151 `143/165` Poké Ball mirror treatment is possible | [151 set rule](https://bulbapedia.bulbagarden.net/wiki/151_(TCG)); exact Korean Poké Ball photo still needed |
| U0785 | `xm2a 136/193` Poké Ball mirror | [Cardmarket seller photo](https://www.cardmarket.com/en/Pokemon/Products/Singles/MEGA-Dream-ex-Additionals/Hops-Snorlax-V2-xm2a136); exact physical specimen |
| U0790 | `xm2a 136/193` Colorless-Energy mirror | [Bunjang seller photo](https://globalbunjang.com/product/420832203); exact physical specimen |

## Remaining work

The research closes the source-discovery gap for most rows, but the following must remain explicit
before exact appearance or finish closure:

1. Obtain a Korean card-face photograph for U0049/U0103 and for the two Korean 151 mirror variants
   U0775/U0780; the 151 rule alone does not assign a particular card to a particular pattern.
2. Find direct Korean card-face photographs for U0440, U0557 and U0680 if picture evidence is a
   completion requirement; do not infer a finish from a filter, offer or catalogue label.
3. Reconcile U0586's `026/039` Beginning Set identity with Collectory's separate `026/036`
   Chespin's Evolution record before any mapping is changed.
4. Keep the local numbering corrections above separate from the Japanese Cardmarket product IDs;
   Korean promos and fixed decks often use different local numbering.

No issue checkbox, legacy mapping, finish record or generated projection was changed by this
research snapshot.

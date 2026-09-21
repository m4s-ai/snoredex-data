<!-- doc: role=second research round evidence for issue 256; stage=reference -->
# Korean research round 2 — 2026-09-21

Six publisher product pages establish regular launch dates for nine existing Korean card releases. Applied in draft PR #390 only, not merged. The baseline is draft head 684e14e. sources.json retains selected title/date fragments and hashes; these are not full HTTP captures. No physical finish, rarity, identity or image claim is inferred from a launch date.

| Set | Cards | Regular launch | Publisher |
|---|---|---|---|
| s1H | 045/060, 046/060, 066/060, 070/060 | 2020-02-07 | https://pokemoncard.co.kr/card/286 |
| s2 | 077/096 | 2020-04-16 | https://pokemoncard.co.kr/card/297 |
| s4 | 084/100 | 2020-10-21 | https://pokemoncard.co.kr/card/333 |
| s5a | 093/070 | 2021-04-21 | https://pokemoncard.co.kr/card/360 |
| s10b | 056/071 | 2022-06-17 | https://pokemoncard.co.kr/card/439 |
| sv9 | 075/100 | 2025-03-21 | https://pokemoncard.co.kr/card/731 |

## Boundaries and separate products

The sv9 page separately announces a card-shop advance sale on 2025-03-15, subject to store schedules. This is retained context, not an inspected physical distribution event. Product 740 is a battle enhancement box released March 28, not the base expansion launch. Likewise s4 product 341 is an October 31 special kit; s2 product 304 is an April 29 bundle. None replaces the expansion dates above. s1H uses the joint Sword/Shield announcement only for the already established Korean Shield edition.

## Physical-card follow-up

- https://m.bunjang.co.kr/products/430221399: seller PalnetTCG lists Snorlax 093/070 UR with eleven image links. The first image https://media.bunjang.co.kr/product/430221399_1_1788929272_w360.jpg failed retrieval in the browsing tool. Title and seller location do not establish card language or physical finish; keep this as a lead for image inspection and canonical specimen intake.
- https://www.coupang.com/vp/products/9470185182: indexed 093/070 UR offer, not visually inspected; no physical confirmation added.
- https://www.ebay.co.uk/usr/daviescollects-4: indexed offer titled Snorlax VMAX 070/060 S1h: Shield Holo Korean NM. Seller page retrieval failed; no exact listing photo was inspected. Remains a lead only.
- https://asia.pokemon-card.com/th/card-search/detail/3495/: Thai s10a 058/071 official card render does not establish a physical finish. Shopee search results are also not specimen evidence.

## Validation

The pre-change full regeneration check passed. Run the full regeneration gate after intake; compare catalogue item fields with the baseline, allowing only releaseDate, releaseDatePrecision and releaseSortKey. Snapshot metadata advances to the actual evidence date, addressing PR review comment 4061384986. The prior draft already had two failing browser checks for stored artwork-review actions; those are separate from the date evidence and must remain visible in PR status.

Final local validation passed: full `python scripts/regen.py`, including determinism and core regressions; browser suite 155/155. Fourteen items across nine releases changed only the three date fields. All six retained excerpt hashes match. Korean gap-free releases rise from 5/52 to 11/52 within the draft; overall remaining tracked-gap releases fall from 159 to 153. Together with round one, this draft addresses nineteen date gaps on 28 items. Main remains unchanged until merge.

Follow-up: the [round-three intake](../issue-256-web-research-20260921-round3/README.md) successfully retained and inspected the s5a 093/070 listing photo as SPEC-0552 and a separate s1H 070/060 listing as SPEC-0553. The earlier inaccessible-photo status above is historical.

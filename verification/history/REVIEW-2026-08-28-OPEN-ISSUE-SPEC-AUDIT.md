<!-- doc: role=open-issue positive-spec audit snapshot; stage=history -->
# Open-issue positive-SPEC audit — 2026-08-28

> [!NOTE]
> **Historical record — a snapshot, not the current state.** This report records the open-issue
> and Cardmarket review at the date and repository head named below. Use the generated audits and
> current issue tracker for later state.

## Scope and rule

This audit rechecked every unchecked card row in the open `Needs Evidence` child issues
[#257](https://github.com/m4s-ai/snoredex-data/issues/257),
[#258](https://github.com/m4s-ai/snoredex-data/issues/258),
[#259](https://github.com/m4s-ai/snoredex-data/issues/259),
[#260](https://github.com/m4s-ai/snoredex-data/issues/260),
[#262](https://github.com/m4s-ai/snoredex-data/issues/262),
[#263](https://github.com/m4s-ai/snoredex-data/issues/263),
[#266](https://github.com/m4s-ai/snoredex-data/issues/266),
[#267](https://github.com/m4s-ai/snoredex-data/issues/267),
[#268](https://github.com/m4s-ai/snoredex-data/issues/268), and
[#271](https://github.com/m4s-ai/snoredex-data/issues/271) against the specimen registry and the
canonical `WORK:` mapping at repository head `f89879d864b7a8dd6e3d728300c0b0f429c922a5`, then added
the three new positive Cardmarket specimens found during the pass.

The governing rule is positive evidence only. An exact Cardmarket product image or seller photo
counts when the visible card face is in the target language. A language filter, offer, seller
comment, result count, missing image, or empty search does not count. A Cardmarket catalogue image
of a Japanese or English card cannot support a different selected language.

The issue checkboxes are a stale research queue, not the current evidence state. The 161 unchecked
rows currently resolve as follows:

| Result | Rows | Meaning |
|---|---:|---|
| Fully direct positive SPEC | 121 | Every unit represented by the row has a target-language SPEC tied to the issue unit/claim or exact localized release. This includes `SPEC-0409` and Korean `XY2 066/080` `SPEC-0411`. |
| Same-language, same-`WORK:` SPEC | 16 | A positive target-language image already establishes the same card work under its actual local set/number. No new card photograph is needed, but the old Cardmarket/Japanese `via-*` alias still needs canonical mapping cleanup. |
| Partially direct | 1 | Korean `xm2a 136 V2` is now retained as `SPEC-0410`; the same checklist row's V1 Colorless-Energy mirror still needs a photograph. |
| No positive SPEC yet | 23 | No target-language SPEC was found for the row. Together with the partial row, 24 rows still need one image each. |

## Per-issue result

| Issue | Language | Rows | Fully direct | Same-work | Partial | No SPEC | Still needs an image |
|---|---|---:|---:|---:|---:|---:|---:|
| #257 | Simplified Chinese | 5 | 2 | 1 | 0 | 2 | 2 |
| #258 | Indonesian | 33 | 31 | 2 | 0 | 0 | 0 |
| #259 | Japanese | 23 | 23 | 0 | 0 | 0 | 0 |
| #260 | Korean | 50 | 22 | 9 | 1 | 18 | 19 |
| #262 | Thai | 17 | 15 | 2 | 0 | 0 | 0 |
| #263 | Traditional Chinese | 22 | 20 | 2 | 0 | 0 | 0 |
| #266 | Spanish (Europe) | 6 | 6 | 0 | 0 | 0 | 0 |
| #267 | French | 1 | 0 | 0 | 0 | 1 | 1 |
| #268 | Italian | 3 | 2 | 0 | 0 | 1 | 1 |
| #271 | Portuguese | 1 | 0 | 0 | 0 | 1 | 1 |
| **Total** |  | **161** | **121** | **16** | **1** | **23** | **24** |

## Rows with positive evidence under the actual localized release

These are not picture gaps. The requested legacy reference and the photographed local release map
to the same target-language `WORK:`. The remaining work is to replace or explicitly map the stale
`via-*` alias; the image must not be copied to an unsupported Japanese collector number.

| Issue | Legacy reference | Positive localized SPEC evidence |
|---|---|---|
| #257 | S-Chinese `sH 038` | `SPEC-0155`, `SPEC-0156` (`CS4DaC 341/414`, `342/414`) |
| #258 | Indonesian `s10a 077` | `SPEC-0174`, `SPEC-0369` (`S10a I 058/071`) |
| #258 | Indonesian `s5a 93` | `SPEC-0165`, `SPEC-0167`, `SPEC-0169`, `SPEC-0171`, `SPEC-0357`, `SPEC-0358`, `SPEC-0360` |
| #260 | Korean `sm9 066`, `sm9 115` | `SPEC-0028` (`SM-P 140`), `SPEC-0250` (`sm9 106/095`) |
| #260 | Korean `CLF 016` | `SPEC-0239` (`s2 077/096`) |
| #260 | Korean `s5a 93` | `SPEC-0240`, `SPEC-0241` (`s4 084/100`, `s8b 126/184`) |
| #260 | Korean `sH 038` | `SPEC-0242`, `SPEC-0243`, `SPEC-0247` (`sI 341/414`, `342/414`, `sN 008/024`) |
| #260 | Korean `sv2a 143`, `sv2a 181`, `sv4a 145` | `SPEC-0251` (`sv4a 310/190`) |
| #260 | Korean `s1H 70` | `SPEC-0245` (`s1H 046/060`) |
| #262 | Thai `s10a 077` | `SPEC-0264`, `SPEC-0368` (`s10a 058/071`) |
| #262 | Thai `s5a 93` | `SPEC-0258`, `SPEC-0259`, `SPEC-0261`, `SPEC-0356`, `SPEC-0359` |
| #263 | T-Chinese `s5a 93` | `SPEC-0278`, `SPEC-0279`, `SPEC-0291` |
| #263 | T-Chinese `svG 021` | `SPEC-0295`, `SPEC-0323`, `SPEC-0324` (`S10a F 058/071`, `077/071`) |

## Still missing positive target-language card images

The repository's Cardmarket catalogue image was inspected for every row below. Every one pictures
a Japanese or English card and is therefore rejected as target-language evidence.

| Issue | Language | Card | Legacy reference / unit | Missing evidence |
|---|---|---|---|---|
| #257 | S-Chinese | Snorlax | `s4 84` / `U0289` | Visible Simplified-Chinese card face for this `WORK:` |
| #257 | S-Chinese | Snorlax | `svIba 046` / `U0646` | Visible Simplified-Chinese card face for this `WORK:` |
| #260 | Korean | Hop's Snorlax | `m2a 136` / `U0127` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Hop's Snorlax | `mC 569` / `U0763` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Hop's Snorlax | `sv9 075` / `U0370` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Hop's Snorlax | `xm2a 136 V1` / `U0790` | V1 Colorless-Energy mirror photograph; V2 Poké Ball mirror is now `SPEC-0410` |
| #260 | Korean | Snorlax | `20th 047` / `U0680` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax | `BW7 055` / `U0579` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax | `HXY 026` / `U0586` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax | `m3 062` / `U0257` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax | `mC 567` / `U0683` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax | `mC 568` / `U0590` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax | `sA 10` / `U0610` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax | `sv5a 051` / `U0233` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax | `svIba 046` / `U0648` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax | `svLN 010` / `U0677` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax | `XY10 057` / `U0541` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax Doll | `sv4K 059` / `U0260` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax ex | `svM 094` / `U0402` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax GX | `SM-P 1` / `U0379` | Visible Korean card face for this `WORK:` |
| #260 | Korean | Snorlax Lv.X | `DP-P 127` / `U0623` | Visible Korean card face plus an explicit work-equivalence basis; `SPEC-0037` does not establish Japanese `DP-P 127` equivalence |
| #267 | French | Snorlax | `WCD23 LOR 143` / `U0433` | Visible French World Championships Deck card face |
| #268 | Italian | Snorlax | `BA20 MWT` / `U0297` | Visible Italian Battle Academy Mewtwo-deck card face |
| #271 | Portuguese | Snorlax | `SWSH 032` / `U0420` | Visible Portuguese card face |

## Cardmarket search checkpoint

- Italian `GEN 58`: one seller scan was inspected and retained as `SPEC-0409`; it visibly shows
  Italian `Snorlax`, the Generations symbol and `58/83`. No finish is inferred.
- Korean `xm2a 136 V2`: the seller scan was retained as `SPEC-0410`; it visibly shows Korean
  `m2a 136/193` and the Poké Ball mirror treatment. V1 remains unpictured.
- Korean `XY2 066`: the seller scan was retained as `SPEC-0411`; it visibly shows Korean
  `066/080`. No finish is inferred.
- Simplified-Chinese-filtered `s4 84`: the attached seller scan is actually a Japanese PSA card
  with Japanese text and a label reading `JPN`; it was rejected rather than projected through the
  language filter.
- Italian `BA20 MWT`: four Italian-filtered offers were visible, with no attached seller scan.
- French `WCD23 LOR 143`: five French-filtered offers were visible, with no attached seller scan.
- Portuguese `SWSH 032`: no Portuguese-filtered offer or seller scan was visible.

All 23 previously blocked product pages were inspected after the user completed Cardmarket's
Cloudflare check. The displayed offer and seller-scan counts were:

| Target-language product | Offers shown | Seller scans | Evidence result |
|---|---:|---:|---|
| S-Chinese `s4 84` | 3 | 1 | Rejected: photographed card is Japanese |
| S-Chinese `svIba 046` | 0 | 0 | None |
| Korean `m2a 136` | 34 | 0 | None |
| Korean `mC 569` | 0 | 0 | None |
| Korean `sv9 075` | 50 | 0 | None |
| Korean `xm2a 136 V2` | 2 | 1 | `SPEC-0410` |
| Korean `xm2a 136 V1` | 1 | 0 | None |
| Korean `20th 047` | 1 | 0 | None |
| Korean `BW7 055` | 0 | 0 | None |
| Korean `HXY 026` | 0 | 0 | None |
| Korean `m3 062` | 33 | 0 | None |
| Korean `mC 567` | 0 | 0 | None |
| Korean `mC 568` | 0 | 0 | None |
| Korean `sA 10` | 0 | 0 | None |
| Korean `sv5a 051` | 38 | 0 | None |
| Korean `svIba 046` | 0 | 0 | None |
| Korean `svLN 010` | 0 | 0 | None |
| Korean `XY10 057` | 4 | 0 | None |
| Korean `XY2 066` | 4 | 1 | `SPEC-0411` |
| Korean `sv4K 059` | 18 | 0 | None |
| Korean `svM 094` | 0 | 0 | None |
| Korean `SM-P 1` | 2 | 0 | None |
| Korean `DP-P 127` | 1 | 0 | None |

These counts are search-routing notes only, never evidence of presence, absence, or completeness.

## What remains

1. Find and retain a target-language photograph for the 24 rows above. Prefer an exact Cardmarket
   product image; otherwise use a seller scan attached to a target-language offer.
2. Repoint the 16 same-work rows to their actual localized releases or record an explicit alias;
   do not keep presenting them as picture gaps.
3. Synchronize issue checkboxes only from this evidence classification. A checkbox must never be
   checked merely because a Cardmarket language filter or offer exists.

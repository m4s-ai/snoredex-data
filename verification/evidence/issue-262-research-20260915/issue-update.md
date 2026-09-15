# Thai: current research progress

Parent: #256

Updated 2026-09-15. PR #375 is **merged** (2026-09-11). Current main: `2c1818c01f299d5f085721145a9d05e3f7dfebeb`.

## Merged state versus draft implementation

- **Merged main: 8/28 gap-free, 20 remaining.** PR #375 supplied the exact Thai photographs and identities, but the two re-keyed releases still have no projected date. The previous prediction of 10/28 after #375 was incorrect.
- **Draft implementation on `codex/research-262-20260915`: 13/28 gap-free, 15 remaining.** These additional changes are being collected in a draft PR, not merged; do not count them as delivered on main.
- Main catalogue fingerprint: `sha256:936f442e94eb44d4ab9b37249d14605bc69f3e8fe43d6ba2b6c5132fdf0b14f3`.
- Draft implementation fingerprint: `sha256:5ce3e811a65336158b29e4e4139f5b80c842bd0b57041cf747688b0cf31169bd`.

Each current canonical release is counted once. These are tracked-field gaps, not a complete finish inventory. `mapped-by-explicit-equivalence` is a valid work mapping. A failed lookup or missing photo is not absence evidence.

| Tracked gap | Main | Draft implementation |
|---|---:|---:|
| Physical printing: no candidate | 14 | 12 |
| Physical printing: candidate needs evidence | 4 | 3 |
| Release date | 2 | 0 |
| Rarity | 1 | 1 |
| Image / collector number / local set identity | 0 | 0 |

## Five implemented recommendations, in the draft

1. **s5a T 093/070:** separate official Thai release event for **2021-04-30**, from the [publisher product listing](https://asia.pokemon-card.com/th/card-search/?pageNo=4). Existing SPEC-0523 remains the physical/identity evidence.
2. **s10a T 077/071:** separate official Thai release event for **2022-07-29**, from the [publisher announcement](https://asia.pokemon-card.com/th/archives/1596/). Existing SPEC-0520 remains the physical/identity evidence. Neither date is attributed to its photograph.
3. **SV-P 082/SV-P:** apply the already registered [Pokumon Non-holo evidence](https://pokumon.com/card/snorlax-082-sv-p-thai-promo/) by correcting the override's legacy lookup number from `082/SV-P` to `082`. The local collector identity remains `082/SV-P`. The printed stamp reads **CENTRAL PATTANA**; the event name stays distribution context.
4. **sc3b T 126/158:** new **SPEC-0526**, a retained [Thai seller scan](https://shopee.co.th/product/431199770/23151999066), visibly demonstrates Holo. Original CDN bytes/hash retained; product-page access was unavailable, and the scan carries a seller watermark, not a card stamp.
5. **sv4a 145/190:** new **SPEC-0527**, the [eBay Thai front photo](https://www.ebay.com/itm/297969171577), visibly demonstrates Reverse Holo. Printed code is sv4a T and matches the retained Thai sv4a release. Conflicting Japanese/Normal listing fields are rejected. The original server-provided JPEG is retained; no exact foil-pattern name is asserted.

The four original research images and source HTML captures are retained locally under `verification/evidence/issue-262-research-20260915/`; canonical photo intake uses SPEC-0526 and SPEC-0527. The unrelated back photo and clean promo illustration are not additional physical-finish confirmations.

## Remaining after the draft implementation

- `RELEASE:TH:Thai:MA4:091/123:Snorlax-Glutton-Topple-Over`: `physical-printing:no-candidate`.
- `RELEASE:TH:Thai:MA6 T:121/130:Snorlax-Good-Sleep-Collapse`: `physical-printing:no-candidate`, `rarity`.
- `RELEASE:TH:Thai:SH:026/038:Snorlax-Heavy-Impact`: `physical-printing:no-candidate`.
- `RELEASE:TH:Thai:s10a:058/071:Snorlax-Unfazed-Fat-Thumping-Snore`: `physical-printing:candidate-needs-evidence`.
- `RELEASE:TH:Thai:s10b:056/071:Snorlax-Block-Collapse`: `physical-printing:candidate-needs-evidence`.
- `RELEASE:TH:Thai:s8b:126/184:Snorlax-Gormandize-Body-Slam`: `physical-printing:candidate-needs-evidence`.
- `RELEASE:TH:Thai:sc1D T:132/164:Snorlax-Rolling-Tackle-Heavy-Impact`: `physical-printing:no-candidate`.
- `RELEASE:TH:Thai:sc1D T:133/164:Snorlax-V-Swallow-Falling-Down`: `physical-printing:no-candidate`.
- `RELEASE:TH:Thai:sc1a T:127/154:Snorlax-Collect-Collapse`: `physical-printing:no-candidate`.
- `RELEASE:TH:Thai:sc1b T:119/153:Snorlax-V-Swallow-Falling-Down`: `physical-printing:no-candidate`.
- `RELEASE:TH:Thai:sc1b T:120/153:Snorlax-VMAX-G-Max-Fall`: `physical-printing:no-candidate`.
- `RELEASE:TH:Thai:scA T:084/135:Snorlax-Gormandize-Body-Slam`: `physical-printing:no-candidate`.
- `RELEASE:TH:Thai:scD T:111/159:Snorlax-Slap-Push-Single-Strike-Tackle`: `physical-printing:no-candidate`.
- `RELEASE:TH:Thai:sv4a:310/190:Snorlax-Voraciousness-Thudding-Press`: `physical-printing:no-candidate`.
- `RELEASE:TH:Thai:svM:094/175:Snorlax-ex-Strength-Toss-and-Turn-Press`: `physical-printing:no-candidate`.

## Remaining research priorities

- Exact Thai original-image leads: [s8b 126/184 R/Foil](https://shopee.co.th/product/34894051/12382671946), [s10b 056/071](https://shopee.co.th/product/412643607/25102563945), [sv4a 310/190 Shiny/Foil](https://shopee.co.th/product/1416820789/27231339385). These are search leads, not accepted finish evidence.
- s10a 058/071 needs a card-specific physical finish observation. A set-wide mirror announcement does not settle this card's treatment.
- [MA6 T 121/130](https://asia.pokemon-card.com/th/archive/special/card/ma6/) is announced for **2026-09-16**, still future at this update. Recheck physical photographs and legible rarity after release; publisher renders do not establish physical finish.
- No repeat photograph is needed for the already supplied s5a T 093/070 or s10a T 077/071 date gaps.

## Verification and scope

The draft implementation passed the full repository gate (`python scripts/regen.py --check`), including targeted checks for both official dates, both seller-photo finish links and the promo identity/stamp. The specimen references reach the physical graph, source registry, artwork views and collector links. Existing tracker count expectations were updated for the two legacy entries now verified.

This issue remains open. The draft implementation must still be delivered before its five improvements are counted on main. No absence decision, complete finish inventory, merge or publication is asserted.

Owner direction (2026-09-15): keep the PR as a draft while collecting more information. Do not mark it ready, merge it or close this issue.

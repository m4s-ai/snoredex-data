<!-- doc: role=retained-image reinspection and identity-reconciliation evidence; stage=reference -->
# Retained-image reinspection, 2026-09-10

Scope: the owner's request to revisit existing Chinese/Japanese images and reconcile
the Indonesian/Thai identifiers already supplied; PR #375 review also identified an
incomplete handoff between physical specimens and language claims.

## Accepted and applied

- **SPEC-0489, Traditional Chinese s5a F 093/070:** visible fine glittering foil across
  the gold background and blue body supports **Holo**. No separate foil pattern is
  asserted. The existing original/hash is reused through the reviewed
  [manifest](issue-263-gold-reinspection-20260910.json).
- **U0602 / SPEC-0489, U0603 / SPEC-0519, U0171 / SPEC-0520:** exact-card language
  evidence replaces the old set-only classification. The original observations are
  preserved in the append-only journal. Photographic language evidence and physical
  finish observations remain separate fields.
- **SPEC-0519:** printed `s5a I 093/070 UR` is now a local Indonesian identity.
- **SPEC-0520:** printed `s10a T 077/071 CHR` is now a local Thai identity.
- **SPEC-0518:** the legacy SV2a 181 record is reconciled with the existing
  `ID:SV2a I:181/165:base` release. Its positive Non-Holo and Holo evidence survives;
  the former duplicate release is not another card to research.

The two newly recorded local identities do not gain release dates from their photos.
Their printed rarity values remain source-native where no reviewed normalization exists.
Legacy product links, claim references and specimen identities are preserved through
explicit aliases. A cited legacy alias can validate a re-keyed specimen; a different
language, number, set or uncited neighbouring unit cannot.

## Inspected images that do not settle finish

| Retained specimen(s) | Card | Result of visual re-examination |
|---|---|---|
| SPEC-0293 / SPEC-0499 | Traditional Chinese SI F 341/414 | Flat card image; pale patterned text background is insufficient to establish physical foil. |
| SPEC-0294 | Traditional Chinese SI F 342/414 | Publisher-style image; no independently clear physical reflection. |
| SPEC-0197 | Japanese BW7 055 | Small scan; no sufficiently distinct foil observation retained. |
| SPEC-0209 | Japanese s2 077 | Small flat image; does not establish either Non-Holo or a foil treatment. |
| SPEC-0219 | Japanese sv4a 145 | Small flat image; no finish promotion. |
| SPEC-0215 / SPEC-0216 | Japanese sI100 341 / 342 | Printed pale patterns are not themselves proof of foil. |
| SPEC-0195 | Japanese 20th 047 | Small scan; subtle colouring is not enough to distinguish the finish. |
| SPEC-0199 | Japanese EC5 062 | Low-resolution image; finish remains undetermined. |
| SPEC-0222 | Japanese XY-P 149 | Subtle colour in the silver area does not establish an exact treatment. |
| SPEC-0230 | Japanese Pt2 070 | Compressed/watermarked scan; no dependable foil observation. |
| SPEC-0224 / SPEC-0104 | Japanese XY10 057 | Small complete scan plus larger owner crop. The larger image is partial and does not clearly distinguish reflection from the illustrated lighting; no new finish assertion. |
| SPEC-0225 | Japanese XY2 066 | Small scan; no dependable physical finish distinction. |
| SPEC-0194 | Japanese G2 Rocket's Snorlax | Full card inspected; no finish assertion. Printed No.143 is a species number, not an inferred collector number. |
| SPEC-0228 | Japanese DP1 Snorlax Lv.35 | Full card inspected; no finish assertion. Species numbering must not be substituted for a collector number. |

No additional images were needed to perform this review. For the unresolved finish
questions, a clearly angled physical photo or an explicit owner identification of
the pictured treatment would add information; simply retrieving the same flat image
again would not. No missing reflection is used as Non-Holo or absence evidence.

## Verification boundary

The migration is scoped to U0051, U0603 and U0171. Language-evidence repair covers
U0602, U0603 and U0171. Regressions cover exact specimen references, established
language application and cited-alias identity validation, including neighbouring-card
and wrong-language rejection. The formerly unspecified Traditional Chinese gold
collection entry now has two possible targets: observed Holo and an unverified
marketplace finish candidate. Migration preserves the old state for explicit user
reconciliation instead of assigning ownership to either finish automatically.
The full regeneration gate remains required before push.

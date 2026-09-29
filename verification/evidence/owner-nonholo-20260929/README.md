<!-- doc: role=owner-confirmed Non-Holo photograph intake and acceptance; stage=task -->
# Owner-confirmed Non-Holo intake — 2026-09-29

**Snapshot at 208fa3f.** The later [s2 Non-Holo follow-up](../owner-s2-nonholo-20260929/README.md)
confirms s2 077/096 through SPEC-0591, reducing this snapshot's three Japanese gaps to two.

All ten images supplied in this conversation are retained unchanged as SPEC-0581–SPEC-0590.
The collection owner explicitly confirms Non-Holo for each pictured card. Nine images identify
Japanese releases; the English Rocket's Snorlax is separate evidence for Gym Heroes 33/132.
No language or finish is transferred between those two Rocket's Snorlax images.

| Image | Retained specimen | Exact target | Additional observed detail |
|---|---|---|---|
| 1 | [SPEC-0581](../../specimens/SPEC-0581.png) | Japanese DP1, unnumbered | DPBP#174 and No.143 are Pokédex identifiers; Ken Sugimori |
| 2 | [SPEC-0582](../../specimens/SPEC-0582.png) | Japanese Pt2 070/090 | Fruit-eating artwork, Lv.40, HP100 |
| 3 | [SPEC-0583](../../specimens/SPEC-0583.png) | Japanese BW7 055/070 | 5ban Graphics; printed Team Plasma design |
| 4 | [SPEC-0584](../../specimens/SPEC-0584.png) | Japanese EC5 062/088 | Exact artwork/layout reference match; supplied image is 169×225 |
| 5 | [SPEC-0585](../../specimens/SPEC-0585.png) | English GH 33/132 | Visible 1st Edition stamp; Shin-ichi Yoshida |
| 6 | [SPEC-0586](../../specimens/SPEC-0586.png) | Japanese XY2 066/080 | Visible 1st Edition mark; Mitsuhiro Arita |
| 7 | [SPEC-0587](../../specimens/SPEC-0587.png) | Japanese 149/XY-P | Visible red 丸美屋 distribution mark; Kouki Saitou |
| 8 | [SPEC-0588](../../specimens/SPEC-0588.png) | Japanese 20th 047/072 | Mitsuhiro Arita; broad surface reflection is not holo evidence |
| 9 | [SPEC-0589](../../specimens/SPEC-0589.png) | Japanese XY10 057/078 | Visible 1st Edition mark; Tomokazu Komiya |
| 10 | [SPEC-0590](../../specimens/SPEC-0590.png) | Japanese G2, unnumbered | No.143 is the Pokédex identifier; Shin-ichi Yoshida |

## Evidence and correction

[Exact owner statements](owner-statements.json), the [replayable manifest](manifest.json) and
[original filenames, dimensions, SHA-256 hashes and field evidence classes](sources.json) retain
the input and its interpretation. The photos were inspected at their supplied resolution.
Local Tesseract OCR was unavailable; manually read text is not represented as OCR output.
EC5's tiny image was compared with the existing exact-card reference
`images/EC5_062_Snorlax_654062.jpg`; its number and artist are reference-matched rather than
claimed as newly legible fine print. No resizing, enhancement, conversion or cropping was applied.
Original external photo providers and physical ownership were not supplied and remain unspecified.

The technical finish is `non-holo`. `ownerAttestedFields: ["finish"]` separately attributes
the explicit collection-owner determination (tier 2) while the retained photograph supports identity
and readable marks. The complete photographed 1st Edition marks and the 丸美屋 mark are visual
observations, not conclusions drawn from the Non-Holo attestation.

For **20th 047/072**, the owner corrected the earlier assistant's treatment of a broad white
reflection as a reason for a Holo caveat. That qualification is withdrawn. Ordinary surface glare
and printed pastel gradients are not positive holo features. This card is accepted as **Non-Holo**;
the correction is retained with the original image and the owner's exact words.

These statements confirm the pictured Non-Holo printings. They do not say that no other finish
exists for those releases, so no new finish-list closure or absence decision is added. Unverified
marketplace reverse-holo candidates remain separately graded. M6a's earlier Holo-only owner
decision is unchanged.

## Projection and accounting

The canonical importer retains one photo per SPEC and exact legacy-unit citations. Existing
finish and graph projectors carry the owner finish sources into the registry, artwork and collector
views. All nine Japanese releases gain confirmed Non-Holo evidence. English GH gains an exact
1st Edition observation alongside its existing edition-unspecified Non-Holo evidence.

The new English observation exposed a collector matching collision: edition-unspecified API
evidence and the exact 1st Edition specimen both borrowed the same legacy checklist row. The
collector matcher now reserves exact semantic matches across the complete physical-printing
set before using an edition-compatible fallback. Both evidence records remain available; the
1st Edition checklist ID is assigned exactly once, independently of input order. The regression
exercises both orders. No edition is inferred for the generic API printing.

The affected current-catalogue audit, grouped by unique release, is:

| Scope | Main d1dc293 | Draft after this intake |
|---|---|---|
| Japanese, 67 releases | 53 gap-free / 14 remaining | **64 gap-free / 3 remaining** |
| Parent, 633 releases | 510 gap-free / 123 remaining | **524 gap-free / 109 remaining** |

The three Japanese gaps are **s2 077/096, sI100 341/414 and sI100 342/414**. These counts require
at least one evidenced physical printing; they are not an exhaustive finish inventory.

Manifest replay, physical-workflow stop reason, consumer checks and the complete regeneration
and post-push audits are recorded in the updated draft PR. The PR remains a draft.

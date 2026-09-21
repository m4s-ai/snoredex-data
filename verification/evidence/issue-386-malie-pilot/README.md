# Reviewed Malie pilot content — 2026-09-21

Issue: [#386](https://github.com/m4s-ai/snoredex-data/issues/386).
Contract: [MALIE-EXPORT.md](../../MALIE-EXPORT.md).
Accepted input: [card_content_observations.json](../../card_content_observations.json).

## Evidence and attribution

The canonical manifest importer retained the original 600×825 TCGdex images as
SPEC-0528 (English, U0012) and SPEC-0529 (German, U0014). The observations support
release-level identity and printed content. They do not establish physical finish,
back, size, ownership, a new printing, or independent corroboration of the existing
TCGdex claim. No language/finish verdict was changed.

Local Windows OCR was run first, using the installed `de-DE` model for both images
(an English model was unavailable). The uncorrected extraction is retained beside
this note. Visual inspection corrected OCR errors, especially small artist credits,
copyright, numbers and symbols. Accepted values are in the reviewed input, not the
OCR text. The optional OCR runtime is not a repository/build dependency.

Each of the two localized fronts was inspected independently. The English credit
is `Illus. HYOGONOSUKE`; the German one is `Illustr. HYOGONOSUKE`. The German
copyright has no spaces around the slashes. Presentation line breaks are joined;
the German `Überreste-Karten` retains its compound hyphen. BASIC/BASIS follows the
explicit profile interpretation. A fully inspected empty resistance area supports
inapplicability for this card; an omitted API property would not.

The selected original Malie records retained under #385 are now qualified **only**
for the explicitly accepted fields and targets in the observation store. They state
`STANDARD` and `POKEMON_1999` directly. Their exact language, set icon, number, name,
text and named variety were matched to the existing physical IDs. `recordBindings`
preserves the original array index and TCGL identifiers for each target. Array
indices locate retained evidence; they are never Snoredex identities.

`NonFoil_None` explicitly supports the non-foil applicability decision alongside
the pre-existing positive non-holo evidence. An omitted `foil` object alone does
not. The English reverse record explicitly states `FLAT_SILVER` and `REVERSE`;
this qualifies its export mapping without inferring a physical foil pattern from
a generic finish label. Digital TCGL records do not establish new physical-print
existence. Malie is attributed as a third-party open database (tier 2), not an
official publisher. No additional licence grant or external compatibility is claimed.

The new TCGdex image surface is separate from the existing API surface. Its scope
includes visible printed content, but excludes back/size/finish. Existing scoped
API-run pins remain unchanged. Source hashes, registered capabilities and exact
release/printing relationships are checked by `scripts/card_content.py`.

### Preview defect found during visual acceptance

The original files were correct, but the existing shared preview encoder capped
the green palette channel at 215 while red and blue reached 255. This made white
and light-grey card areas magenta. Inspection found that the same palette backed
846 PNG derivatives across 423 sources, including these two new scans.

The encoder now uses equal six-level RGB axes and nearest-colour rounding. Its
version invalidates older PNG caches even when their source hashes still match;
legacy JPEG previews remain valid. Preview URLs bind the derivative bytes, so a
corrected encoding with an unchanged original gets a new browser cache key. Tests
cover all 256 neutral greys, primary colours, rounding, old-cache invalidation and
source replacement. Original evidence bytes and hashes are unchanged.

## All selected inputs

The six selected item IDs remain unchanged in `malie_profile.json`. These are
data-preparation outcomes, not a claim that an exporter has already run.

| Existing target | Data state | Evidence or remaining work |
|---|---|---|
| F0225-P01, English MEW 143 | Required field inputs ready | SPEC-0528, exact non-foil Malie record, existing finish evidence |
| F0227-P01, German MEW 143 | Required field inputs ready | SPEC-0529, exact German Malie record, existing finish evidence |
| F0225-P02, English MEW 143 reverse | Required field inputs ready | Explicitly shared release text and exact reverse Malie record; existing reverse printing retained |
| F0507-P01, English SVP 051 | Needs evidence/mapping | Inspect exact SVP front and complete printed fields; retain positive source for the exact foil layer/mask. MEW artwork/text similarity is not a transfer rule. |
| F0507-P02, English SVP 051 Pokémon Center | Needs evidence/mapping | Inspect exact stamped SVP front and foil mapping; retain its distinct distribution/marking identity. No borrowing the plain SVP variant. |
| German Jungle 11 research item | Outside first profile; physical identity unresolved | Historical-era boundary, not SV/TCGL pilot. Do not fabricate a printing ID, non-holo state or local field values. |

No selected input was removed. Missing evidence remains unknown and does not
become an absence decision. #387 must emit the complete machine-readable disposition
report; #388 must prove the real nonempty multilingual export against these inputs.

## Reproduction and verification

`intake.json` now references the retained repository images, so repeating the
canonical importer is offline and idempotent. The original URLs and exact hashes
remain in the specimen registry and content source records.

- `python scripts/card_content.py` checks hashes, source capabilities, target joins
  and field provenance without writes.
- `python verification/test_card_content.py` checks the two real-language expected
  inputs and rejects corrupt hashes, path traversal, provider substitution,
  wrong-printing/locality sources, unsupported front-image back evidence, missing
  evidence, inconsistent field state and duplicate observation IDs.
- The data check is part of the existing core test list. Full regeneration and
  its observational gate remain required; targeted checks alone do not establish
  an accepted export or a release.

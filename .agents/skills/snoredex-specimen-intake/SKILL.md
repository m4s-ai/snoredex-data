---
name: snoredex-specimen-intake
description: File physical Snoredex card or seller-listing photographs as stable specimen records in verification/specimens.json and cite them from data/. Use for local images, issue attachments, scans or listing photos; not for source pages without a card image.
---

<!-- doc: role=specimen-intake workflow skill; stage=task -->

# Snoredex specimen intake

Turn physical-card image evidence into a stable, checkable specimen record without asserting
anything the image cannot establish. There is no importer: filing is a manual
procedure, guarded by `scripts/check.py` and its `--selftest`.

## Specimen-intake context

Read [AGENTS.md](../../../AGENTS.md), the finish and source-technique sections of
[METHODOLOGY.md](../../../METHODOLOGY.md) (recording what a photograph shows, editions, multiple
views, GitHub issue attachments) and [DATA-GUIDE.md](../../../DATA-GUIDE.md).

## Specimen-intake workflow

1. Obtain the original bytes. For an issue attachment, fetch the issue's HTML page and download the
   resolved image URL as METHODOLOGY.md describes. Determine the format from the bytes, not the URL.
2. Inspect the original at sufficient resolution. Identify only visible facts: card identity,
   printed language and locality markers, finish or foil pattern, stamps or markings, distribution
   marks and size cues.
3. Run the collision check below, then assign the next free `SPEC-nnnn`. Identical bytes reuse their
   existing record; never give identical bytes a second id.
4. Save the photograph as `verification/specimens/SPEC-nnnn.<png|jpg>` and add its record to
   `verification/specimens.json`, keeping the fields existing records use: `specimenId`, `setCode`,
   `number`, `variant`, `language`, `heldBy`, `inspectedFrom`, `observed`, `recordedAt` (the real
   inspection date), `photograph`, `photographSha256`, `photographSource` (the issue or image URL)
   and `listingUrl` for a seller photo (never invent one), and `citedBy` (the exact `unitId` or
   printing id the image supports). Update the register's `count`. File a seller photograph as a
   third-party-held specimen, never as a bare marketplace link.
5. Record visible physical properties under `physicalObservation` (`finish`, `foilPattern`,
   `markings`, `markingRole`, `cardSize`, `edition`) with a `basis` that quotes what the image
   shows. Leave a property unset when the image does not establish it. An explicit owner
   determination is recorded as `ownerAttestedFields` with `ownerAttestedAt`. For a set printed in
   both editions, a visible 1st Edition mark is 1st Edition and a visibly empty mark position on a
   complete, legible face is Unlimited.
6. Cite the specimen where it carries a claim: a language claim's `sourceRef: "specimen:SPEC-nnnn"`
   with the matching provider (`inspected-specimen`, `cardmarket-listing-photo` or
   `seller-listing-photo`), or the printing's evidence. Follow
   [claim evidence](../snoredex-claim-evidence/SKILL.md) for the claim change.
7. Run `python scripts/check.py`: every `specimen:SPEC-nnnn` in `data/` must resolve, and specimen
   authority must cite a specimen. Run `python scripts/regen.py` once at delivery. Report retained,
   cited and unresolved evidence separately.

### WebP source photographs

Keep the original WebP and convert losslessly; never ask for another format when the original bytes
are reachable. Retain the untouched WebP under `verification/evidence/<task>-<date>/`, decode to PNG
without cropping, resizing or enhancement, and require exact pixel equality between the decoded
source and the reopened PNG in the same mode. Record the original URL, retrieval date, MIME type,
size, dimensions and SHA-256, plus the PNG's path and SHA-256, the decoder and version and the
equality result, in that folder's `sources.json`. File the PNG as the specimen.

## Specimen-intake image verification

Run local OCR first when its output is readable enough to verify, then inspect the image for
artwork, layout, finish, stamps and damage. OCR establishes printed text (name, attacks, artist,
set code, number), never foil or subtle stamps; finish needs a visible feature, a comparison photo
or an explicit owner determination. Record per field whether it is an observation, OCR extraction,
user confirmation or inference, and leave uncertain finishes unset.

One photograph per `SPEC-nnnn`. For several original photos of the same physical card, give each its
own record and put `"sameCardAs": {"specimenId": "SPEC-nnnn", "basis": "<positive same-card
identification>"}` on every additional view, pointing directly to the primary. Views record only
their own positive properties and never count as independent corroboration. Never deduplicate cards
on text, number or artwork alone, and never overwrite a retained photograph to add an angle.

## Specimen-intake multi-photo batches

1. Inventory every image first with a sequence number, source path, SHA-256 and OCR output.
2. Build one review row per photographed card: identity, language and market, set code, collector
   number, artist, candidate claim ids, visible or owner-confirmed finish, stamp and confidence.
3. Group by `(localization, market, set code, collector number)`, then compare finish and stamp
   separately: cards with identical text may still be distinct variants.
4. Never merge Non-Holo, Holo, Reverse Holo, Cosmos Holo, Poké Ball, Master Ball, stamped and other
   treatments. A model's label is a lead; an explicit owner correction overrides it.
5. One specimen establishes only what its visible face proves, never that no other variant exists.

If the original bytes cannot be obtained or matched, stop with the exact missing input. A missing
photograph is not evidence of absence.

## Specimen-intake collision check

Before assigning ids, fetch `origin/main` and compare its specimen ids and photograph hashes with the
working branch; inspect known overlapping intake PRs without modifying them. A branch-local next
number is not a reservation. Repeat the comparison before pushing. Reuse identical bytes; on a
collision re-key only the unintegrated observation and every reference to it.

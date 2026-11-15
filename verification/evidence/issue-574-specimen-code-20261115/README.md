<!-- doc: role=retained specimen-code correction and handoff; stage=history -->

> Historical record — issue #574 inspection on 2026-11-15, based on main 60b3e9ba.

# SPEC-0015 printed set code

| Target / evidence | Accepted fields | Recorded | Output boundary | Remaining |
|---|---|---|---|---|
| SPEC-0015, Traditional Chinese Snorlax 111/159 | Visible badge `scD F`; regulation E is separate | Specimen `setCode` corrected from `sc?? F`; contradictory illegibility prose reconciled | Rebuild SQLite's specimen JSON; no printing, finish, claim or identity changes | Integrate the metadata correction; edition-code filling is already in PR #590 |

## Original and inspection

- Existing original: https://raw.githubusercontent.com/m4s-ai/snoredex-photos/main/verification/specimens/SPEC-0015.png
- Original SHA-256: `d974ace6deb4917d12acf131f01aca11e7be902c7f369b2ed956879491c9e922`.
- Downloaded on 2026-11-15 and matched to the register hash before inspection: PNG,
  3508 x 2480 pixels, 7713526 bytes. No photograph or hash is changed or newly allocated.
- Parent and delegated specimen worker inspected the existing image. Parent additionally read
  the unscaled lower-left inspection crop `(100, 2130, 750, 2380)` in original pixel coordinates:
  the badge reads `scD F`, followed outside the badge by regulation `E` and `111/159`.
- Local Tesseract was unavailable; this is a visual text reading, not an OCR result. The code
  does not establish a physical finish, a release date, or a new owner decision.
- The specimen's existing observation already recorded this resolution on 2026-08-09. Its
  `citedBy` already names `TW:scD F:111/159:base`; the catalogue's existing local set and edition
  also use `scD F`. The remaining bug was the stale structured specimen field and contradictory
  active prose. Earlier inspection dates and the owner's marker explanation are preserved.

## Parallel set-code work

PR #590, inspected at `e579d76df9c7ee2bd81bce36c319c516e7903a87`, already contains:

- `EDITION:TW:T-Chinese:scD F`: `printedSetCode: scD F`, `localityMarker: F`,
  `sourceRef: specimen:SPEC-0281`;
- `LOCALSET:TW:scD%20F`: `baseSetCode: scD`.

That independent source already supplies #574's follow-up under #573. It is PR-only, not merged
main. This correction does not duplicate or replace the pending set-edition record and does not
change `data/sets.json`.

## Verification and delivery boundary

The unmodified baseline passed `python scripts/regen.py --check`. A focused comparison confirms
that only SPEC-0015's `setCode` and `observed` fields change; all other specimen fields/records,
including the photograph, SHA-256, source URL, id and original `recordedAt`, remain identical.
The parent independently rechecked the image and hash after the delegated edit.

Full `python scripts/regen.py` passed after the correction. The SQLite comparison changes exactly
one `specimens` row, SPEC-0015; every other table is identical. SQLite integrity and foreign-key
checks pass. The catalogue, both pages and tracker template remain byte-identical to the baseline.
The publication audit must also run after the commit; its result and the commit/PR status belong
in the issue delivery. No code or browser behavior is changed, so no browser run was added, and
the full photo repository was not rehashed. No publication or absence decision is implied.

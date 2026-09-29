<!-- doc: role=retained Thai and Indonesian evidence intake; stage=task -->
# Thai and Indonesian owner evidence — 2026-09-29

Scoped follow-up to merged PR #402, for issues #262 and #258. The owner supplied two
images and explicitly extended the Japanese M6a explanation to MA6 T and MA6 I.
This bundle records four existing releases; it does not discover another release.

| Target | Evidence | Accepted fields | Remaining scope |
|---|---|---|---|
| Thai AS5a 142/184 | SPEC-0594, supplied Ojama Card image | Visible `R`; owner confirms Rare, normalized through the reviewed Thai mapping | Existing Non-Holo/Holo evidence is preserved; no finish closure |
| Thai sc1D T 132/164 | SPEC-0595, supplied PP Card Game Shop image | Exact Thai identity; owner-confirmed Non-Holo | Other finishes remain unknown |
| Thai MA6 T 121/130 | Existing SPEC-0516 publisher image and owner statement | Common; owner-confirmed Holo; owner closes finish list to Holo | No new printed rarity symbol or foil pattern asserted |
| Indonesian MA6 I 121/130 | Existing SPEC-0517 publisher image and owner statement | Common; owner-confirmed Holo; owner closes finish list to Holo | No new printed rarity symbol or foil pattern asserted |

`sources.json` retains the original attachment names, hashes, owner statements and
field-level evidence classes. Tesseract was unavailable locally, so the original
images were read visually; no OCR output is claimed. No original listing URL was
supplied for the two new images. Their provenance remains `user-supplied:…`, not an
invented retailer URL or claim that the owner holds the pictured copies.

`manifest.json` is replayable through the canonical specimen importer. SPEC-0594
is identity/rarity support only; its seller FOIL caption introduces no finish claim.
SPEC-0595 records the finish under `ownerAttestedFields`. The original bytes and
hashes of SPEC-0516/0517 remain unchanged; their metadata gains the separately
attributed owner finish determination. `owner-determination.json` retains the
verbatim extension, its prior Japanese context, exact scope and prior specimen
metadata. The two finish-list decisions are separate from positive finish evidence.

The rarity classifications use `owner-attestation`: the owner explicitly calls
AS5a's printed R Rare, and explicitly extends Common to the two MA6 releases.
The photos independently retain the exact identities and visible printed text.
No specimen-provider rarity capability is added. Reviewed rarity claims and their
source records enter the retained graph base; normal projectors produce the
physical nodes, registry, artwork, collector and database consumers.

First-batch result: Thai 20/29 tracked-field-complete (9 finish gaps), Indonesian 18/37
(19 finish gaps). This is not an exhaustive card/finish inventory. The three new
physical printings replace the existing research placeholders through the standard
collector migration path. The additional AS5a photo supports its existing release.
Main-based issue totals stay unchanged until merge.

The subsequent [sc1D T 133/164 owner confirmation](../issue-262-sc1dt133-20260929/README.md)
raises the draft Thai result to 21/29, with eight finish gaps remaining.

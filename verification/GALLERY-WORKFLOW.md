
# Gallery gap rounds and whole-gallery acceptance

[#481](https://github.com/m4s-ai/snoredex-data/issues/481) covers selected image gaps.
[#482](https://github.com/m4s-ai/snoredex-data/issues/482) covers the whole current gallery.
Run from an isolated data checkout. Use a current independent checkout of the photo archive.
Image preparation uses Pillow. Browser checks require Pillow, Playwright and Chromium.

## Run or resume a round

1. Use the next frozen round directory or create its target list with
   `python verification/gallery_workflow.py freeze --out DIR/targets.json --round N ID...`.
   Select up to twenty active image gaps.
2. Check registered owner and third-party originals first, then research alternatives. Review
   the actual language, number, edition, finish cues, marks, completeness and effective face width.
   Record one decision per `itemId` in the `targets` array of `source-review.json`. Selected rows
   use `"decision": "selected"`, the reviewed `candidateId` and `"scope": "representative"` or
   `"exact-printing"`. A gap uses
   `"decision": "needs-image"` and a concrete `reason`. Keep URLs and hashes with the reviewed sources.
3. Follow [specimen intake](../.agents/skills/snoredex-specimen-intake/SKILL.md) for immutable
   archive originals, GPS handling and reserved IDs. Provide `registry-additions.json` with the
   `specimens` array. In `intake.json` provide `round`, `acceptedAssociationCount` and `intake`.
   Each intake row carries `candidateId`, `specimenId`, `itemIds`, `setEditionId`, `setCode`,
   `number`, `language`, `scope`, `mediaKind`, `photograph`, `photoRepositoryPath`,
   `photoRepositorySha256`, `originalSourceSha256`, `originalBytesUnchanged` and `sourceUrl`.
   Intake hashes are raw SHA-256 hex. Use the complete printed number. Use existing specimen IDs
   for identical originals. For an already prepared representative image, put `itemId`,
   `specimenId` and `"scope": "representative"` in `reusedSpecimens`. The source must come
   from the same release and have matching edition, distribution, marks and size. When preparing
   new renditions for a registered specimen, supply its original register record unchanged.
4. Run `python verification/gallery_workflow.py render DIR --candidate KEY --specimen SPEC-ID --source FILE`.
   Use the whole canvas only if it holds a complete, upright face. Add
   `--corners X1 Y1 X2 Y2 X3 Y3 X4 Y4` for perspective correction, clockwise from top left in
   native pixels. Inspect the final face and derivatives before applying.
5. After authorized intake, update the photo checkout's remote-tracking `origin/main` and
   run `python verification/gallery_workflow.py status DIR --photos PHOTO_CHECKOUT`.
   `archived` refers to the recorded bytes at that fetched ref. Investigate `local-only`
   or `missing` before retrying. Add `--report REPORT` to compare a previous verification with
   the current inputs. Use
   `python verification/gallery_workflow.py apply DIR --photos PHOTO_CHECKOUT`.
   Replaying apply with the same inputs reuses identical rows and files. Conflicts stop the
   command. Apply manages gallery associations, derivatives, gallery assets and the specimen
   register. Use the established specimen/evidence process for any primary image or claim change.
6. Regenerate with `python scripts/regen.py`. Then run
   `python verification/gallery_workflow.py verify DIR --photos PHOTO_CHECKOUT --report REPORT`.
   This checks the current release gate, originals, local artifact and all round targets
   on desktop and mobile in the grid, lightbox and eight binder layouts. The report pins
   the verified checkout. Reverify after changing the inputs. Check publication history after
   committing and follow the usual authorization rules for PRs and pushes.

Use `check DIR --photos PHOTO_CHECKOUT` for a read-only round comparison with canonical
rows, image hashes and the photo archive. Round 24 is a working reference on branches containing
that round. `--repo DATA_CHECKOUT` before the command selects a separate checkout.

## Whole-gallery acceptance

1. Run `python verification/gallery_workflow.py audit --photos PHOTO_CHECKOUT --report REVIEW/technical.json`.
   It checks the current active inventory, separates research hypotheses, checks the release gate
   and archive, and builds and verifies the local publication artifact. It checks full grid
   membership and one card per available image scope in each group on desktop and mobile
   in the grid, lightbox and eight binder layouts. It also runs the complete browser suite.
   The report includes the exact sample IDs and leaves visual acceptance pending.
2. Review all groups in `REVIEW/contact-sheets.html` for orientation, framing, colour, sharpness,
   identity, source priority and the representative label. Keep the generated packet in
   local scratch space or a repository cache. Consult original sources for ambiguous
   cases. Regenerate the packet after corrections. Review the linked issue dependencies in #482.
3. Record a JSON object with `reviewedGroups` (group IDs from `REVIEW/group-inventory.json`),
   `imageNeeds` (every remaining item or hypothesis ID mapped to a reason), `reviewer`, `checkedAt`
   and the `basis` from the technical report. Run
   `python verification/gallery_workflow.py sign-off --report REVIEW/technical.json --review REVIEW/visual.json --out REVIEW/acceptance.json`.
   A stale or incomplete report cannot record acceptance. Use the evidence to update the issue
   when authorized. Live publication is a separate owner action.

<!-- doc: role=frozen whole-gallery completion inventory and work plan; stage=task -->
# Remaining gallery rounds, #481 / #482

`inventory.json` freezes the active physical-item universe at `bb563f20`, before round 10:
940 active items, 261 prepared images, 679 image needs. Twenty-five needs had already received
a review in rounds 05–09. The other 654 stable item IDs are divided into 33 fixed rounds 10–42,
with at most twenty targets per round. Two gallery research hypotheses are recorded separately;
they are not physical printings or proof that a card exists.

The freeze is historical. Main `c3a5f156` subsequently normalized x-set metadata into base sets;
current assignments must resolve the stable item IDs against current data rather than reuse
frozen edition fields. The frozen target membership must not silently change with later builds.

`acquisition-index.json` records a bounded retrieval of existing TCGdex source links for rounds
12–42. Its 160 downloaded images are candidates, not accepted evidence or gallery assignments.
Twenty-five API responses have no image and sixty-six requests were unresolved. Neither outcome
establishes absence. Existing retained photographs have priority when they meet the quality
threshold. Each candidate still needs identity, language/locality, effective resolution, full rim,
and target-assignment review. A shared API link is not proof that every routed target matches.
Two reviewed regular-set images (CAT-018/CAT-047) depict Dustox rather than the target Snorlax
TG10; their routing is rejected and the correct trainer-gallery set is recorded separately.

Round 10 has three accepted additions and seventeen remaining image needs. Round 11 source
research is in progress. Rounds 12–42 are planned and partially acquired, not complete. Contact
sheet inspection alone does not complete a round. Final acceptance under #482 remains pending
after the fixed rounds, including the grid, binder, detail views and explicitly retained gaps.

No claim, owner decision or hypothesis is settled by this plan. No merge or publication is
authorized by completing the images. PR #593 remains the review surface.

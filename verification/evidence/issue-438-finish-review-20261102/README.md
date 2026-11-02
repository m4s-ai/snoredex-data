<!-- doc: role=retained finish evidence and TCGdex candidate review for issue 438; stage=history -->

> Historical record — 2026-11-02; canonical stores determine current values. The owner explicitly
> approved the exact candidate hash below; it was accepted without a live refetch.

# #438 — SM05, Build-A-Bear and controlled TCGdex drift review

| Target/evidence | Accepted fields | Canonical integration | Consumers verified | Commit/PR | Remaining |
|---|---|---|---|---|---|
| SM05 DE/ES/FR/IT/PT | Exact native `holo: true` and standard Holo detail rows | Owner-approved snapshot accepted | Five existing collector candidates promoted with their IDs retained | Feature branch | Review/merge |
| EN FLF 80 V2 Build-A-Bear | Exact Pokumon primary record: English, Non-holo | Existing scoped override confirmed; text source carries finish | Confirmed collector item; identity and stamp sources remain separate | Feature branch | Review/merge |
| ES GEN 58 Non-Holo | No accepted new finish evidence | No claim changed | Existing state preserved | Feature branch | Exact positive Spanish finish source |
| TCGdex refresh | 308 URL set unchanged; all 308 payload hashes changed; 49 card records have normal/holo/reverse boolean drift | Exact staged SHA-256 below; no live refetch | All 968 prior collector IDs retained; 886 → 900 technical finish rows; 65 → 59 candidates | Feature branch | Review/merge; future drift reviews |

Staged candidate SHA-256: `2367c6864c3db38088f8aded3d1eb15d6e5fdd019a907bfe660976a04a3d11a4`.
The exact reviewed payloads are now the versioned snapshot. Pricing and richer detail metadata explain
why payload-hash drift is much larger than finish-field drift. There are 49 new `true` flags and
22 `true` to `false` transitions across the 49 changed card records; false is never absence.

`candidate-review.json` retains the historical pre-acceptance preview. Its 23-row gain was an
overcount: subsequent consumer checks folded qualified Cosmos evidence into existing physical
printings. `integration-validation.json` records the final current-main conservation and counts.
A technical finish row, graph physical printing and collector item are different grains.

## Positive-only retention and qualified identities

`historical-positive-records.json` retains 22 exact historical observations from the accepted
2026-09-01 snapshot, with each payload and its original hash:

- Six SM169, four SV2a181, three SV4a310, two SV9 075 and Traditional Chinese S10a058
  Non-Holo observations remain historical positive claims despite the newer false flag.
- Six SWSH068 Holo observations remain the exact prior unknown-detail records. The new details name
  prerelease/set-logo and Staff copies; no unstamped copy or extra stamped printing is inferred.
- The six SM05 Normal flags already rejected by the collection owner are **not** reintroduced.

The retained observations are not independent physical verification, current API positives or
new absence decisions. The date 2026-09-01 identifies the accepted snapshot; it is not
reported as a per-URL HTTP retrieval date, which that snapshot does not retain. Existing scoped overrides preserve their established technical printing
identity. `qualified-positive-records.json` additionally preserves historical positives already
mapped by the owner's SVP184 prerelease decision. Those five owner-backed identities no longer
depend on creating a generic auto Holo before refinement; their exact existing size and distribution
are retained explicitly, with no additional ordinary Holo.

The detail reader qualifies all three technical finish fields. A stamped Normal Player Rewards
JTG117 does not establish ordinary expansion Non-Holo. Likewise a prerelease Holo does not establish
ordinary CL Holo. The FR/IT CL V2 uncertainty from #440, regular reverse printings and owner absence
decisions are unchanged. Reviewed ordinary Cosmos/Gold/Energy treatments establish the technical
finish only; optional pattern names remain unasserted unless another reviewed mapping supplies them.

## Build-A-Bear

[Pokumon's exact primary record](https://pokumon.com/card/build-a-bear-snorlax-80-106-build-a-bear-workshop-special-print/)
is titled **Build-A-Bear Snorlax (80/106 Build-A-Bear Workshop Special Print)**. Its own card fields
state **English** and **Non-holo**. `build-a-bear-pokumon.json` retains the observed fields, primary
post ID, response size and SHA-256. Related-card grids, and the page's release-year field, are not
used for this claim. The existing release date is unchanged.

Pokumon is a registered tier-3 provider with reviewed exact-card finish capability. This exact
URL may carry the positive finish alone; the TCGplayer/TCGCSV observations remain marketplace
context. SPEC-0479 establishes the English face, collector number and Build-A-Bear stamp separately;
no visual Non-Holo observation or fake corroboration is added to that specimen.

## Spanish Generations search

The retained SPEC-0131 reference render establishes identity, not Non-Holo. Reverse-Holo proof
cannot confirm a normal counterpart. Pokexperto's “Normal” icon refers to Pokémon type, not finish.
Spanish queries included “Generaciones 58/83 español/castellano no holo” and localized official
checklist searches. Cardfolio and a Spanish Pokécardex interface exposed English/global catalogue
or price information, not an exact Spanish physical finish. A Procardsmexico denominator 58/117
mismatch was not accepted. No usable exact official Spanish finish checklist was found in this
search. This is an evidence gap, never a nonexistence conclusion.

## Refresh cadence

Normal regeneration remains offline and reproducible. The existing project cadence is a deliberate
review at least monthly and before releases or relevant upstream changes. Neither the repository
nor the inspected Codex automation configuration has a TCGdex updater. No new recurring job was
created by this work. The TCGdex FAQ describes community-maintained data and ongoing detailed-variant
corrections, not a fixed monthly publisher SLA: https://tcgdex.dev/fr/faq .

## Validation and integration boundaries

- `python verification/test_tcgdex_snapshot.py`: passed (308 hashed records, offline).
- Qualifier fixtures cover stamped Normal/Holo/Reverse, jumbo, missing size, subtype, unknown native
  values, reviewed localized ordinary treatments and mirror/League boundaries.
- Seeded missing/downgraded/wrong-stamp printings are detected by the conservation check; rejected
  acceptance leaves old snapshot bytes and the staged candidate unchanged.
- Snapshot acceptance was explicitly approved in this chat. Language units, specimens and owner
  decisions are preserved against current main, including the separately merged #465 decisions.
- Final data conservation is captured in `integration-validation.json`: 968 → 981 collector items,
  903 → 922 verified printings, 65 → 59 candidates, and zero lost prior collector, physical or claim
  IDs. The six promotions are the five SM05 languages plus English Build-A-Bear.
- Full regeneration/core, browser acceptance and post-push publication receipts are reported in
  the PR. They are separate checks and are never inferred from this evidence capture.


## Stable standalone identities

A new exact finish can name an already retained standalone specimen printing. The canonical graph
projector preserves its physical ID, attaches the current compatible specimen provenance once,
and retains the original positive claim as optional `identityAnchorClaimId`. The current finish
claim remains its separate establishing claim. The collector uses that retained anchor so newly
added checklist references do not move collection state to a new item ID. Anchors must reference
positive current evidence attached to the same physical target; missing, pending and wrong-target
anchors fail validation. Tests cover replay, source order and incompatible finishes.

The original reviewed graph base was recovered through the canonical projector after the interrupted
preview, then reconciled to main `fb0ad8c5` (including merged #465 and #466). No reviewed locality base, owner
decision, specimen metadata or image was replaced by a generated catalogue. The official acceptance command consumed the staged cache file. The accepted versioned snapshot
remains byte-identical to the post-acceptance checkpoint; its SHA-256 is recorded in the integration
report. No refetch was used.

The corrected gain is **14 technical finish rows and 13 collector items**, not 23 new cards. Six
Cosmos-only API statements attach finish evidence to existing compatible printings, preserving
their pattern, stamp, distribution and dates. Ambiguous, conflicted or pending targets are not
upgraded through this attachment path.

## P1 product-identity refinement

Review finding 4448392823 exposed duplicate generic English Holo rows for PGO055, VIV131 and
SVP051. New positive API flags previously coexisted with richer curated V1 product identities.
The exact qualified detail rows name products 665278, 512365 and 720390, matching the retained
V1 product references. Product IDs link identities; they do not prove language or finish.

The existing override refinement path now attaches each positive API claim to that V1 identity;
SVP051 also declares its V1 auto-finish mapping explicitly. V2 Tin/Prerelease/Pokemon Center
identities remain separate and receive no borrowed V1 evidence. Positive API suppression was not
weakened. `product-refinement-regression.json` retains the exact approved payloads and hashes.
Regression checks cover all three products, V2 separation, replay, input order and a seeded
generic duplicate. The previous 17-row/16-item preview included these three duplicates and is
superseded by the 14-row/13-item result above. All 968 main collector IDs and existing physical
IDs remain conserved, and the three source/owner stores match merged main byte-for-byte.

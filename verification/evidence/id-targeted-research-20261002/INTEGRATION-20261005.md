<!-- doc: role=Indonesian finish acceptance and conservation record; stage=reference -->
# Seven Indonesian findings accepted — 2026-10-05

The owner authorized acceptance of all seven retained findings into draft PR #421. The baseline
is 8f6dc2bd231d5d380fbaf31eacf5f0357ae06e67, including main a5e8428 and the merged batch workflow.

Six exact deck printings now carry positive Non-Holo evidence: AS1D 108/140, AC3D 120/172,
sc1D I 132/164 and 133/164, scA I 084/135, and scD I 111/159. The five articles explicitly
identify Indonesian releases and the exact card numbers. Existing official identity specimens
establish the printed set codes; they do not supply physical-finish authority. Source-native
excerpts, capture methods and retrieval dates remain the original 2026-10-02 observations.
The acceptance pass uses the existing reviewed-source graph helpers and retains six source
records, five positive finish profiles and six exact physical-printing claims. It is byte-idempotent.

The final reference audit exposed a shared registry gap: reviewed physical-printing evidence
in set-source records was omitted from the evidence index, although the graph and collector
projection consumed it. The existing set-source indexing function now records explicit finish
observations as well as dates. Authority follows the observation's bound URL, including mixed
source containers; identity-only set membership does not create a finish claim. The acceptance
check covers every affected retained source, including the earlier Traditional Chinese and
official localized observations, and rejects the same boundary regression with a mixed-source
fixture. Those earlier printings themselves are unchanged.

Indexing the complete affected scope also exposed an unregistered existing publisher URL.
Its exact Journey Together Build & Battle article now has a manual positive-finish surface,
bound to the retained 2026-09-02 product statement and a separate out-of-scope fixture. It does
not grant general news coverage, regional identity, Staff, patterns or finish-list closure.
The 2026-10-05 web-reader probe returned an iframe rather than article text; no new retrieval
date or claim of current article accessibility is assigned to the historical observation.

The original 900x900 seller JPEG for sc1b I 119/153 was imported through the canonical manifest
importer as SPEC-0607. Its SHA-256 is
4446e79e2dd204ff9d54602e0600c92991c7b756bc8ea00903b63b5a4c5fa106.
Indonesian text and the printed number establish identity; cyan/green foil reflections in the
upper illustration, right border and lower rule bar establish Holo. This is an inspected seller
photo, not owner custody or an owner-attested finish. Tesseract is unavailable; inspection was
visual at original resolution. The original inspection date is preserved as 2026-10-02.

No finish list is closed, no absence is asserted and no rarity is changed. All existing specimen
records, language verdicts, owner decisions, release identities and unrelated collector items
are preserved. The catalogue moves from 19/37 to 26/37 gap-free Indonesian releases, with 11
remaining finish gaps. The HTML research checklist now lists those eleven only.

Reproduction:

```console
python verification/fetch_attachment.py --manifest verification/evidence/id-targeted-research-20261002/manifest.json
python verification/passes/admit_issue258_id_deck_finishes_20261005.py
python scripts/scoped_regen.py --lane source-discovery
python verification/evidence/id-targeted-research-20261002/check_integration.py
python scripts/regen.py
```

The scoped source-discovery checkpoint passed 19/19; it is not the L3 gate. Full delivery
validation and the post-push publication-history check are reported in PR #421.

Local delivery note: the combined write pipeline intermittently raised Windows OSError 22
when opening existing JSON outputs. The same canonical generators completed in isolation;
the completed output tree is validated with the normal full `scripts/regen.py --check` gate.
No checks or generators are omitted and no retry behavior is added to product code.

Final reconciliation: documentation commit 7e5d500feb9393317f461bdb9c0e4c7d34b6b656
was incorporated before push. With expanded execution permissions, the full canonical
`python scripts/regen.py` write/check/core pipeline completed successfully on the combined tree.
The seven-finish conservation check also passed against the original pre-acceptance head.

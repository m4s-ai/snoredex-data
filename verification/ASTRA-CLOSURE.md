<!-- doc: role=dated ASTRA remediation decisions; stage=reference -->
# ASTRA remediation decisions — 2026-09-08

Issue [#357](https://github.com/m4s-ai/snoredex-data/issues/357) completes the authority,
complexity and documentation scope of the original [audit](../ASTRA.md). This document records
bounded implementation decisions; current priorities remain in the issue tracker.

| Finding | Implemented contract / retained decision | Evidence |
|---|---|---|
| F12 | Preserve the hybrid candidate and graph stores. Document field writers, recovery sources and partial regeneration instead of describing the graph as disposable. Separating the reviewed base into new stores is deferred: it would require an identity-preserving migration beyond this repair. | [Ownership and recovery](../WORKFLOW-MAP.md#hybrid-ownership-and-recovery); graph regression preserves reviewed work metadata and verifies repeated projection stability. Existing physical identity/permutation and invalid-write tests remain in the same suite. |
| F17 | Ratchet existing complexity exceptions down to the measured implementation. No baseline is increased. No function body is mechanically split for a documentation repair. High-complexity validators remain explicit maintenance debt, to simplify at the next behavior change with domain fixtures. | `verification/complexity.py` measures 917 active functions, maximum cyclomatic complexity 111, 176 functions above 10 on this date. These are regression metrics, not a cognitive-complexity or maintainability grade. |
| F19 | Correct the public evidence promise, retained graph description, obsolete archive wording and ADR implementation status. Earlier repairs already corrected the Handover anchors, specimen-only count guidance and automatic image-group wording. | Site source `scripts/site.py`; active `CLAUDE.md`, `HANDOVER.md`, `WORKFLOW-MAP.md`; ADR-0008 now distinguishes design from implemented state. Current data counts remain owned by generated audits and checks. |

The original ASTRA measurements and historical reports remain dated evidence. They are not
rewritten to imply that the current implementation existed at audit time. Artwork automatic
image groups do not establish reviewed illustration identity; owner decisions, inspected
specimens and marketplace candidates retain their separate evidence roles.

Validation for this change uses the existing graph fixture suite, `compileall`, full
`scripts/regen.py --check` and `verification/test_site.py`. Commit-specific outcomes belong
in the linked PR and issue update; this document does not predeclare a future gate result.

<!-- doc: role=retained CL prerelease uncertainty review; stage=history -->

> Historical record — 2026-11-01; current values are determined by canonical stores.

# CL 33/95 V2: French and Italian unconfirmed

The owner requested the label **Unbestätigt** for the French (U0469) and Italian
(U0471) prerelease language claims. Both project to `needs-evidence`.

[Elite Fourum posts 583–584](https://www.elitefourum.com/t/list-of-all-tcg-cards-that-exist-for-a-specific-pokemon/16709/584)
explicitly question whether the two prerelease entries were inferred from English.
The list author acknowledges the assumption and retracts those entries. Selected public post
fields, their original timestamps, and the retrieval time are retained in `discussion.json`;
`review.json` binds that file's SHA-256 to the reviewed scope. No photograph was supplied by
these posts and no physical printing or non-printing is asserted from them.

The French legacy TCGdex record identifies the regular card only (`sibling-derived` for V2).
The Italian legacy expansion record does not reach a distribution promo (`product-or-set`).
The historical raw verdicts remain recorded; the application excludes both from `exists`.
Regular V1, English/German V2, specimens, physical identities and owner absence decisions are
outside this correction. The journal preserves both previous observations.

Replay: `python verification/passes/review_cl33_prerelease_languages_20261101.py`, then the
canonical regeneration/release gate from `scripts/regen.py`.

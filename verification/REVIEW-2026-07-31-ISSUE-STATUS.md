# Open-issue status check — 2026-07-31

Re-verification of every open issue (#28–#38) against the tree at `1bcfd8b`. Each claim in each
issue was re-run against the current data and scripts rather than taken from the issue text.

Method: counts recomputed from `snorlax_cards.json`, `verification/units.json` and the
`analysis_*.json` artifacts; script claims checked by reading the cited lines; `review_findings.py`
executed locally.

| Issue | Title | Status |
|---|---|---|
| #28 | [P1] Portable build | Mostly resolved |
| #29 | [P1] Idempotent / atomic passes | Open, unchanged |
| #30 | [P1] Canonical data model | Largely resolved |
| #31 | [P1] Product type vs market | Open |
| #32 | [P1] Evidence policy | Open |
| #33 | [P2] JP artist parser | Open, unchanged |
| #34 | [P2] Image formats | Open, unchanged |
| #35 | [P2] Network cache | Open, unchanged |
| #36 | [P2] Integrity suite / CI | Largely resolved |
| #37 | [P2] Documentation | Partially resolved |
| #38 | [TRACKING] | 0/10 ticked; Phase 3–4 work has largely landed |

## #28 — Portable build — mostly resolved

The hard-coded Windows checkout path quoted in #28 — a `snorlax-cardmarket` directory under a
personal user profile — no longer appears anywhere: 0 hits across all `.ps1` and `.py` files. (The
literal is deliberately not reproduced here: `review_findings.py` check P4 forbids personal paths
anywhere in the tracked tree, and that applies to review notes too.) 72 PowerShell files derive the root from `$PSScriptRoot`, 15
Python files from `Path(__file__)`.

Still outstanding:

- `_chunk1..3.json` and `_cards_stage*.json` are absent from the tree and absent from `.gitignore`,
  so `scripts/build.ps1:4` cannot run from a clean clone.
- `README.md:114` and `HANDOVER.md:85` still document the order
  `mkunits → build → join → getimages → finalize → analyze → finishes`. `scripts/mkunits.ps1:3-11`
  still regenerates units from `snorlax_cards.json` with freshly numbered `U%04d` ids, so following
  the documented order discards the verification state of all 719 units.

## #29 — Idempotent, atomic, transition-safe passes — open, unchanged

- `verification/passes/verify_tcgdex.ps1:33` still reads `if($u.status -eq 'confirmed'){ continue }`.
  Only `confirmed` is protected, so a `contradicted` unit can still be overwritten by a generic
  lookup pass.
- The same file still assigns `no-source-available`, which is not among the four statuses the store
  actually uses (`confirmed` / `contradicted` / `pending` / `needs-manual-review`).
- 0 of the 64 scripts under `verification/passes/` write through a temp file and atomic rename, so
  the `units.json` rewrite and the `evidence.jsonl` append can still diverge on an interrupted run.

## #30 — Canonical data model — largely resolved

Recomputed cross-artifact agreement:

- `analysis_artists.json` now totals 116 printings against 116 carded artists in the main dataset
  (was 79 vs 115).
- `analysis_shared_cards.json`: 0 release-artist deviations from the main dataset (was 34).
- `editions.unlimitedLanguages`: 0 contradicted languages present (was all of them);
  `scripts/editions.py:47-77` now classifies from `c["languages"]`, the confirmed set.
- Unit-vs-card artist drift is down to 1 from 84 — and that single remaining case is the corrupted
  value tracked by #33, not independent drift.

Still outstanding: `scripts/analyze.ps1:3-9` still prefers `_cards_stage3.json`, then
`_cards_stage2.json`, before falling back to `snorlax_cards.json`. The fallback makes it runnable,
but the canonical node stays ambiguous — the acceptance criterion asks for exactly one.

## #31 — Product type vs market — open

The root cause is intact. `scripts/analyze.ps1:18` still classifies by language count:

```powershell
if($langs -contains 'English'){ if($langs.Count -ge 10){return 'Global (code card)'}; return 'Western' }
```

Current consequences in `snorlax_cards.json`:

- KSS Snorlax carries `isCodeCard=false` with `market="Global (code card)"`.
- 4 of the 7 genuine code cards carry `market="Western"` (the two Snorlax Blister cards, the Snorlax
  Tin card, and the Snorlax ex & Blissey ex Special Collection card).
- Market split: Western 83 · Japanese 68 · Simplified Chinese 37 · SEA promo 5 · Global (code card) 4
  · Traditional Chinese 1.

The README sub-point is fixed — `README.md:33` now states 7 code cards. `README.md:167` still reports
"global code cards 4", which is the market bucket rather than the product count; that reads as a
contradiction until product type and market are separated.

## #32 — Evidence policy — open

- 8 xPRE units are still `confirmed` on owner attestation alone: U0097–U0100 and U0311–U0314, each
  with `sourceType = "Owner attestation (domain expert)"` and `sourceUrl =
  "(owner attestation, domain expert)"`.
- `HANDOVER.md:195` still asserts "Currently 0 units rest on attestation alone". Documentation and
  data still disagree, which is the core of this issue.
- 35 resolved units carry prose rather than a URL in `sourceUrl`.
- 44 distinct free-text `sourceType` values (the issue counted 43).

Note that `review_findings.py` check S3 passes — non-URL evidence is correctly never hyperlinked, so
the rendering side is safe. The schema itself is still untyped.

## #33 — JP artist parser — open, unchanged

Both known corrupted values are still present and still propagated:

- `snorlax_cards.json:17064` — `"artist": "aky CG Works V進化"`
- `snorlax_cards.json:35466` — `"artist": "Shizurow レベルアップ LV. X"`

Contamination counts: `snorlax_cards.json` 2, `verification/units.json` 4 (including the evidence
string at `units.json:5773`), `verification/artists_official_jp.json` 1. The regex at
`verification/passes/jp_fetch.ps1:43-48` is unchanged.

## #34 — Image formats — open, unchanged

All 198 files under `images/` end in `.jpg`. Actual content: 143 `image/jpeg`, 55 `image/png` —
exactly the split the issue reports. `scripts/getimages.ps1:13-18` still forces the extension.

`review_findings.py` check R5 passes, but it only verifies that references and files agree by name;
no check inspects magic bytes or decodes the image.

## #35 — Network cache — open, unchanged

- `verification/passes/fetch_full.ps1:13` still ends its `catch` block with
  `'[]' | Set-Content $f -Encoding utf8`, and line 8 treats any existing file as a valid cache hit.
  A timeout therefore becomes a permanent empty result.
- `verification/passes/fetch_tcgdex.ps1:12-14` still has a bare `catch{ }` and writes whatever
  partial `$all` accumulated.
- Both still open with `$ErrorActionPreference='Continue'`. No cache metadata, no retry, no offline
  mode.

## #36 — Integrity suite and CI — largely resolved

`.github/workflows/release-gate.yml` now runs on every pull request across ubuntu-latest and
windows-latest and covers: Python and PowerShell syntax parsing, `review_integrity.ps1`,
`audit_evidence.ps1`, `verify_finish_sources.ps1`, `review_findings.py`, generator freshness for
eight generators enforced with `git diff --exit-code`, Playwright browser tests, the publish
allowlist, and a scan for absolute paths and stray cache directories.

`verification/review_integrity.ps1` is now repo-relative (`$B=Split-Path -Parent $PSScriptRoot`) and
exits 1 on failure — both specific defects named in the issue are fixed. The suite deliberately
reports counts as drift rather than asserting them, which satisfies the "separate snapshot numbers
from invariants" to-do.

`review_findings.py` currently runs 66 checks. Locally it reports 65/66; the single failure is P6
("Full history was available"), caused by this environment's shallow clone (`shallow=True`, 0
sensitive-history hits). That is an environment artifact, not a repository defect — CI checks out
with `fetch-depth: 0`.

Still outstanding from the issue's to-do list: no image format/decode check (blocked on #34), no
status-transition or migration-idempotency tests (blocked on #29), and no JSON Schema files —
validation is imperative Python rather than declarative schemas.

## #37 — Documentation — partially resolved

Resolved:

- `README.md:33` states 7 code cards.
- README carries generated blocks with `scripts/readme_stats.py --check` enforced in CI; the check
  passes on the current tree.
- `verification/RESUME.md` now frames its old numbers as history — `:331` "at this checkpoint",
  `:356` "the then-19 contradictions", `:364` "rose from 79/198 to 108/198", `:471` "Historical
  checkpoint". The current-versus-historical confusion the issue describes is gone.
- Date precision is modelled: `analysis_confirmed_releases.json` rows carry `datePrecision`
  (`year|month|day`), `dateApproximate`, `dateSource` and `dateSort`.

Still outstanding:

- `verification/open-items.html` is still hand-maintained. No generator exists — `scripts/publish.py:53`
  only ships the file and `scripts/site.py:756` only links to it.
- `HANDOVER.md:107` still describes `report.ps1` as "Regenerates coverage + all export files", which
  overstates what it produces.
- `scripts/confirmed_releases.py:280` still hardcodes `"generated": "2026-07-31"`. Worth noting this
  is now in tension with the CI gate: the release gate regenerates artifacts and requires
  `git diff --exit-code` to be clean, so a wall-clock date would fail every run. Resolving this
  needs a source-derived timestamp (for example the input hash or last data commit), not simply
  `date.today()`.
- `dateExact` still appears 204 times in `analysis_confirmed_releases.json`, retained and documented
  as the deprecated inverse of `dateApproximate`.

## #38 — Tracking — partially satisfied

No checkbox is ticked, but the underlying work has moved unevenly relative to the planned phase
order. Phase 4 (#36) is largely done ahead of the Phase 1–2 items it was meant to depend on, and
Phase 1's #28 is mostly done while #29 and #32 are untouched.

Against the eight overall acceptance criteria:

- Clean clone can run the documented build — **no** (#28: missing chunk and stage inputs).
- No script writes outside the active checkout — **yes**.
- Repeated builds and verification passes are idempotent — **partly**; generator freshness is
  enforced in CI, but the verification passes themselves are not idempotent (#29).
- Generated artifacts match the canonical model — **largely yes** (#30).
- Status, evidence and audit log follow a versioned schema — **no** (#32).
- Known market, artist, edition, unit-drift and image errors corrected — **partly**; edition and
  unit-drift errors are fixed, market (#31), artist (#33) and image (#34) errors remain.
- CI covers syntax, schemas, freshness, migrations, images and doc numbers — **partly**; syntax,
  freshness and doc numbers are covered, schemas/migrations/images are not.
- README, HANDOVER, RESUME and HTML represent the same state — **partly** (#37).

## Suggested order from here

1. **#33** — smallest fix with real data impact, and it clears the last unit-vs-card artist drift,
   closing out #30's remaining data criterion.
2. **#31** — a self-contained change to one heuristic in `analyze.ps1`, plus regeneration.
3. **#32** — needs a policy decision on owner-only evidence before any code changes; either
   reclassify the 8 xPRE units or correct `HANDOVER.md:195`.
4. **#34** and **#35** — independent of the above, and each unlocks a CI check listed in #36.
5. **#29** — the largest change; consolidating 64 pass scripts onto one migration library.
6. **#28** and **#37** — finish the build DAG and the remaining documentation gaps last, once the
   data model is settled.

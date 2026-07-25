# Public-readiness audit

Issue #5. Making Git history public cannot be undone once others clone it, so this records what
was actually checked, what passed, and what a human still has to decide.

Re-run the mechanical parts with:

    python verification/review_findings.py     # checks P1–P4, L1

Audit date: 2026-07-25 · commit range: full history, root through `HEAD`.

## Mechanical checks — passed

| Check | Method | Result |
|---|---|---|
| No absolute local paths | `grep -rEI "C:\\\\Users\|/Users/\|/home/[a-z]+/\|D:\\\\"` across all tracked `.ps1`, `.py`, `.md`, `.json` | **0 hits.** Scripts resolve the checkout from `$PSScriptRoot` / `Path(__file__)`. |
| No credentials, tokens, cookies | `grep -rEIn "(api[_-]?key\|secret\|passwd\|password\|token *=\|Bearer \|Authorization\|Cookie:)"` | **0 hits** after excluding `variantToken`, the Cardmarket V-token vocabulary. |
| No email addresses or personal identifiers | regex sweep across tracked text files | **0 hits.** |
| No deleted files hiding in history | `git log --diff-filter=D --name-only` | **Empty.** Nothing was ever committed and removed, so history holds no withdrawn material. |
| Committer identity | `git log --format='%an <%ae>'` | Single committer, GitHub `noreply` address. No personal email exposed. |
| Caches and scratch excluded | `.gitignore` review | `verification/cache/`, `verification/zoom/`, `_evidence_audit.json`, `__pycache__/` all excluded and absent from the tree. |

## Requires human judgement — not cleared

These cannot be settled by a text scan and remain open:

1. **The 198 card images.** Each depicts a Pokémon card and is served from Cardmarket's image
   host. They are third-party material used for identification (`THIRD_PARTY_NOTICES.md`). A human
   should confirm the intended publication basis, and whether any image is a personal photograph
   rather than a catalogue image.
2. **Owner attestations and photographed specimens.** Recorded as anonymous evidence classes with
   no personal identifiers, which is the right shape. Publication consent is still the owner's to
   give explicitly.
3. **Repository vs site visibility.** Publishing the repository exposes the full history —
   including every verification pass and its reasoning. Publishing only a curated Pages artifact
   keeps the working history private. The epic recommends deciding before any visibility change.
4. **Licensor identity.** `m4s-ai` or "contributors to snoredex-data". See `LICENSE.md`.

## Blocking gaps

- **Verbatim licence texts are absent.** `LICENSES/` holds only instructions. The environment
  used for this pass denies outbound access to `polyformproject.org` and `creativecommons.org`,
  and reconstructing a legal text from memory risks silent divergence from the published wording.
  Check `L1` fails until both files exist, and the release gate refuses to publish.

## Verdict

The repository is **clean of secrets, personal paths, and withdrawn material** — the failure mode
most likely to make a visibility change irreversible does not apply here.

It is **not yet publishable**: the verbatim licence texts are missing and four owner decisions are
open. No visibility change should be made until both are resolved.

# Public-readiness audit

Issue #5. Making Git history public cannot be undone once others clone it, so this records what
was actually checked, what passed, and what a human still has to decide.

Re-run the mechanical parts with:

    python verification/review_findings.py     # current tree, every Git blob, licences, decisions
    python verification/publication_gate.py    # intentionally fails until owner approval

Audit date: 2026-07-25 · commit range: full history, root through `HEAD`.

## Mechanical checks — passed

| Check | Method | Result |
|---|---|---|
| Current tracked tree | `git ls-files -z`, binary detection, regex scan of every text file | **0 hits.** Scripts resolve the checkout from `$PSScriptRoot` / `Path(__file__)`. |
| Complete reachable history | `git rev-list --objects --all` + `git cat-file --batch`, every unique reachable blob | **82 hits**, all old `C:\Users\...` absolute-path occurrences across build, verification, and handover blobs. No credential or personal-email hit was found. The executable report prints the current blob count. |
| Shallow-check protection | `git rev-parse --is-shallow-repository` | **False.** CI uses `fetch-depth: 0`, so “full history” cannot silently mean one commit. |
| Deleted-name check | `git log --diff-filter=D --name-only` | Empty, but this is only supplementary: modified historical versions can still contain withdrawn data, which the blob scan catches. |
| Commit identity | `git log <publishable-head> --format='%ae %ce'`, enforced by check P7 | Author and committer addresses in the branch ancestry use GitHub/automation `noreply` identities rather than a personal contact address. GitHub's disposable PR merge commit is not treated as branch history. |
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
3. **Repository vs site visibility — these are not independent.** The enforced safe default is
   `private`. Publishing only a curated Pages artifact does avoid exposing the 82 historical
   local-path blobs, but it cannot deliver a site that collects corrections: the site's entire
   correction affordance is 206 links into this repository — 203 per-row *Correction?* links plus
   the repository and issue-tracker links — and every one of them is a 404 for a visitor who
   cannot see a private repository. Publishing the site alone therefore asks strangers for help
   and then turns them away. Checks P8 and `publication_gate.py` now refuse that combination, so
   the real choice is:

   - **Publish both.** Requires resolving the history finding below, and is the only option that
     makes the stated goal — public review and correction — actually work.
   - **Publish the site alone,** having first removed the correction affordance from it. The site
     becomes a read-only reference with no feedback path.

   Public repository visibility requires an explicit decision and either acceptance of the
   `C:\Users\...` paths or an authorized history rewrite. The repository has never been public and
   has no forks, so a rewrite is cheap now and irreversible-in-practice later: once a public clone
   exists, the paths cannot be recalled.
4. **Licensor identity.** `m4s-ai` or "contributors to snoredex-data". See `LICENSE.md`.

## Mechanical blockers resolved

- Both verbatim licence texts are present. `L1` verifies their publisher SHA-256 values.
- `publication-decisions.json` records every outstanding owner choice with safe false/private
  defaults. The manual Pages workflow calls `publication_gate.py`, so adding licence files alone
  can never trigger publication.

## Verdict

The current tracked tree is clean of detected credentials, personal paths, and contact details.
The complete Git history is **not** clean of personal local paths: 82 reachable blobs contain the
historical `C:\Users\...` checkout prefix. The repository must remain private unless that disclosure
is expressly accepted or a history rewrite is separately authorized.

The implementation is safe to merge but **not yet authorized to publish**. Four owner decisions
remain open, and the deployment gate enforces them independently of ordinary PR validation.

Publishing the site for public review additionally requires the repository to be public, because
that is where corrections are filed. The 82 historical `C:\Users\...` blobs are therefore on the
critical path to the project's stated goal, not a side note: they are the one finding standing
between the current state and a working public correction loop.

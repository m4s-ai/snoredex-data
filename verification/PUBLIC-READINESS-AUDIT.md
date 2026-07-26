# Public-readiness audit

Issue #5. Making Git history public cannot be undone once others clone it, so this records what
was actually checked, what passed, and what a human still has to decide.

Re-run the mechanical parts with:

    python verification/review_findings.py     # current tree, every Git blob, licences, decisions
    python verification/publication_gate.py    # intentionally fails until owner approval

Audit date: 2026-07-25, history re-audited 2026-07-26 after the redaction below · commit range:
full history, root through `HEAD`.

## Mechanical checks — passed

| Check | Method | Result |
|---|---|---|
| Current tracked tree | `git ls-files -z`, binary detection, regex scan of every text file | **0 hits.** Scripts resolve the checkout from `$PSScriptRoot` / `Path(__file__)`. |
| Complete reachable history | `git rev-list --objects --all` + `git cat-file --batch`, every unique reachable blob | **0 hits.** Previously 82, all occurrences of one Windows checkout prefix across build, verification, and handover blobs; redacted on 2026-07-26 (see below). No credential or personal-email hit was ever found. The executable report prints the current blob count. |
| Shallow-check protection | `git rev-parse --is-shallow-repository` | **False.** CI uses `fetch-depth: 0`, so “full history” cannot silently mean one commit. |
| Deleted-name check | `git log --diff-filter=D --name-only` | Empty, but this is only supplementary: modified historical versions can still contain withdrawn data, which the blob scan catches. |
| Commit identity | `git log --all --format='%ae %ce'`, enforced by check P7 | Author and committer addresses on **every reachable commit** use GitHub/automation `noreply` identities rather than a personal contact address. Making a repository public publishes every ref, so the scan spans all of them; the sole exemption is GitHub's disposable PR merge commit, whose identity belongs to neither branch. |
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
   correction affordance is 206 links into this repository — 203 per-row *Correction?* links, one
   general correction entry point, and the repository and issue-tracker links — and every one of
   them is a 404 for a visitor who
   cannot see a private repository. Publishing the site alone therefore asks strangers for help
   and then turns them away. Checks P8 and `publication_gate.py` now refuse that combination, so
   the real choice is:

   - **Publish both.** Requires resolving the history finding below, and is the only option that
     makes the stated goal — public review and correction — actually work.
   - **Publish the site alone,** having first removed the correction affordance from it. The site
     becomes a read-only reference with no feedback path.

   The historical-paths obstacle to publishing both is resolved — see the history redaction
   below. What remains here is the owner's decision to make the repository public at all.
4. **Licensor identity.** `m4s-ai` or "contributors to snoredex-data". See `LICENSE.md`.

## Mechanical blockers resolved

- Both verbatim licence texts are present. `L1` verifies their publisher SHA-256 values.
- `publication-decisions.json` records every outstanding owner choice with safe false/private
  defaults. The manual Pages workflow calls `publication_gate.py`, so adding licence files alone
  can never trigger publication.

### History redaction, 2026-07-26

The 82 historical hits were one literal Windows checkout prefix, introduced as a hardcoded `$base`
in every script and later refactored away in `Make repository scripts path-independent`. The
current tree had been clean since; only reachable history still carried it. Because `git clone`
transfers the entire object graph by default, every clone shipped all 82 blobs regardless.

Owner-authorized on 2026-07-26 and executed with `git filter-repo --replace-text`, redacting the
user segment of the prefix to `C:\redacted` and leaving the remainder of each path intact:

- **All 64 commits across all six branches** were rewritten — 43 on the `main` line, plus four
  stale branches left behind by squash-merged pull requests (`agent/portable-script-paths`,
  `claude/database-review-recommendations-kq8aec`, `codex/finish-verification`,
  `codex/readme-ai-declaration`). Those four are the reason a first pass over `main` alone was not
  enough: `git clone` fetches every `refs/heads/*`, so a merged branch nobody deleted kept
  shipping the full pre-redaction history to every cloner. Verified by cloning the remote and
  scanning the result, not by reasoning about which refs *should* matter.
- Commit messages, authorship, dates and ordering are unchanged. Commit signatures are dropped,
  which is unavoidable: a signature over rewritten content cannot still verify.
- Branch tree hashes are byte-identical before and after, confirming no current content was
  altered — the rewrite reached historical blobs only.
- Re-audit of a fresh clone: **0 hits across 570 blobs**, all six branches. `P4`, `P6` and `P7`
  pass.

Scope, stated precisely: Git transfers only reachable objects, and `git clone` fetches
`refs/heads/*` but never `refs/pull/*`. No clone, fetch or pull can carry the redacted content
again. The pre-rewrite objects still exist on GitHub's servers and stay reachable by direct commit
SHA and through the five merged pull-request refs, which were deliberately retained so the review
history stays intact. Removing those would require deleting the pull requests and asking GitHub
Support to purge unreachable objects; the owner accepted that residual on 2026-07-26.

## Verdict

Both the current tracked tree and the complete Git history are clean of detected credentials,
personal paths, and contact details. The history finding that previously required the repository
to stay private is resolved.

The implementation is safe to merge but **not yet authorized to publish**. The remaining owner
decisions are the publication approvals themselves, and the deployment gate enforces them
independently of ordinary PR validation.

Publishing the site for public review requires the repository to be public, because that is where
corrections are filed. Nothing mechanical now stands in the way of that; what remains is the
owner's decision, recorded in `publication-decisions.json`.

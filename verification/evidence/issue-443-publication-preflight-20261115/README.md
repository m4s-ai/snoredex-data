<!-- doc: role=publication preflight for issue 443; stage=history -->

# #443: publication handoff for PR #591, 2026-11-15

The owner requested #443 and #444 on the same PR as the original #434 follow-ups. PR #591 is the
selected change set. This record prepares its publication; it is not a deployment receipt.

## Live baseline checked

The GitHub Actions API still reports the latest successful `Publish site` run as
[43431726917](https://github.com/m4s-ai/snoredex-data/actions/runs/43431726917), started
2026-11-13T13:12:54Z. A fresh HTTPS read of the live `collector_deployment.json` returned:

- artifactCommit: `920a47bdab6cee7674059e7c8224716f3bb5b055`
- publishedAt: `2026-11-13T13:20:48Z`
- catalogueFingerprint: `sha256:a31e423c475f27d0f85bbe43175ca8c452a5f66e156d4826534a654db4c70c4b`
- byteDigest: `sha256:97a028fe643a0c0f0e3e2600d677d2df8894e4f28dfa8c40e5763c80649a415e`
- byteLength: `4283703`

The repository API reports `public`, matching `publication-decisions.json`. Existing owner
approvals are preserved. The PR's preceding head `396ec74a94d7544e3d8814ceb6e25496bbe10240`
passed both Release gate and UI browser gate; the final PR head must pass its own checks.

## Remaining execution boundary

The workflow `.github/workflows/pages.yml` deliberately accepts only `refs/heads/main`. PR #591
is not merged, and the owner's instruction does not explicitly authorize merging it. Repository
instructions require that separate instruction; no workflow guard is changed to avoid it.

After the owner approves the merge, follow these steps.

1. Verify the selected PR head's checks and merge PR #591 through GitHub; never push main.
2. Read the resulting main SHA and run `Publish site` on main. Confirm the run's `head_sha` is
   that selected merge commit before treating it as this release.
3. Wait for approval, both operating-system L4 checks, artifact handoff and Pages deployment.
   Their manifests must bind the exact commit and the same catalogue bytes.
4. Fetch live `collector_deployment.json` and `collector_catalogue.json`, compare commit,
   fingerprint, byte length and SHA-256 with the successful artifact, then inspect both live pages.
   Confirm active counts, removal of the Italian KSS wave hypothesis and the published source caveats.
5. Update #443 with the run, deployed SHA, fingerprint and observed result; close only after
   publication succeeds. Update #434 without changing the unresolved #438/#440/#444 evidence status.

Open finish, language and source questions are disclosed limitations, not a requirement to finish
unrelated projects before publication. No merge, workflow dispatch or deployment is recorded here.

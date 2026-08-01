# Launch runbook

Everything that has to happen to take the site public, in order. Written to be followed once, by
the repository owner, after which this file describes what was done.

Nothing here is automatic. The deployment gate blocks until the decisions below are recorded, and
it is meant to — publishing is the one step in this project that cannot be undone.

**Status: launched 2026-07-31.** Every step below is done. The site is live at
<https://m4s-ai.github.io/snoredex-data/>, the repository is public, and the correction loop is
verified end to end by issue #22. This file now records what was done rather than what to do.

---

## Before you start

Confirm the gate currently blocks, so you know the mechanism works before you rely on it:

```console
python verification/publication_gate.py    # must exit 1 and list what is missing
python verification/review_findings.py     # must be 59/59
```

---

## Step 1 — Record the publication approvals — **done 2026-07-26**

Three substantive attestations, approved by `M4S.Collection` and recorded in
`publication-decisions.json`:

| Field | What was attested | State |
|---|---|---|
| `licenseGrantsApproved` | The PolyForm and CC BY-NC-SA grants in `LICENSE.md` are **operative**, no longer a described intention. | `true` |
| `ownerAttestationsApproved` | Evidence recorded as owner attestations and photographed specimens may be published. They carry no personal identifiers. | `true` |
| `thirdPartyImagesApproved` | The Cardmarket card images in `images/`, and the licensor's own specimen photographs in `verification/specimens/`, may be published on the basis in `THIRD_PARTY_NOTICES.md`. Covers the categories, so photographs added later need no fresh approval. | `true` |
| `sitePublicationApproved` | The site may be deployed to GitHub Pages. | **`false` — belongs to step 2** |

`licensor` is recorded as `M4S.Collection` and verified byte-exactly by the gate. `approvedBy` and
`approvedAt` are set.

> **Why `sitePublicationApproved` is not set with the rest.** Setting it while the repository is
> still private makes check **P8 fail**, turning the release gate red on every pull request. That
> is deliberate: a public site whose 206 correction links point into a private tracker is broken by
> construction. It is the atomic partner of repository visibility, so both belong in step 2.

## Step 2 — Publish the site and make the repository public — **done 2026-07-31**

```json
  "sitePublicationApproved": true,
  "repositoryVisibility": "public",
  "repositoryPublicationApproved": true,
```

Visibility was flipped in **Settings → General → Danger Zone**, and verified: the GitHub API
reports `visibility: public`, and anonymous requests to the repository and to `CONTRIBUTING.md`
both return HTTP 200.

The decision file is no longer taken on trust. The deploy workflow reads the repository's real
visibility from the API and passes it to `publication_gate.py --actual-visibility`, which refuses
to publish if the record and reality disagree — the failure mode where someone sets the field but
forgets the toggle, and the site goes live with every correction link 404ing.

The history obstacle that previously blocked this is resolved: the historical Windows checkout
paths were redacted on 2026-07-26 and a fresh clone of the remote reports zero hits across all six
branches. See `PUBLIC-READINESS-AUDIT.md` for what a rewrite does and does not remove.

Verify both steps landed:

```console
python verification/publication_gate.py    # must now exit 0
python verification/review_findings.py     # must still be 59/59, with P8 passing
```

## Step 3 — Repository settings for public contribution — **mostly done 2026-07-31**

These are not enforced by any check, because they live in GitHub settings rather than in the
repository. All are in **Settings → General** unless noted.

- **Allow forking** — **enabled.** Pull requests from outside the organisation are possible.
- **Pages source** — **enabled** (`has_pages: true`). Confirm it is set to **GitHub Actions**
  rather than a branch, or the workflow's upload has nowhere to go.
- **Discussions** — still off. Optional. Worth enabling if you want a place for questions that are
  not correction reports, so the issue tracker stays a work queue.
- **Stale branches** — four merged branches remain (`agent/portable-script-paths`,
  `claude/database-review-recommendations-kq8aec`, `codex/finish-verification`,
  `codex/readme-ai-declaration`). Their pull requests are merged and deleting the branches does not
  affect them. Optional tidying, visible to anyone browsing once public.

## Step 4 — Deploy — **done 2026-07-31**

Run the **Publish site** workflow manually: **Actions → Publish site → Run workflow**, on `main`.

It runs, in order: re-check every publication decision, the full release gate on Ubuntu and
Windows, regeneration of every artifact from its inputs, assembly of the public tree from the
allowlist in `scripts/publish.py`, verification that the tree holds nothing else, and only then
the upload. If the approval job fails, nothing is uploaded — that is the intended behaviour, not
an error to work around.

First run: all four jobs green, deployed to <https://m4s-ai.github.io/snoredex-data/>.

## Step 5 — After the first deployment

- **Follow one Correction? link end to end** — the single most important test, because it is the
  reason the site is public at all. **Done 2026-07-31 (issue #22):** the form rendered in full,
  with the row identity, card, set, number and current state pre-filled, and the `Correction` and
  `Needs Evidence` labels applied automatically.

  This test earned its place. The form was rejected outright by GitHub on the first two attempts
  and served a blank issue instead — once for an empty `description` attribute, then for the
  reserved word `None` in a dropdown. Every local check passed throughout: the form existed, was
  current, demanded evidence, and all 203 links pointed at it. Only clicking one revealed that it
  never loaded. Check `T7` now covers both causes.

- Check that `CONTRIBUTING.md`, `verification/FINISH_SOURCES.md` and
  `verification/open-items.html` all resolve from the *Help correct this* section.
- Watch the first few incoming reports against the source ladder. The rule that decides whether a
  report is usable — positive evidence, never absence — is stated in the form, in
  `CONTRIBUTING.md`, and on the site, but it is the thing newcomers most often get wrong.
- Close the test issue once you are satisfied; it is otherwise the first thing a visitor sees in
  the tracker.

---

## What is already done

Nothing below needs action; it is recorded so the launch state is auditable.

- History redacted and verified against a fresh clone — zero hits across all six branches.
- Licensor recorded as `M4S.Collection`, pinned byte-exactly in the gate, with a licensing contact
  in `LICENSE.md` and on the site.
- Correction loop built and tested: 203 per-row links plus a general entry point, all prefilled,
  all targeting the generated issue form; 44 browser checks cover it, and check `T7` validates the
  form against the rules GitHub's own validator enforces — including the reserved words that the
  published JSON Schema does not describe.
- `CONTRIBUTING.md` and the site's *Help correct this* section state the evidence rule.
- Public artifact restricted to an allowlist, with every published page link-checked.
- Release gate runs on Ubuntu and Windows for every pull request.

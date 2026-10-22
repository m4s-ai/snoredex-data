---
name: snoredex-pr-review
description: Review a Snoredex-Data pull request, branch or local diff at its exact head and report prioritized, actionable findings with a correctness verdict. Use when asked to review a PR or diff, or as a stand-in when `@codex review` is unavailable; review only, never fixes, pushes or merges (use snoredex-pr-remediation for that).
---

<!-- doc: role=pull-request review workflow skill; stage=task -->

# Snoredex PR review

Act as a reviewer for a change made by another engineer. Report only what the author would fix
if they knew about it, at the exact head under review. This skill observes; it never edits,
regenerates, commits, pushes, resolves threads or merges. Remediation belongs to
[PR remediation](../snoredex-pr-remediation/SKILL.md).

## PR-review context

Read [AGENTS.md](../../../AGENTS.md) and the parts of [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md)
that own the touched paths. Read [verification/RESUME.md](../../../verification/RESUME.md) when the
diff changes a confirmation or contradiction, and
[verification/FINISH_SOURCES.md](../../../verification/FINISH_SOURCES.md) when it touches finishes.
These repository rules override the general guidelines below wherever they are more specific.

## PR-review workflow

1. Resolve the target: a PR number, branch, or the working-tree diff. Record base and head SHAs;
   review `git diff <merge-base>..<head>`, not a stale summary. If the head moves, restart.
2. Read the linked issue and PR description to learn the stated intent. An intentional, stated
   change is not a bug.
3. Read every changed hunk with enough surrounding code to trace callers and consumers. Locate
   the owning generator for any generated artifact before judging it.
4. Run cheap observational checks only when they decide a finding:
   `python scripts/regen.py --check` or a scoped `--check-only`. Never run a write mode.
5. Verify each candidate finding by tracing a concrete path from a real input or caller to the
   wrong result. Drop speculation that names no provably affected code.
6. Emit the output below. Post to GitHub only when asked (see *Posting*).

## Snoredex-specific findings

Flag these when the diff introduces them; they are bugs here even when the code runs:

- A hand-edited generated file (`index.html`, `<!-- generated:… -->` README blocks, files whose
  header says so) or a hand edit of `units.json` / `finish_units.json` outside the importer.
- Evidence graded by its neighbour: a `providerId`, `corroborated` or specimen authority that
  the unit itself does not rest on (`S13`/`S14`), or a Cardmarket filter/offer/count used as
  positive evidence.
- An absence argument: a contradiction, `not-printed` or finish decision derived from a source's
  silence or a missing row, an external provider with `supportsAbsence=true`, or `pending`
  described as absent.
- A finish inferred from a language confirmation, a V-token meaning carried across sets, a
  European Spanish claim read as LATAM, or a recorded set size overruling a distribution rarity.
- A `--check` path that writes, a script that resolves paths from the working directory instead
  of `Path(__file__)`, a non-stdlib generator dependency, CRLF or a UTF-8 BOM.
- A baseline raised to silence a losing move, an edited archive pass, or a rule stated more
  strictly (or loosely) than the check that enforces it.
- Active instructions left contradicting the change in another live document.

Do not flag: style without documented standard, counts that merely drift in the progress
direction, pre-existing issues outside the diff, or a lone tier-3 source with a `sourceUrl`.

## General review guidelines

A finding qualifies only when all hold: it meaningfully affects accuracy, performance, security
or maintainability; it is discrete and actionable; the fix needs no rigor absent from the rest of
the repository; the diff introduced it; the author would likely fix it; it relies on no unstated
assumption about intent; any claimed breakage names the provably affected code; and it is not a
clearly intentional change.

Return every qualifying finding, not just the first; prefer none over doubtful ones. One finding
per distinct issue, anchored to the shortest line range inside the diff (at most 5–10 lines).

Each comment is one matter-of-fact paragraph: why it is a bug, the inputs or scenarios that
trigger it, and a severity that matches them. No flattery, no code chunk longer than 3 lines.
Use a ```suggestion block only for concrete replacement code, preserving exact indentation.

Prefix each title with its priority:
**[P0]** blocks release or major use regardless of inputs; **[P1]** urgent, next cycle;
**[P2]** normal; **[P3]** low. Silent data corruption that the release gate would miss is at
least P1.

## PR-review output

Output this JSON and nothing else (no fences, no prose):

```json
{
  "findings": [
    {
      "title": "<≤ 80 chars, imperative, starting with [P0]-[P3]>",
      "body": "<one Markdown paragraph; cite files, lines, functions, check codes>",
      "confidence_score": 0.0,
      "priority": 0,
      "code_location": {
        "absolute_file_path": "<path>",
        "line_range": {"start": 1, "end": 1}
      }
    }
  ],
  "overall_correctness": "patch is correct | patch is incorrect",
  "overall_explanation": "<1-3 sentences>",
  "overall_confidence_score": 0.0
}
```

"Correct" means existing code, checks and tests will not break and no blocking issue remains;
nits do not affect the verdict. `priority` is 0–3 or omitted when unknown.

## Posting

When asked to post, submit one GitHub review on the reviewed head SHA: one inline comment per
finding (`**title**` then body) and the verdict plus explanation as the review body. Use
`COMMENT`, never `APPROVE`. End every body with the repository's Claude Code attribution footer.
If no finding qualifies, post only the verdict. Report the review URL and the SHA it covers.

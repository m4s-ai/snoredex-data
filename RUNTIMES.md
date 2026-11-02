<!-- doc: role=runtime-specific notes for agent harnesses; stage=task -->
# Agent runtime notes

[`AGENTS.md`](AGENTS.md) holds the rules every runtime shares. This file holds only what differs
between Claude Code, Codex and Hermes. Read it when you set up a runtime, when instructions or skills
seem to be missing, or when you change model or runtime. A rule that must always hold never lives
only here.

## Instruction loading by runtime

| Runtime | What it loads | Limit to respect |
|---|---|---|
| Claude Code | `CLAUDE.md`, which imports `AGENTS.md` (`@` imports, up to four hops); subdirectory `CLAUDE.md` files on demand | recommended under 200 lines per file |
| Codex | `AGENTS.md` files from the Git root down to the start directory, concatenated; no `@` imports | `project_doc_max_bytes`, 32 KiB combined by default; files past the limit are not added |
| Hermes | the `AGENTS.md` chain (preferred over `CLAUDE.md`); subdirectory files when a tool touches them | `CONTEXT_FILE_MAX_CHARS` 20,000 when the window is unknown, else 6 % of it; truncation keeps head and tail and drops the middle |

These limits are why `D6` caps `AGENTS.md` + `CLAUDE.md`. Sources and the measurements behind this
table are recorded in [#461](https://github.com/m4s-ai/snoredex-data/issues/461); recheck them when
a runtime changes. The repository routes by task (WORKFLOW-MAP §4 → skill), not by directory,
because subdirectory instruction files load differently in each runtime.

## Project skill discovery

- **Codex** discovers the canonical skills in `.agents/skills/`.
- **Claude Code** reads nothing under `.agents/`; each skill has a discovery shim in
  `.claude/skills/<name>/SKILL.md` that carries the canonical name and description and points to
  the canonical file. The documentation test keeps the shims in step; never put procedure in a shim.
- **Hermes** needs an owner-approved project root in `skills.trusted_project_dirs`, enabled
  `skills.project_discovery`, and a session started inside the checkout. After inspecting the
  skills and obtaining the user's trust approval, use `hermes skills trust <repo>` in the intended
  profile, then start a fresh project-scoped session. Inspect discovery/filter/quarantine
  diagnostics if skills remain absent; do not bypass a rejected scan or enable trust automatically.
  A terminal `cd` alone does not rebuild an existing conversation's skill inventory.

Other runtimes use their own supported skill and trust mechanisms, subject to their trust policy.
Without automatic discovery, follow the links in
[WORKFLOW-MAP.md §4](WORKFLOW-MAP.md#4-use-case-contracts) and read the selected skill directly.

## Attribution, branches and clones

- The commit trailer names the agent and model that made the commit, as the runtime supplies it.
  Never copy another runtime's or model's trailer.
- A cloud session may be assigned a branch and allowed to push only there. That branch takes
  precedence over the `fix/<n>-<slug>` convention and over a name an issue prescribes; its base is
  still the current `origin/main`.
- Cloud sessions often start from a shallow clone. `P6` and `collector_catalogue.py` need full
  history: run `git fetch --unshallow` once before the gate.
- [`snoredex-pr-review`](.agents/skills/snoredex-pr-review/SKILL.md) stands in for `@codex review`
  where that reviewer is unavailable.

## Changing model or runtime

A new model, model version, reasoning-effort setting or runtime keeps the same rules, gates and
authority boundaries. Before relying on it, replay the affected cases in
[`verification/SKILL-WORKFLOW-ACCEPTANCE.md`](verification/SKILL-WORKFLOW-ACCEPTANCE.md) and record
the exact model, version, effort and runtime with the results in the PR. Shorten or add an
instruction only for an observed difference, never because a vendor says a model needs less.

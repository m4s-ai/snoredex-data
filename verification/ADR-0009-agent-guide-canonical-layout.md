<!-- doc: role=architecture decision record for the canonical agent-guide layout; stage=reference -->
# ADR-0009 — AGENTS.md as the canonical agent-guide layout

**Status:** accepted; implemented in the #376 agent-guide-layout change

**Builds on:** ADR-0001 (locality-aware print identity) — no relation; listed for ADR continuity only.

## Context

The repository operates Claude Code, Codex and Hermes against one set of working rules
(non-negotiables, data-model traps, command order). Before this change those rules lived in
`CLAUDE.md`, with `AGENTS.md` acting as a pointer to it.

That layout is not portable and it split the runtime:

- **Claude Code** expands `@path` imports and auto-loads `CLAUDE.md`, so the rules reached it.
- **Codex** reads `AGENTS.md` directly and does not expand Claude-style `@path` imports; it
  received the 16-line pointer instead of the rules.
- **Hermes** prefers `AGENTS.md` over `CLAUDE.md` and likewise does not expand the `@` import.

So the rules were invisible to every non-Claude agent, and the pointer duplicated a
\"one rule\" and a read-before list that already lived in `CLAUDE.md` — a second copy to drift.

## Decision

Make `AGENTS.md` the single canonical carrier of the working rules. Reduce `CLAUDE.md` to a
one-line shim, `@AGENTS.md`, for Claude Code compatibility.

- Rules, traps and command order live only in `AGENTS.md`; the shim must never duplicate them.
- All internal references to the rules document (validators, scope guards, active docs, comments)
  point at `AGENTS.md`.
- `stage=auto` stays on both files — it is a load stage, not a generated-file flag, and both are
  auto-injected agent context (`DOC_STAGES` confirms `auto` is a stage, not `generated`).
- The D1/D4/D5 documentation checks and `test_pipeline_documentation.py` validate `AGENTS.md`,
  keeping the deterministic gate on the file the agents actually read.

Immutable and one-shot records (ASTRA audits, `verification/history/`, `verification/passes/`,
`ANALYSIS.md`) are preserved verbatim; their historical `CLAUDE.md` mentions are a record of what
the rules file was called when they were written, not a live path.

## Consequences

- Codex and Hermes now load the full rules; all three runtimes share one text.
- One active source of truth instead of a pointer plus a drifty duplicate.
- The D-series gate validates the file that governs agent behaviour.

Negative: renames ripple through validators and active references, and any future agent must read
`AGENTS.md` for the rules rather than `CLAUDE.md`.
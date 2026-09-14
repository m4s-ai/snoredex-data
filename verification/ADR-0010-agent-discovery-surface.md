<!-- doc: role=agent workflow discovery decision and acceptance boundary; stage=reference -->
# ADR-0010: Repository workflow discovery surface

Status: accepted for implementation under [issue #378](https://github.com/m4s-ai/snoredex-data/issues/378).

## Context and decision

An operator starting without session memory needs to select an existing workflow from a concrete
task, including when automatic skill discovery is unavailable. The repository already owns the
workflows, skills and execution manifests; the missing surface was their explicit connection.

[WORKFLOW-MAP.md §4](../WORKFLOW-MAP.md#4-use-case-contracts) is the single maintained
intent-to-workflow table. Its rows link the existing skill, domain contract and implementation
owner while retaining evidence and graph boundaries. [AGENTS.md](../AGENTS.md) owns the rule to
consult that route before inventing another processing path. [HANDOVER.md](../HANDOVER.md) points
to the same section. Skill descriptions distinguish nearby tasks without duplicating the table.

[llms.txt](../llms.txt) links operators to the rules and routing section using absolute GitHub
URLs. The publisher copies that text without rewriting links; these targets stay in the
repository and do not require publication of internal operator documents. Publication policy,
the allowlist and deployment approvals remain owned by their existing contracts.

## Registration and validation boundary

[The documentation test](test_pipeline_documentation.py) parses the registration cell of each
routing-table row. Each workflow ID from [the gate matrix](workflow_gate_matrix.json) must occur
in exactly one row; each scoped lane from [the manifest](scoped_pipeline_manifest.json) must
occur in at least one compatible row. Incidental IDs elsewhere in prose do not satisfy coverage.

Each route links an existing skill whose frontmatter name matches its directory. Linked
documents and scripts must exist. For registered workflows with projection roots, the entry
must name one of those owners. A scoped lane must support the workflow's impact class, and its
row must name an existing entry or step from that lane. Not every skill is an executable command;
observational routes may have no registered mutation workflow.

This is a bounded workflow assignment check. It does not prove that an operator read a document,
that prose is semantically correct, or that an unregistered script is not another entry point.
Reviewers must explicitly classify new operator entry points against the existing registrations.
Helpers, libraries, tests and archived migrations do not become user workflows merely because
they are Python files. No additional registry or filesystem-wide entry-point scanner is needed.
[scripts/regen.py](../scripts/regen.py) still owns test and generator order.

## Acceptance and evidence

The issue's task examples are tested by a fresh reader: select a skill, reach its domain contract
and implementation owner through at most four routing documents, then state the intended next
step. Test both document navigation without automatic discovery and an entry through llms.txt.
Record the prompts, environment/version, repository revision and worktree, provided skills,
documents read, selected skill and owner in the PR evidence. Additional required domain reading
is separate from the routing budget.

These selection tests do not import evidence, refresh providers, accept snapshots, change
canonical stores or deploy. A read-only request must select observational checks; a scoped lane
alone does not promise read-only behavior.

Regression fixtures cover newly registered workflows with and without a route, row-local
workflow/lane coverage, incompatible lanes, missing owners, renamed skills and missing targets.
An unrelated helper must leave routing coverage unchanged. The documentation test also checks
the operator URLs against their local repository targets. D1/D4 in the existing review gate
check document role/stage and heading hygiene, not semantic task selection.

An isolated publication build and verification must preserve the operator links, followed by
the normal repository gate. Results belong to the implementation PR; this decision alone is
not evidence that those checks passed.

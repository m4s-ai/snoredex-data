---
name: compare-implementations
description: Compare independently produced implementations or coding models on the same task, base and acceptance criteria, with verifiable runtime settings and bounded time/token measurements. Use for an explicitly requested implementation or model comparison; not for an ordinary single implementation, general model advice or an automatic merge decision.
---

<!-- doc: role=portable implementation-comparison skill; stage=task -->

# Compare implementations

Produce a fair, reproducible comparison with evidence for quality, effort and measured cost.
Use the host's supported isolation and execution tools; this skill requires no specific repository,
model family, provider or benchmark service.

## Comparison setup

1. Record the task, base revision, input artifacts, acceptance criteria and user constraints once.
   Give each candidate the same starting files, dependencies and task information. Include dirty
   changes only when they are part of the requested input; record their patch/hash separately.
2. Define the comparison unit before starting: first implementation, or implementation plus an
   equal review/remediation allowance. Use the same start/end events, deadline/budget policy and
   review standard. Separate an existing pair's known differences instead of pretending that they
   ran under controlled conditions. Do not launch new implementations for a read-only comparison.
3. For new attempts, create isolated workspaces from that base. Dispatch agents only when the
   request and runtime permit delegation; create user-visible tasks only when explicitly requested.
   Otherwise use supported isolated runs or report the execution capability that is unavailable.
   Do not pass one candidate's output or review findings to another during the measured attempt.
4. When the user specifies models or reasoning levels, use those exact supported settings. Check
   the effective runtime configuration before work and preserve model/version, reasoning, tool
   access and relevant limits in the run record. A requested label, task title or parent setting is
   not proof of the child's effective configuration. Never silently substitute a model or level;
   if verification is unavailable, label the run unverified and resolve that gap before presenting
   it as a controlled model comparison. Do not choose a different model merely to save resources.

## Comparison execution and acceptance

Keep one record per candidate: base/input hash, workspace, effective configuration, start/end,
result revision, check results, blockers and measurement sources. Keep secrets and private source
material out of shared reports.

Apply the same meaningful acceptance tests to each candidate and inspect behavior, scope,
maintainability and remaining risk. Use project-required gates; a self-awarded quality score is
not evidence. Keep implementation time, active remediation and review/queue wait separate when
telemetry supports that separation. Wall-clock minus known waits is only an estimate, not measured
active time. If a candidate fails or exceeds its allowance, report that outcome and the partial
measurements; do not compare its early stopping time with a completed candidate as equivalent work.
Any later remediation belongs to a new, clearly bounded phase for all candidates.

Wait for comparable acceptance outcomes before ranking. Do not mutate another candidate to make
it pass. Evaluation feedback after the independent phase must be labeled and applied under the
same allowance. Cleanup must preserve user-owned changes and reviewable candidate outputs.

## Comparison measurements

- Bind measurements to the agreed run/phase IDs and start/end events. Do not include unrelated
  conversation history, coordinator work or review calls in only one candidate's totals. Report
  coordinator/reviewer overhead separately, and attribute nested calls once to their owning run.
- Distinguish cumulative counters from per-request usage. For monotonic cumulative counters,
  use end minus baseline; never sum successive cumulative samples. If a counter resets or a phase
  boundary is missing, use complete per-request records or mark the total unavailable. Missing
  telemetry is unknown, not zero.
- Report uncached input, cached input and output separately with the provider's definitions. When
  input includes cached tokens, uncached input is input minus cached input; do not subtract again
  if already disjoint. Reasoning tokens may be part of output: never add them twice. Preserve raw
  counts and explain coverage limits before calculating totals or ratios.
- Calculate a price estimate only when requested and usage categories are known. Verify official
  rates for the actual model, service tier and applicable date; cite the source/date and currency.
  Apply each rate once to its matching category and disclose tool charges or discounts not covered.
  Label the result an estimate, not an invoice or subscription charge. Without suitable rates or
  usage, report the missing input instead of guessing a price.

## Comparison report and selection

Use a compact table: `Candidate | effective configuration | acceptance evidence | active/wait/wall
time | token categories | requested price estimate | limitations`. Omit unrequested price columns.
Link revisions/artifacts and measurement sources. Explain material differences and uncertainty;
a cheaper incomplete result is not automatically a better implementation.

Recommend a candidate when the task asks for a recommendation. Apply or merge one only within
the user's explicit selection/integration authorization and the project's existing gates. A
comparison request alone does not authorize merging, publishing or replacing the working tree.

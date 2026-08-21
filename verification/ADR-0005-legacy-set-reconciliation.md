<!-- doc: role=architecture decision record for the bounded legacy set reconciliation; stage=reference -->
# ADR-0005: bounded legacy set, release and finish reconciliation

- **Status:** Accepted; historical migration record (retired after #140)
- **Date:** 2026-08-09
- **Issue:** #148
- **Depends on:** ADR-0001 print identity (#134), ADR-0002 set identity (#146), and ADR-0004
  source-first adapter runs (#147)
- **Feeds:** identity migration in #138/#139 and database integration in #140

## Context

The legacy compatibility view has 135 Cardmarket set-code/name profiles and 203 generated
card-variant release rows. A scalar release date can appear beside several confirmed languages even
when the reviewed source field covers only one language and market. Of those release rows, 142 have
no row-level date source. The finish store adds 637 set-code/number/language units across 490
set-code/language profiles, including five explicitly closed lists and three mixed-status language
pairs.

Those rows are useful history, but they are not a complete Pokémon set catalogue. Copying a scalar
date onto every listed language would manufacture release events. Grouping source-first Asian
identifiers under a familiar Japanese or Western code would collapse local identities. Promoting
agreement among card finish rows into a set rule would invent a completeness claim.

## Decision

The bounded migration ledger was consumed by #140 and is retained here as history. Its durable
successor is [`authoritative_graph.json`](authoritative_graph.json), which stores the reviewed
entities, provenance edges and one reversible migration disposition for every input. No retired
compatibility projection is a live source of truth.

Every one of the 135 aliases enters exactly one bucket:

- `mapped` for one positively identified local-set target;
- `split-related` where equal raw text occurs in a separately sourced locality;
- `needs-evidence` where no target is positively identified; or
- `positively-retained-legacy` for a source-positive exclusion such as a digital code-card profile.

An equal raw code is not identity. The Japanese and Korean `S-P` source records therefore remain
different local-set nodes joined only by a non-equivalence diagnostic. Source-first records never
become Cardmarket aliases.

Every one of the 203 release rows retains its raw date, precision, approximation flag, source field
and complete row hash. A date links to a release event only through an identified set edition and
the event's positive source record. Event links retain locality, market scope and basis, precision,
status and evidence. Each confirmed language is evaluated separately. An unsupported language is
`needs-evidence` with `copiedLegacyScalar=false`; it never receives a date merely because it shares
a compatibility row.

The release accounting buckets are `lossless-projected`, `explicitly-split`,
`explicitly-superseded`, and `needs-evidence`. For provenance, every formerly unsourced row is
explicitly `newly-sourced`, `inherited-legacy-estimate-with-warning`,
`unknown-needs-evidence`, or `positively-superseded`. A positive market event may refine or
supersede the scalar for its own edition, but the scalar remains unchanged as migration history.
No unsourced scalar is presented as a reviewed exact event.

Every one of the 637 finish units is embedded verbatim and hashed. Its narrowest supported target
is one of:

- `set-edition-profile`, and only when an explicit profile rule establishes it;
- `card-release` for card-specific availability evidence;
- `physical-printing` for specimen or other direct visual evidence; or
- `none` with `needs-evidence`.

Agreement among card rows cannot create a profile. A profile rule cannot be copied back as
per-card evidence. The four `complete-manifest` units and one `owner-adjudicated` unit retain those
different closure dispositions.

The six documented Japanese-source to Traditional-Chinese catch-up cases are card-work edges with
`setMergeAllowed=false`. `AS5a`, `sc1a F`, `sc1b F`, and `scD F` retain their positively sourced
local identities. `svQP F` remains an explicit `blocked-by-source` identity guard: the adversarial
fixture names the failure mode, but the current source registry contains no positive local-set
record from which an identity node could be created.

The mixed `DP-P`/Korean, `XY-P`/Korean and `xJTG`/French claims remain individual confirmed or
contradicted card claims. Their report deliberately has no set-edition verdict.

## Historical compatibility and loss diagnostics

The migration retained all 203 legacy rows, their source fields, and the reconciliation state
before the compatibility exports were retired. The authoritative graph and its SQLite tables
retain the durable identities, provenance, and visible `needs-evidence` dispositions.

Changing any bounded denominator requires a reviewed input change and a new coverage version. The
generator rejects silent drift rather than stretching `v1` around a different population.

## Loop and terminal states

Each reconciliation run follows one loop:

1. load the 135 alias records, 203 release rows and 637 finish units;
2. resolve only accepted ADR-0001/ADR-0002 graph targets;
3. attach positive release events and finish evidence at their narrowest scopes;
4. render split, merge, orphan, unsourced, precision, language and count-delta reports;
5. place every record in exactly one accounting bucket;
6. materialize the reviewed graph and compare its logical contents; and
7. expose `complete`, `needs-evidence`, and `blocked-by-source` terminal states.

`complete` means the bounded legacy record is accounted and its positive graph links are explicit.
It does not mean the set universe, language availability or finish list is complete.
`needs-evidence` preserves a reachable research queue. `blocked-by-source` records that the model has
an identity boundary but no positive source from which it may create the entity. Absence remains no
evidence in all three states.

## Enforcement

The authoritative graph validator, database logical-dump check, and cross-platform release gate
enforce:

- exact 135 + 203 + 637 accounting;
- deterministic graph-backed rebuilds;
- zero dropped rows, language relationships or overwritten scalar dates;
- explicit event locality, market, precision, status and evidence;
- exact finish-unit retention and preservation of all five closed lists;
- separate source-first identities and non-merging catch-up edges; and
- card-level retention of the three mixed-status language pairs.

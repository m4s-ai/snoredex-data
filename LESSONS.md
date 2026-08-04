<!-- doc: role=incident record behind the traps in CLAUDE.md; stage=reference -->
# Lessons

What went wrong here, and what now stops it happening again.

`CLAUDE.md` carries each of these as a one-line trap, because that file is loaded on every task and
a rule without its failure shape reads as arbitrary. This file carries the incident: what happened,
what it cost, and which check holds the line now.

**This file is not imported.** An `@`-import is auto-loading with extra indirection, which is the
problem #100 set out to fix. `CLAUDE.md` is meant to carry enough that opening this one is never
required — only useful.

Newest first.

---

## The neighbour's evidence is not this unit's evidence

**Trap:** *Grade a claim by what it rests on, never by the strongest thing beside it.*

Fourteen Prize Pack units were filed as tier-1 **inspected specimens** — above an official
publisher database — on the owner's word, because one German specimen and one Portuguese listing
happened to sit nearby. Their `sourceRef` held the sentence *"(owner attestation, corroborated by
LigaPokemon + photographed specimens)"*, which is prose, not a reference, and cannot be followed.

The claims themselves were probably true. The grading was not: a reader auditing any one of those
units would have gone looking for a photograph that did not exist for that printing.

**Now guarded by** `S13` — a reference field holds a reference or nothing — and `S14` — only a unit
citing a specimen record may claim specimen authority. `providerId` is the source the unit would
fall over without; corroboration from a neighbour belongs in `evidence`, and `corroborated` means a
second provider agreed about *this* unit.

*Issue #64. Fixed in PR #74.*

---

## A rule stated more strictly than the check enforces

**Trap:** *`E3` enforces checkable **or** strong, not tier alone.*

`CLAUDE.md` said a weaker source *"may not"* stand alone, and that a check enforced it. Neither was
true. `E3` fails only when an uncorroborated claim is **both** un-checkable (no `sourceUrl`) **and**
below tier 2. A tier-3 page with a URL may carry a claim by itself, and five resolved units do.

The cost of the overstatement is invisible and one-directional: an agent reading the stricter
version rejects evidence the project accepts, and reports a false "open" count as though it were
rigour. Nothing fails; the dataset just quietly gets worse.

**Now guarded by** `E3` itself, whose detail line states the real rule, and by this being written
down rather than inferred.

*Issue #65.*

---

## "Complete official manifest" was narrower than intended

**Trap:** *Dependability decides whether a source may carry absence weight, not whether it is a
manufacturer.*

Rule 4 required a *"complete official manifest"* to scope an absence. The owner's intent was
dependability: Bulbapedia and Elite Fourum are the most dedicated researchers in this space and
qualify, manufacturer or not. The narrower wording would have excluded them.

A related withdrawal was caught by a test: removing `elitefourum`'s `supportsAbsence` failed
`test_owner_adjudications.py`, which asserts *"Elite Fourum must retain scoped absence capability"*.
The test was right and the change was wrong.

**Still true either way:** a scoped source alone leaves a claim `disputed`. `absenceScopes` is
recorded rationale, never a mechanism.

*Corrected 2026-08-03, PR #96.*

---

## An absence argument that produced a false contradiction

**Trap:** *Never contradict on bare absence. Prove the source covers the category first.*

`XY-P 149` was marked contradicted because a source did not list a Traditional Chinese printing.
The source did not cover that category at all. The contradiction was wrong and had to be reverted.

The same shape nearly repeated with `DP-P 126`: Japan ran a Domino's Pizza campaign, so the
reasoning went, therefore no Korean printing. But Korea ran its own food tie-ins — Kisstick sausages
— and it was *the same card*. A channel being Japanese does not make a card Japanese-only.

The discipline that works: pokumon lists Korean promos, so a missing Korean row there is meaningful;
its West coverage is one lumped "English" row, so its silence on French means nothing. Prove
coverage, then argue absence.

*Recorded in `verification/RESUME.md`, which carries the full source-by-source detail.*

---

## V-tokens are set-specific, and the guess is sometimes right

**Trap:** *Never assume a V-token means the same thing across sets — read `variantName`.*

`xsv2a` uses V1 for the Poké Ball mirror and V2 for the Master Ball. `xm2a` reverses exactly that
pair. `PPS8` V1 is Non-Holo and V2 Holo; `xJTG` V1/V2/V3 are distribution stamps.

When `SV-P/ID 117` needed its two mirror variants identified, neither unit recorded a
`variantName` and both rested on the same Bulbapedia set-list row, which does not distinguish them.
Carrying `xsv2a`'s order across would have been the reasonable inference — and it would have been
**right**. The owner confirmed V1 = Poké Ball, V2 = Master Ball.

It still would not have been evidence. That is the whole point of the trap: a guess that happens to
land is indistinguishable, in the record, from one that does not.

*PR #98.*

---

## A gate that reddens when the project improves

**Trap:** *Never raise a baseline to silence a rise. Find what changed.*

Closing the language review queue drove `pending units` to 0, and the suite printed
`!!! COUNTS WENT BACKWARDS` on every clean run afterwards, permanently, for the best possible
reason. A gate that goes red on progress is a gate people learn to edit rather than read — and the
banner was camouflage anyway, because `suite.regressed` never reached the exit code.

Metrics now declare a direction. `up-is-progress` measures work that exists; `down-is-progress`
measures work left to do and anchors on the **low-water mark**, so a queue climbing back is caught
immediately. A losing move fails the run.

**Re-anchoring downward after closing a queue is the opposite move and is correct.** When a queue
grows because the corpus grew, say so beside the number — as the finish review queue's
222 → 223 comment does, where an overturned contradiction made one more finish unit applicable.

*Issue #69.*

---

## Prose is not checked, so prose drifts

**Trap:** *A live document must not describe tooling that no longer exists.*

`verification/RESUME.md` described the PowerShell tools under `verification/` as "the five
recurring tools" and `scripts/` as holding the harvest pipeline. Both statements survived a complete
migration to Python, and then survived #68 moving those five scripts into
`verification/archive/passes/`, where they sit today as one-shots that must never be rerun. That
move was enforced for the *code* by check `B1`, and not at all for the sentence describing it.

It survived because nothing read prose. Seven such references were still live when `D2` was
written.

**Now guarded by** `D1`–`D4`: every document declares a role and a load stage, no live document
references archived tooling, frozen and generated documents say so in their own text, and no
heading is maintained in two loadable documents.

*Issues #100–#103.*

---

## Moving a file does not move its history

**Trap:** *A path exemption that covers history must keep the pre-move path.*

`PUBLIC-READINESS-AUDIT.md` moved into `verification/history/`, and every reference to it was
rewritten — including the exemption list inside `P6`, the check that scans **git history** for
sensitive strings. History blobs carry the path a file had at the time, so the rewrite unexcluded
eight known, already-reviewed findings and turned the gate red on both platforms.

Nothing was newly exposed. The audit document quotes the very patterns `P4` and `P6` search for,
which is why it was exempt; the check simply stopped recognising it.

**Now guarded by** `SENSITIVE_SCAN_EXEMPT`, which lists the pre-move path and the current one, with
the reason written beside them. A file can move; its blobs cannot.

*PR #107.*

---

## The eight-generator loop is not the gate

**Trap:** *Run `scripts/tracker.py check-template` too — and note it exits 0 while printing failure.*

Emitting a header from `scripts/database.py` rebuilt the database, which left the tracker template's
catalogue fingerprint stale. The local check loop ran the eight `--check` generators and treated
that as the generator gate; `check-template` is a separate step and the only thing that reads the
template, so it never ran. CI caught it.

The detail that makes this a trap rather than an oversight: **`check-template` prints its failure
and exits 0.** A `|| echo FAIL` wrapper around it stays silent. The workflow catches it only because
it runs as its own step under `-e`.

*PR #106.*

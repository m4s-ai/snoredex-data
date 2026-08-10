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

## A better fact overruled a rule it was never about

**Trap:** *A recorded set size decides run membership — except for a distribution rarity, which is
outside every run whatever its collector number says.*

Recording the printed set size was right, and replacing the rarity word with it was right: the
denominator is the fact, and the word was standing in for it. The override was written to win in
both directions, which is what a fact should do against a proxy.

It won one it should have lost. `RR 33 V2` is the Rival Season promo printing of `RR 33 V1`, an
ordinary Rare — the promo carries the number of the run card it reprints. Comparing 33 against a
111-card run answers a question nobody asked: it establishes that the *number* is inside the run,
which was never in doubt, and from there concludes that a language release of the set reaches a
promo distributed separately from it. The row moved from `does-not-carry` to `carries`.

What made it visible was the inconsistency, not the reasoning. `CL 33 V2` and `FLF 80 V2` are the
same shape, and they stayed on the queue — only because their sets had no recorded size yet. One
promo judged sound and two unsound, decided by which set happened to be measured first. Recording
those two sizes would have quietly moved them too.

The lesson is not "be careful with overrides". It is that a set size and a distribution rarity
answer **different questions** — *where is this number in the run?* and *was this printing part of
the run at all?* — and the second is not a weaker version of the first, so no amount of precision on
the first can settle it.

**Now guarded by** `DISTRIBUTION_RARITIES` in `evidence_semantics.py`, checked before the size, and
by `runMembershipBasis` on every row, which names which of the three rules answered so a reader can
see a promo being excluded rather than measured.

*Issue #137, correcting the size override landed in PR #177.*

---

## The gate ran before the thing it was checking

**Trap:** *`P6` and `P7` read git history, so `review_findings.py` has to run again after the commit
and the push.*

The pre-PR gate was run in full and passed 124/124. The commit made straight afterwards turned CI
red on `P7`, which forbids any author or committer address without `noreply` in it — the commit
carried a personal one.

Nothing was wrong with the gate, and nothing was wrong with the run. Every other check reads the
working tree, so running them before committing is exactly right. `P6` and `P7` read *history*, and
at the moment the gate ran the offending commit did not exist. A green gate before a commit says
nothing about that commit.

The recovery has a second half worth stating, because the obvious fix looks like it failed.
Amending the commit locally left `P7` still red: it scans every published ref, and the pushed branch
still reached the old commit. The amend only takes effect once the branch is force-pushed and the
old commit stops being reachable.

**Now guarded by** a line in `CLAUDE.md`'s gate block: run `review_findings.py` before the commit
for the tree, and again after the push for the history.

*Found by CI on PR #178.*

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

---

## The gate asked for a byte match SQLite cannot give

**Trap:** *`git diff --exit-code` in the documented gate excludes `*.sqlite`, and must keep doing so.*

The pre-PR gate in `CLAUDE.md` regenerated `snoredex.sqlite` and the tracker template for real and
then byte-diffed the whole tree. On a clean `main` that reported drift in both files — not because
anything was stale, but because a SQLite file stores the version number of the library that wrote it
in its own header. Two environments on different SQLite builds cannot produce the same bytes from
the same data.

Measured, rather than assumed: the committed database carried `SQLITE_VERSION_NUMBER` 3053001 and a
local rebuild wrote 3045001, and **128,107 of 2,600,960 bytes differed while `iterdump()` matched
line for line**. Three consecutive rebuilds in one environment were byte-identical, so the
generators are deterministic; they simply cannot be deterministic across versions, and `VACUUM`
does not change that — the header field is written regardless.

The defect was in the document, not the pipeline — and the pipeline had known all along. The
docstring on `sqlite_dump()` in `scripts/database.py` says page layouts differ between the Windows
and Linux SQLite builds "even when every schema object and row is identical", which is why `--check`
compares the logical dump rather than a file hash. CI has only ever run `database.py --check` and
`tracker.py check-template` on these two artifacts, so it never saw the drift and never could.

That is the part worth remembering: this was not a gap in what the project knew, it was a fact that
lived in one generator's docstring and never reached the document telling people what to run. The
mirror of [the eight-generator loop](#the-eight-generator-loop-is-not-the-gate) — there the document
was looser than CI and work reached main unchecked, here it was stricter and reported a defect that
did not exist. Both came from the document and the workflow describing different steps.

**Now guarded by** `D5`, which fails if the documented gate byte-diffs those artifacts again. Their
content stays covered by the two `--check` steps, which is the property that can actually hold.

*PR #130.*

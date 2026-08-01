# Contributing

This project is asking for one specific kind of help: **tell us where the data is wrong.**

You do not need to know Python, Git, or anything about how the repository is built. If you own
Snorlax cards, or you have a photo, a listing, or an official checklist that contradicts what the
site shows, that is the contribution we want.

## Report a correction

Open the collection page, find the row that is wrong, and use its **Correction?** link. The link
pre-fills the row identity and everything the site currently records, so in most cases you only
tick the right boxes and describe what is wrong.

If you would rather start from scratch:
[open a printing correction](https://github.com/m4s-ai/snoredex-data/issues/new?template=printing-correction.yml).

## The one rule that matters

**Positive evidence only. An absence is not evidence.**

A source failing to list a printing is a gap in that source, not proof the printing does not
exist. This rule is not pedantry — an absence argument once produced a false correction here that
had to be reverted.

Concretely:

- **"I have this card in hand"** is a contribution. It is recorded as an owner attestation.
- **"Here is a photo / a listing / an official checklist entry"** is a contribution.
- **"It isn't on <site>, so it must not exist"** is not, and will be closed.

The same rule explains a word you will see everywhere on the site. **`pending` means *not yet
established*, never *does not exist*.** If a finish shows as pending, the project is not claiming
the card is unavailable in that finish — it is saying nobody has shown us one yet. There is
nothing to correct unless you have actually seen it.

## How your report is graded

Evidence is ranked, and the ranking is public:
[`verification/FINISH_SOURCES.md`](verification/FINISH_SOURCES.md) describes the source ladder and
why absence is treated the way it is. Roughly, from strongest:

1. A complete official manifest — the only kind of source that can establish that something is
   *absent*.
2. An official publisher listing or set checklist.
3. An independent database or catalogue outside the marketplace the claim came from.
4. A photographed specimen or an owner attestation.
5. A marketplace claim — the weakest, and the thing this project exists to check.

A correction does not need to reach the top of that ladder to be worth filing. Specimen reports
have already overturned three databases at once here.

## What happens next

A correction is triaged, checked against the ladder above, and either applied with its source
recorded in the evidence registry, or closed with the reason stated in the issue. Every claim in
the dataset traces back to a source, so an accepted correction adds one — it never lands as an
unattributed edit.

## Scope

- **Physical cards only.** Online and live code cards are deliberately excluded.
- **European Spanish.** From *Journey Together* (2025) onward, Latin-American Spanish is a
  physically distinct edition and is out of scope.
- Before reporting, it is worth skimming
  [Scope and caveats](README.md#scope-and-caveats--read-before-using) — some surprising values are
  documented limitations rather than errors.

## Changing the code or data directly

Pull requests are welcome but are not the expected path, and a data change made without a source
will not be merged. Generated files must be regenerated rather than hand-edited — each one carries
a header saying so.

Before opening a pull request, run the same gate CI runs:

```console
pip install -r requirements.txt
python -m playwright install chromium

python verification/review_findings.py     # cross-artifact consistency and publication readiness
python scripts/site.py --check             # generated artifacts match their inputs
python verification/test_site.py           # browser acceptance tests
```

`verification/review_findings.py` is the quickest way to find out whether a change broke an
invariant; it runs on the standard library alone and needs no network access.

## Licensing of contributions

The project's licence grants are **in force**, granted by `M4S.Collection` on 2026-07-26 — see
[`LICENSE.md`](LICENSE.md) and [`publication-decisions.json`](publication-decisions.json). This is
a mixed work: PolyForm Noncommercial 1.0.0 covers the code, CC BY-NC-SA 4.0 covers the data
selection, arrangement and annotation. By filing a correction you are providing factual
information about physical cards and agreeing that it may be recorded in this dataset under those
grants. Please do not paste text or images you do not have the right to share; a link to the
source is always better than a copy of it.

## Conduct

Be straightforward and assume good faith. Disagreements here are about evidence, and evidence
settles them. Reports that are abusive, or that pursue a person rather than a claim, will be
closed without discussion.

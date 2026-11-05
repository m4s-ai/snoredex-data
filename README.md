<!-- doc: role=public entry point for using the data; stage=public -->
# Snoredex Data

**Which Snorlax Pokémon cards (Relaxo, Ronflex, Kabigon …) were really printed — in which language
and finish — checked against evidence, not marketplace listings.** A marketplace tells you which
languages a card is *sold* in. This project records which ones were actually *printed*, and names
the evidence for each.

<!-- generated:badges — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
[![Website](https://img.shields.io/github/deployments/m4s-ai/snoredex-data/github-pages?label=website)](https://m4s-ai.github.io/snoredex-data/)
[![Release gate](https://github.com/m4s-ai/snoredex-data/actions/workflows/release-gate.yml/badge.svg)](https://github.com/m4s-ai/snoredex-data/actions/workflows/release-gate.yml)
[![Open issues](https://img.shields.io/github/issues/m4s-ai/snoredex-data)](https://github.com/m4s-ai/snoredex-data/issues)
[![Current-known checklist](https://img.shields.io/badge/current--known_checklist-888_printings-2563eb)](analysis_checklist.json)
[![Languages](https://img.shields.io/badge/languages-15-2563eb)](DATA-GUIDE.md)
[![Licence](https://img.shields.io/badge/licence-PolyForm_NC_%2B_CC_BY--NC--SA-2ea44f)](LICENSE.md)
[![AI-DECLARATION: copilot](https://img.shields.io/badge/%E4%B7%BC%20AI--DECLARATION-copilot-fee2e2?labelColor=fee2e2)](AI-DECLARATION.md)
<!-- /generated:badges -->

### 👉 [Open the collection](https://m4s-ai.github.io/snoredex-data/)

A sortable, filterable table of every confirmed physical printing, with its evidence, TSV export
and a correction link on every row. Nothing to install.

<!-- generated:status — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
> [!NOTE]
> **Live site:** <https://m4s-ai.github.io/snoredex-data/>. Each deployment is a manual, gated workflow run — merging never publishes — so the live site can lag `main`. See [`WORKFLOW-MAP.md`](WORKFLOW-MAP.md#6-gate-mode-boundaries-292).
>
> **Data coverage:** `cardmarket-search-2026-07-21` is a frozen historical Cardmarket-derived candidate universe, **not a complete all-locality catalogue**. Current collector projections also include separately evidenced source-first admissions. The bounded source-first rebuild completed under [#132](https://github.com/m4s-ai/snoredex-data/issues/132); the completeness gate retains explicit source and locality gaps.
<!-- /generated:status -->

## Why this exists

A marketplace filter answers *"can I buy this here?"*, not *"was this printed?"* — and collectors
read it as the second question. Ask Cardmarket about `KSS 26` (XY Kalos Starter Set) and it offers
**17 languages**; physical printings are currently confirmed in **6**. Spanish is digital-only
(owner adjudication OA-20261001-U0482). Build a collection goal from that and you will hunt cards
that were never made.

So every inherited language claim is re-checked against positive evidence — an official database,
an inspected card, a fan wiki, or an exact card photograph — and each piece of evidence is named,
ranked and dated. Where an outside source disagrees with the marketplace, both survive: the raw
claim, and the verdict beside it. The over-claiming is itself a finding, so it is preserved rather
than quietly corrected away. [METHODOLOGY.md](METHODOLOGY.md) explains how.

## What you can do here

### Browse the collection

Open **<https://m4s-ai.github.io/snoredex-data/>**. Every active confirmed physical printing appears
once, with its locality, printing identity and evidence. To run the same page locally from a
checkout, `index.html` is the whole site:

```console
python -m http.server 8000
```

Then visit <http://localhost:8000/>.

### Use the data

| You want | Use |
|---|---|
| A ready-to-use application database | [`snoredex.sqlite`](snoredex.sqlite) — start from the `app_*` views; see [`DATABASE.md`](DATABASE.md) |
| A personal have/have-not tracker | [`snoredex-tracker-template.sqlite`](snoredex-tracker-template.sqlite) — copy it, or use `scripts/tracker.py` |
| A versioned collector-app contract | [`collector_catalogue.json`](collector_catalogue.json) with its [schema](collector_catalogue.schema.json) |

Every other file, and what each field does *not* mean, is in **[DATA-GUIDE.md](DATA-GUIDE.md)**.
Read its [Scope and caveats](DATA-GUIDE.md#scope-and-caveats--read-before-using) before building on
the data.

### Report a correction

Wrong row, missing printing, a card in your hand that the data calls `pending` — that is the
contribution this project wants, and it needs no Git, Python or setup. Every row on the site
carries a **Correction?** link that pre-fills what the data currently records.
[`CONTRIBUTING.md`](CONTRIBUTING.md) explains what counts as evidence and how a report is graded.

The one thing that is not a correction: *"it isn't listed on `some-site`, so it does not exist."*
See rule 1 below.

### Work on the repository

Python 3.11, standard library only for the generators; `requirements.txt` (Playwright) is
verification-only. Use Python on every platform — PowerShell is not needed for anything.

```console
python -m pip install -r requirements.txt
python -m playwright install chromium
python scripts/regen.py --check             # canonical deterministic PR gate
```

Read [`AGENTS.md`](AGENTS.md) for the working rules, [`HANDOVER.md`](HANDOVER.md) for cold-start
orientation and the repository map, and the
[issue tracker](https://github.com/m4s-ai/snoredex-data/issues) for current priorities.

## Two rules that hold everywhere

1. **Positive evidence only.** A source that fails to list a printing has a gap. It has not
   proved the printing does not exist. Official Pokémon sources confirm only the releases they name
   for the matching language and region. No source settles an absence at any tier. Converging
   evidence from dependable sources is what the collection owner weighs. The decision is theirs,
   recorded in `verification/owner_adjudications.json` and never attributed to a single provider.
   `not-printed` means **no regular release**: a proof copy or an error card is a separate
   category and does not falsify the decision.
2. **`pending` means not yet established — never proven absent.** The same goes for `unmapped` and
   `other-product` on the finish side. Nothing here claims non-existence by silence.

## Project status

<!-- generated:current-state — regenerate with `python scripts/readme_stats.py`; do not hand-edit -->
Current-known status snapshot: **2026-11-04**. Legacy claim counts refer to `cardmarket-search-2026-07-21`; collector projections also include accepted source-first admissions. Neither claims all-locality discovery completeness.

| Area | Current state |
|---|---|
| Legacy Cardmarket baseline | **242 products** harvested: **198 singles** retained and 44 accessories excluded. 7 retained products are code cards and are explicitly flagged. |
| Legacy language-claim review | **719 claims**: 624 externally confirmed, 95 contradicted, 0 awaiting manual review, and 0 still open within the legacy candidate universe. Raw Cardmarket languages remain preserved beside their verdicts. |
| Evidence-safe application status | **622 established**, **2 needs evidence**, **95 owner-adjudicated not printed**, and **0 disputed**. Raw verdicts and observations stay queryable; unsupported confirmation does not mint a printing. |
| Current-known physical checklist | **888 items** across 174 cards and 15 languages: 888 documented printings plus 0 explicit unresolved placeholders. |
| Current-known finish evidence | **637 card-number × language units**: 554 externally confirmed, 6 marketplace-only positives, 0 without positive finish evidence, and 77 not applicable. The remaining detail/mapping queue contains 34 units. |
| Evidence registry | **46 providers**, 1864 evidence records, 1855 unique URLs, and 7,598 attributed claims. Every external provider is positive only. The separate owner-adjudication store records final language and printing absence decisions. |
| Quality gate | Deterministic generators, structural and evidence audits, cross-artifact consistency checks, and the full offline gate run on Ubuntu and Windows for ready pull requests. UI-relevant pull requests add a Chromium behavior lane; browser and live-source release checks run on Linux. |
| Site and publication | The repository is public. The interactive site is live at <https://m4s-ai.github.io/snoredex-data/>; each deployment is a manual, gated workflow run, so the live site can lag `main`. |
| Licensing | Verbatim PolyForm Noncommercial 1.0.0 and CC BY-NC-SA 4.0 texts are present and hash-verified. The intended mixed-work grants are active under the recorded owner approvals. |
| AI transparency | Development used AI in a human-directed copilot workflow. Scope and safeguards are declared in [`AI-DECLARATION.md`](AI-DECLARATION.md). |
<!-- /generated:current-state -->

Counts come from the committed stores and are regenerated, never typed. Open items are not debt to
be hidden: closing one is progress, so the checks report count movement as drift and only fail when
a number moves *backwards*.

## Learn more

| Document | What it covers |
|---|---|
| [DATA-GUIDE.md](DATA-GUIDE.md) | Every data file, and the caveats behind its fields |
| [METHODOLOGY.md](METHODOLOGY.md) | Evidence ladder, finish model, and how the repository is built |
| [DATABASE.md](DATABASE.md) | SQLite schema, application views and example queries |
| [FINDINGS.md](FINDINGS.md) | What the catalogue turned up: language drift, shared `cardKey` groups, the harvest |
| [verification/SOURCES.md](verification/SOURCES.md) | Every provider, its authority tier and attribution |
| [verification/FINISH_SOURCES.md](verification/FINISH_SOURCES.md) | Finish, foil-pattern and stamp evidence |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to report a correction and how it is graded |
| [HANDOVER.md](HANDOVER.md) | Repository map and cold-start orientation for maintainers |

## Licence, attribution and AI transparency

A mixed work, and explicitly **not** OSI open source: **PolyForm Noncommercial 1.0.0** for the
code, **CC BY-NC-SA 4.0** for the data selection, arrangement and annotation. Card images,
artwork, names and trademarks are third-party rights this project does not hold and does not
grant. See [`LICENSE.md`](LICENSE.md) and
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Development used AI in a human-directed copilot workflow, declared under specification 0.1.2 in
[`AI-DECLARATION.md`](AI-DECLARATION.md).

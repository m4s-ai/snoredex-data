<!-- doc: role=public entry point for using the data; stage=public -->
# Snoredex Data

**Which Snorlax Pokémon cards (Relaxo, Ronflex, Kabigon …) were really printed — in which language
and finish — checked against evidence, not marketplace listings.** A marketplace tells you which
languages a card is *sold* in. This project records which ones were actually *printed*, and names
the evidence for each.

### 👉 [Open the collection](https://m4s-ai.github.io/snoredex-data/)

A sortable, filterable table of every confirmed physical printing, with its evidence, TSV export
and a correction link on every row, plus an artwork gallery. Nothing to install. Each deployment is
a manual, gated workflow run — merging never publishes — so the live site can lag `main`.

## What this is, and what it is not

- **Marketplace availability is not a print manifest.** Ask Cardmarket about `KSS 26` (XY Kalos
  Starter Set) and it offers 17 languages; far fewer were physically printed, and the Spanish
  version is digital-only (owner adjudication OA-20261001-U0482). Every inherited language claim is
  therefore re-checked against positive evidence — an official database, an inspected card, a fan
  wiki, or an exact card photograph — and each piece of evidence is named, ranked and dated.
- **Positive evidence only.** A source that fails to list a printing has a gap; it has not proved
  the printing does not exist. Only the collection owner settles an absence, recorded in
  `verification/owner_adjudications.json`. `not-printed` means no regular release; a proof copy or an
  error card is a separate category.
- **`pending` means not yet established — never proven absent.** Nothing here claims
  non-existence by silence.
- **Not a complete all-locality catalogue.** The catalogue grew from a frozen Cardmarket-derived
  candidate universe ([`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json)) plus
  separately evidenced source-first admissions, with source and locality gaps kept explicit.
- **Latin-American Spanish has gaps.** European and LATAM Spanish are physically distinct editions;
  Cardmarket does not carry LATAM at all, so the retained LATAM printings are a positive slice, not
  a complete list.

[DATA-GUIDE.md](DATA-GUIDE.md#scope-and-caveats--read-before-using) has the full list of caveats;
read it before building on the data. [METHODOLOGY.md](METHODOLOGY.md) explains how a claim becomes
a fact.

## The files

| File | What it is |
|---|---|
| [`data/`](data/printings.json) | The canonical model, edited by hand and checked: `printings.json` (one record per catalogue item), `sets.json`, `images.json`, `evidence.json`, `claims.json` |
| [`collector_catalogue.json`](collector_catalogue.json) | The versioned collector-app contract 1.0.0, with its [schema](collector_catalogue.schema.json) and [migration routes](collector_migrations.json) |
| [`snoredex.sqlite`](snoredex.sqlite) | The same facts as an application database; start from the `app_*` views ([DATABASE.md](DATABASE.md)) |
| [`snoredex-tracker-template.sqlite`](snoredex-tracker-template.sqlite) | A blank personal have/need tracker; manage your copy with `scripts/collection.py` |
| [`index.html`](index.html), [`gallery.html`](gallery.html) | The table and the artwork gallery |
| [`verification/owner_adjudications.json`](verification/owner_adjudications.json), [`verification/specimens.json`](verification/specimens.json) | Owner decisions and the register of inspected physical specimens |

The catalogue, both pages, the database and the tracker template are built from `data/` by
`scripts/build.py`; never edit them by hand.

## Build and check

Python 3.11, standard library only; `requirements.txt` (Playwright) is for the browser suite.

```console
python -m pip install -r requirements.txt
python -m playwright install chromium
python scripts/regen.py           # build the outputs from data/, then run every check
python scripts/regen.py --check   # the same, observational (what CI runs)
python -m http.server 8000        # serve the site locally at http://localhost:8000/
```

[`AGENTS.md`](AGENTS.md) has the working rules; the
[issue tracker](https://github.com/m4s-ai/snoredex-data/issues) has the current priorities.

## Report a correction

Wrong row, missing printing, a card in your hand that the data calls `pending`: every row on the
site carries a **Correction?** link that pre-fills what the data records. No Git, Python or setup is
needed. [`CONTRIBUTING.md`](CONTRIBUTING.md) explains what counts as evidence. The one thing that is
not a correction: *"it isn't listed on some site, so it does not exist."*

## Licence, attribution and AI transparency

A mixed work, and explicitly **not** OSI open source: **PolyForm Noncommercial 1.0.0** for the
code, **CC BY-NC-SA 4.0** for the data selection, arrangement and annotation. Card images,
artwork, names and trademarks are third-party rights this project does not hold and does not
grant. See [`LICENSE.md`](LICENSE.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Development used AI in a human-directed copilot workflow, declared in
[`AI-DECLARATION.md`](AI-DECLARATION.md).

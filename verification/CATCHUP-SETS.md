<!-- doc: role=catch-up-set scope expansion plan and evidence index; stage=reference -->
# Catch-up-set scope expansion (Traditional Chinese & related)

Owner-directed scope expansion (issues #84, 2026-08-03/04; auditor follow-up 2026-08-05).
This document tracks the *decision* to treat T-Chinese (and related) **catch-up-set reprints as
their own products**, not as a `language` claim on the Japanese/English set-slot the marketplace
lists them under. It is a plan plus the evidence index for each code; it is **not** a second copy
of the data.

## Why this exists

The repository's early T-Chinese adjudication rested on Bulbapedia's market-history argument —
"no official Traditional Chinese before the October 2019 launch" — and treated a pre-2019 set as
`not-printed`/`disputed` in T-Chinese. That argument does **not** close the catch-up case: after
the market opened, T-Chinese received older Sun & Moon / earlier-era sets as **catch-up reprints**
under their **own set codes and numbering** (e.g. `AS5a`, `sc1a`/`sc1b`/`sc1bF`), not as a 1:1
language of the Japanese slot. A "printed before market start" claim therefore cannot rule a
catch-up reprint `not-printed`, and the correct model is a separate product/unit, not a language.

## Principle (no data change in this file)

- A catch-up reprint is a **distinct product** (`own set code + own number`), confirmed by its own
  evidence — not a `language` attribute of the overseas slot.
- Absence rules unchanged: no catch-up code is assumed `not-printed` without positive evidence or an
  explicit owner adjudication; `pending` = unresolved, never absent.
- `snorlax_cards.json` is a historical harvest (input, not reproducible). This plan does **not**
  invent products there; it records the codes and their specimens so a real product pass can pick
  them up with machine identity, or an owner can adjudicate per code.

## Catch-up codes in scope

| Code | Market | Notes / status | Evidence |
|---|---|---|---|
| `AS5a` | T-Chinese | Sun & Moon-era catch-up repack; e.g. `AS5a 142` Snorlax = the card Cardmarket lists as `sm10 076`. | SPEC-0024 (52poke image, verified 2026-08-05) |
| `sc1a`/`sc1aF` | S-Chinese / T-Chinese | Sword & Shield catch-up (VMAX-era `s1H` equivalents). | SPEC-0011 (`sc1aF 127/154`), sc1a/S-Chinese via 52poke |
| `sc1b`/`sc1bF` | S-Chinese / T-Chinese | Sword & Shield catch-up (V/VMAX `s1H` equivalents). | SPEC-0007..0010 (`sc1bF 119/120/165/177`) |
| `FXY` | Korean | Korean counterpart of `HXY` (XY Beginning Set). | SPEC-0018 (owner photo, `FXY` code owner-attested) |
| `SV-P` (SEA promos) | Indonesian/Thai/CS | `Scarlet & Violet` regional promos (e.g. `SV-P/ID 117`). Already in catalogue as `SV-P/ID`. | SPEC-0012/0013/0019/0020 (photos) |

## Evidence index (specimens)

- **SPEC-0024** (`AS5a 142`, T-Chinese, Snorlax) — 52poke wiki image, verified bytes on
  `s1.52poke.com`, photograph in `verification/specimens/SPEC-0024.png`. New (2026-08-05).
- SPEC-0007..0010, 0015 (`sc1bF` / `sc? F`) — existing T-Chinese specimens filed in a prior pass.
- SPEC-0011 (`sc1aF 127/154`) — existing.
- SPEC-0014 (`S-P 101`, Korean), SPEC-0018 (`FXY 026`, Korean) — existing.
- SPEC-0012/0013/0019/0020 (`SV-P/ID 117`, Indonesian) — existing.

## Source

- **52poke (wiki.52poke.com)** — registered in `source_registry.py` (tier 2, T-/S-Chinese,
  `supportsAbsence: false`) on the owner's recommendation (issue #84, 2026-08-04). Static image
  host `s1.52poke.com` is reachable without bot protection; the wiki pages sit behind a JS
  challenge. Positive-evidence only.

## Owner decision, 2026-08-09 (D1)

The owner chose option 1 for every code backed by a physical specimen. `AS5a 142`,
`sc1b F 119`/`120`/`165`/`177` and `S-P 101` are admitted as prints of their own in
[`source_first_prints.json`](source_first_prints.json), keyed by the machine identity this
document asked for and [`ADR-0001`](ADR-0001-locality-aware-print-identity.md) defines.

`sc1a F 127/154` (SPEC-0011) and `?? 111/159` (SPEC-0015) are **held**: their own specimen records
decline to assert the set glyph, and a print is keyed by its local set code. They still need
either a legible glyph or a per-code ruling.

Codes with no specimen of their own — the Simplified-Chinese `sc1a`/`sc1b` rows reachable through
52poke, and `FXY` — were not covered by D1 and remain open below.

## Open owner decisions (per code)

For the codes not settled by D1, the owner decides whether to:
1. **Add it as its own product** (new `snorlax_cards.json`-adjacent entry + units + checklist),
   which is a real data-model expansion requiring a machine identity per code; or
2. **Adjudicate per unit** (record `exists under its own code` in `owner_adjudications.json`
   without a new catalogue product), which moves the claim off `disputed`/`not-printed` without a
   catalogue change.

This document is the handoff point: it names the codes, the evidence, and the two ways to land it.
Nothing in it is data to be regenerated.

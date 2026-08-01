# Licensing scope

This repository is a **mixed work**. No single licence covers all of it, and presenting one as if
it did would claim rights the project does not hold. This document says exactly which material is
licensed by this project, under which terms, and which material is excluded because it belongs to
someone else.

This project is **noncommercial and source-available**. It is deliberately **not** OSI open source.

> **Status: in force since 2026-07-26.** The owner approved the licence grants on that date and
> `publication-decisions.json` records it, so the terms below are an operative grant rather than a
> described intention. The two verbatim licence texts are present and hash-verified.
>
> Publication of the site is a separate decision and is still pending; the grants do not depend on
> it.

## 1. Original software — PolyForm Noncommercial 1.0.0

Covers the build and verification code written for this project:

- `scripts/**` — dataset build pipeline, finish modelling, chronological and site generators;
- `verification/*.py`, `verification/archive/**` — verification tooling;
- any workflow or configuration files authored here.

Full text: `LICENSES/PolyForm-Noncommercial-1.0.0.md` ·
canonical source <https://polyformproject.org/licenses/noncommercial/1.0.0/>

The publisher's versioned source file is
<https://github.com/polyformproject/polyform-licenses/blob/1.0.0/PolyForm-Noncommercial-1.0.0.md>;
the older rendered URL currently returns 404 but remains the URL printed in the licence itself.

Permits personal, hobby, research, and other noncommercial use, including modification and
redistribution. Commercial use requires a separate grant from the licensor.

## 2. Original data selection, arrangement and annotation — CC BY-NC-SA 4.0

Covers the parts of the data that are this project's own intellectual contribution:

- the **selection and arrangement** of the catalogue — which units exist, how they are keyed,
  the finish/pattern/marking/distribution/size decomposition, the edition model;
- the **verification annotations** — status verdicts, evidence strings, source grading,
  contradiction findings, completeness judgements;
- the **documentation and site copy** — `README.md`, `HANDOVER.md`, `verification/*.md`,
  generated page prose.

Full text: `LICENSES/CC-BY-NC-SA-4.0.md` ·
canonical source <https://creativecommons.org/licenses/by-nc-sa/4.0/>

Version 4.0 is used deliberately: it addresses sui generis database rights, which matter for a
work whose value is largely in selection and arrangement. Attribution, noncommercial use, and
ShareAlike apply.

## 3. Explicitly excluded — third-party rights this project does not hold

The licences above grant **nothing** in respect of:

- **Pokémon card artwork and card images**, including every file in `images/`;
- **Pokémon names, logos, character designs, and trademarks**;
- **illustrator credits and the underlying illustrations**;
- **quoted or extracted factual content** from Bulbapedia, TCGdex, TCGplayer/TCGCSV, PSA,
  pokumon.com, Elite Fourum, Cardmarket, and the official Pokémon sites — each carries its own
  terms, recorded in `THIRD_PARTY_NOTICES.md`;
- **photographs of physical cards** supplied by third parties.

Raw factual observations — that a given card exists in a given language with a given finish — are
facts. This project claims no ownership of facts; the claim is over the selection, arrangement,
and verification layer built around them.

## 4. Non-affiliation

This is an unofficial fan project. It is not affiliated with, endorsed by, sponsored by, or
associated with Nintendo, Creatures Inc., GAME FREAK inc., The Pokémon Company, Cardmarket, or any
other rights holder or data provider named here.

Pokémon and all related names are trademarks of Nintendo, Creatures Inc., and GAME FREAK inc.
© Pokémon / Nintendo / Creatures / GAME FREAK.

## 5. No warranty

The dataset records evidence and its strength. It is not a print manifest and is not guaranteed
complete or correct. `pending` means *not established*, never *proven absent*. Do not rely on it
for purchase, grading, insurance, or valuation decisions without independent verification.

## Owner decisions

Recorded in `publication-decisions.json`, which `verification/publication_gate.py` verifies before
any deployment.

**Settled 2026-07-26, approved by `M4S.Collection`:**

1. **Scope of "private use".** Noncommercial reuse *with* modification and redistribution
   permitted — which is what the two licences above provide.
2. **Licensor identity.** `M4S.Collection`. This is the name downstream CC BY-NC-SA attribution
   must reproduce, and the party from whom a commercial exception is sought. It is a pseudonymous
   handle rather than a legal entity name; see *Licensor* below.
3. **Publication consent.** Owner attestations and photographed specimens may be published. They
   are represented as anonymous evidence classes carrying no personal identifiers.
4. **Third-party images.** The 198 Cardmarket card images may be published on the basis set out in
   `THIRD_PARTY_NOTICES.md`.

**Still open:**

5. **Site publication and repository visibility.** The site's correction links all point into this
   repository's issue tracker, so publishing the site for public review requires the repository to
   be public too, and `publication_gate.py` enforces that the two are decided together. The
   historical local paths that previously blocked public visibility were redacted on 2026-07-26;
   see `verification/PUBLIC-READINESS-AUDIT.md` and `verification/LAUNCH-RUNBOOK.md`.

The licence grants above are in force and do not depend on decision 5. Merging code does not
deploy the site: the Pages workflow is manual and calls the publication gate before any upload.

See issue #5 and `verification/PUBLIC-READINESS-AUDIT.md`.

## Licensor

**`M4S.Collection`** — selected 2026-07-26 and recorded in `publication-decisions.json`, which
`publication_gate.py` verifies before any deployment.

Where the name appears once the grants are in force:

- **Attribution.** CC BY-NC-SA 4.0 requires reuse to credit the licensor by name, so
  `M4S.Collection` is the credit line downstream users must reproduce.
- **Commercial exceptions.** Both licences are noncommercial. Anyone wanting commercial use needs
  a separate grant, and `M4S.Collection` is the party who can give it.

Two properties worth stating plainly, because they are consequences rather than problems:

- It is a **pseudonymous handle, not a legal entity**. That is a deliberate choice and keeps the
  collection owner's legal name out of every downstream attribution. It does mean the licence is
  granted by a pseudonym, which is normal for hobby projects and sufficient for attribution, but
  is weaker than a named person or company if a grant ever had to be enforced or transferred.
- A licensor must be **reachable**, or a commercial exception cannot be requested and the
  attribution requirement points at no one.

### Contact

Commercial-use enquiries and licensing questions: **[@M4S.Collection on
Instagram](https://www.instagram.com/m4s.collection/)**.

This is a licensing contact, not a corrections channel. Data corrections belong in the issue
tracker, where they are graded against the source ladder and recorded with their evidence — see
[`CONTRIBUTING.md`](CONTRIBUTING.md). Corrections sent by direct message cannot be attributed to a
source and will be redirected.

If a longer-lived contact route is added later, add it alongside this one rather than replacing
the attribution name, so credits already published downstream stay correct.

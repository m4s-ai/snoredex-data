# Licensing scope

This repository is a **mixed work**. No single licence covers all of it, and presenting one as if
it did would claim rights the project does not hold. This document says exactly which material is
licensed by this project, under which terms, and which material is excluded because it belongs to
someone else.

This project is **noncommercial and source-available**. It is deliberately **not** OSI open source.

> **Status: not yet in force.** The two verbatim licence texts are present and hash-verified, but
> the owner decisions listed below have not been approved. Until
> `publication-decisions.json` records that approval, this file describes the intended structure,
> not an operative grant.

## 1. Original software — PolyForm Noncommercial 1.0.0

Covers the build and verification code written for this project:

- `scripts/**` — dataset build pipeline, finish modelling, chronological and site generators;
- `verification/*.ps1`, `verification/*.py`, `verification/passes/**` — verification tooling;
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

## Open decisions

These belong to the repository owner and remain false/unset in
`publication-decisions.json`:

1. **Scope of "private use".** Recommended default: noncommercial reuse *with* modification and
   redistribution permitted — which is what the two licences above provide. The alternative,
   individual use only, would need different licences.
2. ~~**Licensor identity.**~~ **Decided 2026-07-26: the licensor is `M4S.Collection`.** This is
   the name downstream CC BY-NC-SA attribution must reproduce, and the party from whom a
   commercial exception is sought. It is a pseudonymous handle rather than a legal entity name;
   see *Licensor* below.
3. **Publication consent.** Owner attestations and any photographed specimens need explicit
   consent before publication. These are currently represented as anonymous evidence classes with
   no personal identifiers, which is the right shape, but consent is still the owner's to give.
4. **Repository versus site publication.** The site's correction links all point into this
   repository's issue tracker, so publishing the site for public review requires the repository to
   be public too — `publication_gate.py` enforces that. The historical local paths that previously
   blocked this were redacted on 2026-07-26; see `verification/PUBLIC-READINESS-AUDIT.md`.

Merging the implementation does not grant these approvals and does not deploy the site. The Pages
workflow is manual and calls `verification/publication_gate.py` before any upload.

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
  attribution requirement points at no one. The handle is reachable on Instagram under the same
  name; if a longer-lived contact route is wanted later, add it here rather than replacing the
  attribution name, so existing downstream credits stay correct.

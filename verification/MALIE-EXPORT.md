<!-- doc: role=Malie export profile and implementation contract; stage=task -->
# Malie export contract

Implementation contract for #385, under #384. Profile identifier:
`snoredex-malie-sv-pilot/1`. This document does not claim that the exporter,
field evidence or release package has already been delivered.

## Boundary and upstream pin

The [upstream draft](https://malie.io/static/draft/html/pkproto_sv.html)
is an interchange description, not the owner of Snoredex identities or evidence.
`malie_profile.json` records the exact retrieved HTML digest, its declared version,
and a second digest after replacing only dynamic Cloudflare email-link fragments.
The latter is a drift diagnostic; it never substitutes for the exact response hash.
Do not interpret a changed response digest alone as a changed field contract.

The initial profile covers the explicitly selected English and German SV cards.
It supports Pokémon with the fields below, standard size and reviewed card backs.
Other languages, eras, types, sizes and unresolved physical candidates are reported,
not coerced into this profile. A supported language is not proof of TCGL membership.
Record membership evidence separately before claiming strict upstream scope.

The pilot has two mandatory positive targets: regular non-holo MEW 143 in English
and German. Both already have physical identities and positive finish records.
The English reverse-holo version exercises a separate physical variant. English
SVP 051 regular and Pokémon Center variants exercise distribution/stamp identity
and incomplete foil mapping. A German Jungle research row exercises unresolved
identity and era exclusions. Exact existing IDs are in `malie_profile.json`.
Selection is not export approval: #386 must supply the field-level evidence.
Never remove a blocked mandatory target silently. A substitution requires a versioned
selection change recording the old ID, replacement ID and evidence-based reason.

### Current enrichment worklist

At selection base `899688cd40071095e502513c19e0430891b20da8`, the two mandatory
MEW printings have confirmed non-holo identity and standard size in the collector
join. Both have a null `localCardName`. The retained finish snapshot supplies
positive normal/reverse flags, not complete printed content. Fresh read-only TCGdex
probes on 2026-09-21 expose localized names, artist, HP, ability/attack text,
weakness, retreat and regulation mark; these probes have not been accepted as
content observations and cannot yet back the export.

For each mandatory target, #386 must retain and qualify those fields, inspect the
exact localized front for printed credit, set/number formatting, copyright,
rarity icon, stage label, flavor text and all optional-field applicability, and
establish the exact back and TCGL scope. A front image does not establish a back.
Existing size/finish claims must be traced to their field-specific supporting
records. Neither the direct API's missing resistance field nor its absent copyright
field proves an empty field on the card.

For the reverse target, additionally qualify the foil layer and mask; an intricate
pattern alone does not establish either. For both SVP targets, preserve the known
distinct distribution/stamp identities while recording missing content and exact
foil mapping. The Jungle placeholder remains a research/era boundary with no
physical identity. All six stay in the selection and final accounting.

## Field ownership and observation gap

The authoritative graph owns release/printing existence and identities. Existing
finish inputs own finish, patterns, markings, distribution, edition and size;
`collector_catalogue.py` exposes the reviewed joins. The export consumes these joins
and preserves the existing IDs; it does not write the graph or collector catalogue.
Reuse the shared specimen/source reference resolution, not a new identity algorithm.

Neither the graph's release/work payload nor the finish snapshot is a complete
printed-card-content store. The snapshot intentionally retains finish flags only.
For that bounded gap, `verification/card_content_observations.json` will contain
reviewed observations keyed to existing release/printing IDs. It is not another
catalogue: no independent membership, existence verdict, identity or collector state.
Release-scoped printed content can be shared by physical variants only through an
explicit reviewed applicability list. Physical observations apply to named printings.
Existing non-null source-backed owners must agree with observations; disagreements
are reported as conflicts, never overwritten by export precedence.

Each observation records a stable observation ID, target, field, state, source-native
value, retained source/SPEC reference, actual observation date and applicability.
States are `known`, `not-applicable`, `unknown` and `blocked-by-source`.
`not-applicable` needs positive inspection or an explicit type rule; omission from
an API does not establish it. Multiple incompatible supported values are a conflict.
Photo intake and evidence acceptance use the existing workflows in WORKFLOW-MAP.

The store envelope is `{schemaVersion: 1, sources: [], observations: []}`. A source
has `sourceId`, `providerId`, `url`, `retrievedAt`, `retainedPath`, `sha256` and
`scope`. Paths are repository-relative, cannot escape the repository, and resolve
to retained bytes or an existing specimen's photograph. `scope` states the exact
release/printing and fields established, plus limits. A content observation has
`observationId`, `cardReleaseId`, `physicalPrintingIds`, `field`, `state`,
`value` (only for `known`), `sourceIds`, `observedAt`, `method` and `basis`.
`field` is a JSON Pointer into the intended payload; compound values carry source
coverage for every leaf they assert. Applicability markers may apply to the whole
optional object. `method` distinguishes transcription, structured-source assertion,
owner determination and an explicit reviewed transformation. Known values and
positive inapplicability require at least one resolving supporting source. An
unknown or failed-source observation records its reason and next retrieval step.
No observable fact is admitted merely because an observation has the right shape.

## Field matrix

`C` below means a reviewed content observation, `P` an existing physical owner plus
any required exact-print observation, and `G` the existing graph/localization owner.
Every emitted leaf retains its observation/source references in the companion.
Unless stated otherwise, unknown or blocked applicable data withholds the whole card.
The permitted enumerations are in the profile's `vocabulary`. Rarity designation
and icon arrays correspond by index and must be validated as pairs, not independently.
`FREE` is allowed only as the sole attack-cost element; it is not a Pokémon type.
The number parser uses the profile's full-match pattern, accepting one decimal digit
run with optional Latin-letter prefix/suffix, and returns the integer capture.
Other source-native forms require an explicit mapping; no character stripping heuristic.

| Field | Type / applicability | Owner and transformation | Empty/unknown behavior |
|---|---|---|---|
| `lang` | required enum | G plus C: explicit WEST/en → en-US or WEST/de → de-DE after printed-language evidence | No generic `pt` narrowing; unsupported languages outside profile |
| `card_type` | required enum | C, printed Pokémon classification → `POKEMON` | Other types outside first profile |
| `subtype` | inapplicable to Pokémon | Reviewed type rule | Omit; never add trainer/energy subtype |
| `name` | required nonempty string | C, exact localized printed name with upstream symbol markup | No English display-name fallback |
| `subtitle` | applicable only if separately printed | C, exact text, excluding presentation parentheses | Omit only with established inapplicability |
| `artists.text` | required when credits appear | C, entire printed credit including localized prefix | Do not manufacture `Illus.` from an artist name |
| `artists.list` | nonempty ordered string array with credits | C, names stripped only of the evidenced credit prefix | Preserve spelling and order |
| `regulation_mark` | printed nonempty string | C, exact mark; pilot `G` | Missing observation withholds card |
| `set_icon` | required nonempty string | C, printed set text + `_` + printed language suffix | Never use a marketplace alias as printed text |
| `collector_number.full` | required for pilot | C, exact printed number including slash if present | Preserve zeros and prefixes |
| `.numerator` | required string | C, left printed part of full number | Not an integer |
| `.denominator` | optional string | C, right printed part if present | Omit only when inspected as absent |
| `.numeric` | required integer | Derive from the single decimal digit run in numerator | Reject ambiguous/no digit run; preserve 0 |
| `rarity.designation` | required when rarity printed | C and reviewed rarity owner, explicit upstream enum mapping | Unsupported designation needs mapping |
| `rarity.icon` | required with rarity | C, inspected symbol → upstream enum | Pilot uncommon uses `SOLID_DIAMOND`; no inference from finish |
| `copyright.text` | required nonempty string | C, exact complete printed notice | No guessed publisher/year template |
| `copyright.year` | required integer | Largest explicit year in the evidenced notice | Not set release year |
| `tags` | applicable unordered enum array | C, reviewed graphical/gameplay attributes | Sort and deduplicate known tags; omit established empty set |
| `size` | required enum | P, positively established standard → `STANDARD` | `unknown` withholds; generic jumbo not mapped |
| `back` | required enum | P, exact supported back → `POKEMON_1999` | No default from language or era |
| `foil` | required for positively foiled card | P, explicitly evidenced layer and mask | Omit only for positively established non-holo |
| `foil.type` | enum when foil applies | P, reviewed upstream layer mapping | Pattern name or V-token is insufficient |
| `foil.mask` | enum when foil applies | P, reviewed HOLO/REVERSE/ETCHED/STAMPED mapping | Technical finish alone does not prove exact mask |
| `text` | ordered nonempty array for pilot | C, printed top-to-bottom/left-to-right blocks | No regrouping abilities and attacks |
| `text[].kind` | enum | C, supported ABILITY/ATTACK; other kinds require profile extension | Unknown kinds fail closed |
| `text[].name` | required nonempty string for both kinds | C, exact printed name | No translation or generated label |
| `text[].text` | required for ability; attack applicability varies | C, exact printed text and upstream energy markup | Attack may omit only if inspected as textless |
| `text[].cost` | required ordered array for attack | C, energy symbols → explicit type enums; zero cost → `["FREE"]` | Empty array is not a free attack |
| `text[].damage.amount` | required integer when damage present | C, printed number | Preserve 0, reject boolean-as-integer |
| `text[].damage.suffix` | optional `×`, `+`, `-` | C, exact printed operator | Omit only if inspected absent |
| `stage` | required enum | C, explicit printed stage mapping; pilot `BASIC` | No stage inferred from Pokémon species |
| `stage_text` | required string | C, profile interpretation below | Required even for BASIC |
| `hp` | required positive integer | C, printed HP | Reject null, bool and guessed defaults |
| `types` | required nonempty ordered enum array | C, printed symbols | Preserve order; explicit localized mapping |
| `weakness.types` | nonempty ordered enum array if present | C, printed symbols | Omit whole weakness only after inspection |
| `weakness.amount` | required integer if present | C, printed multiplier | Preserve value independently of operator |
| `weakness.operator` | required enum if present | C, printed `×` for pilot | No generic string replacement |
| `resistance.types` | ordered array if present | C, printed symbols | Source omission is unknown |
| `resistance.amount` | required integer if present | C, printed magnitude (`30` for SV) | Keep magnitude separate from sign |
| `resistance.operator` | required enum if present | C, printed `-` for pilot | Do not encode the sign twice |
| `retreat` | required integer ≥ 0 | C, count of printed retreat symbols | 0 remains present, null is invalid |
| `flavor_text` | applicable string | C, complete printed flavor text | Omit only if positively inapplicable |
| `images`, `ext` | unfinished upstream sections | Excluded from payload | Source/asset links belong in companion |

### Explicit draft interpretations

The draft calls `stage_text` required but illustrates evolutionary text. For BASIC
cards this profile retains the actual printed stage label (`BASIC` / `BASIS`) as
text in the stage graphic. This is a named profile interpretation, not a claim
that reference TCGL exports have been checked to use the same representation.
The independently consumed example and validation must enforce this choice.

The retained comparison in `evidence/issue-385-malie-reference.json` now includes
the exact MEW 143 records from both `v0.1.9.13` reference exports, with whole-response
and clearly distinguished excerpt digests. All four omit `stage_text`; this profile
deliberately follows the written required-field rule rather than silently inheriting
that omission. The German references also lack artist credits, copyright and flavor
text. Those are data gaps to resolve from the printed card, not permission to omit
applicable fields. The reference's explicit `FLAT_SILVER`/`REVERSE` pair is a lead
for the reverse target's mapping and needs qualified evidence acceptance in #386.
The reference includes `images` and `ext`, but this profile retains their useful
identity/source information in the companion instead of treating unfinished draft
sections as a stable payload contract.

Optional means genuinely inapplicable, not unknown. This profile serializes known
inapplicable optional fields by omission, keeps required numeric zero, and never
uses null/empty-string equivalence to evade a required field. Presentation line
wrapping may be joined with spaces after inspection; punctuation, accents, symbol
markup, printed wording and element order remain significant. No Unicode or
apostrophe normalization is applied silently.

## Bundle, identity and complete accounting

Public package: `exports/malie/cards.json`, `exports/malie/report.json` and
`exports/malie/profile.json`. The last is the generated public contract, not a
second hand-maintained profile. All are UTF-8 without BOM, LF terminated, two-space
JSON indentation, sorted object keys and `ensure_ascii=False`. Cards and report
entries sort by existing `itemId`; order is serialization, never identity.

`report.json` contains `schemaVersion`, `profileId`, `upstream`, `inputs`,
`cardsSha256`, `profileSha256`, `entries` and `summary`. Input digests bind all read
canonical files and observation assets using repository-relative paths. No build
time, absolute path or containing-commit SHA appears in deterministic outputs.
After committing, existing release metadata binds package bytes to that commit.

Each entry contains `itemId`, `cardReleaseId`, nullable `physicalPrintingId`,
`status`, sorted `reasons`, `identity`, `fieldSources`, and `cardIndex` plus
`cardSha256` only when exported. `cardIndex` locates an object in the cards array;
`cardSha256` hashes that object's canonical serialization (same JSON settings,
including trailing LF). Neither is an identity. Whole-file digest validation is
mandatory before using positions. A consumer validates the selected input ID set,
unique entry IDs, exported positions, per-card hashes and count conservation.

`identity` preserves localization, local set, edition ID/value/status, technical
finish, foil pattern, markings with their roles and multiplicity, distribution,
size and error classification from the reviewed collector join. Missing metadata
remains explicitly null/unknown. An equal card payload never merges physical IDs.
Consumers needing physical identity must consume the report together with cards.
Unsupported physical properties are retained there and receive a mapping reason;
they must not be hidden by injecting undocumented fields into the cards payload.

Every selected input has exactly one main status and every applicable reason:

1. `outside-profile`: positively identified scope exclusion, including era/language.
2. `blocked-by-source`: an applicable required field has a recorded failed source.
3. `needs-evidence`: required existence, applicability or field evidence is missing.
4. `needs-mapping`: supported evidence exists but is conflicting or lacks a mapping.
5. `exported`: no blocking reason; payload fully validates.

This precedence selects only the main status; reasons from lower priorities are
not discarded. Failure to resolve a selected ID, duplicate selections, malformed
profile/observations or broken source hashes is a bundle-build error, not a scope
exclusion. Research entries must not acquire a physical ID or payload. Global
catalogue coverage must not be confused with the finite pilot denominator.

## Implementation and verification handoff

The `malie_export.py` command in `scripts/`, with `--write`, creates validated outputs, with the report
written last as the bundle's digest binding. Temporary-file replacement protects
individual files; a partial multi-file replacement is rejected by digest checks.
`--check` is strictly observational even if an output is missing or corrupt.
No network, repair, timestamps or canonical-store writes are allowed in that mode.

Run `python scripts/malie_export.py --write` after accepting the #386 field inputs;
then run `python scripts/malie_export.py --check`. Both commands fail if those
inputs are unavailable. The separate exporter branch intentionally carries no
invented substitute for the real observations. `python verification/test_malie_export.py`
checks the implementation against independently specified synthetic expectations.

The finite profile declares supported local-set IDs, printed language suffixes
and the mappings to existing rarity-owner IDs. The exporter checks observed set
markers, numbering, locale, name when known, size, rarity and finish against the
collector owners. An absent mapping is a reason to withhold a card, never permission
to invent an identity. Additional physical dimensions stay in the companion entry.
Known numbering components cannot be omitted. Unknown physical size needs evidence;
positive non-standard size is outside the profile. Distribution, markings, edition
and error distinctions remain visible but block export until a mapping is reviewed.
The single reviewed foil-pattern agreement covers the retained English MEW reverse
record: `intricate-tiled-type-symbol` with explicitly observed `FLAT_SILVER`/`REVERSE`.
This is an agreement check, never a rule to manufacture missing foil observations.

Determinism means identical accepted input bytes produce identical bundle bytes.
Reordering in-memory traversal produces the same cards, entries and provenance.
Reformatting or reordering a retained input file changes its exact raw-file digest
in `report.inputs`, even when the resulting card values are unchanged: preserving
that evidence binding takes precedence over pretending different source bytes
are identical. No runtime timestamp participates in either case.

#387 supplies independent expected fixtures and tests for required/nested enums,
zero versus null, localized names, prefixed and zero-padded numbers, duplicate
payloads with distinct physical IDs, reordered equivalent inputs, missing evidence,
unknown foil, source conflicts and damaged/mixed bundles. Synthetic cases are
explicitly labeled and cannot satisfy the real-pilot requirement.

The initial independent values and adversarial expectations live in
`fixtures/malie_contract.json`. Run `python verification/test_malie_profile.py`
from the repository root to validate the selection against the current catalogue.
This contract check does not validate exported payloads or replace the later gates.

#388 registers the exporter/check/tests in the existing `regen.py` lists and test
ownership/gate contracts. Full Linux and Windows gates must use identical input
bytes. The pure export must leave all existing identities, verdicts and collector
state unchanged relative to the same accepted inputs.

#389 extends the existing package allowlist/verification and adds a standalone
stdlib consumer that reads only the three package files. It checks independently
specified expected IDs and values; importing exporter internals is not acceptance.
The two real-language outputs, all dispositions, exact revision and package digests
must be recorded before completion. External Malie interoperability remains
unverified until actually exercised. Release readiness does not authorize deployment.

<!-- doc: role=data file guide and usage caveats; stage=public -->
# Using the data

Which file answers which question, and what each field does *not* mean. Start at the
[README](README.md) for what the project is; read [Scope and caveats](#scope-and-caveats--read-before-using)
before building anything on the data. Several fields mean something narrower than their name
suggests, and that section is the difference between using this data and misreading it.

## Which file to use

| You want | Read | Watch out for |
|---|---|---|
| The immutable pre-migration candidate universe | [`legacy-cardmarket-baseline.json`](legacy-cardmarket-baseline.json) | It records the historical Cardmarket boundary and every inherited card/unit; it is provenance, not an all-locality manifest. |
| A ready-to-use application database | [`snoredex.sqlite`](snoredex.sqlite) / [`DATABASE.md`](DATABASE.md) | Start from the `app_*` views. Historical `contradicted` rows become `disputed` unless explicit owner adjudication resolves them. |
| A personal have/have-not tracker | [`snoredex-tracker-template.sqlite`](snoredex-tracker-template.sqlite) | Copy the blank template or use `scripts/tracker.py`; catalogue sync preserves ownership state. |
| The Cardmarket product view — identity, rarity, art, artist, editions | [`snorlax_cards.json`](snorlax_cards.json) | Use `languagesConfirmed` for established prints and `languagesNeedsEvidence` / `languagesDisputed` for open questions. `languagesRepositoryConfirmed`, `languagesContradicted`, and raw `languages` preserve the research inputs. |
| The current-known list of physical things to collect | [`analysis_checklist.json`](analysis_checklist.json) | One record per documented printing *or* per explicitly unresolved one within current coverage — placeholders are items too. |
| A versioned collector-app contract | [`collector_catalogue.json`](collector_catalogue.json) / [`collector_catalogue.schema.json`](collector_catalogue.schema.json) / [`collector_migrations.json`](collector_migrations.json) / [`collector_catalogue.fixture.json`](collector_catalogue.fixture.json) | The graph defines existence. Verified printings are `current-known`; finish candidates and unresolved placeholders remain `research`. A deployment additionally publishes `collector_deployment.json`, binding the exact bytes to their containing commit. |
| A bounded Malie interchange pilot | [Bundle and standalone-reader instructions](exports/malie/README.md) | Three real printings in two languages; all six selected inputs are accounted for. Keep cards, report and profile together to preserve printing IDs, evidence and gaps. |
| The evidenced locality/era discovery frontier | [`LOCALITY-ERA-MATRIX.md`](verification/LOCALITY-ERA-MATRIX.md) / [`locality_era_matrix.json`](verification/locality_era_matrix.json) | Established, provisional and candidate tracks stay distinct; provider slices are positive frontiers, not complete print manifests. |
| Which languages a card exists in, and on whose word | [`verification/units.json`](verification/units.json) | Keyed by `(setCode, number, variant, language)`. |
| Final owner decisions on disputed claims | [`verification/owner_adjudications.json`](verification/owner_adjudications.json) | Explicit cross-source application decisions; they do not rewrite `units.json` or credit a single provider. |
| Which finishes a card exists in | [`verification/finish_units.json`](verification/finish_units.json) | Keyed by `(setCode, number, language)` — deliberately *not* by variant token. |
| Release chronology | [`analysis_confirmed_releases.json`](analysis_confirmed_releases.json) / [`.csv`](analysis_confirmed_releases.csv) | Dates follow the matching market inside a shared Bulbapedia article. |
| The authoritative migration graph | [`verification/authoritative_graph.json`](verification/authoritative_graph.json) / [`DATABASE.md`](DATABASE.md) | Preserves migration dispositions, reversible redirects and graph-backed locality identities. |
| Who said what, and how strong it is | [`verification/SOURCES.md`](verification/SOURCES.md), [`verification/source_registry.json`](verification/source_registry.json) | Every claim names a provider and an authority tier — see [How a claim becomes a fact](METHODOLOGY.md#how-a-claim-becomes-a-fact). |

## Scope and caveats — read before using

- **`languages` is marketplace availability, not a print manifest — proven, not suspected.**
  Cross-checking every card × language against outside sources produced contradictions: cases where
  Cardmarket offers a language for which no printing exists, `KSS 26` being the clearest. The raw
  field is preserved because the over-claiming is the finding; the repository verdict lives beside
  it in `languagesRepositoryConfirmed` / `languagesContradicted`, while the evidence-safe
  application view uses `languagesConfirmed` / `languagesNeedsEvidence`. See
  [`verification/CONTRADICTED.json`](verification/CONTRADICTED.json).
- **A repository confirmation may still need card-level evidence.** A set/product release or a
  sibling printing is retained as an observation but cannot establish this exact card unless the
  step to the card is positively supported. Those rows are `languagesNeedsEvidence`, are also in
  `languagesUnresolved`, and do not enter chronological or checklist outputs.
- **A contradicted language is not automatically a proven absence.** `languagesContradicted`
  splits into `languagesNotPrinted` — where an explicit collection-owner adjudication settled the
  question after reviewing the bounded evidence — and `languagesDisputed`, where a source disagrees
  and nothing has settled it. Current counts are in the [README status table](README.md#project-status).
  Both are excluded from the checklist, so
  that nobody is sent hunting a printing the evidence points away from, but only the first is a
  claim that the card does not exist. An exact photograph establishing the disputed property can
  resolve a disputed row.
- **Legacy Cardmarket-derived "Spanish" claims mean European Spanish.** From Journey Together (2025), LATAM-ES is
  a physically distinct edition for regular sets — different attack translations, set name and set
  code (specimen-verified on `SVP 184`). Cardmarket does not carry it, so it is absent from this
  legacy candidate universe; that absence is not evidence that the printing does not exist.
  LATAM-ES came **into scope on 2026-08-09** as its own locality. The completed #139 discovery work
  retains three official `LA` releases (`JTG LA 117/159`, `POR LA 063/088`, and `SVP LA 184`) as a
  complete positive slice; `xJTG` remains an explicit evidence gap, so this is not a complete
  historical catalogue.
- **`cardKey` groups the same *card*, not the same *artwork*.** It is Cardmarket's own grouping by
  card name plus attack names, so a reprint with brand-new art shares the key. Useful — it is how
  the re-illustrated reprints were found — but never read it as art identity.
- **Artist coverage is partial.** Illustrators come from pokemontcg.io/limitlesstcg
  (English-market), the official pokemon-card.com and Asia databases, official Korean card images,
  exact release histories and the credit printed on an exact-print image. Where no reviewed credit
  is available, `artist` stays `null`. An illustrator belongs to the *artwork* (owner rule,
  2026-10-22): every print of the same artwork — any language, edition or finish, including a
  rainbow/hyper-rare recolour of the same composition — shares it, and the printed credit beats a
  database field. A sibling's `cardKey` alone still does not justify transferring a credit: the two
  images must show the same illustration, and a propagated credit is graded `internal-derivation`.
- **Localized names are reviewed, not guessed.** `localCardName` comes from
  [`verification/local_card_names.json`](verification/local_card_names.json): an exact-print name
  first, then the official species name for species-only cards. Mechanic and trainer-owned names
  are never derived, with one owner-approved exception (Hop's Snorlax per-language pattern).
- **Editions are one item per edition.** Where a card is documented in both 1st Edition and
  Unlimited, the collector catalogue carries one item for each. A photograph establishes its own
  edition only when the face is legible: a visible 1st Edition mark, or a visibly empty mark
  position on a set printed in both editions. Card-level finish flags (TCGdex) attach to both
  edition items rather than forming a third, editionless one. Whether a set has an edition system
  at all comes from `verification/edition_rules.json` for every item, whatever source created it.
- **Set facts reach every item.** A recorded printed set size (`printed-set-size-record` in
  `verification/set_catalogue_sources.json`) supplies the collector-number denominator in the
  item's own regional numbering; promo, prize-pack, jumbo and championship-deck rows take none.
  A gallery subset (Trainer Gallery `TG10/TG30`) ships inside its main set and has its own
  `printed-subset-size-record`; unnumbered Japanese releases take no denominator.
  Card size defaults to standard (owner decision 2026-10-23); it stays unknown only where the item
  may be the jumbo twin of an otherwise identical standard printing.
- **`variantAxes` and `hasReverseHolo` are marketplace hints, not the finish manifest.** The two
  finish layers answer different questions: `finishAvailability` on a card says what evidence
  attributes to *this Cardmarket product*, while `finish_units.json` says what is known for the
  *set number and language*, whichever product carries it. Product attribution is the weaker of the
  two, so each card row also carries `unitAvailableFinishes` and `unitFinishStatus` from the store.
  Read the status words exactly: `pending` = no positive evidence anywhere in the unit; `unmapped`
  = the finish is known but not yet attributed to a product; `other-product` = attributed to a
  different listing of the same card. None of the three ever means "does not exist".
- **A Cardmarket V-token is not a finish, and is set-specific.** TCGdex's `normal`/`holo`/`reverse`
  flags apply to the set number and language (a `true` confirms a finish unless the collection owner
  has rejected it — `PCG3 062` is holo only although TCGdex reports `normal`); a `V1`/`V2`/`V3` mapping is recorded only where it is
  unambiguous or independently identified. `xsv2a 143` uses Poké Ball and Master Ball mirror
  treatments. `xm2a 136` uses Colorless Energy star and Poké Ball mirror treatments. Always read
  `variantName`.
- **Marking role is a trichotomy.** `print-identity` covers rarity symbols and contest credits;
  `reverse-holo-treatment` covers EX-era set-logo stamps that *are* part of the reverse design;
  `distribution-promo` covers prerelease, Staff, retailer and Pokémon Center stamps, which do
  **not** imply a reverse holo.
- **Release dates follow the matching market inside a shared Bulbapedia article.** A page such as
  Gym Challenge carries both `enrelease` and `jarelease`; the translated set name decides which
  applies. Reviewed records in
  [`verification/bulbapedia_release_dates.json`](verification/bulbapedia_release_dates.json) take
  precedence over the generic API fallback, and where a field lists several regional waves the
  chronological row uses the first and records that choice. The full set-by-set review is
  [`verification/history/BULBAPEDIA-RELEASE-DATE-AUDIT.md`](verification/history/BULBAPEDIA-RELEASE-DATE-AUDIT.md).
- **Code cards are excluded from the checklist** and flagged in the dataset —
  [`verification/excluded_codecards.json`](verification/excluded_codecards.json).

-- snoredex.sqlite 2.0.0: the canonical model in data/ as a relational database, built by
-- scripts/build.py. This file is the database contract. JSON text columns end in _json.
-- Absence is never encoded: `not-printed` exists only beside an owner adjudication, and no
-- column claims that a source supports absence.

-- One key/value fact about this build (schema, version, data date, fingerprints, baseline).
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

-- One language of the legacy language claims (the old candidate-universe language codes).
CREATE TABLE languages (
    language_code TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    region TEXT NOT NULL,
    display_order INTEGER NOT NULL
) WITHOUT ROWID;

-- One locality-qualified language a printing is published in (catalogue localization).
CREATE TABLE localizations (
    localization_id TEXT PRIMARY KEY,
    locality TEXT NOT NULL,
    language_id TEXT NOT NULL,
    language TEXT NOT NULL,
    language_tag TEXT NOT NULL,
    script TEXT,
    display_name TEXT NOT NULL,
    display_order INTEGER NOT NULL
) WITHOUT ROWID;

-- One local set or product of one locality.
CREATE TABLE local_sets (
    local_set_id TEXT PRIMARY KEY,
    locality TEXT NOT NULL,
    local_set_code TEXT,
    local_set_name TEXT,
    product_kind TEXT NOT NULL,
    identity_state TEXT NOT NULL,
    source_refs_json TEXT NOT NULL,
    sort_key TEXT NOT NULL
) WITHOUT ROWID;

-- One release of a local set in one localization, with its release date where known.
CREATE TABLE set_editions (
    set_edition_id TEXT PRIMARY KEY,
    local_set_id TEXT NOT NULL REFERENCES local_sets(local_set_id),
    localization_id TEXT NOT NULL REFERENCES localizations(localization_id),
    identity_state TEXT NOT NULL,
    release_date TEXT,
    release_date_precision TEXT,
    release_approximate INTEGER NOT NULL CHECK (release_approximate IN (0, 1)),
    release_event_id TEXT,
    sort_key TEXT NOT NULL
) WITHOUT ROWID;

-- One card text (name plus attacks), shared by printings across sets and languages.
CREATE TABLE works (
    work_id TEXT PRIMARY KEY,
    card_key TEXT NOT NULL,
    display_name TEXT
) WITHOUT ROWID;

-- One retained image file; preview is the derivative pages show for a specimen original.
CREATE TABLE assets (
    asset_id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    url TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    image_scope TEXT NOT NULL,
    alt_text_basis TEXT NOT NULL,
    attribution_json TEXT NOT NULL,
    preview TEXT
) WITHOUT ROWID;

-- One source provider and its evidence tier (1 strongest; 5 is not external evidence).
CREATE TABLE providers (
    provider_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL UNIQUE,
    organization TEXT,
    homepage TEXT,
    category TEXT NOT NULL,
    authority_tier INTEGER NOT NULL CHECK (authority_tier IN (1, 2, 3, 5)),
    coverage TEXT NOT NULL,
    used_for_json TEXT NOT NULL,
    attribution TEXT NOT NULL,
    notes TEXT NOT NULL,
    hosts_json TEXT NOT NULL
) WITHOUT ROWID;

-- One catalogue item (collector_catalogue.json items, derived fields resolved); item_id is the
-- stable key collections are tracked by.
CREATE TABLE printings (
    item_id TEXT PRIMARY KEY,
    identity_anchor TEXT NOT NULL,
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    item_kind TEXT NOT NULL,
    progress_class TEXT NOT NULL,
    work_id TEXT REFERENCES works(work_id),
    work_mapping_state TEXT NOT NULL,
    set_edition_id TEXT NOT NULL REFERENCES set_editions(set_edition_id),
    local_set_id TEXT NOT NULL REFERENCES local_sets(local_set_id),
    localization_id TEXT NOT NULL REFERENCES localizations(localization_id),
    card_release_id TEXT NOT NULL,
    physical_printing_id TEXT,
    source_printing_id TEXT,
    finish_unit_id TEXT REFERENCES finish_units(finish_unit_id),
    source_claim_refs_json TEXT NOT NULL,
    card_name TEXT NOT NULL,
    local_card_name TEXT,
    local_set_code TEXT,
    local_set_name TEXT,
    collector_number TEXT,
    collector_number_denominator TEXT,
    collector_number_sort_key TEXT NOT NULL,
    edition TEXT,
    edition_assignment_status TEXT NOT NULL,
    finish_verification_status TEXT NOT NULL,
    finish TEXT,
    finish_family TEXT,
    finish_group_id TEXT NOT NULL,
    foil_pattern TEXT,
    distribution_json TEXT,
    card_size TEXT NOT NULL,
    error_class TEXT,
    rarity_json TEXT NOT NULL,
    completeness_status TEXT,
    completeness_evidence_json TEXT,
    release_date TEXT,
    release_date_precision TEXT,
    release_approximate INTEGER NOT NULL CHECK (release_approximate IN (0, 1)),
    release_sort_key TEXT NOT NULL,
    image_asset_id TEXT REFERENCES assets(asset_id),
    image_scope TEXT NOT NULL,
    correction_link TEXT NOT NULL,
    artist TEXT,
    language_provider_id TEXT REFERENCES providers(provider_id),
    language_corroborated INTEGER CHECK (language_corroborated IN (0, 1)),
    language_checkable INTEGER CHECK (language_checkable IN (0, 1)),
    date_source_json TEXT
) WITHOUT ROWID;

CREATE INDEX printings_browse ON printings(localization_id, local_set_code, collector_number_sort_key);

-- One predecessor checklist id an item carries (the old tracker key).
CREATE TABLE printing_legacy_ids (
    item_id TEXT NOT NULL REFERENCES printings(item_id),
    legacy_checklist_id TEXT NOT NULL UNIQUE,
    PRIMARY KEY (item_id, legacy_checklist_id)
) WITHOUT ROWID;

-- One stamp or marking printed on an item, in printed order.
CREATE TABLE printing_markings (
    item_id TEXT NOT NULL REFERENCES printings(item_id),
    marking_order INTEGER NOT NULL,
    kind TEXT NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (item_id, marking_order)
) WITHOUT ROWID;

-- One source link of an item (its evidence and source URLs).
CREATE TABLE printing_source_links (
    item_id TEXT NOT NULL REFERENCES printings(item_id),
    url TEXT NOT NULL,
    PRIMARY KEY (item_id, url)
) WITHOUT ROWID;

-- One prepared gallery image of an item (reviewed crop recipe and its responsive sizes).
CREATE TABLE gallery_images (
    item_id TEXT PRIMARY KEY REFERENCES printings(item_id),
    recipe TEXT NOT NULL,
    media_kind TEXT NOT NULL,
    scope TEXT NOT NULL,
    source TEXT NOT NULL,
    images_json TEXT NOT NULL
) WITHOUT ROWID;

-- One card release's artwork group in the gallery.
CREATE TABLE artwork_groups (
    card_release_id TEXT PRIMARY KEY,
    "group" TEXT NOT NULL
) WITHOUT ROWID;

-- One open gallery research hypothesis, shown beside the printing it varies.
CREATE TABLE gallery_placeholders (
    id TEXT PRIMARY KEY,
    base_item_id TEXT NOT NULL REFERENCES printings(item_id),
    finish TEXT NOT NULL,
    foil_pattern TEXT,
    distribution TEXT,
    status TEXT NOT NULL,
    note TEXT,
    sources_json TEXT NOT NULL
) WITHOUT ROWID;

-- One Cardmarket product of the legacy candidate universe (marketplace context, not evidence).
CREATE TABLE legacy_products (
    product_id INTEGER PRIMARY KEY,
    card_name TEXT NOT NULL,
    set_code TEXT NOT NULL,
    collector_number TEXT,
    set_name TEXT NOT NULL,
    rarity TEXT,
    variant_token TEXT NOT NULL,
    variant_name TEXT,
    variant_name_source TEXT,
    card_key TEXT,
    market TEXT NOT NULL,
    is_code_card INTEGER NOT NULL CHECK (is_code_card IN (0, 1)),
    artist TEXT,
    artist_source TEXT,
    artist_source_url TEXT,
    image_path TEXT NOT NULL,
    image_url TEXT NOT NULL,
    cardmarket_url TEXT NOT NULL,
    axes_json TEXT NOT NULL
);

-- One collection-owner decision; only these settle an absence (verification/owner_adjudications.json).
CREATE TABLE owner_adjudications (
    adjudication_id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL UNIQUE REFERENCES language_claims(unit_id),
    decision TEXT NOT NULL,
    authority TEXT NOT NULL,
    basis TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    rationale TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL
) WITHOUT ROWID;

-- One legacy language claim (unit): does this product exist in this language, and on what evidence.
CREATE TABLE language_claims (
    unit_id TEXT PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES legacy_products(product_id),
    language_code TEXT NOT NULL REFERENCES languages(language_code),
    repository_verdict TEXT NOT NULL,
    application_status TEXT NOT NULL,
    adjudication_id TEXT REFERENCES owner_adjudications(adjudication_id),
    provider_id TEXT REFERENCES providers(provider_id),
    corroborated INTEGER CHECK (corroborated IN (0, 1)),
    source_url TEXT,
    source_ref TEXT,
    source_type TEXT,
    evidence TEXT,
    evidence_granularity TEXT,
    evidence_inference TEXT,
    checked_at TEXT,
    editions_json TEXT NOT NULL,
    UNIQUE (product_id, language_code),
    CHECK (application_status <> 'not-printed' OR adjudication_id IS NOT NULL)
) WITHOUT ROWID;

-- One legacy release row: a product's edition run and its release date source.
CREATE TABLE release_rows (
    row_id TEXT PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES legacy_products(product_id),
    edition TEXT NOT NULL,
    release_date TEXT NOT NULL,
    date_precision TEXT NOT NULL,
    date_approximate INTEGER NOT NULL CHECK (date_approximate IN (0, 1)),
    date_sort TEXT NOT NULL,
    source_provider_id TEXT REFERENCES providers(provider_id),
    source_url TEXT,
    source_page TEXT,
    source_field TEXT
) WITHOUT ROWID;

-- One card-number x language finish unit and its finish evidence state.
CREATE TABLE finish_units (
    finish_unit_id TEXT PRIMARY KEY,
    card_name TEXT NOT NULL,
    set_code TEXT NOT NULL,
    collector_number TEXT,
    language_code TEXT NOT NULL REFERENCES languages(language_code),
    applicability_status TEXT NOT NULL,
    availability_status TEXT NOT NULL,
    completeness_status TEXT NOT NULL,
    product_mapping_status TEXT NOT NULL,
    pattern_status TEXT NOT NULL,
    available_finishes_json TEXT NOT NULL,
    finish_status_json TEXT NOT NULL,
    unresolved_json TEXT NOT NULL
) WITHOUT ROWID;

-- One legacy product a finish unit's claim names, with that claim's status.
CREATE TABLE finish_unit_products (
    finish_unit_id TEXT NOT NULL REFERENCES finish_units(finish_unit_id),
    product_id INTEGER NOT NULL REFERENCES legacy_products(product_id),
    claim_status TEXT NOT NULL,
    PRIMARY KEY (finish_unit_id, product_id)
) WITHOUT ROWID;

-- One finish-store printing; item_id is the item that carries it, if any.
CREATE TABLE finish_printings (
    printing_id TEXT PRIMARY KEY,
    item_id TEXT UNIQUE REFERENCES printings(item_id),
    finish_unit_id TEXT NOT NULL REFERENCES finish_units(finish_unit_id),
    finish TEXT NOT NULL,
    finish_family TEXT,
    foil_pattern TEXT,
    card_size TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    distribution_json TEXT,
    markings_json TEXT NOT NULL,
    product_id INTEGER REFERENCES legacy_products(product_id),
    release_date TEXT,
    image_path TEXT,
    physical_printing_id TEXT
) WITHOUT ROWID;

-- One source a finish printing cites, in recorded order; source_json is the record verbatim.
CREATE TABLE finish_printing_sources (
    printing_id TEXT NOT NULL REFERENCES finish_printings(printing_id),
    source_order INTEGER NOT NULL,
    provider_id TEXT REFERENCES providers(provider_id),
    url TEXT,
    identity_url TEXT,
    source_type TEXT NOT NULL,
    evidence TEXT NOT NULL,
    authority_class TEXT,
    coverage TEXT,
    retrieved_at TEXT,
    source_json TEXT NOT NULL,
    PRIMARY KEY (printing_id, source_order)
) WITHOUT ROWID;

-- One physical specimen the owner holds or inspected (verification/specimens.json, verbatim).
CREATE TABLE specimens (
    specimen_id TEXT PRIMARY KEY,
    specimen_json TEXT NOT NULL
) WITHOUT ROWID;

-- One flat row per catalogue item to collect, with names resolved.
CREATE VIEW app_checklist AS
SELECT
    p.item_id, p.item_kind, p.progress_class, p.active, p.card_name, p.local_card_name,
    p.local_set_code AS set_code, p.local_set_name AS set_name, p.localization_id,
    l.display_name AS language, p.collector_number, p.collector_number_denominator,
    p.edition, p.edition_assignment_status, p.finish, p.finish_family, p.foil_pattern,
    (SELECT group_concat(m.text, '; ') FROM printing_markings m WHERE m.item_id = p.item_id) AS markings,
    json_extract(p.distribution_json, '$.name') AS distribution, p.card_size,
    json_extract(p.rarity_json, '$.display') AS rarity,
    p.finish_verification_status, p.completeness_status,
    p.release_date, p.release_date_precision, p.release_approximate,
    p.artist, a.path AS image_path
FROM printings p
JOIN localizations l USING (localization_id)
LEFT JOIN assets a ON a.asset_id = p.image_asset_id;

-- One row per language claim with its product, provider grade and any owner adjudication.
CREATE VIEW app_language_claims AS
SELECT
    c.unit_id, c.product_id, lp.card_name, lp.set_code, lp.collector_number, lp.variant_token,
    lp.variant_name, lp.cardmarket_url, c.language_code, lg.source_name AS language,
    c.repository_verdict, c.application_status, pr.display_name AS provider,
    pr.authority_tier, c.corroborated, c.source_url, c.source_ref, c.source_type, c.evidence,
    c.evidence_granularity, c.evidence_inference, c.checked_at, c.adjudication_id,
    oa.decision AS adjudication_decision, oa.decided_at AS adjudication_decided_at,
    oa.rationale AS adjudication_rationale
FROM language_claims c
JOIN legacy_products lp USING (product_id)
JOIN languages lg USING (language_code)
LEFT JOIN providers pr ON pr.provider_id = c.provider_id
LEFT JOIN owner_adjudications oa ON oa.adjudication_id = c.adjudication_id;

-- One blank personal-tracker row per item; only current-known items start as wanted.
CREATE VIEW collection_tracker_seed AS
SELECT item_id, 0 AS have, CASE WHEN progress_class = 'current-known' THEN 1 ELSE 0 END AS wanted,
       0 AS quantity
FROM printings;

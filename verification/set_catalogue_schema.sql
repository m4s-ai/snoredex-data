-- Snoredex local set catalogue schema 0.1.0 (#146).
-- This is the executable constraint contract for ADR-0002. The dry-run loads it into an
-- in-memory SQLite database on every build; #140 decides whether/when it enters snoredex.sqlite.

PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

CREATE TABLE source_record (
    source_record_id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_record_key TEXT NOT NULL,
    retrieved TEXT NOT NULL CHECK (retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    raw_json TEXT NOT NULL CHECK (json_valid(raw_json)),
    UNIQUE (provider, provider_record_key, retrieved)
) STRICT;

-- Source records are append-only observations. Reinterpretation belongs in assertions and
-- dispositions; changing the provider row would destroy the reversible path to the raw record.
CREATE TRIGGER source_record_no_update
BEFORE UPDATE ON source_record BEGIN
    SELECT RAISE(ABORT, 'source_record is immutable');
END;
CREATE TRIGGER source_record_no_delete
BEFORE DELETE ON source_record BEGIN
    SELECT RAISE(ABORT, 'source_record is immutable');
END;

CREATE TABLE set_concept (
    set_concept_id TEXT PRIMARY KEY,
    editorial_label TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('asserted', 'candidate'))
) STRICT;

CREATE TABLE local_set (
    local_set_id TEXT PRIMARY KEY,
    locality TEXT NOT NULL,
    local_code TEXT NOT NULL,
    local_name TEXT,
    product_kind TEXT NOT NULL,
    UNIQUE (locality, local_code)
) STRICT;

CREATE TABLE local_set_concept (
    local_set_id TEXT NOT NULL REFERENCES local_set(local_set_id),
    set_concept_id TEXT NOT NULL REFERENCES set_concept(set_concept_id),
    source_record_id TEXT NOT NULL REFERENCES source_record(source_record_id),
    relation TEXT NOT NULL CHECK (relation IN ('realizes', 'relates-to')),
    PRIMARY KEY (local_set_id, set_concept_id, source_record_id, relation)
) STRICT;

CREATE TABLE set_edition (
    set_edition_id TEXT PRIMARY KEY,
    local_set_id TEXT NOT NULL REFERENCES local_set(local_set_id),
    locality TEXT NOT NULL,
    language TEXT NOT NULL,
    script TEXT NOT NULL CHECK (length(script) = 4),
    local_code TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('identified', 'needs-evidence')),
    establishing_claims_json TEXT NOT NULL CHECK (json_valid(establishing_claims_json)),
    UNIQUE (local_set_id, language, script),
    CHECK (locality <> '' AND language <> '' AND local_code <> '')
) STRICT;

CREATE TABLE edition_relation (
    edition_relation_id TEXT PRIMARY KEY,
    from_edition_id TEXT NOT NULL REFERENCES set_edition(set_edition_id),
    to_edition_id TEXT NOT NULL REFERENCES set_edition(set_edition_id),
    relation TEXT NOT NULL CHECK (relation IN ('derived-from', 'reprints', 'overlaps', 'related')),
    source_record_id TEXT NOT NULL REFERENCES source_record(source_record_id),
    CHECK (from_edition_id <> to_edition_id)
) STRICT;

CREATE TABLE release_event (
    release_event_id TEXT PRIMARY KEY,
    local_set_id TEXT NOT NULL REFERENCES local_set(local_set_id),
    event_kind TEXT NOT NULL CHECK (event_kind IN
        ('launch', 'launch-wave', 'reprint', 'distribution', 'delay', 'cancellation')),
    date_value TEXT,
    date_precision TEXT NOT NULL CHECK (date_precision IN ('day', 'month', 'year', 'unknown')),
    approximate INTEGER NOT NULL CHECK (approximate IN (0, 1)),
    status TEXT NOT NULL CHECK (status IN ('announced', 'released', 'delayed', 'cancelled', 'unknown')),
    timezone TEXT,
    source_record_id TEXT NOT NULL REFERENCES source_record(source_record_id),
    CHECK (
        (date_precision = 'unknown' AND date_value IS NULL)
        OR (date_precision = 'year' AND date_value GLOB '[0-9][0-9][0-9][0-9]')
        OR (date_precision = 'month' AND date_value GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]')
        OR (date_precision = 'day' AND date_value GLOB
            '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
    )
) STRICT;

CREATE TABLE release_event_market (
    release_event_id TEXT NOT NULL REFERENCES release_event(release_event_id),
    market_scope TEXT NOT NULL,
    PRIMARY KEY (release_event_id, market_scope)
) STRICT;

CREATE TABLE edition_release_event (
    set_edition_id TEXT NOT NULL REFERENCES set_edition(set_edition_id),
    release_event_id TEXT NOT NULL REFERENCES release_event(release_event_id),
    link_basis TEXT NOT NULL,
    PRIMARY KEY (set_edition_id, release_event_id)
) STRICT;

CREATE TABLE finish_profile (
    finish_profile_id TEXT PRIMARY KEY,
    local_set_id TEXT NOT NULL REFERENCES local_set(local_set_id),
    scope_precision TEXT NOT NULL CHECK (scope_precision IN ('exact', 'scoped', 'partial')),
    closed_within_scope INTEGER NOT NULL CHECK (closed_within_scope IN (0, 1)),
    closure_scope TEXT,
    closure_authority TEXT CHECK (closure_authority IN
        ('official-complete-manifest', 'equivalent-explicit-complete-statement')),
    source_record_id TEXT NOT NULL REFERENCES source_record(source_record_id),
    CHECK (
        closed_within_scope = 0
        OR (closure_scope IS NOT NULL AND closure_authority IS NOT NULL)
    )
) STRICT;

CREATE TABLE finish_profile_edition (
    finish_profile_id TEXT NOT NULL REFERENCES finish_profile(finish_profile_id),
    set_edition_id TEXT NOT NULL REFERENCES set_edition(set_edition_id),
    PRIMARY KEY (finish_profile_id, set_edition_id)
) STRICT;

CREATE TABLE finish_profile_rule (
    finish_profile_rule_id TEXT PRIMARY KEY,
    finish_profile_id TEXT NOT NULL REFERENCES finish_profile(finish_profile_id),
    priority INTEGER NOT NULL,
    effect TEXT NOT NULL CHECK (effect IN ('include', 'exclude')),
    finish TEXT NOT NULL,
    condition_json TEXT NOT NULL CHECK (json_valid(condition_json)),
    source_record_id TEXT NOT NULL REFERENCES source_record(source_record_id)
) STRICT;

-- These are references to existence-bearing nodes established by ADR-0001. This schema has no
-- INSERT path that can mint a card release from set availability or rarity.
CREATE TABLE card_release_ref (
    card_release_id TEXT PRIMARY KEY,
    set_edition_id TEXT NOT NULL REFERENCES set_edition(set_edition_id),
    collector_number TEXT NOT NULL,
    origin TEXT NOT NULL CHECK (origin = 'print-identity-dryrun')
) STRICT;

CREATE TABLE rarity_claim (
    rarity_claim_id TEXT PRIMARY KEY,
    card_release_id TEXT NOT NULL REFERENCES card_release_ref(card_release_id),
    source_record_id TEXT NOT NULL REFERENCES source_record(source_record_id),
    source_provider TEXT NOT NULL,
    source_vocabulary TEXT NOT NULL,
    source_native_value TEXT NOT NULL,
    normalized_rarity_id TEXT,
    source_product_key TEXT,
    UNIQUE (card_release_id, source_record_id, source_native_value, source_product_key)
) STRICT;

CREATE TABLE alias_assertion (
    alias_assertion_id TEXT PRIMARY KEY,
    source_record_id TEXT NOT NULL REFERENCES source_record(source_record_id),
    provider TEXT NOT NULL,
    raw_identifier TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK (target_type IN ('local-set', 'set-edition')),
    local_set_id TEXT REFERENCES local_set(local_set_id),
    set_edition_id TEXT REFERENCES set_edition(set_edition_id),
    relationship TEXT NOT NULL CHECK (relationship IN ('identifies', 'alias-candidate')),
    reversible_projection INTEGER NOT NULL CHECK (reversible_projection = 1),
    CHECK (
        (target_type = 'local-set' AND local_set_id IS NOT NULL AND set_edition_id IS NULL)
        OR (target_type = 'set-edition' AND set_edition_id IS NOT NULL AND local_set_id IS NULL)
    )
) STRICT;

CREATE TABLE source_assertion (
    source_assertion_id TEXT PRIMARY KEY,
    source_record_id TEXT NOT NULL REFERENCES source_record(source_record_id),
    assertion_kind TEXT NOT NULL,
    set_concept_id TEXT REFERENCES set_concept(set_concept_id),
    local_set_id TEXT REFERENCES local_set(local_set_id),
    set_edition_id TEXT REFERENCES set_edition(set_edition_id),
    finish_profile_id TEXT REFERENCES finish_profile(finish_profile_id),
    release_event_id TEXT REFERENCES release_event(release_event_id),
    rarity_claim_id TEXT REFERENCES rarity_claim(rarity_claim_id),
    edition_relation_id TEXT REFERENCES edition_relation(edition_relation_id),
    CHECK (
        (set_concept_id IS NOT NULL) + (local_set_id IS NOT NULL)
        + (set_edition_id IS NOT NULL)
        + (finish_profile_id IS NOT NULL) + (release_event_id IS NOT NULL)
        + (rarity_claim_id IS NOT NULL) + (edition_relation_id IS NOT NULL) = 1
    )
) STRICT;

CREATE TABLE record_disposition (
    source_record_id TEXT PRIMARY KEY REFERENCES source_record(source_record_id),
    disposition TEXT NOT NULL CHECK (disposition IN
        ('mapped', 'matched', 'related', 'positively-excluded', 'needs-evidence')),
    target_ref TEXT,
    reason TEXT NOT NULL,
    CHECK (
        disposition IN ('positively-excluded', 'needs-evidence')
        OR target_ref IS NOT NULL
    )
) STRICT;

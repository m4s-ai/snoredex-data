#!/usr/bin/env python3
"""Build the current-state SQLite handoff database.

The repository deliberately keeps its raw Cardmarket snapshot, evidence journal, verification
stores and generated checklist separate.  That is useful while researching, but it makes every
consumer repeat the same joins.  This generator creates one read-only application snapshot without
the append-only history:

    python scripts/database.py
    python scripts/database.py --check

The source JSON files remain authoritative.  The SQLite file is a deterministic projection with a
source fingerprint, foreign keys, stable Cardmarket product ids, conservative application statuses
and explicit quality findings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from absence_model import absence_decision, absence_scope_urls  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "snoredex.sqlite"
AUDIT = ROOT / "verification" / "DATA-HANDOFF-AUDIT.md"
SCHEMA_VERSION = "1.1.0"

INPUTS = [
    "snorlax_cards.json",
    "analysis_checklist.json",
    "analysis_confirmed_releases.json",
    "verification/units.json",
    "verification/excluded_codecards.json",
    "verification/finish_units.json",
    "verification/source_registry.json",
    "verification/specimens.json",
    "verification/owner_adjudications.json",
]

LANGUAGES = [
    ("en", "English", "English", "Western", 10),
    ("fr", "French", "French", "Western", 20),
    ("de", "German", "German", "Western", 30),
    ("it", "Italian", "Italian", "Western", 40),
    ("es-ES", "Spanish", "European Spanish", "Western", 50),
    ("pt", "Portuguese", "Portuguese", "Western", 60),
    ("nl", "Dutch", "Dutch", "Western", 70),
    ("pl", "Polish", "Polish", "Western", 80),
    ("ru", "Russian", "Russian", "Western", 90),
    ("cs", "Czech", "Czech", "Western", 100),
    ("hu", "Hungarian", "Hungarian", "Western", 110),
    ("ja", "Japanese", "Japanese", "Asia", 120),
    ("ko", "Korean", "Korean", "Asia", 130),
    ("zh-Hant", "T-Chinese", "Traditional Chinese", "Asia", 140),
    ("zh-Hans", "S-Chinese", "Simplified Chinese", "Asia", 150),
    ("id", "Indonesian", "Indonesian", "Southeast Asia", 160),
    ("th", "Thai", "Thai", "Southeast Asia", 170),
]
LANGUAGE_CODE = {
    source_name: code for code, source_name, _display_name, _region, _order in LANGUAGES
}


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def compact(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    for relative in INPUTS:
        payload = (ROOT / relative).read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(payload).digest())
    return digest.hexdigest()


def input_hashes() -> dict[str, str]:
    return {
        relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in INPUTS
    }


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sqlite_dump(path: Path) -> str:
    """Return a portable logical dump for cross-platform rebuild checks.

    SQLite page layouts can differ between the Windows and Linux SQLite builds even when every
    schema object and row is identical. Comparing the logical dump keeps the determinism check
    meaningful without requiring consumers to use a platform-specific binary.
    """
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return "\n".join(connection.iterdump())
    finally:
        connection.close()


def variant(value) -> str:
    return value or "base"


def product_id(card: dict) -> int:
    match = re.search(r"/(\d+)\.(?:jpe?g|png|webp)$", card["imageUrl"], re.I)
    if not match:
        match = re.search(r"_(\d+)\.(?:jpe?g|png|webp)$", card["imageFile"], re.I)
    if not match:
        raise ValueError(f"cannot derive Cardmarket product id from {card['imageUrl']!r}")
    return int(match.group(1))


def finish_family(value: str) -> str:
    if value in {"reverse-holo", "mirror-holo"}:
        return "reverse-holo"
    return value


def provider_for_source(source: dict, providers: list[dict]) -> str | None:
    url = source.get("url") or source.get("identityUrl")
    if url:
        host = (urlparse(url).hostname or "").lower()
        for provider in providers:
            if host in {item.lower() for item in provider.get("hosts", [])}:
                return provider["providerId"]
    label = (source.get("sourceType") or "").lower()
    for provider_id, token in [
        ("owner-attestation", "owner attestation"),
        ("cardmarket-listing-photo", "seller listing photograph"),
        ("inspected-specimen", "photograph"),
        ("bulbapedia", "bulbapedia"),
        ("tcgdex", "tcgdex"),
        ("tcgcsv", "tcgcsv"),
        ("cardmarket", "cardmarket"),
        ("pokemon-official", "official checklist"),
    ]:
        if token in label:
            return provider_id
    return None


SCHEMA = r"""
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;
PRAGMA temp_store = MEMORY;
PRAGMA page_size = 4096;
PRAGMA user_version = 10001;

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE languages (
    language_code TEXT PRIMARY KEY,
    source_name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL UNIQUE,
    region TEXT NOT NULL,
    display_order INTEGER NOT NULL UNIQUE
) WITHOUT ROWID;

CREATE TABLE providers (
    provider_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    organization TEXT,
    homepage TEXT,
    category TEXT NOT NULL,
    authority_tier INTEGER NOT NULL CHECK (authority_tier BETWEEN 1 AND 5),
    coverage TEXT NOT NULL,
    supports_absence INTEGER NOT NULL CHECK (supports_absence IN (0, 1)),
    used_for_json TEXT NOT NULL,
    attribution TEXT NOT NULL,
    notes TEXT NOT NULL,
    hosts_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE owner_adjudications (
    adjudication_id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL UNIQUE,
    decision TEXT NOT NULL CHECK (decision = 'not-printed'),
    authority TEXT NOT NULL CHECK (authority = 'collection-owner'),
    basis TEXT NOT NULL CHECK (basis = 'multi-source-adjudication'),
    decided_at TEXT NOT NULL,
    rationale TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    card_name TEXT NOT NULL,
    set_code TEXT NOT NULL,
    collector_number TEXT NOT NULL,
    set_name TEXT NOT NULL,
    rarity TEXT NOT NULL,
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
    cardmarket_url TEXT NOT NULL UNIQUE,
    marketplace_reverse_holo_hint INTEGER NOT NULL CHECK (marketplace_reverse_holo_hint IN (0, 1)),
    marketplace_first_edition_hint INTEGER NOT NULL CHECK (marketplace_first_edition_hint IN (0, 1))
);

CREATE UNIQUE INDEX products_collectible_identity
ON products(set_code, collector_number, variant_token)
WHERE is_code_card = 0;

CREATE INDEX products_card_key ON products(card_key);
CREATE INDEX products_set_number ON products(set_code, collector_number);

CREATE TABLE product_market_state (
    product_id INTEGER PRIMARY KEY REFERENCES products(product_id) ON DELETE CASCADE,
    observed_on TEXT NOT NULL,
    available_items INTEGER NOT NULL CHECK (available_items >= 0)
);

CREATE TABLE product_axes (
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    axis TEXT NOT NULL,
    PRIMARY KEY (product_id, axis)
) WITHOUT ROWID;

CREATE TABLE product_languages (
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    language_code TEXT NOT NULL REFERENCES languages(language_code),
    marketplace_claimed INTEGER NOT NULL DEFAULT 1 CHECK (marketplace_claimed = 1),
    verification_status TEXT NOT NULL CHECK (verification_status IN (
        'confirmed', 'contradicted', 'needs-manual-review', 'pending', 'out-of-scope'
    )),
    application_status TEXT NOT NULL CHECK (application_status IN (
        'exists', 'not-printed', 'disputed', 'unresolved', 'out-of-scope'
    )),
    absence_supported INTEGER NOT NULL CHECK (absence_supported IN (0, 1)),
    adjudication_id TEXT REFERENCES owner_adjudications(adjudication_id),
    unit_id TEXT,
    provider_id TEXT REFERENCES providers(provider_id),
    corroborated INTEGER CHECK (corroborated IN (0, 1)),
    source_url TEXT,
    source_ref TEXT,
    source_type TEXT,
    evidence TEXT,
    checked_at TEXT,
    PRIMARY KEY (product_id, language_code)
) WITHOUT ROWID;

CREATE INDEX product_languages_status ON product_languages(application_status, language_code);
CREATE INDEX product_languages_unit ON product_languages(unit_id);

CREATE TABLE product_editions (
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    language_code TEXT NOT NULL REFERENCES languages(language_code),
    edition TEXT NOT NULL CHECK (edition IN ('first-edition', 'unlimited', 'no-edition-system')),
    edition_system TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (product_id, language_code, edition)
) WITHOUT ROWID;

CREATE TABLE release_rows (
    row_id TEXT PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    edition TEXT NOT NULL,
    release_date TEXT NOT NULL,
    date_precision TEXT NOT NULL CHECK (date_precision IN ('year', 'month', 'day')),
    date_approximate INTEGER NOT NULL CHECK (date_approximate IN (0, 1)),
    date_sort TEXT NOT NULL,
    source_provider_id TEXT REFERENCES providers(provider_id),
    source_url TEXT,
    source_page TEXT,
    source_field TEXT
) WITHOUT ROWID;

CREATE INDEX release_rows_date ON release_rows(date_sort, row_id);

CREATE TABLE finish_units (
    finish_unit_id TEXT PRIMARY KEY,
    card_name TEXT NOT NULL,
    set_code TEXT NOT NULL,
    collector_number TEXT NOT NULL,
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

CREATE INDEX finish_units_card_language
ON finish_units(set_code, collector_number, language_code);

CREATE TABLE finish_unit_products (
    finish_unit_id TEXT NOT NULL REFERENCES finish_units(finish_unit_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    claim_status TEXT NOT NULL,
    PRIMARY KEY (finish_unit_id, product_id)
) WITHOUT ROWID;

CREATE TABLE printings (
    printing_id TEXT PRIMARY KEY,
    finish_unit_id TEXT NOT NULL REFERENCES finish_units(finish_unit_id) ON DELETE CASCADE,
    finish TEXT NOT NULL,
    finish_family TEXT NOT NULL,
    foil_pattern TEXT,
    card_size TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    distribution_kind TEXT,
    distribution_name TEXT,
    distribution_region TEXT,
    distribution_date TEXT,
    release_date TEXT,
    image_path TEXT
) WITHOUT ROWID;

CREATE UNIQUE INDEX printings_unit_identity
ON printings(printing_id, finish_unit_id);

CREATE INDEX printings_finish ON printings(finish_family, finish);

CREATE TABLE printing_product_map (
    printing_id TEXT NOT NULL REFERENCES printings(printing_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    PRIMARY KEY (printing_id, product_id)
) WITHOUT ROWID;

CREATE TABLE printing_markings (
    printing_id TEXT NOT NULL REFERENCES printings(printing_id) ON DELETE CASCADE,
    marking_order INTEGER NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN (
        'print-identity', 'reverse-holo-treatment', 'distribution-promo'
    )),
    PRIMARY KEY (printing_id, marking_order)
) WITHOUT ROWID;

CREATE TABLE printing_sources (
    printing_id TEXT NOT NULL REFERENCES printings(printing_id) ON DELETE CASCADE,
    source_order INTEGER NOT NULL,
    provider_id TEXT REFERENCES providers(provider_id),
    source_url TEXT,
    identity_url TEXT,
    source_type TEXT NOT NULL,
    evidence TEXT NOT NULL,
    authority_tier INTEGER,
    coverage TEXT,
    supports_absence INTEGER CHECK (supports_absence IN (0, 1)),
    retrieved_at TEXT,
    source_json TEXT NOT NULL,
    PRIMARY KEY (printing_id, source_order)
) WITHOUT ROWID;

CREATE TABLE checklist_items (
    checklist_id TEXT PRIMARY KEY,
    row_id TEXT NOT NULL REFERENCES release_rows(row_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    finish_unit_id TEXT NOT NULL REFERENCES finish_units(finish_unit_id),
    printing_id TEXT,
    language_code TEXT NOT NULL REFERENCES languages(language_code),
    edition TEXT NOT NULL,
    edition_scope TEXT NOT NULL,
    catalog_status TEXT NOT NULL CHECK (catalog_status IN ('documented', 'unresolved')),
    finish TEXT NOT NULL,
    finish_family TEXT NOT NULL,
    finish_group_id TEXT NOT NULL,
    finish_verification_status TEXT NOT NULL,
    foil_pattern TEXT,
    marking_roles_json TEXT NOT NULL,
    markings_json TEXT,
    distribution_json TEXT,
    card_size TEXT NOT NULL,
    product_mapping TEXT NOT NULL,
    mapped_variants_json TEXT NOT NULL,
    completeness_status TEXT NOT NULL,
    release_date TEXT NOT NULL,
    release_date_precision TEXT NOT NULL,
    release_approximate INTEGER NOT NULL CHECK (release_approximate IN (0, 1)),
    release_sort TEXT NOT NULL,
    image_path TEXT,
    CHECK (
        (catalog_status = 'documented' AND printing_id IS NOT NULL) OR
        (catalog_status = 'unresolved' AND printing_id IS NULL)
    ),
    FOREIGN KEY (printing_id, finish_unit_id)
        REFERENCES printings(printing_id, finish_unit_id)
) WITHOUT ROWID;

CREATE INDEX checklist_browse
ON checklist_items(language_code, catalog_status, release_sort, checklist_id);
CREATE INDEX checklist_finish
ON checklist_items(finish_family, finish, checklist_id);

CREATE TABLE checklist_evidence_refs (
    checklist_id TEXT NOT NULL REFERENCES checklist_items(checklist_id) ON DELETE CASCADE,
    evidence_order INTEGER NOT NULL,
    evidence_ref TEXT NOT NULL,
    PRIMARY KEY (checklist_id, evidence_order)
) WITHOUT ROWID;

CREATE TABLE specimens (
    specimen_id TEXT PRIMARY KEY,
    specimen_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE quality_issues (
    issue_id TEXT PRIMARY KEY,
    severity TEXT NOT NULL CHECK (severity IN ('warning', 'information')),
    category TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    message TEXT NOT NULL
) WITHOUT ROWID;

CREATE INDEX quality_issues_category ON quality_issues(category, severity);

CREATE VIEW app_products AS
SELECT
    p.*,
    ms.observed_on AS market_observed_on,
    ms.available_items,
    (SELECT COUNT(*) FROM product_languages pl
      WHERE pl.product_id = p.product_id AND pl.application_status = 'exists') AS confirmed_language_count,
    (SELECT COUNT(*) FROM product_languages pl
      WHERE pl.product_id = p.product_id AND pl.application_status = 'disputed') AS disputed_language_count
FROM products p
LEFT JOIN product_market_state ms ON ms.product_id = p.product_id;

CREATE VIEW app_language_availability AS
SELECT
    pl.unit_id,
    pl.product_id,
    p.card_name,
    p.set_code,
    p.collector_number,
    p.variant_token,
    pl.language_code,
    l.display_name AS language,
    pl.verification_status AS repository_verdict,
    pl.application_status,
    pl.absence_supported,
    pl.absence_supported AS source_absence_supported,
    pl.adjudication_id,
    CASE
        WHEN oa.adjudication_id IS NOT NULL THEN oa.authority
        WHEN pl.application_status = 'not-printed' AND pl.absence_supported = 1
            THEN 'source-scope'
        ELSE NULL
    END AS decision_authority,
    CASE
        WHEN oa.adjudication_id IS NOT NULL THEN oa.basis
        WHEN pl.application_status = 'not-printed' AND pl.absence_supported = 1
            THEN 'scoped-source'
        ELSE NULL
    END AS decision_basis,
    oa.decided_at AS decision_decided_at,
    oa.rationale AS decision_rationale,
    oa.evidence_refs_json AS decision_evidence_refs_json,
    pl.provider_id,
    pr.display_name AS provider,
    pr.authority_tier,
    pl.corroborated,
    pl.source_url,
    pl.source_ref,
    pl.source_type,
    pl.evidence,
    pl.checked_at
FROM product_languages pl
JOIN products p USING(product_id)
JOIN languages l USING(language_code)
LEFT JOIN providers pr USING(provider_id)
LEFT JOIN owner_adjudications oa USING(adjudication_id);

CREATE VIEW app_checklist AS
SELECT
    ci.checklist_id,
    ci.row_id,
    ci.product_id,
    ci.finish_unit_id,
    ci.printing_id,
    ci.catalog_status,
    p.card_name,
    p.set_code,
    p.collector_number,
    p.set_name,
    p.rarity,
    p.variant_token,
    p.variant_name,
    ci.language_code,
    l.display_name AS language,
    ci.edition,
    ci.edition_scope,
    ci.finish_family,
    ci.finish,
    ci.finish_group_id,
    ci.foil_pattern,
    ci.marking_roles_json,
    ci.markings_json,
    ci.distribution_json,
    ci.card_size,
    ci.finish_verification_status,
    ci.completeness_status,
    ci.product_mapping,
    ci.mapped_variants_json,
    ci.release_date,
    ci.release_date_precision,
    ci.release_approximate,
    ci.release_sort,
    p.artist,
    ci.image_path,
    p.cardmarket_url
FROM checklist_items ci
JOIN products p USING(product_id)
JOIN languages l USING(language_code);

CREATE VIEW collection_tracker_seed AS
SELECT
    checklist_id,
    0 AS have,
    CASE WHEN catalog_status = 'documented' THEN 1 ELSE 0 END AS wanted,
    0 AS quantity
FROM checklist_items;

CREATE VIEW quality_summary AS
SELECT severity, category, COUNT(*) AS issue_count
FROM quality_issues
GROUP BY severity, category;
"""


def build_database(target: Path) -> dict[str, int | str]:
    cards_doc = load("snorlax_cards.json")
    cards = cards_doc["cards"]
    checklist_doc = load("analysis_checklist.json")
    checklist = checklist_doc["items"]
    releases = load("analysis_confirmed_releases.json")["variants"]
    units = load("verification/units.json")
    excluded = load("verification/excluded_codecards.json")
    finishes_doc = load("verification/finish_units.json")
    finish_units = finishes_doc["units"]
    registry = load("verification/source_registry.json")
    providers = registry["providers"]
    specimens_doc = load("verification/specimens.json")
    owner_adjudications_doc = load("verification/owner_adjudications.json")
    owner_adjudications = owner_adjudications_doc["decisions"]
    if owner_adjudications_doc.get("meta", {}).get("schemaVersion") != "1.0.0":
        raise ValueError("owner adjudications schemaVersion must be 1.0.0")

    temporary = target.with_name(target.name + ".tmp")
    if temporary.exists():
        temporary.unlink()
    temporary.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(temporary)
    connection.executescript(SCHEMA)
    cursor = connection.cursor()

    fingerprint = source_fingerprint()
    snapshot_date = max(
        cards_doc["meta"]["verification"]["lastUpdated"],
        checklist_doc["meta"]["generated"],
        load("analysis_confirmed_releases.json")["generated"],
    )
    metadata = {
        "schema": "snoredex-current-state",
        "schema_version": SCHEMA_VERSION,
        "generated": snapshot_date,
        "source_fingerprint_sha256": fingerprint,
        "history_included": "false",
        "scope": "All 198 Cardmarket product rows; code cards retained but marked out-of-scope.",
        "application_status_policy": (
            "confirmed=exists; contradicted becomes not-printed only when its source is explicitly "
            "absence-capable within scope or an explicit collection-owner adjudication exists, "
            "otherwise disputed; pending/manual=unresolved; code cards=out-of-scope"
        ),
        "checklist_schema_version": checklist_doc["meta"]["schemaVersion"],
        "owner_adjudications_schema_version": owner_adjudications_doc["meta"]["schemaVersion"],
        "generator_sha256": file_hash(Path(__file__)),
    }
    for relative, digest in input_hashes().items():
        metadata[f"input_sha256:{relative}"] = digest
    cursor.executemany("INSERT INTO metadata VALUES (?, ?)", sorted(metadata.items()))
    cursor.executemany("INSERT INTO languages VALUES (?, ?, ?, ?, ?)", LANGUAGES)

    provider_by_id = {item["providerId"]: item for item in providers}
    # The declared complete manifests, read from the provider config rather than from the evidence
    # index, so this and scripts/language_status.py apply one rule from one place (#66). The two
    # sets are identical today; deriving them separately is how they would stop being.
    absence_source_urls = absence_scope_urls(providers)
    cursor.executemany(
        "INSERT INTO providers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                item["providerId"], item["displayName"], item.get("organization"),
                item.get("homepage"), item["category"], item["authorityTier"],
                item["coverage"], int(item["supportsAbsence"]), compact(item.get("usedFor", [])),
                item["attribution"], item["notes"], compact(item.get("hosts", [])),
            )
            for item in providers
        ],
    )

    owner_by_unit: dict[str, dict] = {}
    for decision in owner_adjudications:
        unit_id = decision.get("unitId")
        if not unit_id or unit_id in owner_by_unit:
            raise ValueError(f"owner adjudication has missing or duplicate unitId: {unit_id!r}")
        if decision.get("decision") != "not-printed":
            raise ValueError(f"owner adjudication {decision.get('adjudicationId')} is not not-printed")
        if decision.get("authority") != "collection-owner":
            raise ValueError(f"owner adjudication {decision.get('adjudicationId')} has invalid authority")
        if decision.get("basis") != "multi-source-adjudication":
            raise ValueError(f"owner adjudication {decision.get('adjudicationId')} has invalid basis")
        if not decision.get("rationale") or not decision.get("evidenceRefs"):
            raise ValueError(f"owner adjudication {decision.get('adjudicationId')} lacks rationale/evidence")
        owner_by_unit[unit_id] = decision
        cursor.execute(
            "INSERT INTO owner_adjudications VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                decision["adjudicationId"], decision["unitId"], decision["decision"],
                decision["authority"], decision["basis"], decision["decidedAt"],
                decision["rationale"], compact(decision["evidenceRefs"]),
            ),
        )

    product_by_url: dict[str, int] = {}
    product_by_identity: dict[tuple[str, str, str], int] = {}
    card_by_id: dict[int, dict] = {}
    for card in cards:
        pid = product_id(card)
        if pid in card_by_id:
            raise ValueError(f"duplicate Cardmarket product id {pid}")
        card_by_id[pid] = card
        product_by_url[card["productUrl"]] = pid
        if not card["isCodeCard"]:
            identity = (card["setCode"], card["number"], variant(card.get("variantToken")))
            if identity in product_by_identity:
                raise ValueError(f"duplicate collectible identity {identity}")
            product_by_identity[identity] = pid
        cursor.execute(
            "INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                pid, card["name"], card["setCode"], card["number"], card["setName"],
                card["rarity"], variant(card.get("variantToken")), card.get("variantName"),
                card.get("variantNameSource"), card.get("cardKey"), card["market"],
                int(card["isCodeCard"]), card.get("artist"), card.get("artistSource"),
                card.get("artistSourceUrl"), card["imageFile"], card["imageUrl"],
                card["productUrl"], int(card["hasReverseHolo"]), int(card["hasFirstEdition"]),
            ),
        )
        cursor.execute(
            "INSERT INTO product_market_state VALUES (?, ?, ?)",
            (pid, cards_doc["meta"]["retrieved"], card["availableItems"]),
        )
        cursor.executemany(
            "INSERT INTO product_axes VALUES (?, ?)",
            [(pid, axis) for axis in card.get("variantAxes", [])],
        )

    established_languages: set[tuple[int, str]] = set()
    language_application_status: dict[tuple[int, str], str] = {}
    for unit in units:
        identity = (unit["setCode"], unit["number"], variant(unit.get("variant")))
        pid = product_by_identity.get(identity)
        if pid is None:
            raise ValueError(f"language unit {unit['unitId']} has no collectible product {identity}")
        provider = provider_by_id[unit["providerId"]]
        source_url = unit.get("sourceUrl")
        absence_supported = int(
            bool(source_url) and source_url.rstrip("/") in absence_source_urls
        )
        adjudication = owner_by_unit.get(unit["unitId"])
        if adjudication and unit["status"] != "contradicted":
            raise ValueError(
                f"owner adjudication {adjudication['adjudicationId']} targets non-contradicted "
                f"unit {unit['unitId']}"
            )
        app_status = absence_decision(
            unit["status"], source_url, absence_source_urls, bool(adjudication)
        )
        if app_status == "exists":
            established_languages.add((pid, LANGUAGE_CODE[unit["language"]]))
        language_application_status[(pid, LANGUAGE_CODE[unit["language"]])] = app_status
        cursor.execute(
            "INSERT INTO product_languages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                pid, LANGUAGE_CODE[unit["language"]], 1, unit["status"], app_status,
                absence_supported, adjudication["adjudicationId"] if adjudication else None,
                unit["unitId"], unit["providerId"],
                int(unit["corroborated"]), source_url, unit.get("sourceRef"),
                unit.get("sourceType"), unit.get("evidence"), unit.get("checkedAt"),
            ),
        )

    unit_by_id = {unit["unitId"]: unit for unit in units}
    unknown_adjudications = sorted(set(owner_by_unit) - set(unit_by_id))
    if unknown_adjudications:
        raise ValueError(
            "owner adjudications reference unknown units: " + ", ".join(unknown_adjudications)
        )

    for unit in excluded:
        pid = product_by_url.get(unit["cmUrl"])
        if pid is None:
            raise ValueError(f"excluded unit {unit['unitId']} has no product URL match")
        cursor.execute(
            "INSERT INTO product_languages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                pid, LANGUAGE_CODE[unit["language"]], 1, "out-of-scope", "out-of-scope", 0,
                None, unit["unitId"], None, None, None, None, None, None, None,
            ),
        )

    suppressed_edition_claims: list[tuple[int, str, str, str]] = []
    for pid, card in card_by_id.items():
        if card["isCodeCard"]:
            continue
        edition_data = card.get("editions") or {}
        system = edition_data.get("system") or "none"
        source = edition_data.get("source") or "No edition source recorded."
        edition_languages = [
            (language, "first-edition")
            for language in sorted(set(edition_data.get("firstEditionLanguages", [])))
        ]
        label = (
            "unlimited"
            if edition_data.get("hasFirstEdition") or system in {
                "WOTC-unlimited-only", "JP-unlimited-only"
            }
            else "no-edition-system"
        )
        edition_languages.extend(
            (language, label)
            for language in sorted(set(edition_data.get("unlimitedLanguages", [])))
        )
        for language, edition in edition_languages:
            language_code = LANGUAGE_CODE[language]
            if (pid, language_code) not in established_languages:
                status = language_application_status.get((pid, language_code), "unresolved")
                category = (
                    "suppressed-absent-edition"
                    if status == "not-printed" else "suppressed-unverified-edition"
                )
                suppressed_edition_claims.append((pid, language_code, edition, category))
                continue
            cursor.execute(
                "INSERT INTO product_editions VALUES (?, ?, ?, ?, ?)",
                (pid, language_code, edition, system, source),
            )

    for row in releases:
        pid = product_by_url.get(row["cardmarketUrl"])
        if pid is None:
            raise ValueError(f"release row {row['rowId']} has no product URL match")
        source = row.get("dateSource") or {}
        source_provider_id = provider_for_source(source, providers) if source else None
        cursor.execute(
            "INSERT INTO release_rows VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                row["rowId"], pid, row["edition"], row["date"], row["datePrecision"],
                int(row["dateApproximate"]), row["dateSort"], source_provider_id,
                source.get("url"), source.get("page"), source.get("field"),
            ),
        )

    for unit in finish_units:
        language_code = LANGUAGE_CODE[unit["language"]]
        cursor.execute(
            "INSERT INTO finish_units VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                unit["finishUnitId"], unit["cardName"], unit["setCode"], unit["number"],
                language_code, unit["applicabilityStatus"], unit["availabilityStatus"],
                unit["completenessStatus"], unit["productMappingStatus"], unit["patternStatus"],
                compact(unit["availableFinishes"]), compact(unit["finishStatus"]),
                compact(unit["unresolved"]),
            ),
        )
        finish_products: dict[str, int] = {}
        for product in unit["products"]:
            pid = product_by_url.get(product["cardmarketUrl"])
            if pid is None:
                raise ValueError(
                    f"finish unit {unit['finishUnitId']} has unknown product {product['cardmarketUrl']}"
                )
            finish_products[product["variant"]] = pid
            cursor.execute(
                "INSERT INTO finish_unit_products VALUES (?, ?, ?)",
                (unit["finishUnitId"], pid, product["claimStatus"]),
            )
        for printing in unit["printings"]:
            distribution = printing.get("distribution") or {}
            cursor.execute(
                "INSERT INTO printings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    printing["printingId"], unit["finishUnitId"], printing["finish"],
                    finish_family(printing["finish"]), printing.get("foilPattern"),
                    printing["cardSize"], printing["verificationStatus"],
                    distribution.get("kind"), distribution.get("name"),
                    distribution.get("region"), distribution.get("date"),
                    printing.get("releaseDate"), printing.get("image"),
                ),
            )
            for mapped_variant in printing.get("mappedVariants", []):
                pid = finish_products.get(mapped_variant)
                if pid is None:
                    raise ValueError(
                        f"printing {printing['printingId']} maps unknown variant {mapped_variant}"
                    )
                cursor.execute(
                    "INSERT INTO printing_product_map VALUES (?, ?)",
                    (printing["printingId"], pid),
                )
            for order, marking in enumerate(printing.get("markings") or []):
                cursor.execute(
                    "INSERT INTO printing_markings VALUES (?, ?, ?, ?, ?)",
                    (
                        printing["printingId"], order, marking["kind"], marking["text"],
                        marking["role"],
                    ),
                )
            for order, source in enumerate(printing.get("sources", [])):
                cursor.execute(
                    "INSERT INTO printing_sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        printing["printingId"], order, provider_for_source(source, providers),
                        source.get("url"), source.get("identityUrl"), source["sourceType"],
                        source["evidence"], source.get("authorityTier"), source.get("coverage"),
                        int(source["supportsAbsence"]) if "supportsAbsence" in source else None,
                        source.get("retrievedAt"), compact(source),
                    ),
                )

    for item in checklist:
        pid = product_by_url.get(item["cardmarketUrl"])
        if pid is None:
            raise ValueError(f"checklist item {item['checklistId']} has no product URL match")
        status = "documented" if item.get("printingId") else "unresolved"
        cursor.execute(
            "INSERT INTO checklist_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                item["checklistId"], item["rowId"], pid, item["finishUnitId"],
                item.get("printingId"), LANGUAGE_CODE[item["language"]], item["edition"],
                item["editionScope"], status, item["finish"], item["finishFamily"],
                item["finishGroupId"], item["finishVerificationStatus"], item.get("foilPattern"),
                compact(item["markingRoles"]), compact(item["markings"]) if item.get("markings") else None,
                compact(item["distribution"]) if item.get("distribution") else None,
                item["cardSize"], item["productMapping"], compact(item["mappedVariants"]),
                item["completenessStatus"], item["releaseDate"], item["releaseDatePrecision"],
                int(item["releaseApproximate"]), item["releaseSort"], item.get("image"),
            ),
        )
        cursor.executemany(
            "INSERT INTO checklist_evidence_refs VALUES (?, ?, ?)",
            [
                (item["checklistId"], order, source_id)
                for order, source_id in enumerate(item["sourceIds"])
            ],
        )

    specimens = specimens_doc.get("specimens", specimens_doc if isinstance(specimens_doc, list) else [])
    for specimen in specimens:
        sid = specimen.get("specimenId") or specimen.get("id")
        if not sid:
            raise ValueError("specimen without stable id")
        cursor.execute("INSERT INTO specimens VALUES (?, ?)", (sid, compact(specimen)))

    issue_number = 0

    def issue(severity: str, category: str, entity_type: str, entity_id: str, message: str):
        nonlocal issue_number
        issue_number += 1
        cursor.execute(
            "INSERT INTO quality_issues VALUES (?, ?, ?, ?, ?, ?)",
            (f"Q{issue_number:04d}", severity, category, entity_type, entity_id, message),
        )

    for unit in units:
        provider = provider_by_id[unit["providerId"]]
        adjudication = owner_by_unit.get(unit["unitId"])
        source_absence_supported = bool(
            unit.get("sourceUrl")
            and unit["sourceUrl"].rstrip("/") in absence_source_urls
        )
        if adjudication:
            issue(
                "information", "owner-adjudicated-absence", "language-unit", unit["unitId"],
                "The collection owner adopted not-printed after reviewing the cited claims and "
                "evidence; no single provider is treated as proving absence.",
            )
        elif unit["status"] == "contradicted" and not source_absence_supported:
            issue(
                "warning", "unsupported-negative-language-claim", "language-unit", unit["unitId"],
                f"Repository verdict is contradicted, but source {unit.get('sourceUrl') or unit['providerId']} "
                "is not marked as an absence-capable complete scope. App status is conservatively disputed.",
            )
    for pid, language_code, edition, category in suppressed_edition_claims:
        if category == "suppressed-absent-edition":
            message = (
                "The source edition projection included this language, but its language claim is "
                "explicitly not-printed. The edition row is omitted from the app model."
            )
        else:
            message = (
                "The source edition projection included this marketplace-claimed language, but the "
                "language is not positively established. The edition row is omitted from the app model."
            )
        issue(
            "information", category, "product-language",
            f"{pid}:{language_code}:{edition}",
            message,
        )
    for item in checklist:
        if not item.get("printingId"):
            issue(
                "information", "unresolved-physical-printing", "checklist-item",
                item["checklistId"], "Confirmed card/language/edition has no identified finish printing.",
            )
    for pid, card in card_by_id.items():
        if card.get("artist") is None:
            issue(
                "information", "missing-artist", "product", str(pid),
                "Illustrator is not established; null is preserved rather than inferred.",
            )
        if card.get("cardKey") is None:
            issue(
                "information", "missing-card-key", "product", str(pid),
                "Cardmarket did not supply a card-text grouping key.",
            )
        if variant(card.get("variantToken")) != "base" and not card.get("variantName"):
            issue(
                "information", "opaque-variant", "product", str(pid),
                "Cardmarket variant token is present but its physical meaning is not identified.",
            )
    for row in releases:
        if not row.get("dateSource"):
            issue(
                "information", "release-date-without-row-source", "release-row", row["rowId"],
                "Release date has no row-level dateSource; precision/approximation remain explicit.",
            )
    issue(
        "information", "volatile-marketplace-field", "dataset", "availableItems",
        f"availableItems is isolated in product_market_state and dated {cards_doc['meta']['retrieved']}.",
    )
    if all(card.get("versionsCount") is None for card in cards):
        issue(
            "information", "empty-source-field", "dataset", "versionsCount",
            "versionsCount is null for every product and is omitted from the handoff schema.",
        )

    connection.commit()
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_keys:
        connection.close()
        temporary.unlink(missing_ok=True)
        raise ValueError(f"database integrity failed: integrity={integrity!r}, foreign_keys={foreign_keys[:3]}")
    connection.execute("VACUUM")
    connection.close()
    os.replace(temporary, target)

    return database_stats(target)


def database_stats(target: Path) -> dict[str, int | str]:
    connection = sqlite3.connect(target)
    scalar = lambda sql: connection.execute(sql).fetchone()[0]
    stats: dict[str, int | str] = {
        "fingerprint": scalar("SELECT value FROM metadata WHERE key='source_fingerprint_sha256'"),
        "generated": scalar("SELECT value FROM metadata WHERE key='generated'"),
        "products": scalar("SELECT COUNT(*) FROM products"),
        "collectible_products": scalar("SELECT COUNT(*) FROM products WHERE is_code_card=0"),
        "code_cards": scalar("SELECT COUNT(*) FROM products WHERE is_code_card=1"),
        "owner_adjudications": scalar("SELECT COUNT(*) FROM owner_adjudications"),
        "language_claims": scalar("SELECT COUNT(*) FROM product_languages"),
        "language_confirmed": scalar(
            "SELECT COUNT(*) FROM product_languages WHERE verification_status='confirmed'"
        ),
        "language_contradicted": scalar(
            "SELECT COUNT(*) FROM product_languages WHERE verification_status='contradicted'"
        ),
        "language_disputed": scalar(
            "SELECT COUNT(*) FROM product_languages WHERE application_status='disputed'"
        ),
        "language_not_printed": scalar(
            "SELECT COUNT(*) FROM product_languages WHERE application_status='not-printed'"
        ),
        "language_owner_adjudicated": scalar(
            "SELECT COUNT(*) FROM product_languages WHERE adjudication_id IS NOT NULL"
        ),
        "language_source_scoped_absence": scalar(
            "SELECT COUNT(*) FROM product_languages WHERE application_status='not-printed' "
            "AND absence_supported=1 AND adjudication_id IS NULL"
        ),
        "language_out_of_scope": scalar(
            "SELECT COUNT(*) FROM product_languages WHERE application_status='out-of-scope'"
        ),
        "product_editions": scalar("SELECT COUNT(*) FROM product_editions"),
        "suppressed_editions": scalar(
            "SELECT COUNT(*) FROM quality_issues WHERE category IN "
            "('suppressed-unverified-edition', 'suppressed-absent-edition')"
        ),
        "suppressed_unverified_editions": scalar(
            "SELECT COUNT(*) FROM quality_issues WHERE category='suppressed-unverified-edition'"
        ),
        "suppressed_absent_editions": scalar(
            "SELECT COUNT(*) FROM quality_issues WHERE category='suppressed-absent-edition'"
        ),
        "finish_units": scalar("SELECT COUNT(*) FROM finish_units"),
        "printings": scalar("SELECT COUNT(*) FROM printings"),
        "checklist_items": scalar("SELECT COUNT(*) FROM checklist_items"),
        "documented_items": scalar(
            "SELECT COUNT(*) FROM checklist_items WHERE catalog_status='documented'"
        ),
        "unresolved_items": scalar(
            "SELECT COUNT(*) FROM checklist_items WHERE catalog_status='unresolved'"
        ),
        "release_rows": scalar("SELECT COUNT(*) FROM release_rows"),
        "release_rows_without_source": scalar(
            "SELECT COUNT(*) FROM release_rows WHERE source_url IS NULL"
        ),
        "missing_artists": scalar("SELECT COUNT(*) FROM products WHERE artist IS NULL"),
        "opaque_variants": scalar(
            "SELECT COUNT(*) FROM products WHERE variant_token <> 'base' AND variant_name IS NULL"
        ),
        "quality_issues": scalar("SELECT COUNT(*) FROM quality_issues"),
    }
    connection.close()
    return stats


def validate_database(target: Path) -> list[str]:
    problems: list[str] = []
    if not target.is_file():
        return [f"missing database: {target}"]
    try:
        connection = sqlite3.connect(f"file:{target.as_posix()}?mode=ro", uri=True)
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            problems.append("PRAGMA integrity_check did not return ok")
        fk = connection.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            problems.append(f"foreign key errors: {fk[:3]}")
        fingerprint = connection.execute(
            "SELECT value FROM metadata WHERE key='source_fingerprint_sha256'"
        ).fetchone()
        if not fingerprint or fingerprint[0] != source_fingerprint():
            problems.append("database source fingerprint does not match current canonical inputs")
        generator = connection.execute(
            "SELECT value FROM metadata WHERE key='generator_sha256'"
        ).fetchone()
        current_generator = file_hash(Path(__file__))
        if not generator or generator[0] != current_generator:
            problems.append("database was built by a different version of scripts/database.py")
        if connection.execute("PRAGMA user_version").fetchone()[0] != 10001:
            problems.append("database PRAGMA user_version is not 10001")
        owner_schema = connection.execute(
            "SELECT value FROM metadata WHERE key='owner_adjudications_schema_version'"
        ).fetchone()
        if not owner_schema or owner_schema[0] != "1.0.0":
            problems.append("owner adjudications schema version is missing or unsupported")
        expected = {
            "products": len(load("snorlax_cards.json")["cards"]),
            "product_languages": (
                len(load("verification/units.json"))
                + len(load("verification/excluded_codecards.json"))
            ),
            "owner_adjudications": len(load("verification/owner_adjudications.json")["decisions"]),
            "finish_units": len(load("verification/finish_units.json")["units"]),
            "checklist_items": len(load("analysis_checklist.json")["items"]),
        }
        for table, count in expected.items():
            actual = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if actual != count:
                problems.append(f"{table}: expected {count}, found {actual}")
        hard_negatives = connection.execute(
            "SELECT COUNT(*) FROM product_languages "
            "WHERE application_status='not-printed' AND absence_supported=0 "
            "AND adjudication_id IS NULL"
        ).fetchone()[0]
        if hard_negatives:
            problems.append(
                f"{hard_negatives} hard negatives lack scoped source evidence or owner adjudication"
            )
        invalid_statuses = connection.execute(
            "SELECT COUNT(*) FROM product_languages WHERE "
            "(verification_status='confirmed' AND application_status<>'exists') OR "
            "(verification_status='contradicted' AND adjudication_id IS NOT NULL "
            " AND application_status<>'not-printed') OR "
            "(verification_status='contradicted' AND adjudication_id IS NULL AND absence_supported=1 "
            " AND application_status<>'not-printed') OR "
            "(verification_status='contradicted' AND adjudication_id IS NULL AND absence_supported=0 "
            " AND application_status<>'disputed') OR "
            "(verification_status IN ('pending','needs-manual-review') "
            " AND application_status<>'unresolved') OR "
            "(verification_status='out-of-scope' AND application_status<>'out-of-scope')"
        ).fetchone()[0]
        if invalid_statuses:
            problems.append(f"{invalid_statuses} product-language application statuses are inconsistent")
        owner_rows = connection.execute(
            "SELECT adjudication_id, unit_id, decision, authority, basis "
            "FROM owner_adjudications"
        ).fetchall()
        owner_decisions = load("verification/owner_adjudications.json")["decisions"]
        expected_owner_ids = {item["adjudicationId"] for item in owner_decisions}
        actual_owner_ids = {row[0] for row in owner_rows}
        if actual_owner_ids != expected_owner_ids:
            problems.append("owner adjudication ids do not match verification/owner_adjudications.json")
        raw_units = {
            item["unitId"]: item for item in load("verification/units.json")
        }
        for adjudication_id, unit_id, decision, authority, basis in owner_rows:
            raw_unit = raw_units.get(unit_id)
            if raw_unit is None:
                problems.append(f"owner adjudication {adjudication_id} references unknown unit {unit_id}")
                continue
            if raw_unit["status"] != "contradicted":
                problems.append(f"owner adjudication {adjudication_id} targets non-contradicted unit {unit_id}")
            row = connection.execute(
                "SELECT application_status, adjudication_id FROM product_languages WHERE unit_id=?",
                (unit_id,),
            ).fetchone()
            if not row or row[0] != decision or row[1] != adjudication_id:
                problems.append(f"owner adjudication {adjudication_id} is not applied to {unit_id}")
            if decision != "not-printed" or authority != "collection-owner" or basis != "multi-source-adjudication":
                problems.append(f"owner adjudication {adjudication_id} has invalid decision metadata")
        unverified_editions = connection.execute(
            "SELECT COUNT(*) FROM product_editions pe JOIN product_languages pl "
            "USING(product_id, language_code) WHERE pl.application_status<>'exists'"
        ).fetchone()[0]
        if unverified_editions:
            problems.append(f"{unverified_editions} edition rows lack an established language")
        missing_images = connection.execute("SELECT image_path FROM products").fetchall()
        for (image_path,) in missing_images:
            if not (ROOT / image_path).is_file():
                problems.append(f"database references missing product image: {image_path}")
                break
        connection.close()
        rebuilt = target.with_name(target.name + ".check")
        try:
            build_database(rebuilt)
            if sqlite_dump(target) != sqlite_dump(rebuilt):
                problems.append("database contents differ from a fresh deterministic rebuild")
        finally:
            rebuilt.unlink(missing_ok=True)
            rebuilt.with_name(rebuilt.name + ".tmp").unlink(missing_ok=True)
    except (sqlite3.Error, OSError, ValueError) as error:
        problems.append(f"cannot validate database: {error}")
    return problems


def audit_text(stats: dict[str, int | str]) -> str:
    return f"""<!-- doc: role=current-state data audit; stage=generated -->
<!-- generated by scripts/database.py; do not hand-edit -->
# Data handoff audit — current repository state

Snapshot date: **{stats['generated']}** · SQLite schema: **{SCHEMA_VERSION}** · source fingerprint:
`{str(stats['fingerprint'])[:16]}…`

## Outcome

The research stores are internally consistent, but they are not a clean application boundary on
their own: a consumer otherwise has to join product, language, edition, release, finish, source and
checklist JSON while remembering which fields are raw marketplace claims. `snoredex.sqlite` is the
normalized current-state projection. It contains no evidence journal and no migration history.

| Area | Audited current state |
|---|---:|
| Cardmarket products | {stats['products']} ({stats['collectible_products']} collectible, {stats['code_cards']} code cards) |
| Raw product-language claims | {stats['language_claims']} ({stats['language_out_of_scope']} code-card claims out of scope) |
| Repository language verdicts | {stats['language_confirmed']} confirmed · {stats['language_contradicted']} contradicted |
| App language statuses | {stats['language_not_printed']} not-printed · {stats['language_disputed']} disputed ({stats['language_owner_adjudicated']} owner-adjudicated) |
| Established product-edition rows | {stats['product_editions']} ({stats['suppressed_absent_editions']} absent-language and {stats['suppressed_unverified_editions']} unverified-language projections suppressed) |
| Finish units / logical printings | {stats['finish_units']} / {stats['printings']} |
| Physical checklist | {stats['checklist_items']} ({stats['documented_items']} documented · {stats['unresolved_items']} unresolved placeholders) |
| Release rows without row-level source | {stats['release_rows_without_source']} / {stats['release_rows']} |
| Products without established artist | {stats['missing_artists']} |
| Opaque V-token products without a physical variant name | {stats['opaque_variants']} |

## The challenged data point

The database preserves the original `repository_verdict='contradicted'` while recording the final
application decision separately. **{stats['language_owner_adjudicated']}** rows are linked to
`owner_adjudications`: the collection owner reviewed all cited claims and evidence and adopted
`application_status='not-printed'`. This is deliberately not attributed to Elite Fourum or any
other single provider. **{stats['language_source_scoped_absence']}** rows, if any, would instead be
not-printed because their source is explicitly complete within a named scope. The remaining
**{stats['language_disputed']}** rows stay `application_status='disputed'` because neither a
scoped absence source nor an owner adjudication exists.

The owner decision and its rationale are queryable in `owner_adjudications` and through the
`app_language_availability` view. The raw evidence and repository verdict remain unchanged, so a
consumer can distinguish source capability from the collection owner's final adjudication. The
Portuguese `xPRE 076` rows, for example, remain disputed because no owner adjudication exists.

## Other field decisions

- `availableItems` is volatile marketplace state. It is isolated in `product_market_state`
  with the harvest date instead of being presented as timeless card data.
- `versionsCount` is null on all 198 source rows and is omitted.
- Cardmarket's numeric image/product id is extracted into the stable `products.product_id`; all 198
  values are present and unique.
- Language codes are BCP 47 tags. Repository scope defines Cardmarket's Spanish row as European
  Spanish, so the application code is `es-ES`; Portuguese remains the source's unqualified `pt`.
- Edition rows exist only for positively established product languages. The source projection's
  {stats['suppressed_absent_editions']} rows for explicitly absent languages and
  {stats['suppressed_unverified_editions']} rows for unverified languages are recorded as quality
  issues, not exported as facts.
- Code cards remain queryable but are `out-of-scope` and never enter the physical checklist.
- Missing artists, missing date sources, opaque variants and unresolved finishes stay null or
  explicit placeholders. The database never fills them by inference.
- `quality_issues` makes every warning queryable instead of burying it in prose.

## Handoff rule

Apps should start from `app_checklist`, `app_products`, and `app_language_availability`. Collection
ownership is deliberately separate; `scripts/tracker.py` creates or refreshes a tracker with
stable `checklist_id` keys and `have` / `wanted` fields without overwriting user state.
"""


def write_audit(stats: dict[str, int | str]) -> None:
    AUDIT.write_text(audit_text(stats), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DATABASE, help="SQLite output path")
    parser.add_argument("--check", action="store_true", help="validate committed output only")
    args = parser.parse_args()
    target = args.out if args.out.is_absolute() else ROOT / args.out

    if args.check:
        problems = validate_database(target)
        if not problems:
            stats = database_stats(target)
            expected_audit = audit_text(stats)
            if not AUDIT.is_file() or AUDIT.read_text(encoding="utf-8") != expected_audit:
                problems.append("verification/DATA-HANDOFF-AUDIT.md is not current")
        if problems:
            print("handoff database check failed:", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1
        print(
            f"handoff database is current: {stats['products']} products, "
            f"{stats['checklist_items']} checklist items, fingerprint {str(stats['fingerprint'])[:12]}"
        )
        return 0

    stats = build_database(target)
    write_audit(stats)
    print(
        f"wrote {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}: "
        f"{stats['products']} products, {stats['language_claims']} language claims, "
        f"{stats['checklist_items']} checklist items"
    )
    print(f"wrote {AUDIT.relative_to(ROOT)} with {stats['quality_issues']} queryable findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())

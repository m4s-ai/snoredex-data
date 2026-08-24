#!/usr/bin/env python3
"""Create and maintain a collection tracker separate from canonical Snoredex data.

The tracker copies the app checklist from ``snoredex.sqlite`` and adds user-owned state keyed by
the stable checklist id.  ``sync`` refreshes catalogue fields, inserts new items and marks removed
items inactive without changing ``have``, ``wanted``, quantities or notes.

Examples:

    python scripts/tracker.py init
    python scripts/tracker.py set pju-no-number-japanese-none-holo have
    python scripts/tracker.py summary
    python scripts/tracker.py sync
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "snoredex.sqlite"
DEFAULT_TRACKER = ROOT / "snoredex-tracker.sqlite"
TEMPLATE = ROOT / "snoredex-tracker-template.sqlite"
TRACKER_SCHEMA_VERSION = "1.0.0"

SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = DELETE;
PRAGMA user_version = 10000;

CREATE TABLE tracker_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE catalog_items (
    checklist_id TEXT PRIMARY KEY,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    catalog_status TEXT NOT NULL CHECK (catalog_status IN ('documented', 'unresolved')),
    card_name TEXT NOT NULL,
    set_code TEXT NOT NULL,
    collector_number TEXT NOT NULL,
    set_name TEXT NOT NULL,
    language_code TEXT NOT NULL,
    language TEXT NOT NULL,
    edition TEXT NOT NULL,
    finish_family TEXT NOT NULL,
    finish TEXT NOT NULL,
    foil_pattern TEXT,
    markings_json TEXT,
    distribution_json TEXT,
    card_size TEXT NOT NULL,
    finish_verification_status TEXT NOT NULL,
    release_date TEXT NOT NULL,
    image_path TEXT,
    cardmarket_url TEXT NOT NULL
) WITHOUT ROWID;

CREATE INDEX catalog_items_browse
ON catalog_items(active, language, set_code, collector_number, checklist_id);

CREATE TABLE collection_state (
    checklist_id TEXT PRIMARY KEY REFERENCES catalog_items(checklist_id),
    have INTEGER NOT NULL DEFAULT 0 CHECK (have IN (0, 1)),
    wanted INTEGER NOT NULL DEFAULT 1 CHECK (wanted IN (0, 1)),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    notes TEXT NOT NULL DEFAULT '',
    updated_at TEXT,
    CHECK ((have = 1 AND quantity >= 1) OR (have = 0 AND quantity = 0))
) WITHOUT ROWID;

CREATE VIEW tracker AS
SELECT
    ci.*,
    cs.have,
    cs.wanted,
    cs.quantity,
    cs.notes,
    cs.updated_at,
    CASE
        WHEN cs.have = 1 THEN 'have'
        WHEN ci.catalog_status = 'unresolved' THEN 'research'
        WHEN cs.wanted = 0 THEN 'skip'
        ELSE 'need'
    END AS collection_status
FROM catalog_items ci
JOIN collection_state cs USING(checklist_id);

CREATE VIEW active_tracker AS
SELECT * FROM tracker WHERE active = 1;
"""


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def catalog_fingerprint(catalog: Path) -> str:
    if not catalog.is_file():
        raise FileNotFoundError(f"catalogue database not found: {catalog}")
    connection = sqlite3.connect(f"file:{catalog.as_posix()}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT value FROM metadata WHERE key='schema'"
        ).fetchone()
        if not row or row[0] != "snoredex-current-state":
            raise ValueError(f"{catalog} is not a Snoredex handoff database")
    finally:
        connection.close()
    return file_hash(catalog)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sqlite_dump(path: Path) -> str:
    """Return a portable logical dump for cross-platform rebuild checks."""
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return "\n".join(connection.iterdump())
    finally:
        connection.close()


def catalog_rows(catalog: Path) -> list[tuple]:
    connection = sqlite3.connect(f"file:{catalog.as_posix()}?mode=ro", uri=True)
    try:
        return connection.execute(
            """
            SELECT checklist_id, catalog_status, card_name, set_code, collector_number, set_name,
                   language_code, language, edition, finish_family, finish, foil_pattern, markings_json,
                   distribution_json, card_size, finish_verification_status, release_date,
                   image_path, cardmarket_url
            FROM app_checklist
            ORDER BY checklist_id
            """
        ).fetchall()
    finally:
        connection.close()


def one_to_one_rekeys(connection: sqlite3.Connection, rows: list[tuple]) -> list[tuple[str, str]]:
    """Match replaced checklist IDs only when the stable catalogue identity is unambiguous."""
    existing = {
        row[0] for row in connection.execute("SELECT checklist_id FROM catalog_items").fetchall()
    }
    incoming = {row[0] for row in rows}
    old_by_identity: dict[tuple, list[str]] = defaultdict(list)
    for row in connection.execute(
        """
        SELECT checklist_id, card_name, set_code, collector_number, language_code, edition,
               cardmarket_url
        FROM catalog_items
        WHERE active=1
        """
    ):
        if row[0] not in incoming:
            old_by_identity[tuple(row[1:])].append(row[0])

    new_by_identity: dict[tuple, list[str]] = defaultdict(list)
    for row in rows:
        if row[0] not in existing:
            identity = (row[2], row[3], row[4], row[6], row[8], row[18])
            new_by_identity[identity].append(row[0])

    return sorted(
        (old_ids[0], new_by_identity[identity][0])
        for identity, old_ids in old_by_identity.items()
        if len(old_ids) == 1 and len(new_by_identity.get(identity, [])) == 1
    )


def sync_database(tracker: Path, catalog: Path) -> tuple[int, int, int]:
    rows = catalog_rows(catalog)
    fingerprint = catalog_fingerprint(catalog)
    connection = sqlite3.connect(tracker)
    connection.execute("PRAGMA foreign_keys=ON")
    existing = {
        row[0] for row in connection.execute("SELECT checklist_id FROM catalog_items").fetchall()
    }
    incoming = {row[0] for row in rows}
    rekeys = one_to_one_rekeys(connection, rows)
    connection.execute("UPDATE catalog_items SET active=0")
    connection.executemany(
        """
        INSERT INTO catalog_items (
            checklist_id, active, catalog_status, card_name, set_code, collector_number, set_name,
            language_code, language, edition, finish_family, finish, foil_pattern, markings_json,
            distribution_json, card_size, finish_verification_status, release_date, image_path,
            cardmarket_url
        ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(checklist_id) DO UPDATE SET
            active=1,
            catalog_status=excluded.catalog_status,
            card_name=excluded.card_name,
            set_code=excluded.set_code,
            collector_number=excluded.collector_number,
            set_name=excluded.set_name,
            language_code=excluded.language_code,
            language=excluded.language,
            edition=excluded.edition,
            finish_family=excluded.finish_family,
            finish=excluded.finish,
            foil_pattern=excluded.foil_pattern,
            markings_json=excluded.markings_json,
            distribution_json=excluded.distribution_json,
            card_size=excluded.card_size,
            finish_verification_status=excluded.finish_verification_status,
            release_date=excluded.release_date,
            image_path=excluded.image_path,
            cardmarket_url=excluded.cardmarket_url
        """,
        rows,
    )
    connection.executemany(
        "UPDATE collection_state SET checklist_id=? WHERE checklist_id=?",
        [(new_id, old_id) for old_id, new_id in rekeys],
    )
    connection.executemany(
        "INSERT OR IGNORE INTO collection_state(checklist_id, wanted) VALUES (?, ?)",
        [(row[0], 1 if row[1] == "documented" else 0) for row in rows],
    )
    metadata = {
        "schema": "snoredex-collection-tracker",
        "schema_version": TRACKER_SCHEMA_VERSION,
        "catalog_fingerprint_sha256": fingerprint,
        "catalog_schema": "snoredex-current-state",
        "history_included": "false",
        "generator_sha256": file_hash(Path(__file__)),
    }
    connection.executemany(
        "INSERT INTO tracker_metadata VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        sorted(metadata.items()),
    )
    connection.commit()
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    connection.close()
    if integrity != "ok" or foreign_keys:
        raise ValueError(f"tracker integrity failed: {integrity}, {foreign_keys[:3]}")
    return len(incoming - existing), len(incoming & existing), len(existing - incoming)


def build_tracker(tracker: Path, catalog: Path) -> int:
    tracker.parent.mkdir(parents=True, exist_ok=True)
    temporary = tracker.with_name(tracker.name + ".tmp")
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    connection.executescript(SCHEMA)
    connection.commit()
    connection.close()
    added, _updated, _retired = sync_database(temporary, catalog)
    os.replace(temporary, tracker)
    return added


def initialize(tracker: Path, catalog: Path, force: bool) -> None:
    if not catalog.is_file():
        raise FileNotFoundError(f"catalogue database not found: {catalog}; run scripts/database.py")
    if tracker.exists() and not force:
        raise FileExistsError(f"tracker already exists: {tracker}; use sync or pass --force")
    added = build_tracker(tracker, catalog)
    print(f"initialized {tracker}: {added} items, all have=0; unresolved items are research-only")


def set_state(tracker: Path, checklist_id: str, state: str, quantity: int | None, notes: str | None):
    if not tracker.is_file():
        raise FileNotFoundError(f"tracker not found: {tracker}; run the init command")
    connection = sqlite3.connect(tracker)
    exists = connection.execute(
        "SELECT 1 FROM collection_state WHERE checklist_id=?", (checklist_id,)
    ).fetchone()
    if not exists:
        connection.close()
        raise KeyError(f"unknown checklist id: {checklist_id}")
    have = 1 if state == "have" else 0
    wanted = 0 if state == "skip" else 1
    if quantity is None:
        quantity = 1 if have else 0
    if have and quantity < 1:
        connection.close()
        raise ValueError("a have item must have quantity >= 1")
    if not have:
        quantity = 0
    connection.execute(
        """
        UPDATE collection_state
        SET have=?, wanted=?, quantity=?, notes=COALESCE(?, notes),
            updated_at=strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        WHERE checklist_id=?
        """,
        (have, wanted, quantity, notes, checklist_id),
    )
    connection.commit()
    connection.close()
    print(f"{checklist_id}: {state}, quantity={quantity}")


def summary(tracker: Path) -> None:
    if not tracker.is_file():
        raise FileNotFoundError(f"tracker not found: {tracker}; run the init command")
    connection = sqlite3.connect(tracker)
    row = connection.execute(
        """
        SELECT COUNT(*),
               SUM(collection_status='have'),
               SUM(collection_status='need'),
               SUM(collection_status='skip'),
               SUM(collection_status='research')
        FROM active_tracker
        """
    ).fetchone()
    connection.close()
    print(f"active={row[0]} have={row[1]} need={row[2]} skip={row[3]} research={row[4]}")


def check_template(template: Path, catalog: Path) -> list[str]:
    problems: list[str] = []
    if not template.is_file():
        return [f"missing tracker template: {template}"]
    try:
        connection = sqlite3.connect(f"file:{template.as_posix()}?mode=ro", uri=True)
        fingerprint = connection.execute(
            "SELECT value FROM tracker_metadata WHERE key='catalog_fingerprint_sha256'"
        ).fetchone()
        if not fingerprint or fingerprint[0] != catalog_fingerprint(catalog):
            problems.append("tracker template catalogue fingerprint is stale")
        generator = connection.execute(
            "SELECT value FROM tracker_metadata WHERE key='generator_sha256'"
        ).fetchone()
        current_generator = file_hash(Path(__file__))
        if not generator or generator[0] != current_generator:
            problems.append("tracker template was built by a different version of scripts/tracker.py")
        if connection.execute("PRAGMA user_version").fetchone()[0] != 10000:
            problems.append("tracker template PRAGMA user_version is not 10000")
        count, changed = connection.execute(
            "SELECT COUNT(*), SUM(CASE WHEN have<>0 "
            "OR wanted<>CASE WHEN catalog_status='documented' THEN 1 ELSE 0 END "
            "OR quantity<>0 OR notes<>'' OR updated_at IS NOT NULL THEN 1 ELSE 0 END) "
            "FROM collection_state JOIN catalog_items USING(checklist_id)"
        ).fetchone()
        expected_count = len(catalog_rows(catalog))
        if count != expected_count:
            problems.append(f"tracker template expected {expected_count} states, found {count}")
        if changed:
            problems.append(f"tracker template contains {changed} non-default personal states")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            problems.append("tracker template integrity check failed")
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_keys:
            problems.append(f"tracker template foreign key errors: {foreign_keys[:3]}")
        connection.close()
        rebuilt = template.with_name(template.name + ".check")
        try:
            build_tracker(rebuilt, catalog)
            if sqlite_dump(template) != sqlite_dump(rebuilt):
                problems.append("tracker template contents differ from a fresh deterministic rebuild")
        finally:
            rebuilt.unlink(missing_ok=True)
            rebuilt.with_name(rebuilt.name + ".tmp").unlink(missing_ok=True)
    except (sqlite3.Error, OSError, ValueError) as error:
        problems.append(str(error))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG, help="Snoredex catalogue database")
    parser.add_argument("--tracker", type=Path, default=DEFAULT_TRACKER, help="tracker database")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a tracker with default have=0")
    init_parser.add_argument("--force", action="store_true", help="replace the exact tracker path")

    subparsers.add_parser("sync", help="refresh catalogue rows without changing collection state")

    set_parser = subparsers.add_parser("set", help="set have / need / skip for one checklist id")
    set_parser.add_argument("checklist_id")
    set_parser.add_argument("state", choices=["have", "need", "skip"])
    set_parser.add_argument("--quantity", type=int)
    set_parser.add_argument("--notes")

    subparsers.add_parser("summary", help="show collection counts")
    subparsers.add_parser("check-template", help="validate the committed blank tracker template")

    args = parser.parse_args()
    catalog = resolve(args.catalog)
    tracker = resolve(args.tracker)

    try:
        if args.command == "init":
            initialize(tracker, catalog, args.force)
        elif args.command == "sync":
            added, updated, retired = sync_database(tracker, catalog)
            print(f"synced {tracker}: added={added} retained={updated} retired={retired}")
        elif args.command == "set":
            set_state(tracker, args.checklist_id, args.state, args.quantity, args.notes)
        elif args.command == "summary":
            summary(tracker)
        elif args.command == "check-template":
            template = tracker if args.tracker != DEFAULT_TRACKER else TEMPLATE
            problems = check_template(template, catalog)
            if problems:
                for problem in problems:
                    print(f"tracker template check failed: {problem}", file=sys.stderr)
                return 1
            count = len(catalog_rows(catalog))
            print(f"tracker template is current: {template.name}, {count} blank collection states")
    except (FileNotFoundError, FileExistsError, KeyError, ValueError, sqlite3.Error) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

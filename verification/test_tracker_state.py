#!/usr/bin/env python3
"""Regression test for preserving tracker state across one-to-one checklist ID changes."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import tracker  # noqa: E402


def write_catalog(path: Path, rows: list[tuple]) -> None:
    path.unlink(missing_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO metadata VALUES ('schema', 'snoredex-current-state');
        CREATE TABLE app_checklist (
            checklist_id TEXT PRIMARY KEY,
            catalog_status TEXT NOT NULL,
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
            release_date TEXT,
            image_path TEXT,
            cardmarket_url TEXT NOT NULL
        );
        """
    )
    connection.executemany(
        "INSERT INTO app_checklist VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    connection.commit()
    connection.close()


def item(
    checklist_id: str, number: str, finish: str = "unresolved",
    release_date: str | None = "1999-06-16",
) -> tuple:
    return (
        checklist_id, "unresolved" if finish == "unresolved" else "documented", "Snorlax",
        "JU", number, "Jungle", "NL", "Dutch", "Unlimited", finish, finish, None,
        None, None, "unknown" if finish == "unresolved" else "standard",
        "pending" if finish == "unresolved" else "confirmed", release_date, None,
        f"https://www.cardmarket.com/ju/{number}",
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        catalog = root / "catalog.sqlite"
        personal = root / "tracker.sqlite"
        old_id = "ju-11-dutch-unl-unresolved-unknown"
        ambiguous_id = "ju-27-dutch-unl-unresolved-unknown"
        write_catalog(catalog, [item(old_id, "11", release_date=None), item(ambiguous_id, "27")])
        tracker.build_tracker(personal, catalog)

        connection = sqlite3.connect(personal)
        connection.execute(
            "UPDATE collection_state SET have=1, wanted=1, quantity=2, notes='kept', "
            "updated_at='2026-08-24T10:00:00Z' WHERE checklist_id=?",
            (old_id,),
        )
        connection.execute(
            "UPDATE collection_state SET have=1, wanted=1, quantity=1, notes='ambiguous' "
            "WHERE checklist_id=?",
            (ambiguous_id,),
        )
        connection.commit()
        connection.close()

        new_id = "ju-11-dutch-unl-holo"
        write_catalog(catalog, [
            item(new_id, "11", "holo"),
            item("ju-27-dutch-unl-non-holo", "27", "non-holo"),
            item("ju-27-dutch-unl-holo", "27", "holo"),
        ])
        tracker.sync_database(personal, catalog)

        connection = sqlite3.connect(personal)
        assert connection.execute(
            "SELECT have, wanted, quantity, notes, updated_at FROM collection_state "
            "WHERE checklist_id=?", (new_id,),
        ).fetchone() == (1, 1, 2, "kept", "2026-08-24T10:00:00Z")
        assert connection.execute(
            "SELECT active FROM catalog_items WHERE checklist_id=?", (old_id,),
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT have, quantity, notes FROM collection_state WHERE checklist_id=?",
            (ambiguous_id,),
        ).fetchone() == (1, 1, "ambiguous")
        assert connection.execute(
            "SELECT COUNT(*) FROM collection_state WHERE checklist_id LIKE 'ju-27-dutch-unl-%' "
            "AND checklist_id<>? AND have=0 AND quantity=0", (ambiguous_id,),
        ).fetchone() == (2,)
        connection.execute(
            "UPDATE collection_state SET quantity=3, notes='latest', "
            "updated_at='2026-08-24T11:00:00Z' WHERE checklist_id=?",
            (new_id,),
        )
        connection.commit()
        connection.close()

        write_catalog(catalog, [
            item(old_id, "11"),
            item("ju-27-dutch-unl-non-holo", "27", "non-holo"),
            item("ju-27-dutch-unl-holo", "27", "holo"),
        ])
        tracker.sync_database(personal, catalog)

        connection = sqlite3.connect(personal)
        assert connection.execute(
            "SELECT have, wanted, quantity, notes, updated_at FROM collection_state "
            "WHERE checklist_id=?", (old_id,),
        ).fetchone() == (1, 1, 3, "latest", "2026-08-24T11:00:00Z")
        connection.execute(
            "INSERT INTO collection_state(checklist_id, wanted) VALUES (?, 0)",
            (new_id,),
        )
        connection.execute(
            "UPDATE collection_state SET quantity=4, notes='newest', "
            "updated_at='2026-08-24T12:00:00Z' WHERE checklist_id=?",
            (old_id,),
        )
        connection.commit()
        connection.close()

        write_catalog(catalog, [
            item(new_id, "11", "holo"),
            item("ju-27-dutch-unl-non-holo", "27", "non-holo"),
            item("ju-27-dutch-unl-holo", "27", "holo"),
        ])
        tracker.sync_database(personal, catalog)

        connection = sqlite3.connect(personal)
        assert connection.execute(
            "SELECT have, wanted, quantity, notes, updated_at FROM collection_state "
            "WHERE checklist_id=?", (new_id,),
        ).fetchone() == (1, 1, 4, "newest", "2026-08-24T12:00:00Z")
        assert connection.execute(
            "SELECT COUNT(*) FROM collection_state WHERE checklist_id=?", (old_id,),
        ).fetchone() == (0,)
        connection.close()

    print("tracker one-to-one state rekey regression passed")


if __name__ == "__main__":
    main()

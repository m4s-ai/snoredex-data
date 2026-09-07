#!/usr/bin/env python3
"""Regression test for preserving tracker state across one-to-one checklist ID changes."""

from __future__ import annotations

import sqlite3
import json
from contextlib import closing
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import tracker  # noqa: E402
import checklist  # noqa: E402


def collector_compatibility_regression(root: Path) -> None:
    """Provider evidence, marketplace, owner candidate and open research stay distinct."""
    graph = json.loads((ROOT / "verification/authoritative_graph.json").read_text(encoding="utf-8"))
    legacy = json.loads((ROOT / "analysis_checklist.json").read_text(encoding="utf-8"))["items"]
    collector = json.loads((ROOT / "collector_catalogue.json").read_text(encoding="utf-8"))["items"]
    before = [row["checklistId"] for row in legacy]
    checklist.apply_collector_contract(legacy, graph)
    assert before == [row["checklistId"] for row in legacy]
    with closing(sqlite3.connect(f"file:{(ROOT / 'snoredex.sqlite').as_posix()}?mode=ro", uri=True)) as connection:
        sql_states = {row[0]: row[1:] for row in connection.execute(
            "SELECT checklist_id, item_kind, progress_class, catalog_status FROM app_checklist")}
    by_legacy = {cid: row for row in collector for cid in row["legacyChecklistIds"]}
    for row in legacy:
        counterpart = by_legacy[row["checklistId"]]
        assert (row["itemKind"], row["progressClass"]) == (
            counterpart["itemKind"], counterpart["progressClass"])
        assert row["physicalPrintingId"] == counterpart["physicalPrintingId"]
        assert sql_states[row["checklistId"]] == (
            row["itemKind"], row["progressClass"], row["catalogStatus"])
    matrix = [next(row for row in legacy if row["finishVerificationStatus"] == status)
              for status in ("confirmed", "marketplace-claimed", "owner-attested", "pending")]
    assert [row["itemKind"] for row in matrix] == [
        "verified-printing", "finish-candidate", "finish-candidate", "research-placeholder"]
    assert all(row["establishingClaimId"] for row in matrix[:3])
    assert matrix[3]["printingId"] is None
    catalog, personal = root / "matrix.sqlite", root / "matrix-tracker.sqlite"
    rows = []
    for number, row in enumerate(matrix):
        values = list(item(row["checklistId"], str(number), row["finish"]))
        values[1], values[15] = row["catalogStatus"], row["finishVerificationStatus"]
        rows.append(tuple(values))
    write_catalog(catalog, rows)
    tracker.build_tracker(personal, catalog)
    with closing(sqlite3.connect(personal)) as connection, connection:
        states = dict(connection.execute("SELECT checklist_id, collection_status FROM tracker"))
        assert [states[row[0]] for row in rows] == ["need", "research", "research", "research"]
        wanted = dict(connection.execute("SELECT checklist_id, wanted FROM collection_state"))
        assert [wanted[row[0]] for row in rows] == [1, 0, 0, 0]
        connection.execute("UPDATE collection_state SET wanted=1, notes='deliberate purchase', "
                           "updated_at='2026-09-07T00:00:00Z' WHERE checklist_id=?", (rows[1][0],))
        connection.execute("UPDATE collection_state SET have=1, quantity=2, notes='owner copy' "
                           "WHERE checklist_id=?", (rows[2][0],))
        # Reproduce a pre-E/10 tracker: candidate catalogue rows were called documented.
        connection.execute("UPDATE catalog_items SET catalog_status='documented' "
                           "WHERE finish_verification_status IN ('marketplace-claimed', 'owner-attested')")
        snapshot = connection.execute("SELECT * FROM collection_state ORDER BY checklist_id").fetchall()
    tracker.sync_database(personal, catalog)
    with closing(sqlite3.connect(personal)) as connection:
        assert snapshot == connection.execute("SELECT * FROM collection_state ORDER BY checklist_id").fetchall()
        states = dict(connection.execute("SELECT checklist_id, collection_status FROM tracker"))
        assert [states[row[0]] for row in rows] == ["need", "research", "have", "research"]


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
        collector_compatibility_regression(root)
        catalog = root / "catalog.sqlite"
        personal = root / "tracker.sqlite"
        old_id = "ju-11-dutch-unl-unresolved-unknown"
        ambiguous_id = "ju-27-dutch-unl-unresolved-unknown"
        write_catalog(catalog, [item(old_id, "11"), item(ambiguous_id, "27")])

        legacy_schema = tracker.SCHEMA.replace(
            f"PRAGMA user_version = {tracker.TRACKER_USER_VERSION};",
            "PRAGMA user_version = 10000;",
        ).replace("release_date TEXT,", "release_date TEXT NOT NULL,")
        connection = sqlite3.connect(personal)
        connection.executescript(legacy_schema)
        rows = tracker.catalog_rows(catalog)
        connection.executemany(
            "INSERT INTO catalog_items VALUES (" + ",".join("?" for _ in range(20)) + ")",
            [(row[0], 1, *row[1:]) for row in rows],
        )
        connection.executemany(
            "INSERT INTO collection_state(checklist_id, wanted) VALUES (?, ?)",
            [(row[0], 1 if row[1] == "documented" else 0) for row in rows],
        )
        connection.executemany(
            "INSERT INTO tracker_metadata VALUES (?, ?)",
            [("schema", "snoredex-collection-tracker"), ("schema_version", "1.0.0")],
        )
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

        write_catalog(catalog, [
            item(old_id, "11", release_date=None),
            item(ambiguous_id, "27"),
        ])
        tracker.sync_database(personal, catalog)

        connection = sqlite3.connect(personal)
        assert next(
            row for row in connection.execute("PRAGMA table_info(catalog_items)")
            if row[1] == "release_date"
        )[3] == 0
        assert connection.execute("PRAGMA user_version").fetchone() == (
            tracker.TRACKER_USER_VERSION,
        )
        assert connection.execute(
            "SELECT value FROM tracker_metadata WHERE key='schema_version'"
        ).fetchone() == (tracker.TRACKER_SCHEMA_VERSION,)
        assert connection.execute(
            "SELECT release_date FROM catalog_items WHERE checklist_id=?", (old_id,)
        ).fetchone() == (None,)
        assert connection.execute(
            "SELECT have, wanted, quantity, notes, updated_at FROM collection_state "
            "WHERE checklist_id=?", (old_id,),
        ).fetchone() == (1, 1, 2, "kept", "2026-08-24T10:00:00Z")
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

        template = root / "template.sqlite"
        tracker.build_tracker(template, catalog)
        check_sentinel = template.with_name(template.name + ".check")
        tmp_sentinel = template.with_name(template.name + ".check.tmp")
        check_sentinel.write_bytes(b"keep tracker check")
        tmp_sentinel.write_bytes(b"keep tracker temp")
        tracker.check_template(template, catalog)
        assert check_sentinel.read_bytes() == b"keep tracker check"
        assert tmp_sentinel.read_bytes() == b"keep tracker temp"

    print("tracker state and read-only check regressions passed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Keep a personal collection tracker beside the Snoredex catalogue, keyed by item_id.

The tracker copies `app_checklist` from a built snoredex.sqlite (schema 2.x) and adds the user's
state: have, wanted, quantity, notes. `sync` refreshes catalogue fields, adds new items and marks
vanished ones inactive; it never changes the user's state. `migrate` carries state from an old
tracker keyed by checklist_id onto item_id and never writes to the old file.

    python scripts/collection.py init
    python scripts/collection.py set ITEM_ID have --quantity 2 --notes "binder 3"
    python scripts/collection.py summary
    python scripts/collection.py sync
    python scripts/collection.py migrate snoredex-tracker.sqlite
    python scripts/collection.py selftest
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "snoredex.sqlite"
TRACKER = ROOT / "snoredex-collection.sqlite"
SCHEMA = """
CREATE TABLE tracker_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE collection_state (
    item_id TEXT PRIMARY KEY REFERENCES items(item_id),
    have INTEGER NOT NULL DEFAULT 0 CHECK (have IN (0, 1)),
    wanted INTEGER NOT NULL DEFAULT 1 CHECK (wanted IN (0, 1)),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    notes TEXT NOT NULL DEFAULT '',
    updated_at TEXT,
    CHECK ((have = 1 AND quantity >= 1) OR (have = 0 AND quantity = 0))
) WITHOUT ROWID;
"""
VIEW = """
CREATE VIEW tracker AS
SELECT i.*, s.have, s.wanted, s.quantity, s.notes, s.updated_at,
       CASE WHEN s.have = 1 THEN 'have' WHEN i.progress_class = 'research' THEN 'research'
            WHEN s.wanted = 0 THEN 'skip' ELSE 'need' END AS status
FROM items i JOIN collection_state s USING (item_id);
"""
STATE = ("have", "wanted", "quantity", "notes")


def catalogue_rows(catalogue: Path) -> tuple[list, list, list, str]:
    """Everything the tracker copies from a 2.x catalogue; any other file ends in one error line."""
    try:
        with closing(sqlite3.connect(f"file:{catalogue.as_posix()}?mode=ro", uri=True)) as db:
            return read_catalogue(db)
    except sqlite3.Error as error:
        raise SystemExit(f"error: cannot use catalogue {catalogue}: {error}")


def read_catalogue(db) -> tuple[list, list, list, str]:
    version = db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
    if not version or not version[0].startswith("2."):
        raise sqlite3.DatabaseError("not a 2.x catalogue; build it with scripts/build.py")
    cursor = db.execute("SELECT * FROM app_checklist ORDER BY item_id")
    columns, rows = [row[0] for row in cursor.description], cursor.fetchall()
    seed = db.execute("SELECT item_id, wanted FROM collection_tracker_seed ORDER BY item_id").fetchall()
    fingerprint = db.execute("SELECT value FROM metadata WHERE key='catalogue_fingerprint'").fetchone()[0]
    return columns, rows, seed, fingerprint


def sync(tracker: Path, catalogue: Path, read=None) -> tuple[int, int]:
    """Refresh the catalogue copy; returns (added, retired). User state is only ever inserted."""
    columns, rows, seed, fingerprint = read or catalogue_rows(catalogue)
    db = sqlite3.connect(tracker)
    known = {row[1] for row in db.execute("PRAGMA table_info(items)")}
    if not known:
        db.execute("CREATE TABLE items (item_id TEXT PRIMARY KEY) WITHOUT ROWID")
        db.executescript(VIEW)
    for column in (c for c in columns if c not in known | {"item_id"}):
        db.execute(f'ALTER TABLE items ADD COLUMN "{column}"')
    before = {row[0] for row in db.execute("SELECT item_id FROM items")}
    updates = ", ".join(f'"{c}"=excluded."{c}"' for c in columns if c != "item_id")
    db.execute("UPDATE items SET active = 0")  # an item the catalogue no longer has stays, inactive
    db.executemany(f'INSERT INTO items ({", ".join(columns)}) VALUES ({", ".join("?" * len(columns))}) '
                   f"ON CONFLICT(item_id) DO UPDATE SET {updates}", rows)
    db.executemany("INSERT OR IGNORE INTO collection_state (item_id, wanted) VALUES (?, ?)", seed)
    db.executemany("INSERT OR REPLACE INTO tracker_metadata VALUES (?, ?)",
                   [("schema", "snoredex-collection"), ("schema_version", "2.0.0"),
                    ("catalogue_fingerprint", fingerprint)])
    db.commit()
    db.close()
    incoming = {row[columns.index("item_id")] for row in rows}
    return len(incoming - before), len(before - incoming)


def init(tracker: Path, catalogue: Path, force: bool = False) -> int:
    if tracker.exists() and not force:
        raise SystemExit(f"error: {tracker} exists; use sync, or --force to start over")
    read = catalogue_rows(catalogue)  # validated before the tracker is touched
    tracker.unlink(missing_ok=True)
    db = sqlite3.connect(tracker)
    db.executescript(SCHEMA)
    db.close()
    return sync(tracker, catalogue, read)[0]


def set_state(tracker: Path, item_id: str, state: str, quantity: int | None, notes: str | None) -> None:
    have, wanted = int(state == "have"), int(state != "skip")
    quantity = (1 if quantity is None else quantity) if have else 0
    if have and quantity < 1:
        raise SystemExit("error: a have item needs quantity >= 1")
    db = sqlite3.connect(tracker)
    changed = db.execute("UPDATE collection_state SET have=?, wanted=?, quantity=?, notes=COALESCE(?, notes), "
                         "updated_at=? WHERE item_id=?",
                         (have, wanted, quantity, notes, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                          item_id)).rowcount
    db.commit()
    db.close()
    if not changed:
        raise SystemExit(f"error: unknown item id: {item_id}")


def summary(tracker: Path) -> str:
    db = sqlite3.connect(f"file:{tracker.as_posix()}?mode=ro", uri=True)
    counts = dict(db.execute("SELECT status, COUNT(*) FROM tracker WHERE active = 1 GROUP BY status").fetchall())
    db.close()
    return "active={} have={} need={} skip={} research={}".format(
        sum(counts.values()), *(counts.get(key, 0) for key in ("have", "need", "skip", "research")))


def legacy_map(catalogue: Path) -> dict:
    db = sqlite3.connect(f"file:{catalogue.as_posix()}?mode=ro", uri=True)
    mapping = dict(db.execute("SELECT legacy_checklist_id, item_id FROM printing_legacy_ids"))
    db.close()
    return mapping


def old_defaults(source) -> dict:
    """Each old row's seeded `wanted`, as the old tracker seeded it; empty when the old file cannot say."""
    try:
        return {cid: int(progress == "current-known") for cid, progress in source.execute(
            "SELECT checklist_id, collector_progress_class FROM catalog_items")}
    except sqlite3.OperationalError:
        return {}


def placed_state(old_rows: list, mapping: dict, defaults: dict) -> tuple[dict, list]:
    """Old rows by item_id; rows with state that cannot be placed (unknown id or conflict) are problems.

    `defaults` holds each old row's untouched `wanted`; without one, wanted=0 counts as state (skip).
    """
    placed, problems = {}, []
    for checklist_id, *state in old_rows:
        item_id = mapping.get(checklist_id)
        personal = tuple(state) != (0, defaults.get(checklist_id, 1), 0, "")
        if item_id is None or placed.get(item_id, tuple(state)) != tuple(state):
            problems.append((checklist_id, item_id, tuple(state), personal))
        elif personal:
            placed[item_id] = tuple(state)
    return placed, problems


def migrate(old: Path, tracker: Path, catalogue: Path) -> int:
    """Carry state onto item_id; write nothing if any row with state cannot be placed."""
    source = sqlite3.connect(f"file:{old.as_posix()}?mode=ro", uri=True)  # never written
    old_rows = source.execute(f"SELECT checklist_id, {', '.join(STATE)} FROM collection_state "
                              "ORDER BY checklist_id").fetchall()
    defaults = old_defaults(source)
    source.close()
    db = sqlite3.connect(tracker)
    placed, problems = placed_state(old_rows, legacy_map(catalogue), defaults)
    for checklist_id, item_id, state, personal in problems:
        print(f"{'LOST' if personal else 'skipped'}: {checklist_id} -> {item_id or 'no item'} {state}")
    if any(personal for *_, personal in problems):
        db.close()
        print("migrate: nothing written; rows with personal state could not be placed")
        return 1
    db.executemany("UPDATE collection_state SET have=?, wanted=?, quantity=?, notes=? WHERE item_id=?",
                   [(*state, item_id) for item_id, state in sorted(placed.items())])
    db.commit()
    db.close()
    print(f"migrate: {len(placed)} items carried state, {len(problems)} stateless rows not placed")
    return 0


def selftest_catalogue(path: Path, items: list) -> Path:
    """A minimal 2.x catalogue: the three objects the tracker reads."""
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO metadata VALUES ('schema_version', '2.0.0'), ('catalogue_fingerprint', 'sha256:test');
        CREATE TABLE app_checklist (item_id TEXT, active INTEGER, progress_class TEXT, card_name TEXT);
        CREATE TABLE printing_legacy_ids (item_id TEXT, legacy_checklist_id TEXT);
        CREATE VIEW collection_tracker_seed AS SELECT item_id, progress_class = 'current-known' AS wanted
            FROM app_checklist;""")
    db.executemany("INSERT INTO app_checklist VALUES (?, 1, ?, 'Snorlax')", [(i, k) for i, k, _ in items])
    db.executemany("INSERT INTO printing_legacy_ids VALUES (?, ?)", [(i, legacy) for i, _, legacy in items])
    db.commit()
    db.close()
    return path


def old_catalogue(path: Path) -> Path:
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)")
    db.execute("INSERT INTO metadata VALUES ('schema_version', '1.7.0')")
    db.commit()
    db.close()
    return path


def refused(call) -> bool:
    try:
        call()
    except SystemExit as stop:
        return isinstance(stop.code, str) and stop.code.startswith("error:")
    return False


def selftest_tracker(tmp: Path) -> Path:
    """init refuses a bad catalogue without leaving a file; set and sync keep state."""
    catalogue = selftest_catalogue(tmp / "a.sqlite", [("i1", "current-known", "c1"), ("i2", "research", "c2")])
    tracker = tmp / "t.sqlite"
    for bad in (tmp / "missing.sqlite", old_catalogue(tmp / "v1.sqlite")):
        assert refused(lambda: init(tracker, bad)) and not tracker.exists(), bad
    assert init(tracker, catalogue) == 2
    set_state(tracker, "i1", "have", 2, "binder")
    assert sync(tracker, selftest_catalogue(tmp / "b.sqlite", [("i1", "current-known", "c1"),
                                                               ("i3", "current-known", "c3")])) == (1, 1)
    assert summary(tracker) == "active=2 have=1 need=1 skip=0 research=0", summary(tracker)
    db = sqlite3.connect(tracker)
    assert db.execute("SELECT have, quantity, notes FROM collection_state WHERE item_id='i1'").fetchone() == (
        1, 2, "binder")
    assert db.execute("SELECT active FROM items WHERE item_id='i2'").fetchone() == (0,)
    db.close()
    return tracker


def selftest_migrate(tmp: Path, tracker: Path) -> None:
    """migrate carries state, skips untouched rows, refuses lost state; a failed init --force keeps all."""
    old = tmp / "old.sqlite"
    db = sqlite3.connect(old)
    db.execute("CREATE TABLE collection_state (checklist_id TEXT, have, wanted, quantity, notes)")
    db.execute("CREATE TABLE catalog_items (checklist_id TEXT, collector_progress_class TEXT)")
    db.executemany("INSERT INTO collection_state VALUES (?, ?, ?, ?, ?)",
                   [("c3", 1, 1, 1, "old"), ("gone", 0, 1, 0, ""), ("retired", 0, 0, 0, "")])
    db.executemany("INSERT INTO catalog_items VALUES (?, ?)", [("c3", "current-known"), ("retired", "research"),
                                                               ("lost", "research")])
    db.commit()
    db.close()
    assert migrate(old, tracker, tmp / "b.sqlite") == 0  # an untouched retired research row is no state
    db = sqlite3.connect(tracker)
    assert db.execute("SELECT have, notes FROM collection_state WHERE item_id='i3'").fetchone() == (1, "old")
    db.close()
    db = sqlite3.connect(old)
    db.execute("INSERT INTO collection_state VALUES ('lost', 1, 1, 1, 'keep me')")
    db.commit()
    db.close()
    assert migrate(old, tracker, tmp / "b.sqlite") == 1  # a retired row with state stops it
    assert refused(lambda: init(tracker, tmp / "v1.sqlite", force=True))  # a failed --force keeps the tracker
    assert summary(tracker) == "active=2 have=2 need=0 skip=0 research=0", summary(tracker)


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        selftest_migrate(tmp, selftest_tracker(tmp))
    print("collection selftest ok: init refusals, set, sync (one item added, one retired), migrate, "
          "lost-state refusal, failed init --force keeps the tracker")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tracker", type=Path, default=TRACKER)
    parser.add_argument("--catalogue", type=Path, default=CATALOGUE)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init").add_argument("--force", action="store_true")
    setter = commands.add_parser("set")
    setter.add_argument("item_id")
    setter.add_argument("state", choices=["have", "need", "skip"])
    setter.add_argument("--quantity", type=int)
    setter.add_argument("--notes")
    for name in ("summary", "sync", "selftest"):
        commands.add_parser(name)
    commands.add_parser("migrate").add_argument("old_tracker", type=Path)
    args = parser.parse_args()
    return run(args)


def run(args) -> int:
    if args.command == "selftest":
        return selftest()
    if args.command != "init" and not args.tracker.is_file():  # never create a stub tracker
        raise SystemExit(f"error: no tracker at {args.tracker}; run init first")
    if args.command == "init":
        print(f"{args.tracker}: {init(args.tracker, args.catalogue, args.force)} items")
    elif args.command == "set":
        set_state(args.tracker, args.item_id, args.state, args.quantity, args.notes)
    elif args.command == "sync":
        print("added={} retired={}".format(*sync(args.tracker, args.catalogue)))
    elif args.command == "migrate":
        return migrate(args.old_tracker, args.tracker, args.catalogue)
    print(summary(args.tracker))
    return 0


if __name__ == "__main__":
    sys.exit(main())

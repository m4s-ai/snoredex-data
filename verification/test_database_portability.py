#!/usr/bin/env python3
"""Regression test for platform-neutral database input fingerprints."""

from __future__ import annotations

import sys
import tempfile
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import database  # noqa: E402


def main() -> None:
    original_root = database.ROOT
    original_inputs = database.INPUTS
    try:
        with tempfile.TemporaryDirectory() as directory:
            database.ROOT = Path(directory)
            database.INPUTS = ["input.json"]
            path = database.ROOT / "input.json"

            path.write_bytes(b'{\n  "status": "exists"\n}\n')
            lf_fingerprint = database.source_fingerprint()
            lf_hashes = database.input_hashes()

            path.write_bytes(b'{\r\n  "status": "exists"\r\n}\r\n')
            assert database.source_fingerprint() == lf_fingerprint
            assert database.input_hashes() == lf_hashes
    finally:
        database.ROOT = original_root
        database.INPUTS = original_inputs

    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "handoff.sqlite"
        shutil.copy2(ROOT / "snoredex.sqlite", target)
        check_sentinel = target.with_name(target.name + ".check")
        tmp_sentinel = target.with_name(target.name + ".check.tmp")
        check_sentinel.write_bytes(b"keep database check")
        tmp_sentinel.write_bytes(b"keep database temp")
        assert not database.validate_database(target)
        with closing(sqlite3.connect(target)) as connection:
            assert connection.execute("PRAGMA user_version").fetchone() == (10007,)
            assert connection.execute(
                "SELECT value FROM metadata WHERE key='schema_version'"
            ).fetchone() == ("1.7.0",)
            connection.execute("PRAGMA user_version=10006")
        assert "database PRAGMA user_version is not 10007" in database.validate_database(target)
        assert check_sentinel.read_bytes() == b"keep database check"
        assert tmp_sentinel.read_bytes() == b"keep database temp"

    print("database fingerprint portability and read-only check regressions passed")


if __name__ == "__main__":
    main()

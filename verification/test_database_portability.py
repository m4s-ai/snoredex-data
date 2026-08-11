#!/usr/bin/env python3
"""Regression test for platform-neutral database input fingerprints."""

from __future__ import annotations

import sys
import tempfile
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

    print("database fingerprint portability regression passed")


if __name__ == "__main__":
    main()

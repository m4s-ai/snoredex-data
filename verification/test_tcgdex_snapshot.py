#!/usr/bin/env python3
"""Regression checks for the versioned, offline TCGdex finish input."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "verification" / "finish_tcgdex_snapshot.json"
UNITS = ROOT / "verification" / "units.json"


def load_finishes():
    spec = importlib.util.spec_from_file_location("finishes", ROOT / "scripts" / "finishes.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    finishes = load_finishes()
    document = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    records = document.get("records", {})
    expected = {
        row["sourceUrl"] for row in json.loads(UNITS.read_text(encoding="utf-8"))
        if row.get("status") == "confirmed"
        and str(row.get("sourceUrl") or "").startswith("https://api.tcgdex.net/")
    }
    assert document.get("schema") == "snoredex-tcgdex-snapshot/1"
    assert set(records) == expected
    assert all(finishes.json_hash(row["payload"]) == row["contentHash"]
               and finishes.implausible(row["payload"]) is None
               for row in records.values())
    url = sorted(records)[0]
    fetched_url, payload, error = finishes.fetch_tcgdex(url, offline=True)
    assert (fetched_url, error) == (url, None)
    assert payload == records[url]["payload"]
    assert finishes.snapshot_drift(
        {"same": {"contentHash": "sha256:a"}, "removed": {"contentHash": "sha256:b"}},
        {"same": {"contentHash": "sha256:c"}, "added": {"contentHash": "sha256:d"}},
    ) == (["same"], ["added"], ["removed"])
    candidate_path = ROOT / ".tcgdex-refresh-candidate-test.json"
    original_candidate_path = finishes.REFRESH_CANDIDATE_PATH
    original_cache_dir = finishes.CACHE_DIR
    finishes.REFRESH_CANDIDATE_PATH = candidate_path
    # Keep the refresh-candidate regression out of the production fetch cache.  The release
    # gate deliberately rejects cache directories left behind by any test or generator.
    finishes.CACHE_DIR = candidate_path.parent
    try:
        staged = {"https://api.tcgdex.net/test": {
            "contentHash": finishes.json_hash({"id": "test-card"}),
            "payload": {"id": "test-card"},
        }}
        finishes.write_refresh_candidate(staged)
        assert finishes.load_refresh_candidate(set(staged)) == staged
        candidate_path.write_text(candidate_path.read_text(encoding="utf-8")
                                  .replace("test-card", "tampered"), encoding="utf-8")
        try:
            finishes.load_refresh_candidate(set(staged))
        except ValueError:
            pass
        else:
            raise AssertionError("tampered refresh candidate must fail closed")
    finally:
        finishes.REFRESH_CANDIDATE_PATH = original_candidate_path
        finishes.CACHE_DIR = original_cache_dir
        candidate_path.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        temporary_root = Path(temporary)
        snapshot_path = temporary_root / "snapshot.json"
        candidate_path = temporary_root / "candidate.json"
        old_snapshot = {
            "schema": "snoredex-tcgdex-snapshot/1",
            "generated": "2026-08-01",
            "records": staged,
        }
        snapshot_path.write_text(json.dumps(old_snapshot), encoding="utf-8")
        original_snapshot_path = finishes.SNAPSHOT_PATH
        original_candidate_path = finishes.REFRESH_CANDIDATE_PATH
        original_arguments = sys.argv
        finishes.SNAPSHOT_PATH = snapshot_path
        finishes.REFRESH_CANDIDATE_PATH = candidate_path
        try:
            finishes.write_refresh_candidate(staged)
            sys.argv = ["finishes.py", "--refresh", "--accept-refresh"]
            context = {"tcgdex_urls": sorted(staged), "snapshot_document": old_snapshot}
            assert finishes._resolve_tcgdex(context) is None
            accepted = json.loads(snapshot_path.read_text(encoding="utf-8"))
            assert context["snapshot_document"] == accepted
        finally:
            finishes.SNAPSHOT_PATH = original_snapshot_path
            finishes.REFRESH_CANDIDATE_PATH = original_candidate_path
            sys.argv = original_arguments
    print(f"tcgdex snapshot regression passed: {len(records)} hashed records, offline")


if __name__ == "__main__":
    main()

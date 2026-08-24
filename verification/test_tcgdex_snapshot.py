#!/usr/bin/env python3
"""Regression checks for the versioned, offline TCGdex finish input."""

from __future__ import annotations

import importlib.util
import json
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
    print(f"tcgdex snapshot regression passed: {len(records)} hashed records, offline")


if __name__ == "__main__":
    main()

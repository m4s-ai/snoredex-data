#!/usr/bin/env python3
"""Ensure retired migration projections are absent from the live tree."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = "verification/test_retired_projections.py"
RETIRED_PATHS = {
    "scripts/print_identity_dryrun.py",
    "scripts/set_catalogue_dryrun.py",
    "scripts/legacy_set_reconciliation.py",
    "verification/print_identity_dryrun.json",
    "verification/set_catalogue_dryrun.json",
    "verification/legacy_set_reconciliation.json",
    "analysis_confirmed_releases_reconciled.json",
    "analysis_confirmed_releases_reconciled.csv",
}
RETIRED_TOKENS = {path.rsplit("/", 1)[-1] for path in RETIRED_PATHS}


def tracked_paths() -> list[str]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [item.decode("utf-8") for item in output.split(b"\0") if item]


def main() -> None:
    paths = tracked_paths()
    assert not RETIRED_PATHS.intersection(paths)
    hits: list[str] = []
    for relative in paths:
        if relative == SELF or relative.startswith(("verification/archive/", "verification/history/")):
            continue
        path = ROOT / relative
        if path.suffix.lower() not in {".md", ".py", ".json", ".yml", ".yaml", ".toml", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(token in text for token in RETIRED_TOKENS):
            hits.append(relative)
    assert not hits, f"live references to retired projections: {hits}"
    print("retired projection grep passed")


if __name__ == "__main__":
    main()

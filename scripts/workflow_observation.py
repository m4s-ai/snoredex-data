"""Shared, content-based observation of workflow working-tree changes."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path, PurePosixPath
from typing import Mapping


SQLITE_SUFFIX = ".sqlite"
MISSING_DIGEST = "missing"


def _git_output(root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", "--no-optional-locks", "-c", "diff.autoRefreshIndex=false", *args],
        cwd=root, text=True, encoding="utf-8",
        stdout=subprocess.PIPE, check=True,
    )
    return [record for record in result.stdout.split("\0") if record]


def _normalise(paths: list[str]) -> set[str]:
    return {
        path.replace("\\", "/")
        for path in paths
        if not path.replace("\\", "/").endswith(SQLITE_SUFFIX)
    }


def tree_paths(root: Path) -> set[str]:
    """Return dirty non-SQLite paths from staged, unstaged, and untracked state."""
    # Numstat reads contents even on Git versions that list stat-only name changes.
    staged = _git_output(root, "diff", "--cached", "--numstat", "--no-renames", "-z", "--", ".")
    unstaged = _git_output(root, "diff", "--numstat", "--no-renames", "-z", "--", ".")
    untracked = _git_output(root, "ls-files", "--others", "--exclude-standard", "-z")
    return _normalise([record.split("\t", 2)[2] for record in staged + unstaged] + untracked)


def tree_snapshot(root: Path, *, paths: list[str] | None = None) -> dict[str, str]:
    """Hash explicit paths, or the workflow's dirty paths, excluding SQLite bytes."""
    snapshot: dict[str, str] = {}
    for relative in tree_paths(root) if paths is None else _normalise(paths):
        path = root / PurePosixPath(relative)
        try:
            snapshot[relative] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        except FileNotFoundError:
            # A tracked file can be removed by a workflow. Keep that deletion observable.
            snapshot[relative] = MISSING_DIGEST
    return snapshot


def changed_paths(before: Mapping[str, str], after: Mapping[str, str]) -> set[str]:
    """Return paths whose content digest changed between two observations."""
    return {
        path for path in set(before) | set(after) if before.get(path) != after.get(path)
    }

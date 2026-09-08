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
        ["git", *args], cwd=root, check=True, text=True, encoding="utf-8",
        stdout=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line]


def _normalise(paths: list[str]) -> set[str]:
    return {
        path.replace("\\", "/")
        for path in paths
        if not path.replace("\\", "/").endswith(SQLITE_SUFFIX)
    }


def tree_paths(root: Path) -> set[str]:
    """Return dirty non-SQLite paths from staged, unstaged, and untracked state."""
    staged = _git_output(root, "diff", "--cached", "--name-only", "--", ".")
    unstaged = _git_output(root, "diff", "--name-only", "--", ".")
    untracked = _git_output(root, "ls-files", "--others", "--exclude-standard")
    return _normalise(staged + unstaged + untracked)


def tree_snapshot(root: Path) -> dict[str, str]:
    """Hash the current bytes of every dirty path, including pre-existing dirty files."""
    snapshot: dict[str, str] = {}
    for relative in tree_paths(root):
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

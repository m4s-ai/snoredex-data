#!/usr/bin/env python3
"""Regression checks for portable workflow-runtime diagnostics."""
from __future__ import annotations

import sys
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.measure_workflow import (  # noqa: E402
    display_command,
    display_paths,
    pages_specs,
    redact_runtime_paths,
)
from scripts.workflow_observation import changed_paths, tree_snapshot  # noqa: E402


def main() -> int:
    temp = f"{ROOT}\\_site-measure-ci-r4nd0m"
    command = display_command(["scripts/publish.py", "--out", temp])
    assert command == "scripts/publish.py --out <tempdir>", command
    output = redact_runtime_paths(f"assembled files into {temp}")
    assert output == "assembled files into <tempdir>", output
    paths = display_paths({f"_site-measure-ci-r4nd0m/file.txt", "scripts/measure_workflow.py"})
    assert paths == ["<tempdir>/file.txt", "scripts/measure_workflow.py"], paths
    assert str(ROOT) not in command
    assert "r4nd0m" not in output

    fixture_root = ROOT / "verification" / "cache"
    fixture_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=fixture_root) as raw_root:
        repo = Path(raw_root)

        def git(*args: str) -> None:
            subprocess.run(
                ["git", *args], cwd=repo, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )

        git("init", "--quiet")
        git("config", "user.email", "workflow-test.invalid")
        git("config", "user.name", "workflow-test")
        (repo / "tracked.txt").write_text("base", encoding="utf-8")
        (repo / "ignored.sqlite").write_bytes(b"base")
        git("add", ".")
        git("commit", "--quiet", "-m", "base")

        # A pre-existing unstaged edit must still be observed when the measured step edits it.
        (repo / "tracked.txt").write_text("dirty before", encoding="utf-8")
        before = tree_snapshot(repo)
        (repo / "tracked.txt").write_text("dirty after", encoding="utf-8")
        (repo / "new.txt").write_text("created", encoding="utf-8")
        after = tree_snapshot(repo)
        assert "tracked.txt" in changed_paths(before, after)
        assert "new.txt" in changed_paths(before, after)
        assert "ignored.sqlite" not in before and "ignored.sqlite" not in after

        # Staged paths are part of the same observed tree and are compared by bytes, not status.
        (repo / "staged.txt").write_text("staged before", encoding="utf-8")
        git("add", "staged.txt")
        before = tree_snapshot(repo)
        (repo / "staged.txt").write_text("staged after", encoding="utf-8")
        assert "staged.txt" in changed_paths(before, tree_snapshot(repo))

    specs = pages_specs(ROOT / "_site-measure-pages-test")
    commands = [" ".join(spec["args"]) for spec in specs]
    assert len(specs) == 5
    assert all("finishes.py" not in command and "site.py" not in command for command in commands)
    assert any("scripts/publish.py --out" in command for command in commands)
    assert any("verification/publication_gate.py" in command for command in commands)
    print("workflow measurement path-redaction regression passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

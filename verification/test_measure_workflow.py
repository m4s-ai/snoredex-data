#!/usr/bin/env python3
"""Regression checks for portable workflow-runtime diagnostics."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.measure_workflow import display_command, display_paths, redact_runtime_paths  # noqa: E402


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
    print("workflow measurement path-redaction regression passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

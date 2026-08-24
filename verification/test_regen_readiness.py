"""regen.py readiness: a stale artifact must make --check fail.

Regression for #213: the whole point of the single command is that a stale
derived artifact is caught before merge, not after three CI restarts. This test
stales a regenerated artifact, asserts `regen.py --check` exits non-zero, then
restores it.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGEN = pathlib.Path("scripts/regen.py")
# Two small deterministic artifacts make the aggregation guarantee observable without
# touching SQLite or depending on a network response.
TARGETS = [
    (ROOT / "verification" / "evidence_semantics.json",
     b'"units": ', b'"units": 999999, "stale": '),
    (ROOT / "verification" / "authoritative_graph.json",
     b'"schemaVersion": "1.1.0"', b'"schemaVersion": "0.0.0"'),
]


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8",
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def main() -> int:
    if not all(path.is_file() for path, _, _ in TARGETS):
        print("SKIP: a readiness target is missing")
        return 0

    originals = [(path, path.read_bytes()) for path, _, _ in TARGETS]
    try:
        for (path, marker, replacement), (_, original) in zip(TARGETS, originals):
            corrupted = original.replace(marker, replacement, 1)
            if corrupted == original:
                print(f"SKIP: could not find marker in {path}")
                return 0
            path.write_bytes(corrupted)
        proc = run([sys.executable, str(REGEN), "--check"])
        expected_header = "FAILED determinism checks:"
        expected_commands = (
            "scripts/evidence_semantics.py --check",
            "scripts/authoritative_graph.py --check",
        )
        if proc.returncode == 0 or expected_header not in proc.stdout \
                or any(command not in proc.stdout for command in expected_commands):
            print("FAIL: regen.py --check did not identify all stale artifacts")
            print(proc.stdout)
            return 1
        print(f"OK: regen.py --check rejected both stale artifacts (exit {proc.returncode})")
        return 0
    finally:
        for path, original in originals:
            path.write_bytes(original)


if __name__ == "__main__":
    sys.exit(main())

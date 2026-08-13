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
# A small, deterministic artifact regen.py --check verifies and that is cheap to
# corrupt and restore: tracker's catalogue fingerprint is a build artifact, but
# simplest is a generated JSON meta field. Use evidence_semantics.json's keystone
# count — touching it must fail the determinism step.
TARGET = ROOT / "verification" / "evidence_semantics.json"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8",
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def main() -> int:
    if not TARGET.is_file():
        print(f"SKIP: {TARGET} missing")
        return 0

    original = TARGET.read_bytes()
    try:
        # Corrupt the committed artifact: bump the units count so the --check
        # determinism step must notice the committed file differs from a fresh
        # regeneration.
        corrupted = original.replace(b'"units": ', b'"units": 999999, "stale": ', 1)
        if corrupted == original:
            print("SKIP: could not find marker to corrupt")
            return 0
        TARGET.write_bytes(corrupted)
        proc = run([sys.executable, str(REGEN), "--check"])
        expected = "FAILED determinism scripts/evidence_semantics.py --check"
        if proc.returncode == 0 or expected not in proc.stdout:
            print("FAIL: regen.py --check did not identify the stale artifact")
            print(proc.stdout)
            return 1
        print(f"OK: regen.py --check rejected stale artifact (exit {proc.returncode})")
        return 0
    finally:
        TARGET.write_bytes(original)


if __name__ == "__main__":
    sys.exit(main())

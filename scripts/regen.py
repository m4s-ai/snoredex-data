#!/usr/bin/env python3
"""The one gate: build the outputs from data/, then check the model, the code and the publication boundary.

    python scripts/regen.py          # write the outputs with build.py, then run every --check step
    python scripts/regen.py --check  # observational: every check, build.py --check included (what CI calls)

Exit code is non-zero when any step fails. The browser suite (verification/test_site.py) and the
Pages artifact steps (publish.py, gate_manifest.py, publication_gate.py) stay in the workflows.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = (
    ("scripts/check.py",),
    ("scripts/check.py", "--selftest"),
    ("scripts/collection.py", "selftest"),
    ("scripts/build.py", "--check"),
    ("verification/test_complexity.py",),
    ("verification/test_sensitive_scan.py",),
    ("verification/test_gate_handoff.py",),
    ("verification/test_links.py",),
    ("verification/publication_audit.py",),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="write nothing; fail if an output is stale")
    args = parser.parse_args()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GIT_OPTIONAL_LOCKS": "0"}
    # Write mode builds first, then runs exactly the --check steps, so the delivery command itself
    # proves that an immediate second `regen.py --check` is clean.
    for step in STEPS if args.check else (("scripts/build.py",), *STEPS):
        command = list(step)
        print(f"=== {' '.join(command)}", flush=True)
        if subprocess.run([sys.executable, *command], cwd=ROOT, env=env).returncode:
            print(f"regen.py: FAILED at {' '.join(command)}")
            return 1
    print("regen.py: OK. Outputs current, model and code checks pass, publication boundary clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

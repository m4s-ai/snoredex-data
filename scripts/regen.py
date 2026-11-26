#!/usr/bin/env python3
"""The one gate: build the outputs from data/, then check the model, the code and the publication boundary.

    python scripts/regen.py          # write the outputs with build.py, then run every check
    python scripts/regen.py --check  # observational: build.py --check instead of writing (what CI calls)
    python scripts/regen.py --photos DIR  # its model check also verifies the photo archive (intake, #677)

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
    ("scripts/build.py",),  # --check is appended under --check
    ("verification/test_build_summary.py",),
    ("verification/test_owner_photo.py",),
    ("verification/test_yourls.py",),
    ("verification/test_complexity.py",),
    ("verification/test_gallery_workflow.py",),
    ("verification/test_sensitive_scan.py",),
    ("verification/test_gate_handoff.py",),
    ("verification/test_inbox_ci.py",),
    ("verification/test_links.py",),
    ("verification/publication_audit.py",),
)


def step_command(step: tuple, check: bool, photos: Path | None) -> list[str]:
    """One step as it runs: build.py observational under --check, the model check with the archive."""
    if check and step == ("scripts/build.py",):
        return [*step, "--check"]
    if photos and step == ("scripts/check.py",):
        return [*step, "--photos", str(photos)]
    return list(step)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="write nothing; fail if an output is stale")
    parser.add_argument("--photos", type=Path, metavar="DIR", help="also verify the originals in a photo checkout")
    args = parser.parse_args()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GIT_OPTIONAL_LOCKS": "0"}
    for step in STEPS:
        command = step_command(step, args.check, args.photos)
        print(f"=== {' '.join(command)}", flush=True)
        if subprocess.run([sys.executable, *command], cwd=ROOT, env=env).returncode:
            print(f"regen.py: FAILED at {' '.join(command)}")
            return 1
    print("regen.py: OK. Outputs current, model and code checks pass, publication boundary clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

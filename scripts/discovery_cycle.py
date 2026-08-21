#!/usr/bin/env python3
"""Run one bounded source-first refresh, then the #141 completeness gate.

The cycle is intentionally explicit: it never commits or publishes a newly observed record.
Review the immutable run directories and the generated summary before opening a data PR.

    python scripts/discovery_cycle.py --check
    python scripts/discovery_cycle.py --refresh --run-id 20260821T120000Z
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run([sys.executable, *command], cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check retained runs only")
    parser.add_argument("--refresh", action="store_true", help="create one new immutable run")
    parser.add_argument("--run-id", help="YYYYMMDDTHHMMSSZ; required with --refresh")
    args = parser.parse_args()
    if args.check == args.refresh:
        parser.error("choose exactly one of --check or --refresh")
    run_id = args.run_id
    if args.refresh and not run_id:
        run_id = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")
    try:
        if args.refresh:
            run(["scripts/source_adapters.py", "--refresh", "--run-id", run_id])
            run(["scripts/card_discovery.py", "--refresh", "--run-id", run_id])
            run(["scripts/completeness_gate.py"])
        else:
            run(["scripts/source_adapters.py", "--check"])
            run(["scripts/card_discovery.py", "--check"])
            run(["scripts/completeness_gate.py", "--check"])
    except subprocess.CalledProcessError as error:
        return error.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

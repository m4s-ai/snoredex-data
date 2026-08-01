#!/usr/bin/env python3
"""Differential runner for the PowerShell-to-Python migration (Wave 0).

The migration replaces five live PowerShell scripts with Python twins. "The twin is correct"
is not a code review — it is a measurement: run both against the same inputs and compare what
they wrote and what they printed. This is the instrument that takes that measurement, and the
plan in POWERSHELL-MIGRATION-PLAN.md makes an empty diff from it the exit condition for every
later wave.

    python verification/parity.py selftest          # null test: each script against itself
    python verification/parity.py capture           # record golden stdout and artifact hashes
    python verification/parity.py compare a.ps1 b.py

Every run happens inside a throwaway copy of the tracked tree, so a writer under test cannot
touch the real repository. Scripts are located and invoked by suffix, so a `.ps1` and its `.py`
twin are interchangeable arguments to `compare`.

PowerShell is required for anything involving a `.ps1`. It is found on PATH or through
SNOREDEX_PWSH; a missing interpreter is an error rather than a skip, because a parity run that
silently checks nothing is worse than no parity run at all.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "verification" / "parity" / "golden"

# The five live checkers, each pointing at its *current* implementation: everything a CI step or
# the documented recurring workflow reaches. The 61 archived passes and the dormant scripts/
# pipeline are deliberately absent — they are record, not code that runs. Entries move from .ps1
# to .py as the migration lands, so `selftest` keeps proving determinism after the port too.
LIVE = {
    "review_integrity": "verification/review_integrity.py",
    "audit_evidence": "verification/audit_evidence.py",
    "report": "verification/report.py",
    "classify_manual": "verification/classify_manual.py",
    "verify_finish_sources": "verification/verify_finish_sources.ps1",
}

# verify_finish_sources calls TCGCSV live, so it is only as reproducible as the upstream API.
NETWORK = {"verify_finish_sources"}

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# An ISO instant, not a date: release dates like 1999-06-16 are data and must keep comparing
# unequal when they differ. `checkedAt` values are wall-clock and would otherwise make every
# comparison fail for a reason that says nothing about the port.
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?")
TEXT_SUFFIXES = {".json", ".jsonl", ".csv", ".md", ".txt", ".html", ".ps1", ".py", ".js", ".css"}


def die(message: str) -> None:
    print(f"parity: {message}", file=sys.stderr)
    raise SystemExit(2)


def powershell() -> str:
    explicit = os.environ.get("SNOREDEX_PWSH")
    if explicit:
        if not Path(explicit).exists():
            die(f"SNOREDEX_PWSH points at {explicit}, which does not exist")
        return explicit
    found = shutil.which("pwsh") or shutil.which("powershell")
    if not found:
        die("no PowerShell found; install pwsh or set SNOREDEX_PWSH to its path")
    return found


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [name for name in out.stdout.decode("utf-8", "surrogateescape").split("\0") if name]


def isolate(names: list[str], destination: Path) -> None:
    """Copy the working-tree content of every tracked file into a scratch tree.

    Working tree rather than HEAD, so a port can be measured before it is committed. Real copies
    rather than hardlinks: a writer under test truncates its outputs, and a hardlink would carry
    that straight back into the repository.
    """
    for name in names:
        source = ROOT / name
        if not source.is_file():
            continue
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalise_text(text: str, tree: Path) -> str:
    text = ANSI.sub("", text)
    text = text.replace(str(tree), "<TREE>").replace(str(tree).replace("/", "\\"), "<TREE>")
    text = TIMESTAMP.sub("<TIMESTAMP>", text)
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip()


def snapshot(tree: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(tree.rglob("*")):
        if path.is_file():
            files[str(path.relative_to(tree)).replace("\\", "/")] = path.read_bytes()
    return files


def artifact_hashes(before: dict[str, bytes], after: dict[str, bytes], tree: Path) -> dict:
    """What the run changed, hashed both raw and with wall-clock instants neutralised.

    Both figures are reported. `raw` answers "are the bytes identical", which is what the gate
    ultimately needs; `normalised` answers "are they identical apart from the clock", which is
    what tells you whether a difference is a defect or a timestamp.
    """
    changed = {}
    for name in sorted(set(before) | set(after)):
        old, new = before.get(name), after.get(name)
        if old == new:
            continue
        state = "created" if old is None else "deleted" if new is None else "modified"
        entry = {"state": state}
        if new is not None:
            entry["raw"] = digest(new)
            suffix = Path(name).suffix.lower()
            if suffix in TEXT_SUFFIXES:
                try:
                    entry["normalised"] = digest(
                        normalise_text(new.decode("utf-8-sig"), tree).encode("utf-8"))
                except UnicodeDecodeError:
                    entry["normalised"] = entry["raw"]
            else:
                entry["normalised"] = entry["raw"]
        changed[name] = entry
    return changed


def execute(script: str, names: list[str]) -> dict:
    """Run one implementation in its own scratch tree and record everything observable."""
    suffix = Path(script).suffix.lower()
    with tempfile.TemporaryDirectory(prefix="snoredex-parity-") as raw_tree:
        tree = Path(raw_tree)
        isolate(names, tree)
        before = snapshot(tree)
        target = tree / script
        if not target.exists():
            die(f"{script} does not exist in the tracked tree")
        if suffix == ".ps1":
            command = [powershell(), "-NoProfile", "-NonInteractive", "-File", str(target)]
        elif suffix == ".py":
            command = [sys.executable, str(target)]
        else:
            die(f"cannot run {script}: expected a .ps1 or .py file")
        # A Python twin that imports a shared module drops a .pyc next to it, which is not an
        # artifact by any definition its readers would recognise. Suppressed rather than filtered
        # out, so the comparison keeps reporting every file that actually appears. The release
        # gate sets the same variable.
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        completed = subprocess.run(command, cwd=tree, capture_output=True, timeout=900, env=env)
        after = snapshot(tree)
        return {
            "script": script,
            "exit_code": completed.returncode,
            "stdout": normalise_text(completed.stdout.decode("utf-8", "replace"), tree),
            "stderr": normalise_text(completed.stderr.decode("utf-8", "replace"), tree),
            "artifacts": artifact_hashes(before, after, tree),
        }


def compare(left: dict, right: dict) -> tuple[bool, list[str]]:
    """True when the two runs are indistinguishable apart from the clock."""
    findings: list[str] = []
    if left["exit_code"] != right["exit_code"]:
        findings.append(f"exit code {left['exit_code']} vs {right['exit_code']}")
    if left["stdout"] != right["stdout"]:
        findings.append("stdout differs:\n" + first_difference(left["stdout"], right["stdout"]))

    names = sorted(set(left["artifacts"]) | set(right["artifacts"]))
    for name in names:
        a, b = left["artifacts"].get(name), right["artifacts"].get(name)
        if a is None or b is None:
            findings.append(f"{name}: written by only one implementation")
            continue
        if a["state"] != b["state"]:
            findings.append(f"{name}: {a['state']} vs {b['state']}")
        if a.get("normalised") != b.get("normalised"):
            findings.append(f"{name}: content differs beyond timestamps")
    return not findings, findings


def clock_only(left: dict, right: dict) -> list[str]:
    """Artifacts that match once instants are neutralised but differ byte for byte."""
    drifting = []
    for name, a in left["artifacts"].items():
        b = right["artifacts"].get(name)
        if b and a.get("normalised") == b.get("normalised") and a.get("raw") != b.get("raw"):
            drifting.append(name)
    return sorted(drifting)


def first_difference(left: str, right: str) -> str:
    left_lines, right_lines = left.split("\n"), right.split("\n")
    for index in range(max(len(left_lines), len(right_lines))):
        a = left_lines[index] if index < len(left_lines) else "<missing>"
        b = right_lines[index] if index < len(right_lines) else "<missing>"
        if a != b:
            return f"    line {index + 1}\n      left:  {a!r}\n      right: {b!r}"
    return "    (no line-level difference; whitespace only)"


def selected(requested: list[str] | None) -> dict[str, str]:
    if not requested:
        chosen = dict(LIVE)
    else:
        unknown = [name for name in requested if name not in LIVE]
        if unknown:
            die(f"unknown script(s): {', '.join(unknown)}; known: {', '.join(LIVE)}")
        chosen = {name: LIVE[name] for name in requested}
    if os.environ.get("SNOREDEX_PARITY_SKIP_NETWORK"):
        chosen = {name: path for name, path in chosen.items() if name not in NETWORK}
    return chosen


def cmd_selftest(args: argparse.Namespace) -> int:
    """The null test: every live script against a second run of itself.

    An instrument that reports "identical" for two implementations it cannot actually tell apart
    proves nothing. Running each script against itself is the calibration — anything that fails
    here is a fault in the harness or genuine nondeterminism in the script, and both need to be
    known before a single port is written.
    """
    names = tracked_files()
    scripts = selected(args.scripts)
    failures = 0
    for label, script in scripts.items():
        first = execute(script, names)
        second = execute(script, names)
        identical, findings = compare(first, second)
        drifting = clock_only(first, second)
        status = "identical" if identical else "DIFFERS"
        detail = f"exit={first['exit_code']} artifacts={len(first['artifacts'])}"
        if drifting:
            detail += f" clock-only={len(drifting)}"
        print(f"[{status:>9}] {label:<22} {detail}")
        for name in drifting:
            print(f"            not idempotent: {name} differs only in wall-clock instants")
        for finding in findings:
            print(f"            {finding}")
        failures += 0 if identical else 1
    print(f"\n{len(scripts) - failures}/{len(scripts)} scripts reproduce themselves.")
    return 1 if failures else 0


def cmd_capture(args: argparse.Namespace) -> int:
    """Record what the PowerShell does today, before anything moves."""
    names = tracked_files()
    scripts = selected(args.scripts)
    GOLDEN.mkdir(parents=True, exist_ok=True)
    for label, script in scripts.items():
        result = execute(script, names)
        result["platform"] = platform.system().lower()
        destination = GOLDEN / f"{label}.{result['platform']}.json"
        destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
        print(f"captured {label:<22} exit={result['exit_code']} "
              f"artifacts={len(result['artifacts'])} -> {destination.relative_to(ROOT)}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    names = tracked_files()
    left = execute(args.left, names)
    right = execute(args.right, names)
    identical, findings = compare(left, right)
    drifting = clock_only(left, right)
    print(f"{args.left}\n{args.right}\n")
    print(f"exit codes: {left['exit_code']} / {right['exit_code']}")
    print(f"artifacts:  {len(left['artifacts'])} / {len(right['artifacts'])}")
    for name in drifting:
        print(f"clock-only difference: {name}")
    if identical:
        print("\nidentical apart from wall-clock instants.")
        return 0
    print("\ndifferences:")
    for finding in findings:
        print(f"  {finding}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    selftest = sub.add_parser("selftest", help="run each live script against itself")
    selftest.add_argument("scripts", nargs="*", help=f"subset of: {', '.join(LIVE)}")
    selftest.set_defaults(handler=cmd_selftest)

    capture = sub.add_parser("capture", help="record golden output for the live scripts")
    capture.add_argument("scripts", nargs="*", help=f"subset of: {', '.join(LIVE)}")
    capture.set_defaults(handler=cmd_capture)

    compare_parser = sub.add_parser("compare", help="diff two implementations")
    compare_parser.add_argument("left")
    compare_parser.add_argument("right")
    compare_parser.set_defaults(handler=cmd_compare)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

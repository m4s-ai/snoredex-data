#!/usr/bin/env python3
"""Verification memo: skip a gate step whose observed inputs have not changed since it passed (#460).

A step runs once under `memo_trace/sitecustomize.py`, which records every repository file it
opened, every directory it listed, every path whose existence it probed and every Git command it
ran, in Python child processes too. When the step passes and nothing marks it non-memoizable, the
digests of those inputs are stored. A later run that finds every recorded input unchanged reports
the step as unchanged instead of running it again. Anything the tracer cannot see (network, other
programs, Git batch/stdin or write commands, untraced Python children, a check that writes inside
the repository) makes the step non-memoizable, so it always runs.

The memo lives in `<git-common-dir>/snoredex-memo/v1/steps/`, outside the working tree. It is never
evidence; deleting it only costs time. `--memo off` is the reference mode (the Linux L4 lane uses it) and
`--memo refresh` runs every step while rewriting the memo (each push to `main` uses it).

    python scripts/check_memo.py run [--memo use|refresh|off] -- scripts/X.py --check
    python scripts/check_memo.py clear
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TRACER_DIR = Path(__file__).resolve().parent / "memo_trace"
MEMO_VERSION = 1
MAX_AGE_DAYS = 14
MODES = ("use", "refresh", "off")
TRACE_VAR, ROOT_VAR, MODE_VAR = "SNOREDEX_MEMO_TRACE", "SNOREDEX_MEMO_ROOT", "SNOREDEX_MEMO"
ENV_KEYS_PREFIX = ("PYTHON", "SNOREDEX_", "GIT_")
ENV_KEYS_EXACT = ("LANG", "LC_ALL", "LC_CTYPE", "TZ")
ENV_KEYS_EXCLUDED = ("PYTHONPATH", TRACE_VAR, ROOT_VAR, MODE_VAR)
READ_ONLY_GIT = {
    "ls-files", "rev-parse", "show", "log", "rev-list", "cat-file", "diff", "diff-files",
    "diff-index", "diff-tree", "status", "for-each-ref", "ls-tree", "merge-base", "describe",
    "check-attr", "version", "symbolic-ref", "show-ref", "name-rev", "config",
}
CONFIG_READS = {"--get", "--get-all", "--list", "-l"}
ISOLATING_FLAGS = {"-I", "-E", "-S"}
MEMO_PATH_PREFIX = ".git/snoredex-memo"


def store_dir(root: Path) -> Path | None:
    """`<git-common-dir>/snoredex-memo/v1/steps`, or None outside a Git checkout."""
    try:
        common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=root, check=True,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return (root / common.strip()).resolve() / "snoredex-memo" / f"v{MEMO_VERSION}" / "steps"


@functools.lru_cache(maxsize=None)
def engine_digest() -> str:
    """Any change to the memo engine or tracer invalidates every entry."""
    digest = hashlib.sha256()
    for path in (Path(__file__).resolve(), TRACER_DIR / "sitecustomize.py"):
        digest.update(path.read_bytes())
    return digest.hexdigest()


@functools.lru_cache(maxsize=None)
def git_version() -> str:
    try:
        return subprocess.run(["git", "--version"], text=True, stdout=subprocess.PIPE).stdout.strip()
    except OSError:
        return "unavailable"


def key_env(env: dict[str, str]) -> dict[str, str]:
    """The environment variables a gate step may read; the T21 test keeps this list honest."""
    return {
        name: value for name, value in sorted(env.items())
        if (name.startswith(ENV_KEYS_PREFIX) or name in ENV_KEYS_EXACT) and name not in ENV_KEYS_EXCLUDED
    }


def step_key(phase: str, command: list[str], env: dict[str, str]) -> str:
    payload = {"v": MEMO_VERSION, "engine": engine_digest(), "phase": phase, "command": command,
               "python": sys.version, "platform": sys.platform, "git": git_version(), "env": key_env(env)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


class DigestCache:
    """Per-run content digests, re-read whenever a file's size, mtime or inode changes."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._cache: dict[str, tuple[tuple, str]] = {}

    def sha256(self, relative: str) -> str:
        path = self.root / relative
        try:
            info = path.stat()
        except OSError:
            return "missing"
        if path.is_dir():
            return "dir"
        signature = (info.st_size, info.st_mtime_ns, info.st_ino)
        cached = self._cache.get(relative)
        if cached and cached[0] == signature:
            return cached[1]
        with open(path, "rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        self._cache[relative] = (signature, digest)
        return digest

    def clear(self) -> None:
        self._cache.clear()


def probe_state(root: Path, relative: str) -> str:
    try:
        info = (root / relative).stat()
    except OSError:
        return "missing"
    if os.path.isdir(root / relative):
        return "dir"
    return f"file:{info.st_size}" if os.path.isfile(root / relative) else "other"


def listing_digest(root: Path, relative: str) -> str:
    try:
        with os.scandir(root / relative) as entries:
            names = sorted((entry.name, entry.is_dir()) for entry in entries)
    except OSError:
        return "missing"
    return hashlib.sha256(json.dumps(names).encode("utf-8")).hexdigest()


def git_subcommand(argv: list[str]) -> str | None:
    index = 1
    while index < len(argv):
        argument = argv[index]
        if argument == "--version":
            return "version"
        if argument in {"-c", "-C"}:
            index += 2
        elif argument.startswith("-"):
            index += 1
        else:
            return argument
    return None


def git_replayable(argv: list[str]) -> bool:
    subcommand = git_subcommand(argv)
    if subcommand not in READ_ONLY_GIT:
        return False
    if any(argument == "--stdin" or argument.startswith("--batch") for argument in argv):
        return False
    return subcommand != "config" or bool(CONFIG_READS & set(argv))


def is_git(argv: list[str]) -> bool:
    return Path(argv[0]).name.lower() in {"git", "git.exe"}


def is_python(argv: list[str]) -> bool:
    name = Path(argv[0]).name.lower()
    return name.startswith("python") or os.path.abspath(argv[0]) == os.path.abspath(sys.executable)


def touches_root(root: Path, process: dict[str, Any]) -> bool:
    text = os.path.normcase(str(root))
    cwd = os.path.normcase(os.path.abspath(process["cwd"]))
    return cwd == text or cwd.startswith(text + os.sep) or any(text in os.path.normcase(argument) for argument in process["argv"])


def replay_digest(root: Path, process: dict[str, Any]) -> str:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    for name in (TRACE_VAR, ROOT_VAR):
        env.pop(name, None)
    result = subprocess.run(process["argv"], cwd=root / process["cwd"], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return hashlib.sha256(result.stdout + b"\0" + str(result.returncode).encode()).hexdigest()


def merge_traces(trace_dir: Path) -> dict[str, Any]:
    merged: dict[str, Any] = {"reads": set(), "writes": set(), "lists": set(), "probes": set(),
                              "procs": [], "events": set()}
    traces = sorted(trace_dir.glob("*.json"))
    for path in traces:
        record = json.loads(path.read_text(encoding="utf-8"))
        for name in ("reads", "writes", "lists", "probes", "events"):
            merged[name].update(record.get(name, []))
        merged["procs"].extend(record.get("procs", []))
    merged["traceCount"] = len(traces)
    merged["forkCount"] = len(list(trace_dir.glob("*.forked")))
    return merged


def _process_problem(root: Path, process: dict[str, Any]) -> str | None:
    argv = process["argv"]
    if is_python(argv):
        traced = process["envTraced"] and not ISOLATING_FLAGS & set(argv[1:])
        return None if traced else "untraced python child"
    if not is_git(argv):
        return f"runs {Path(argv[0]).name}"
    if touches_root(root, process) and not git_replayable(argv):
        return f"git {git_subcommand(argv)} is not replayable"
    return None


def assess(merged: dict[str, Any], phase: str, root: Path) -> str | None:
    """Why this traced run must not be memoized, or None when it may be."""
    if merged["events"]:
        return "uses " + "/".join(sorted(merged["events"]))
    for process in merged["procs"]:
        problem = _process_problem(root, process)
        if problem:
            return problem
    children = sum(1 for process in merged["procs"] if is_python(process["argv"]))
    if merged["traceCount"] != 1 + children + merged["forkCount"]:
        return "trace missing for a child process"
    if phase == "check" and merged["writes"]:
        return "check wrote inside the repository"
    return None


def source_for_bytecode(path: str) -> str | None:
    """`pkg/__pycache__/mod.cpython-311.pyc` -> `pkg/mod.py`: a cached import still depends on its source."""
    parent, _, name = ("/" + path).rpartition("/__pycache__/")
    parent = parent.lstrip("/")
    if not _ or not name.endswith(".pyc"):
        return None
    return f"{parent}/{name.split('.', 1)[0]}.py" if parent else f"{name.split('.', 1)[0]}.py"


def _inputs(merged: dict[str, Any]) -> set[str]:
    reads = {path for path in merged["reads"] if not path.startswith(MEMO_PATH_PREFIX)}
    return reads | {source for source in map(source_for_bytecode, reads) if source}


def _git_replays(root: Path, merged: dict[str, Any]) -> list[dict[str, Any]]:
    replays = []
    for process in merged["procs"]:
        if is_git(process["argv"]) and touches_root(root, process):
            relative = os.path.relpath(os.path.abspath(process["cwd"]), root).replace(os.sep, "/")
            entry = {"argv": process["argv"], "cwd": relative}
            entry["digest"] = replay_digest(root, entry)
            replays.append(entry)
    return replays


def build_entry(root: Path, merged: dict[str, Any], phase: str, command: list[str],
                digests: DigestCache) -> dict[str, Any]:
    inputs = _inputs(merged)
    entry = {
        "memoVersion": MEMO_VERSION,
        "createdAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "phase": phase,
        "command": command,
        "inputs": {path: digests.sha256(path) for path in sorted(inputs)},
        "listings": {path: listing_digest(root, path) for path in sorted(merged["lists"])},
        "probes": {path: probe_state(root, path) for path in sorted(merged["probes"] - inputs)},
        "git": _git_replays(root, merged),
        "outputs": {},
    }
    if phase == "write":
        written = {path for path in merged["writes"] if (root / path).is_file()}
        entry["outputs"] = {path: digests.sha256(path) for path in sorted(written)}
    return entry


def _fresh(entry: dict[str, Any]) -> bool:
    try:
        created = dt.datetime.fromisoformat(entry["createdAt"])
    except (KeyError, TypeError, ValueError):
        return False
    age = dt.datetime.now(dt.timezone.utc) - created
    return entry.get("memoVersion") == MEMO_VERSION and age <= dt.timedelta(days=MAX_AGE_DAYS)


def is_current(root: Path, entry: dict[str, Any], digests: DigestCache) -> bool:
    """Cheap comparisons first; the first difference ends the check."""
    if not _fresh(entry):
        return False
    if any(probe_state(root, path) != state for path, state in entry["probes"].items()):
        return False
    if any(listing_digest(root, path) != state for path, state in entry["listings"].items()):
        return False
    if any(replay_digest(root, replay) != replay["digest"] for replay in entry["git"]):
        return False
    files = {**entry["inputs"], **entry["outputs"]}
    return all(digests.sha256(path) == digest for path, digest in files.items())


def read_entry(path: Path) -> dict[str, Any] | None:
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    required = {"createdAt", "inputs", "listings", "probes", "git", "outputs"}
    return entry if isinstance(entry, dict) and required <= set(entry) else None


def write_entry(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(entry, sort_keys=True), encoding="utf-8", newline="\n")
    os.replace(temporary, path)


@dataclass
class StepOutcome:
    returncode: int
    output: str | None
    hit: dict[str, Any] | None
    reason: str | None


def run_command(root: Path, command: list[str], env: dict[str, str], capture: bool) -> tuple[int, str | None]:
    options: dict[str, Any] = {}
    if capture:
        options = {"text": True, "encoding": "utf-8", "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT}
    process = subprocess.run([sys.executable, *command], cwd=root, env=env, **options)
    return process.returncode, process.stdout if capture else None


class MemoSession:
    """One gate run's view of the memo: lookups, traced execution, staged entries, final commit."""

    def __init__(self, root: Path, mode: str = "use", store: Path | None = None) -> None:
        self.root = Path(root).resolve()
        nested = TRACE_VAR in os.environ  # an outer step's tracer owns this process tree
        self.mode = "off" if nested or os.environ.get(MODE_VAR) == "off" else mode
        self.store = store if store is not None else (store_dir(self.root) if self.mode != "off" else None)
        if self.store is None:
            self.mode = "off"
        self.digests = DigestCache(self.root)
        self.pending: list[tuple[str, dict[str, Any]]] = []
        self.deferred: list[tuple[str, list[str], dict[str, Any], str]] = []
        self.counts: Counter[str] = Counter()
        self.reasons: dict[str, str] = {}
        self.lock = threading.Lock()  # regen.py runs observational steps in parallel threads

    def _entry_path(self, phase: str, command: list[str], env: dict[str, str]) -> Path:
        return self.store / f"{step_key(phase, command, env)[:40]}.json"

    def lookup(self, phase: str, command: list[str], env: dict[str, str]) -> dict[str, Any] | None:
        if self.mode != "use":
            return None
        entry = read_entry(self._entry_path(phase, command, env))
        return entry if entry and is_current(self.root, entry, self.digests) else None

    def traced_env(self, env: dict[str, str], trace_dir: Path) -> dict[str, str]:
        traced = dict(env)
        traced[TRACE_VAR], traced[ROOT_VAR] = str(trace_dir), str(self.root)
        traced["PYTHONDONTWRITEBYTECODE"] = "1"  # a traced step must not write bytecode into the checkout
        existing = env.get("PYTHONPATH")
        traced["PYTHONPATH"] = str(TRACER_DIR) + (os.pathsep + existing if existing else "")
        return traced

    def execute(self, phase: str, command: list[str], env: dict[str, str], capture: bool = False) -> StepOutcome:
        hit = self.lookup(phase, command, env)
        with self.lock:
            self.counts["skipped" if hit is not None else "executed"] += 1
        if hit is not None:
            return StepOutcome(0, None, hit, None)
        if self.mode == "off":
            return StepOutcome(*run_command(self.root, command, env, capture), None, None)
        with tempfile.TemporaryDirectory(prefix="snoredex-memo-") as folder:
            returncode, output = run_command(self.root, command, self.traced_env(env, Path(folder)), capture)
            merged = merge_traces(Path(folder))
        reason = f"exit {returncode}" if returncode else assess(merged, phase, self.root)
        staged = build_entry(self.root, merged, phase, command, self.digests) \
            if reason is None and phase == "check" else None
        with self.lock:
            self._stage(phase, command, env, merged, reason, staged)
        return StepOutcome(returncode, output, None, reason)

    def _stage(self, phase: str, command: list[str], env: dict[str, str], merged: dict[str, Any],
               reason: str | None, staged: dict[str, Any] | None) -> None:
        path = str(self._entry_path(phase, command, env))
        if phase == "write":
            self.digests.clear()  # a generator may have rewritten anything it read before
        if reason is not None:
            if not reason.startswith("exit "):
                self.reasons[" ".join(command)] = reason
            return
        if phase == "write":
            self.deferred.append((path, command, merged, phase))
        else:
            self.pending.append((path, staged))

    def commit(self, full_success: bool) -> None:
        """Write passed observational entries; generator entries only after a fully green run."""
        if self.mode == "off":
            return
        entries = list(self.pending)
        if full_success:
            self.digests.clear()
            entries += [(path, build_entry(self.root, merged, phase, command, self.digests))
                        for path, command, merged, phase in self.deferred]
        for path, entry in entries:
            write_entry(Path(path), entry)
        self.prune()

    def prune(self) -> None:
        limit = dt.datetime.now().timestamp() - MAX_AGE_DAYS * 86400
        for path in self.store.glob("*.json") if self.store.is_dir() else []:
            if path.stat().st_mtime < limit:
                path.unlink(missing_ok=True)

    def summary(self) -> str:
        reasons = "; ".join(f"{command}: {reason}" for command, reason in sorted(self.reasons.items()))
        text = (f"memo ({self.mode}): {self.counts['skipped']} unchanged and skipped, "
                f"{self.counts['executed']} executed, {len(self.reasons)} not memoizable")
        return text + (f" ({reasons})" if reasons else "")


def hit_line(label: str, hit: dict[str, Any]) -> str:
    return (f"--- {label}: memo hit, unchanged since {hit['createdAt']} "
            f"({len(hit['inputs'])} inputs) - skipped")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Split at "--" ourselves: argparse.REMAINDER swallows options before it on Python 3.11.
    command = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     usage="%(prog)s {run,clear} [--memo MODE] [-- script.py [arguments]]")
    parser.add_argument("action", choices=("run", "clear"))
    parser.add_argument("--memo", choices=MODES, default="use")
    args = parser.parse_args(argv)
    if args.action == "clear":
        store = store_dir(ROOT)
        if store is not None:
            shutil.rmtree(store, ignore_errors=True)
        return 0
    if not command:
        parser.error("run needs -- script.py [arguments]")
    session = MemoSession(ROOT, args.memo)
    outcome = session.execute("check", command, dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if outcome.hit is not None:
        print(hit_line(" ".join(command), outcome.hit))
    session.commit(full_success=outcome.returncode == 0)
    print(session.summary())
    return outcome.returncode


if __name__ == "__main__":
    raise SystemExit(main())

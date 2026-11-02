#!/usr/bin/env python3
"""Regression checks for the verification memo (#460, cases T1-T21).

Every case runs real traced child processes in a throwaway Git repository. A step appends one line
to a counter file outside that repository whenever it actually runs, so "skipped" is observable.
"""
from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_memo as memo  # noqa: E402

# An outer gate step's tracer must not turn this test's own sessions off.
for _name in (memo.TRACE_VAR, memo.ROOT_VAR, memo.MODE_VAR):
    os.environ.pop(_name, None)

COUNTER_PREFIX = "import os\nopen(os.environ['MEMO_TEST_COUNTER'], 'a').write('x\\n')\n"
NETWORK_EVENTS = "socket.getaddrinfo('localhost', None)"
# Environment variables read outside the gate steps; they never reach a memoized command.
ENV_EXCEPTIONS = {
    "verification/gate_manifest.py": {"GITHUB_SHA", "GITHUB_WORKFLOW", "GITHUB_RUN_ID", "RUNNER_OS"},
}


class Repo:
    def __init__(self, folder: Path) -> None:
        self.root = folder / "repo"
        self.root.mkdir()
        self.store = folder / "store"
        self.counter = folder / "counter.txt"
        self.git("init", "-q")
        self.git("config", "user.email", "test" + "@" + "users.noreply.github.com")
        self.git("config", "user.name", "test")
        (self.root / "data.txt").write_text("one\n", encoding="utf-8")
        (self.root / "listed").mkdir()
        self.commit()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, check=True, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout

    def commit(self) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", "fixture")

    def step(self, name: str, body: str) -> str:
        (self.root / f"{name}.py").write_text(COUNTER_PREFIX + body + "\n", encoding="utf-8")
        return f"{name}.py"

    def runs(self) -> int:
        return len(self.counter.read_text(encoding="utf-8").splitlines()) if self.counter.exists() else 0

    def run(self, script: str, phase: str = "check", mode: str = "use", success: bool = True):
        session = memo.MemoSession(self.root, mode, store=self.store)
        before = self.runs()
        env = dict(os.environ, MEMO_TEST_COUNTER=str(self.counter))
        outcome = session.execute(phase, [script], env, capture=True)
        session.commit(full_success=success and outcome.returncode == 0)
        return self.runs() - before, outcome


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def cases_inputs(repo: Repo) -> None:
    reader = repo.step("reader", "open('data.txt').read()")
    check(repo.run(reader)[0] == 1 and repo.run(reader)[0] == 0, "T1 unchanged inputs are skipped")
    (repo.root / "data.txt").write_text("two\n", encoding="utf-8")
    check(repo.run(reader)[0] == 1, "T2 a changed input runs again")
    prober = repo.step("prober", "from pathlib import Path\nPath('maybe.txt').exists()")
    repo.run(prober)
    (repo.root / "maybe.txt").write_text("now\n", encoding="utf-8")
    check(repo.run(prober)[0] == 1, "T3 a probed path that appears runs again")
    lister = repo.step("lister", "os.listdir('listed')")
    repo.run(lister)
    (repo.root / "listed" / "new.txt").write_text("x", encoding="utf-8")
    check(repo.run(lister)[0] == 1, "T4 a listed directory that gains a file runs again")
    head = repo.step("head", "import subprocess\nsubprocess.run(['git', 'rev-parse', 'HEAD'], check=True)")
    repo.run(head)
    repo.commit()
    check(repo.run(head)[0] == 1, "T5 a replayed Git command with new output runs again")


def never_stored(repo: Repo, script: str, label: str, phase: str = "check") -> None:
    first, outcome = repo.run(script, phase)
    second, _ = repo.run(script, phase)
    check(first == 1 and second == 1 and outcome.reason is not None, label)


def cases_unsafe(repo: Repo) -> None:
    child = "import subprocess, sys\n"
    never_stored(repo, repo.step("untraced", child + "env = {k: v for k, v in os.environ.items() "
                 "if k != 'SNOREDEX_MEMO_TRACE'}\nsubprocess.run([sys.executable, '-c', 'pass'], env=env)"),
                 "T6 an untraced python child is never memoized")
    never_stored(repo, repo.step("isolated", child + "subprocess.run([sys.executable, '-I', '-c', 'pass'])"),
                 "T7 an isolated python child is never memoized")
    other = "['cmd', '/c', 'exit 0']" if os.name == "nt" else "['sh', '-c', 'true']"
    never_stored(repo, repo.step("foreign", child + f"subprocess.run({other})"),
                 "T8 a foreign program is never memoized")
    never_stored(repo, repo.step("writer", "open('written.txt', 'w').write('x')"),
                 "T9 a check that writes inside the repository is never memoized")
    never_stored(repo, repo.step("failing", "raise SystemExit(1)"), "T10 a failing step is never stored")
    never_stored(repo, repo.step("network", "import socket\n" + NETWORK_EVENTS),
                 "T18 network use is never memoized")
    if hasattr(os, "fork"):
        never_stored(repo, repo.step("forker", "pid = os.fork()\nif pid == 0:\n    os._exit(0)\nos.waitpid(pid, 0)"),
                     "T19 a forked child without a trace is never memoized")


def only_entry(repo: Repo) -> Path:
    entries = sorted(repo.store.glob("*.json"), key=lambda path: path.stat().st_mtime)
    return entries[-1]


def cases_store(repo: Repo) -> None:
    steady = repo.step("steady", "open('data.txt').read()")
    repo.run(steady)
    only_entry(repo).write_text("{broken", encoding="utf-8")
    check(repo.run(steady)[0] == 1, "T11 a corrupt entry is a miss, not a crash")
    entry_path = only_entry(repo)
    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    entry["createdAt"] = "2000-01-01T00:00:00+00:00"
    entry_path.write_text(json.dumps(entry), encoding="utf-8")
    check(repo.run(steady)[0] == 1, "T12 an entry older than MAX_AGE_DAYS is a miss")
    original = memo.engine_digest
    memo.engine_digest = lambda: "another engine"
    try:
        check(repo.run(steady)[0] == 1, "T13 a different engine digest is a miss")
    finally:
        memo.engine_digest = original
    check(repo.run(steady, mode="refresh")[0] == 1 and repo.run(steady)[0] == 0,
          "T16 refresh runs and rewrites the entry")
    count = len(list(repo.store.glob("*.json")))
    probe = repo.step("offmode", "open('data.txt').read()")
    check(repo.run(probe, mode="off")[0] == 1 and len(list(repo.store.glob("*.json"))) == count,
          "T16 off never writes the memo")


def cases_session(repo: Repo) -> None:
    os.environ[memo.TRACE_VAR] = "outer"
    try:
        check(memo.MemoSession(repo.root, "use", store=repo.store).mode == "off",
              "T14 a nested run inside a traced step is off")
    finally:
        os.environ.pop(memo.TRACE_VAR)
    default = memo.store_dir(repo.root)
    check(default is not None and ".git" in default.parts, "T15 the default store is inside .git")
    generator = repo.step("generator", "open('out.txt', 'w').write(open('data.txt').read())")
    repo.run(generator, phase="write", success=False)
    check(repo.run(generator, phase="write")[0] == 1, "T17 no write entry without a fully green run")
    check(repo.run(generator, phase="write")[0] == 0, "T17 a fully green run stores the write entry")
    (repo.root / "out.txt").write_text("edited by hand\n", encoding="utf-8")
    check(repo.run(generator, phase="write")[0] == 1, "T17 a changed output runs the generator again")
    database = repo.root / "store.sqlite"
    with contextlib.closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("create table t (v)")
    reader = repo.step("sqlitereader", "import sqlite3\nsqlite3.connect('store.sqlite').execute('select 1').fetchall()")
    repo.run(reader)
    with contextlib.closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("insert into t values (1)")
    check(repo.run(reader)[0] == 1, "T20 a changed SQLite input runs again")


ENV_READ = re.compile(r"""(?:os\.environ\.get|os\.getenv|getenv)\(\s*["']([A-Z0-9_]+)["']|os\.environ\[\s*["']([A-Z0-9_]+)["']\s*\]""")


def case_cli(repo: Repo) -> None:
    script = repo.step("cli", "pass")
    original_root = memo.ROOT
    memo.ROOT = repo.root
    try:
        env_before = os.environ.get("MEMO_TEST_COUNTER")
        os.environ["MEMO_TEST_COUNTER"] = str(repo.counter)
        before = repo.runs()
        check(memo.main(["run", "--memo", "off", "--", script, "--flag"]) == 0 and repo.runs() == before + 1,
              "T23 the CLI accepts --memo before -- on every supported Python")
    finally:
        memo.ROOT = original_root
        if env_before is None:
            os.environ.pop("MEMO_TEST_COUNTER", None)


def case_windows_command_lines() -> None:
    spec = importlib.util.spec_from_file_location("memo_tracer", memo.TRACER_DIR / "sitecustomize.py")
    tracer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tracer)  # inert: SNOREDEX_MEMO_TRACE is not set here
    argv = ["git", "show", "abc:path with space.json", 'quote"d']
    line = subprocess.list2cmdline(argv)
    check(tracer.argv_list(line, {line: argv}) == argv, "T24 a Windows command line maps back to its arguments")
    check(tracer.argv_list(argv, {}) == argv, "T24 a POSIX argument list passes through")
    check(tracer.argv_list("cmd /c dir", {}) == ["cmd", "/c", "dir"], "T24 an unknown shell string stays foreign")


def case_bytecode() -> None:
    check(memo.source_for_bytecode("scripts/__pycache__/regen.cpython-311.pyc") == "scripts/regen.py"
          and memo.source_for_bytecode("__pycache__/top.cpython-313.pyc") == "top.py"
          and memo.source_for_bytecode("scripts/regen.py") is None,
          "T22 a cached bytecode read depends on its source file")
    merged = {"reads": {"scripts/__pycache__/x.cpython-311.pyc"}}
    check("scripts/x.py" in memo._inputs(merged), "T22 the source joins the recorded inputs")


def case_environment() -> None:
    allowed = memo.key_env
    unexpected = []
    for path in sorted([*ROOT.glob("scripts/*.py"), *ROOT.glob("verification/*.py")]):
        relative = path.relative_to(ROOT).as_posix()
        for match in ENV_READ.finditer(path.read_text(encoding="utf-8")):
            name = match.group(1) or match.group(2)
            covered = name in ENV_EXCEPTIONS.get(relative, set()) or name in memo.ENV_KEYS_EXCLUDED
            if not covered and not allowed({name: ""}) and not name.startswith("MEMO_TEST"):
                unexpected.append(f"{relative}: {name}")
    check(not unexpected, f"T21 every environment variable a step reads is in the memo key: {unexpected}")


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        repo = Repo(Path(folder))
        cases_inputs(repo)
        cases_unsafe(repo)
        cases_store(repo)
        cases_session(repo)
        case_cli(repo)
    case_bytecode()
    case_windows_command_lines()
    case_environment()
    print("check memo passed: T1-T24 (inputs, probes, listings, Git replays, unsafe steps, "
          "store integrity, sessions, generators, SQLite, environment key, bytecode sources, CLI, Windows command lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

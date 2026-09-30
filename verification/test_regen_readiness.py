"""regen.py readiness: a stale artifact must make --check fail.

Regression for #213: the whole point of the single command is that a stale
derived artifact is caught before merge, not after three CI restarts. This test
stales two regenerated artifacts, asserts the selected `regen.py --check-only`
determinism pass catches both in an isolated temporary directory. The complete L3
suite is covered by the normal `regen.py --check` invocation; this meta-test does not
start that suite a second time.
"""
from __future__ import annotations

import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGEN = pathlib.Path("scripts/regen.py")
sys.path.insert(0, str(ROOT / "scripts"))
import regen as regen_module  # noqa: E402

# Two small deterministic artifacts make the aggregation guarantee observable without
# touching SQLite or depending on a network response.
TARGETS = [
    (ROOT / "verification" / "evidence_semantics.json",
     b'"units": ', b'"units": 999999, "stale": '),
    (ROOT / "verification" / "authoritative_graph.json",
     b'"schemaVersion": "1.1.0"', b'"schemaVersion": "0.0.0"'),
]


def run_aggregation_regressions() -> None:
    """Child failures, including P6, must share one non-green exit path."""
    original_regen = regen_module.REGEN
    original_check = regen_module.CHECK
    original_tests = regen_module.TESTS
    original_run = regen_module.subprocess.run
    original_argv = sys.argv

    def invoke(fake_run: object) -> tuple[int, str, str]:
        regen_module.subprocess.run = fake_run  # type: ignore[assignment]
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = regen_module.main()
        finally:
            regen_module.subprocess.run = original_run
        return code, stdout.getvalue(), stderr.getvalue()

    try:
        sys.argv = [str(REGEN)]
        regen_module.REGEN = []
        regen_module.CHECK = []
        regen_module.TESTS = [["verification/review_findings.py"]]

        def p6_failure(cmd: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess:
            if cmd[-1] == "verification/review_findings.py":
                return subprocess.CompletedProcess(cmd, 1, "[FAIL] P6 simulated history failure\n")
            return original_run(cmd, *args, **kwargs)

        code, stdout, stderr = invoke(p6_failure)
        assert code == 1
        assert "[FAIL] P6 simulated history failure" in stdout
        assert "FAILED verification/review_findings.py" in stderr
        assert "regen.py: OK" not in stdout
        assert "CI gate is green" not in stderr

        regen_module.REGEN = [["missing-step"]]
        regen_module.TESTS = []

        def missing_step(cmd: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess:
            if cmd[-1] == "missing-step":
                return subprocess.CompletedProcess(cmd, 1)
            return original_run(cmd, *args, **kwargs)

        code, _, stderr = invoke(missing_step)
        assert code == 1
        assert "FAILED regenerating missing-step" in stderr

        regen_module.REGEN = []
        code, stdout, stderr = invoke(original_run)
        assert code == 0
        assert "regen.py: OK. Generated artifacts and core regressions are current." in stdout
        assert not stderr
    finally:
        regen_module.REGEN = original_regen
        regen_module.CHECK = original_check
        regen_module.TESTS = original_tests
        regen_module.subprocess.run = original_run
        sys.argv = original_argv


def check_writes(scratch: pathlib.Path) -> None:
    tracked = scratch / "tracked.txt"
    tracked.write_text("original")
    subprocess.run(["git", "add", "tracked.txt"], cwd=scratch, check=True)
    tracked.write_text("pre-existing dirty edit")
    untracked = scratch / "untracked.txt"
    untracked.write_text("before")
    mutations = [
        "p=Path('tracked.txt'); s=p.stat(); os.utime(p, ns=(s.st_atime_ns, s.st_mtime_ns+2000000000))",
        "Path('untracked.txt').write_text('after')",
        "Path('new.txt').write_text('created')",
        "Path('tracked.txt').unlink()",
    ]
    with patch.multiple(regen_module, ROOT=scratch, REGEN=[], CHECK=[], TESTS=[]), \
            patch.object(sys, "argv", ["regen.py", "--check"]):
        def invoke() -> tuple[int, str]:
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                code = regen_module.main()
            return code, output.getvalue()

        before = regen_module.tree_state()
        assert invoke()[0] == 0
        assert regen_module.tree_state() == before
        for phase in ("CHECK", "TESTS"):
            for mutation in mutations:
                for exit_code in (0, 1):
                    tracked.write_text("pre-existing dirty edit")
                    untracked.write_text("before")
                    (scratch / "new.txt").unlink(missing_ok=True)
                    command = ["-c", "import os; from pathlib import Path; "
                               + mutation + f"; raise SystemExit({exit_code})"]
                    with patch.object(regen_module, phase, [command]):
                        code, output = invoke()
                    assert code == 1 and "Read-only gate changed" in output, (phase, mutation, output)
                    assert "regen.py: OK" not in output


def check_stale_artifacts(scratch: pathlib.Path) -> None:
    targets = {
        "scripts/evidence_semantics.py": ("OUTPUT_PATH", "evidence_semantics.json"),
        "scripts/authoritative_graph.py": ("OUTPUT", "authoritative_graph.json"),
    }
    originals = [(path, path.read_bytes(), path.stat().st_mtime_ns) for path, _, _ in TARGETS]
    for path, original, _ in originals:
        (scratch / path.name).write_bytes(original)
    original_run = regen_module.run

    def isolated_run(cmd: list[str], label: str) -> bool:
        attribute, name = targets[cmd[1]]
        script = (
            "import pathlib, sys; "
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r}); "
            f"import {pathlib.Path(cmd[1]).stem} as module; "
            f"module.{attribute} = pathlib.Path({str(scratch / name)!r}); "
            "sys.argv = [sys.argv[0], '--check']; raise SystemExit(module.main())"
        )
        return original_run([sys.executable, "-c", script], label)

    with patch.multiple(regen_module, ROOT=scratch, TESTS=[]), \
            patch.object(regen_module, "run", isolated_run), \
            patch.object(sys, "argv", ["regen.py", "--check", "--check-only",
                                      "scripts/evidence_semantics.py", "--check-only",
                                      "scripts/authoritative_graph.py"]):
        assert regen_module.main() == 0
        for path, marker, replacement in TARGETS:
            target = scratch / path.name
            original = target.read_bytes()
            corrupted = original.replace(marker, replacement, 1)
            assert corrupted != original, f"stale-artifact marker missing in {path}"
            target.write_bytes(corrupted)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = regen_module.main()
        assert code == 1 and "FAILED determinism checks:" in output.getvalue()
        assert all(f"{script} --check" in output.getvalue() for script in targets)
        assert "Read-only gate changed" not in output.getvalue()
    assert all((path.read_bytes(), path.stat().st_mtime_ns) == (original, mtime)
               for path, original, mtime in originals)

    # Input-derived dates are a behavior, not a required spelling in generator source.
    import evidence_semantics
    for date in ("2001-01-01", "2099-12-31"):
        report = evidence_semantics.build([], [], {"decisions": [], "meta": {"generated": date}},
                                          {"sourceRecords": []})
        assert report["meta"]["generated"] == date


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        scratch = pathlib.Path(directory)
        subprocess.run(["git", "init", "-q"], cwd=scratch, check=True)
        with patch.object(regen_module, "ROOT", scratch):
            run_aggregation_regressions()
        check_writes(scratch)
        check_stale_artifacts(scratch)
    print("regen readiness passed: stale artifacts, child failures and read-only CHECK/TESTS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

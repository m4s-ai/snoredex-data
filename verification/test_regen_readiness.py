"""regen.py readiness: a stale artifact must make --check fail.

Regression for #213: the whole point of the single command is that a stale
derived artifact is caught before merge, not after three CI restarts. This test
stales two regenerated artifacts, asserts the selected `regen.py --check-only`
determinism pass catches both, then restores them. The complete L3 suite is
covered by the normal `regen.py --check` invocation; this meta-test does not
start that suite a second time.
"""
from __future__ import annotations

import contextlib
import io
import pathlib
import subprocess
import sys

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
INPUT_DATE_MARKERS = {
    ROOT / "scripts" / "source_registry.py": "generated = latest_input_date(",
    ROOT / "scripts" / "source_capabilities.py": 'str(manifest["meta"]["reviewedAt"])[:10]',
    ROOT / "scripts" / "evidence_semantics.py": "generated = max(",
    ROOT / "scripts" / "checklist.py": "generated = max(",
    ROOT / "scripts" / "finishes.py": "generated_date = latest_input_date(",
}


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8",
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


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


def main() -> int:
    run_aggregation_regressions()
    for path, marker in INPUT_DATE_MARKERS.items():
        source = path.read_text(encoding="utf-8")
        if "date.today()" in source or marker not in source:
            print(f"FAIL: {path.relative_to(ROOT)} does not derive its write date from inputs")
            return 1
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
        proc = run([
            sys.executable, str(REGEN), "--check",
            "--check-only", "scripts/evidence_semantics.py",
            "--check-only", "scripts/authoritative_graph.py",
        ])
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

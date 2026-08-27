"""Regression tests for the active-Python cyclomatic-complexity guard."""

from __future__ import annotations

import ast
import pathlib
import tempfile

from complexity import DEFAULT_CEILING, FunctionMetric, _ComplexityVisitor, format_report, scan

ROOT = pathlib.Path(__file__).resolve().parent.parent


def metric(source: str, name: str) -> int:
    tree = ast.parse(source)
    function = next(node for node in ast.walk(tree)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == name)
    visitor = _ComplexityVisitor(function)
    visitor.visit(function)
    return visitor.score


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"[ok ] {label}")


def main() -> int:
    fixture = """
def outer(value, rows):
    def inner(flag):
        if flag:
            return 1
        return 0
    assert value
    if value and (value > 1 or value < -1):
        result = [row for row in rows if row]
    else:
        result = (row for row in rows)
    for row in result:
        while row:
            break
    try:
        match value:
            case 0:
                pass
            case _:
                raise ValueError
    except ValueError:
        return lambda x: x or value
    return result

"""
    check("all AST branch forms are counted", metric(fixture, "outer") == 12)
    check("nested functions are scored independently", metric(fixture, "outer") == 12)
    check("nested function score is independent", metric(fixture, "inner") == 2)
    check("default ceiling is ten", DEFAULT_CEILING == 10)

    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        (root / "scripts").mkdir()
        (root / "verification").mkdir()
        (root / "verification" / "archive").mkdir()
        (root / "verification" / "passes").mkdir()
        def nested_ifs(name: str, count: int) -> str:
            return f"def {name}(x):\n" + "".join(
                f"{'    ' * (index + 1)}if x:\n" for index in range(count)
            ) + f"{'    ' * (count + 1)}pass\n"

        (root / "scripts" / "active.py").write_text(
            nested_ifs("eleven", 10), encoding="utf-8"
        )
        (root / "verification" / "test_excluded.py").write_text(
            nested_ifs("test_bad", 20), encoding="utf-8"
        )
        (root / "verification" / "archive" / "old.py").write_text(
            nested_ifs("old", 20), encoding="utf-8"
        )
        (root / "verification" / "passes" / "old.py").write_text(
            nested_ifs("old", 20), encoding="utf-8"
        )
        (root / "verification" / "complexity_baseline.json").write_text(
            '{"exceptions": {}}', encoding="utf-8"
        )
        metrics, failures, _, _ = scan(root)
        check("new CC 11 fails", any("active.py::eleven" in failure for failure in failures))
        check("test/archive/pass files are excluded", not any("old" in failure for failure in failures))

        (root / "verification" / "complexity_baseline.json").write_text(
            '{"exceptions": {"scripts/active.py::eleven": 11}}', encoding="utf-8"
        )
        _, failures, _, _ = scan(root)
        check("allowlisted score passes", not failures)
        (root / "scripts" / "active.py").write_text(
            nested_ifs("eleven", 11), encoding="utf-8"
        )
        _, failures, _, _ = scan(root)
        check("allowlisted score increase fails", any("exceeds 11" in failure for failure in failures))
        (root / "verification" / "complexity_baseline.json").write_text(
            '{"exceptions": {"scripts/active.py::eleven": 12, "scripts/gone.py::gone": 11}}',
            encoding="utf-8",
        )
        (root / "scripts" / "active.py").write_text(
            nested_ifs("eleven", 10), encoding="utf-8"
        )
        _, failures, tightening, removed = scan(root)
        check("lower score is non-blocking", not failures)
        check("lowered and removed exceptions are reported", tightening and removed)

    check("CC 10 passes", metric("def ten(x):\n" + "    if x: pass\n" * 9, "ten") == 10)
    report = format_report(
        [FunctionMetric("x.py", "f", 2, 1)], [], ["x.py::f: 4 -> 2"], ["y.py::gone: removed"]
    )
    check("tightening and removal are reported", "[TIGHTEN]" in "\n".join(report)
          and "[REMOVED]" in "\n".join(report))
    metrics, failures, tightening, removed = scan(ROOT)
    for line in format_report(metrics, failures, tightening, removed):
        print(line)
    check("active baseline has no regressions", not failures)
    print("complexity guard fixtures passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

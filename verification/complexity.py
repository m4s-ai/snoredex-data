"""Deterministic cyclomatic-complexity measurement for the active Python surface."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CEILING = 10
BASELINE_PATH = Path(__file__).with_name("complexity_baseline.json")


@dataclass(frozen=True)
class FunctionMetric:
    path: str
    qualified_name: str
    complexity: int
    line: int

    @property
    def key(self) -> str:
        return f"{self.path}::{self.qualified_name}"


class _ComplexityVisitor(ast.NodeVisitor):
    """Count branches in one function without folding nested functions into it."""

    def __init__(self, root: ast.AST) -> None:
        self.root = root
        self.score = 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node is self.root:
            self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_If(self, node: ast.If) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.score += 1
        self.generic_visit(node)

    visit_AsyncFor = visit_For

    def visit_While(self, node: ast.While) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.score += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        self.score += len(node.cases)
        self.generic_visit(node)


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.stack: list[str] = []
        self.metrics: list[FunctionMetric] = []

    def _record(self, node: ast.AST, name: str) -> None:
        qualified_name = ".".join((*self.stack, name))
        visitor = _ComplexityVisitor(node)
        visitor.visit(node)
        self.metrics.append(FunctionMetric(
            self.path, qualified_name, visitor.score, getattr(node, "lineno", 0)
        ))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record(node, node.name)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()


def active_paths(root: Path) -> list[Path]:
    scripts = sorted((root / "scripts").rglob("*.py"))
    verification = sorted((root / "verification").glob("*.py"))
    return [path for path in (*scripts, *verification) if not path.name.startswith("test_")]


def collect_metrics(path: Path, root: Path) -> list[FunctionMetric]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    relative = path.relative_to(root).as_posix()
    collector = _FunctionCollector(relative)
    collector.visit(tree)
    return collector.metrics


def load_baseline(path: Path = BASELINE_PATH) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): int(value) for key, value in payload["exceptions"].items()}


def scan(
    root: Path, baseline_path: Path | None = None
) -> tuple[list[FunctionMetric], list[str], list[str], list[str]]:
    baseline = load_baseline(baseline_path or root / "verification" / "complexity_baseline.json")
    metrics = [metric for path in active_paths(root) for metric in collect_metrics(path, root)]
    current = {metric.key: metric.complexity for metric in metrics}
    failures = [
        f"{metric.key} CC {metric.complexity} exceeds "
        f"{baseline.get(metric.key, DEFAULT_CEILING)}"
        for metric in metrics
        if metric.complexity > baseline.get(metric.key, DEFAULT_CEILING)
    ]
    tightening = [
        f"{key}: {value} -> {current[key]}"
        for key, value in sorted(baseline.items())
        if key in current and current[key] < value
    ]
    removed = [f"{key}: removed" for key in sorted(set(baseline) - set(current))]
    return metrics, failures, tightening, removed


def format_report(
    metrics: list[FunctionMetric], failures: list[str], tightening: list[str], removed: list[str]
) -> list[str]:
    active = [metric for metric in metrics if metric.complexity > DEFAULT_CEILING]
    lines = [
        f"complexity guard: {len(metrics)} active functions; "
        f"max CC={max((metric.complexity for metric in metrics), default=0)}; "
        f"exceptions={len(active)}",
    ]
    lines.extend(f"[FAIL] {failure}" for failure in failures)
    lines.extend(f"[TIGHTEN] {note}" for note in tightening)
    lines.extend(f"[REMOVED] {note}" for note in removed)
    return lines

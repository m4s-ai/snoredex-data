#!/usr/bin/env python3
"""Measure incremental and full retained-run discovery cost.

The diagnostic keeps parser, retained raw-response I/O and projection timing separate. It reads
immutable runs only and prints JSON; it never rewrites a staging artifact or creates a cache.
"""

from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import sys
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.projection_runs import select_projection_run_ids  # noqa: E402


class Measurement:
    """Temporarily instrument one adapter without changing its production API."""

    def __init__(self, module):
        self.module = module
        self.active: dict[str, Any] | None = None
        self.original_read_bytes = pathlib.Path.read_bytes
        self.original_build = module.build_projection
        self.parser_names = (
            ("parse_response",)
            if module.__name__.endswith("source_adapters")
            else ("parse_list", "parse_detail")
        )
        self.original_parsers = {
            name: getattr(module, name) for name in self.parser_names
        }

    def reset(self) -> dict[str, Any]:
        self.active = {
            "rawReadBytes": 0, "rawReadSeconds": 0.0,
            "parserCalls": 0, "parserSeconds": 0.0,
            "projectionCalls": 0, "projectionSeconds": 0.0,
        }
        return self.active

    def read_bytes(self, path: pathlib.Path) -> bytes:
        started = time.perf_counter()
        value = self.original_read_bytes(path)
        if self.active is not None and path.is_relative_to(self.module.RUNS_DIR):
            self.active["rawReadBytes"] += len(value)
            self.active["rawReadSeconds"] += time.perf_counter() - started
        return value

    def build(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        started = time.perf_counter()
        result = self.original_build(*args, **kwargs)
        self.active["projectionCalls"] += 1
        self.active["projectionSeconds"] += time.perf_counter() - started
        return result

    def parser(self, name: str):
        original = self.original_parsers[name]

        def wrapped(*args: Any, **kwargs: Any):
            started = time.perf_counter()
            result = original(*args, **kwargs)
            self.active["parserCalls"] += 1
            self.active["parserSeconds"] += time.perf_counter() - started
            return result

        return wrapped

    def __enter__(self):
        pathlib.Path.read_bytes = lambda path: self.read_bytes(path)
        self.module.build_projection = self.build
        for name in self.parser_names:
            setattr(self.module, name, self.parser(name))
        return self

    def __exit__(self, *_args: Any) -> None:
        pathlib.Path.read_bytes = self.original_read_bytes
        self.module.build_projection = self.original_build
        for name, original in self.original_parsers.items():
            setattr(self.module, name, original)


def measure_adapter(module_name: str, identity: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    module = importlib.import_module(module_name)
    contract_data = module.load_inputs()
    contract, capability = contract_data[:2]
    identity_value = identity if identity is not None else (
        contract_data[2] if module_name.endswith("card_discovery") else None
    )
    latest_id = module.newest_compatible_complete_run(contract, capability)
    if latest_id is None:
        raise RuntimeError(f"{module_name} has no compatible complete run")
    retained = [path.name for path in module.run_directories()]
    with Measurement(module) as measurement:
        reports = []
        for full_refresh in (False, True):
            selected = select_projection_run_ids(retained, latest_id, full_refresh)
            active = measurement.reset()
            started = time.perf_counter()
            if module_name.endswith("source_adapters"):
                module.build_latest(contract, capability, full_refresh=full_refresh)
            else:
                module.build_latest(contract, capability, identity_value, full_refresh=full_refresh)
            active["totalSeconds"] = time.perf_counter() - started
            reports.append({
                "adapter": module_name.rsplit(".", 1)[-1],
                "mode": "full-refresh" if full_refresh else "incremental",
                "retainedRuns": len(retained),
                "projectedRuns": selected,
                **{key: round(value, 4) if isinstance(value, float) else value
                   for key, value in active.items()},
            })
        return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = measure_adapter("scripts.source_adapters")
    report.extend(measure_adapter("scripts.card_discovery"))
    print(json.dumps({"schema": "snoredex-discovery-runtime", "version": "1.0.0", "runs": report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

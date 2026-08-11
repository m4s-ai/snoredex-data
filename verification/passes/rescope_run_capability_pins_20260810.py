#!/usr/bin/env python3
"""Re-pin the retained runs to the surfaces they actually used (#147).

The capability pin covered the whole graph, so a run expired whenever *any* provider's capabilities
moved — including providers it had never fetched from. Measured before the change: declaring one
locale-archive surface on `pokemon-official` took the graph from 23 coverage edges to 24, and both
retained runs then failed with `captured under another capability graph`, although the set-adapter
run touched only `tcgdex` and the card-discovery run only `pokemon-card-asia`.

That made the capability graph unable to grow without discarding run history, which is the blocker
`RESUME.md` records against the publisher's per-locale card archive. `capability_pin` is now
computed over the slice a run depends on. This pass migrates the two manifests written under the old
rule.

WHAT CHANGES, AND WHY THAT IS NOT AN EDIT TO AN IMMUTABLE RUN

Only two fields move, and neither is evidence:

* `capabilityGraphHash` — recomputed over the run's own surfaces;
* `capabilityGraphSurfaces` — added, so validation reconstructs the same slice instead of inferring
  it, and so a manifest states its own pin scope.

Every raw response, every `responseHash`, every parsed record hash and the entire `requests` array
are untouched. `N12` hashes the raw bytes against the manifest and is what "immutable run" protects;
a validation field that says which capabilities the run was captured under is metadata about that
evidence, not the evidence.

The pin does not get weaker. A surface the run used still cannot move without expiring it — that is
the property worth having. A surface it never touched no longer can, which is the defect.

    python verification/passes/rescope_run_capability_pins_20260810.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import source_adapters as adapters  # noqa: E402

CAPABILITY = ROOT / "verification" / "source_capability_graph.json"
RUN_ROOTS = (
    ROOT / "verification" / "runs" / "source-adapters",
    ROOT / "verification" / "runs" / "card-discovery",
)

BASIS = (
    "capability contract for the surfaces this run used — their providers, surfaces, coverage "
    "edges, observations and meta.schemaVersion. meta.generated and sourceResolution are excluded "
    "because neither is a capability, and pinning them expired the run on a date change or a "
    "single new citation. The slice is scoped to capabilityGraphSurfaces because pinning the whole "
    "graph expired a run whenever an unrelated provider gained a surface, which made the graph "
    "unable to grow without discarding history."
)


def main() -> int:
    capability = json.loads(CAPABILITY.read_text(encoding="utf-8"))

    changed = 0
    for root in RUN_ROOTS:
        for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            path = run_dir / "manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            surfaces = adapters.surfaces_used(manifest["requests"])
            if not surfaces:
                print(f"{run_dir.name}: no request names a surface", file=sys.stderr)
                return 1

            before_raw = json.dumps(manifest["requests"], sort_keys=True)
            pinned = adapters.capability_pin(capability, surfaces)
            if manifest.get("capabilityGraphSurfaces") == surfaces \
                    and manifest.get("capabilityGraphHash") == pinned:
                continue

            manifest["capabilityGraphHash"] = pinned
            manifest["capabilityGraphSurfaces"] = surfaces
            manifest["capabilityGraphHashBasis"] = BASIS
            # The evidence must come through untouched; this is the assertion, not a comment.
            if json.dumps(manifest["requests"], sort_keys=True) != before_raw:
                print(f"{run_dir.name}: requests changed", file=sys.stderr)
                return 1

            path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
            changed += 1
            print(f"{run_dir.name}: pinned to {', '.join(surfaces)}")

    print(f"re-pinned {changed} run manifest(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

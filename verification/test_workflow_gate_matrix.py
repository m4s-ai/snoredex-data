"""Keep the workflow gate matrix internally consistent and cycle-free."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "verification" / "workflow_gate_matrix.json"


def main() -> int:
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    levels = data["gateLevels"]
    ordered = sorted(levels, key=lambda key: levels[key]["order"])
    assert ordered == ["L0", "L1", "L2", "L3", "L4"]
    assert levels["L3"]["mergeRequired"] is True
    assert levels["L4"]["releaseRequired"] is True
    assert levels["L0"]["network"] is False
    assert levels["L3"]["network"] is False

    impacts = data["impactClasses"]
    for impact_id, impact in impacts.items():
        assert impact["minimumGate"] in levels, impact_id
        assert impact["projectionGate"] in levels, impact_id
        assert impact["mergeGate"] == "L3", impact_id
        assert impact["canonicalStores"], impact_id
        assert impact["graphEntityTypes"], impact_id
        assert impact["graphRelations"], impact_id
        assert isinstance(impact["projectionRoots"], list), impact_id

    workflows = data["workflows"]
    workflow_ids = {workflow["id"] for workflow in workflows}
    assert len(workflow_ids) == len(workflows)
    for workflow in workflows:
        assert workflow["impactClass"] in impacts, workflow["id"]
        assert workflow["minimumGate"] in levels, workflow["id"]
        assert workflow["projectionGate"] in levels, workflow["id"]
        assert workflow["mergeGate"] == "L3", workflow["id"]
        assert workflow["releaseGate"] == "L4", workflow["id"]
        assert levels[workflow["minimumGate"]]["order"] \
            <= levels[workflow["projectionGate"]]["order"] \
            <= levels[workflow["mergeGate"]]["order"] \
            <= levels[workflow["releaseGate"]]["order"], workflow["id"]
        assert workflow["forbiddenShortcuts"], workflow["id"]
        assert set(workflow["dependsOn"]).issubset(workflow_ids), workflow["id"]

    adjacency = {workflow_id: [] for workflow_id in workflow_ids}
    for workflow in workflows:
        adjacency[workflow["id"]].extend(workflow["dependsOn"])

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        assert node not in visiting, f"workflow dependency cycle at {node}"
        if node in visited:
            return
        visiting.add(node)
        for dependency in adjacency[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for workflow_id in workflow_ids:
        visit(workflow_id)

    dependency_sources = [dependency["from"] for dependency in data["graphDependencies"]]
    assert len(dependency_sources) == len(set(dependency_sources))
    impact_ids = set(dependency_sources)
    assert impact_ids == set(impacts), impact_ids ^ set(impacts)
    for dependency in data["graphDependencies"]:
        assert set(dependency["to"]).issubset(impacts), dependency["from"]
        assert dependency["reason"].strip(), dependency["from"]

    print(f"workflow gate matrix regression passed: {len(workflows)} workflows, "
          f"{len(impacts)} impact classes, {len(data['graphDependencies'])} graph dependencies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

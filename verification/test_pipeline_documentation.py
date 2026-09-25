#!/usr/bin/env python3
"""Keep active pipeline documentation and deployment orchestration aligned."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

from review_findings import documentation_inventory


ROOT = Path(__file__).resolve().parent.parent
ACTIVE_MARKDOWN = tuple(
    ROOT / relative
    for relative, document in documentation_inventory().items()
    if document["stage"] != "history"
) + (ROOT / "llms.txt", ROOT / "LICENSES" / "README.md")
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "release-gate.yml",
    ROOT / ".github" / "workflows" / "pages.yml",
    ROOT / ".github" / "workflows" / "ui-pr.yml",
)
SCRIPT_REF = re.compile(r"(?<![\w/])((?:scripts|verification)/[\w./-]+\.(?:py|ps1))\b")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
RUNTIME_LINKS = {(ROOT / "llms.txt", "collector_deployment.json")}


def workflow_routes(text: str) -> list[list[str]]:
    """Read the one six-column routing table in section 4, not incidental prose IDs."""
    heading = "## 4. Use-case contracts\n"
    assert text.count(heading) == 1, "missing or duplicate workflow routing section"
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    table = [line for line in section.splitlines() if line.startswith("|")]
    assert table and table[0].startswith("| Task / intent | Registered workflow / lane | Skill |")
    rows = [list(map(str.strip, line.strip("|").split("|"))) for line in table[2:]]
    assert rows and all(len(row) == 6 and all(row) for row in rows), "malformed workflow route"
    return rows


def route_registration(cell: str) -> tuple[str | None, str | None]:
    if cell == "—":
        return None, None
    match = re.fullmatch(r"`workflow:([a-z0-9-]+)`(?: / `lane:([a-z0-9-]+)`)?", cell)
    assert match, f"invalid route registration: {cell}"
    return match.group(1), match.group(2)


def check_route_targets(row: list[str], root: Path) -> set[str]:
    skill_paths = MARKDOWN_LINK.findall(row[2])
    assert skill_paths, f"route has no linked skill: {row[0]}"
    for path in skill_paths:
        assert re.fullmatch(r"\.agents/skills/[a-z0-9-]+/SKILL\.md", path), path
        assert (root / path).is_file(), f"missing route skill: {path}"
        skill = (root / path).read_text(encoding="utf-8")
        assert re.search(rf"^name: {re.escape(Path(path).parent.name)}$", skill, re.MULTILINE), path
    for target in MARKDOWN_LINK.findall(" ".join(row)):
        assert not target.startswith(("http:", "https:")), f"route targets must be local: {target}"
        assert (root / unquote(target.split("#", 1)[0])).is_file(), f"missing route target: {target}"
    scripts = set(SCRIPT_REF.findall(row[3]))
    assert all((root / script).is_file() for script in scripts), f"missing entry script: {scripts}"
    return scripts


def check_workflow_routes(text: str, matrix: dict, manifest: dict, root: Path) -> list[list[str]]:
    workflows = {item["id"]: item for item in matrix["workflows"]}
    lanes = {item["id"]: item for item in manifest["lanes"]}
    seen_workflows, seen_lanes = set(), set()
    rows = workflow_routes(text)
    for row in rows:
        workflow_id, lane_id = route_registration(row[1])
        scripts = check_route_targets(row, root)
        if workflow_id is None:
            continue
        assert workflow_id in workflows, f"unknown workflow: {workflow_id}"
        assert workflow_id not in seen_workflows, f"duplicate workflow route: {workflow_id}"
        seen_workflows.add(workflow_id)
        impact = workflows[workflow_id]["impactClass"]
        owners = set(matrix["impactClasses"][impact]["projectionRoots"])
        assert not owners or scripts & owners, f"route lacks workflow owner: {workflow_id}"
        if lane_id is not None:
            assert lane_id in lanes, f"unknown lane: {lane_id}"
            lane = lanes[lane_id]
            assert impact in lane["impactClasses"], f"incompatible workflow/lane: {row[1]}"
            entry_scripts = set(SCRIPT_REF.findall(lane["entry"]))
            entry_scripts.update(step["command"][0] for step in lane["steps"])
            assert scripts & entry_scripts, f"route lacks lane entry: {lane_id}"
            seen_lanes.add(lane_id)
    assert seen_workflows == set(workflows), f"unrouted workflows: {set(workflows) - seen_workflows}"
    assert seen_lanes == set(lanes), f"unrouted lanes: {set(lanes) - seen_lanes}"
    return rows

def routing_regressions() -> None:
    """Exercise registration and target drift without scanning arbitrary Python files."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="snoredex-routing-") as directory:
        root = Path(directory)
        skill_path = ".agents/skills/example/SKILL.md"
        for path, content in {
            skill_path: "---\nname: example\ndescription: Fixture workflow.\n---\n",
            "scripts/example.py": "# registered owner\n",
        }.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        row = (
            "| Example | `workflow:example` / `lane:example` | "
            f"[example]({skill_path}) | [owner](scripts/example.py) | Observation | Review |\n"
        )
        text = (
            "## 4. Use-case contracts\n\n"
            "| Task / intent | Registered workflow / lane | Skill | Canonical entry | Graph impact | Required boundary |\n"
            "|---|---|---|---|---|---|\n" + row
        )
        matrix = {
            "workflows": [{"id": "example", "impactClass": "example"}],
            "impactClasses": {"example": {"projectionRoots": ["scripts/example.py"]}},
        }
        manifest = {"lanes": [{
            "id": "example", "impactClasses": ["example"], "entry": "scripts/example.py",
            "steps": [{"command": ["scripts/example.py", "--check"]}],
        }]}

        def check(document: str = text) -> None:
            check_workflow_routes(document, matrix, manifest, root)

        def rejects(document: str, expected: str) -> None:
            try:
                check(document)
            except AssertionError as error:
                assert expected in str(error), str(error)
            else:
                raise AssertionError(f"routing regression accepted: {expected}")

        check()
        rejects(text.replace("`workflow:example` / `lane:example`", "—")
                + "\nworkflow:example lane:example\n", "unrouted workflows")
        rejects(text.replace(" / `lane:example`", "")
                + "\nlane:example\n", "unrouted lanes")
        rejects(text + row, "duplicate workflow")
        rejects(text.replace("workflow:example", "workflow:unknown"), "unknown workflow")
        rejects(text.replace("lane:example", "lane:unknown"), "unknown lane")
        rejects(text.replace("[owner](scripts/example.py)", "No owner"), "lacks workflow owner")
        rejects(text.replace(f"[example]({skill_path})", "example"), "no linked skill")

        matrix["workflows"].append({"id": "new", "impactClass": "example"})
        rejects(text, "unrouted workflows")
        check(text + row.replace("workflow:example", "workflow:new"))
        matrix["workflows"].pop()

        manifest["lanes"][0]["impactClasses"] = ["other"]
        rejects(text, "incompatible workflow/lane")
        manifest["lanes"][0]["impactClasses"] = ["example"]
        manifest["lanes"][0]["entry"] = "scripts/other.py"
        manifest["lanes"][0]["steps"] = []
        rejects(text, "lacks lane entry")
        manifest["lanes"][0]["entry"] = "scripts/example.py"

        for path, expected in ((skill_path, "missing route skill"),
                               ("scripts/example.py", "missing route target")):
            target = root / path
            renamed = target.with_suffix(".renamed")
            target.rename(renamed)
            rejects(text, expected)
            renamed.rename(target)
            rejects(text.replace(path, path + ".missing"), path)
        (root / skill_path).write_text("---\nname: renamed\n---\n", encoding="utf-8")
        rejects(text, skill_path)
        (root / skill_path).write_text("---\nname: example\n---\n", encoding="utf-8")
        (root / "scripts" / "helper.py").write_text("# not an operator entry\n", encoding="utf-8")
        check()


def main() -> int:
    texts = {path: path.read_text(encoding="utf-8") for path in ACTIVE_MARKDOWN + WORKFLOWS}

    missing: set[str] = set()
    for path, text in texts.items():
        for reference in SCRIPT_REF.findall(text):
            if not (ROOT / reference).is_file():
                missing.add(f"{path.relative_to(ROOT)} -> {reference}")
    if missing:
        raise SystemExit("active documentation references missing scripts:\n" + "\n".join(sorted(missing)))

    dead_links: set[str] = set()
    for path in ACTIVE_MARKDOWN:
        for raw_target in MARKDOWN_LINK.findall(texts[path]):
            target = raw_target.strip().strip("<>").split(maxsplit=1)[0]
            if target.startswith(("#", "http://", "https://", "mailto:", "data:")):
                continue
            relative = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if (
                relative
                and not (path.parent / relative).exists()
                and (path, relative) not in RUNTIME_LINKS
            ):
                dead_links.add(f"{path.relative_to(ROOT)} -> {target}")
    if dead_links:
        raise SystemExit("active documentation has dead relative links:\n" + "\n".join(sorted(dead_links)))

    workflow_map = texts[ROOT / "WORKFLOW-MAP.md"]
    routes = check_workflow_routes(
        workflow_map,
        json.loads((ROOT / "verification" / "workflow_gate_matrix.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "verification" / "scoped_pipeline_manifest.json").read_text(encoding="utf-8")),
        ROOT,
    )
    routing_regressions()

    for entry in ("AGENTS.md", "HANDOVER.md"):
        assert "WORKFLOW-MAP.md#4-use-case-contracts" in MARKDOWN_LINK.findall(texts[ROOT / entry]), entry
    # The data-workflow table is bounded; unmatched repository tasks still need discoverable skills.
    assert ".agents/skills/" in MARKDOWN_LINK.findall(texts[ROOT / "AGENTS.md"]), (
        "AGENTS.md must retain the skill-directory fallback for tasks outside the routing table"
    )
    operator_section = texts[ROOT / "llms.txt"].split("## Repository operators\n", 1)[1].split("\n## ", 1)[0]
    operator_targets = set(MARKDOWN_LINK.findall(operator_section))
    github_base = "https://github.com/m4s-ai/snoredex-data/blob/main/"
    assert {
        github_base + "AGENTS.md", github_base + "WORKFLOW-MAP.md#4-use-case-contracts",
    } <= operator_targets, "operator links must reach the repository rules and route from the published llms.txt"
    for target in operator_targets:
        assert target.startswith(github_base), target
        relative = target.removeprefix(github_base).split("#", 1)[0]
        assert (ROOT / relative).is_file(), target
    assert "scripts/regen.py` owns the ordered" in workflow_map
    assert "### D. Manual Pages deployment lane" in workflow_map
    assert "scripts/regen.py" in texts[ROOT / "README.md"]
    assert "WORKFLOW-MAP.md" in texts[ROOT / "AGENTS.md"]
    # AGENTS.md is canonical; CLAUDE.md must stay a thin @AGENTS.md shim, never a rules copy.
    shim = texts[ROOT / "CLAUDE.md"]
    assert "@AGENTS.md" in shim, "CLAUDE.md must import AGENTS.md"
    assert not any(l.startswith("## ") for l in shim.splitlines()), (
        "CLAUDE.md must not duplicate AGENTS.md section rules"
    )
    assert "scripts/regen.py" in texts[ROOT / "HANDOVER.md"]
    active_text = "\n".join(texts[path] for path in ACTIVE_MARKDOWN)
    assert "prioritised backlog" not in active_text
    assert "current backlog" not in active_text
    assert "source-first rebuild is tracked" not in active_text
    assert "no rows are recorded yet" not in active_text.lower()
    assert "verification/test_evidence_application.py" not in workflow_map
    assert "verification/verification" not in active_text
    workflow_loop = (ROOT / "scripts" / "workflow_loop.py").read_text(encoding="utf-8")
    discovery_contract = " ".join("\n".join((
        workflow_map,
        texts[ROOT / ".agents" / "skills" / "snoredex-source-refresh" / "SKILL.md"],
        texts[ROOT / "verification" / "RECURRENCE.md"],
        workflow_loop,
        next(
            loop["retry"]
            for loop in json.loads((ROOT / "verification" / "workflow_loop_manifest.json").read_text(
                encoding="utf-8",
            ))["loops"]
            if loop["id"] == "discovery"
        ),
    )).split())
    assert "explicit unresolved decision" not in discovery_contract
    assert "reconcile-to-release-or-record-open-decision" not in discovery_contract
    assert "reconcile-by-reviewed-mapping-or-positive-exclusion" in discovery_contract
    assert discovery_contract.count("no separate unresolved-disposition record") == 3
    assert "Unresolved identities remain new-candidate" in discovery_contract
    assert "Generated by scripts/site.py" in (ROOT / "index.html").read_text(encoding="utf-8")

    pages = texts[ROOT / ".github" / "workflows" / "pages.yml"]
    ui = texts[ROOT / ".github" / "workflows" / "ui-pr.yml"]
    lane = workflow_map.split("### D. Manual Pages deployment lane", 1)[1].split("### E.", 1)[0]
    lane_commands = re.findall(r"scripts/[\w.-]+\.py(?:\s+--reproject)?", lane)
    assert lane_commands, "Pages lane has no commands in WORKFLOW-MAP.md"
    for command in lane_commands:
        assert f"python {command}" in pages, f"Pages workflow drifted from documented lane: {command}"
    assert "verified Pages artifact" in pages
    assert "uses: ./.github/workflows/release-gate.yml" in pages
    assert "audit_evidence.py" not in "\n".join(texts.values())
    assert "name: UI browser gate" in ui
    assert "paths:" in ui and "site/app.css" in ui and "site/app.js" in ui
    assert "requirements.txt" in ui
    assert "llms.txt" in ui
    assert "verification/test_site.py" in ui
    assert "python verification/test_site.py" in ui

    print(
        f"pipeline documentation contract passed: {len(ACTIVE_MARKDOWN)} active documents, "
        f"{len(lane_commands)} Pages commands, {len(routes)} workflow routes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

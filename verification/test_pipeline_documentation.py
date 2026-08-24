#!/usr/bin/env python3
"""Keep active pipeline documentation and deployment orchestration aligned."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ACTIVE_DOCS = (
    ROOT / "README.md",
    ROOT / "CLAUDE.md",
    ROOT / "HANDOVER.md",
    ROOT / "WORKFLOW-MAP.md",
    ROOT / ".github" / "workflows" / "release-gate.yml",
    ROOT / ".github" / "workflows" / "pages.yml",
)
SCRIPT_REF = re.compile(r"(?<![\w/])((?:scripts|verification)/[\w./-]+\.py)\b")


def main() -> int:
    texts = {path: path.read_text(encoding="utf-8") for path in ACTIVE_DOCS}

    missing: set[str] = set()
    for path, text in texts.items():
        for reference in SCRIPT_REF.findall(text):
            if "/archive/" not in reference and not (ROOT / reference).is_file():
                missing.add(f"{path.relative_to(ROOT)} -> {reference}")
    if missing:
        raise SystemExit("active documentation references missing scripts:\n" + "\n".join(sorted(missing)))

    workflow_map = texts[ROOT / "WORKFLOW-MAP.md"]
    assert "scripts/regen.py` owns the ordered" in workflow_map
    assert "### D. Manual Pages deployment lane" in workflow_map
    assert "scripts/regen.py" in texts[ROOT / "README.md"]
    assert "WORKFLOW-MAP.md" in texts[ROOT / "CLAUDE.md"]
    assert "scripts/regen.py" in texts[ROOT / "HANDOVER.md"]

    pages = texts[ROOT / ".github" / "workflows" / "pages.yml"]
    lane = workflow_map.split("### D. Manual Pages deployment lane", 1)[1].split("### E.", 1)[0]
    lane_commands = re.findall(r"scripts/[\w.-]+\.py(?:\s+--reproject)?", lane)
    assert lane_commands, "Pages lane has no commands in WORKFLOW-MAP.md"
    for command in lane_commands:
        assert f"python {command}" in pages, f"Pages workflow drifted from documented lane: {command}"
    assert "deployment-only Pages projection lane" in pages
    assert "uses: ./.github/workflows/release-gate.yml" in pages
    assert "audit_evidence.py" not in "\n".join(texts.values())

    print(f"pipeline documentation contract passed: {len(ACTIVE_DOCS)} active files, {len(lane_commands)} Pages commands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

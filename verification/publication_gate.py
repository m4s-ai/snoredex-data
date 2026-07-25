#!/usr/bin/env python3
"""Require explicit owner approval before an irreversible public deployment (#5, #11)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECISIONS = ROOT / "publication-decisions.json"


def main() -> int:
    try:
        decision = json.loads(DECISIONS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"publication approval unavailable: {error}", file=sys.stderr)
        return 1

    required_true = {
        "sitePublicationApproved",
        "licenseGrantsApproved",
        "ownerAttestationsApproved",
        "thirdPartyImagesApproved",
    }
    problems = [f"{key} must be true" for key in sorted(required_true) if decision.get(key) is not True]

    if decision.get("licensor") not in {"m4s-ai", "contributors to snoredex-data"}:
        problems.append("licensor must name an approved project licensor")
    if not decision.get("approvedBy"):
        problems.append("approvedBy must identify the approving repository owner")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(decision.get("approvedAt") or "")):
        problems.append("approvedAt must be an ISO date")

    visibility = decision.get("repositoryVisibility")
    if visibility not in {"private", "public"}:
        problems.append("repositoryVisibility must be private or public")
    if visibility == "public" and decision.get("repositoryPublicationApproved") is not True:
        problems.append("repositoryPublicationApproved must be true before public visibility")

    if problems:
        print("publication remains blocked:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"publication approved by {decision['approvedBy']} on {decision['approvedAt']}")
    print(f"repository visibility decision: {visibility}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
